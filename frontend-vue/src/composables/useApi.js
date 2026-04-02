import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import router from '@/router'

// API_URL: en producción viene de Cloudflare Pages env vars
const API_BASE = import.meta.env.VITE_API_URL || '/api'
// Token de acceso compartido para despliegue en HF Spaces (vacío en dev local)
const ACCESS_TOKEN = import.meta.env.VITE_ACCESS_TOKEN || ''

async function handleResponse(res) {
  const contentType = res.headers.get('content-type') || ''

  if (contentType.includes('application/pdf') || contentType.includes('application/octet-stream')) {
    if (!res.ok) throw new Error(`Error ${res.status}: ${res.statusText}`)
    return res.blob()
  }

  if (contentType.includes('application/json')) {
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.detail || data.message || `Error ${res.status}`)
    }
    return data
  }

  const text = await res.text()
  if (!res.ok) throw new Error(text || `Error ${res.status}`)
  return text
}

function getHeaders(isJson = true) {
  const auth = useAuthStore()
  const headers = {}
  if (isJson) headers['Content-Type'] = 'application/json'
  if (auth.token) headers['Authorization'] = `Bearer ${auth.token}`
  if (ACCESS_TOKEN) headers['X-Access-Token'] = ACCESS_TOKEN
  return headers
}

function handleAuthError(error) {
  const { showToast } = useToast()
  const auth = useAuthStore()

  const is401 = error.message.includes('401') || error.message.toLowerCase().includes('token') || error.message.toLowerCase().includes('no autorizado')
  if (is401) {
    showToast('Sesión expirada. Iniciando sesión nuevamente.', 'error')
    setTimeout(() => {
      auth.clearSession()
      router.push({ name: 'login' })
    }, 1500)
  }
}

export function useApi() {
  async function get(endpoint, params = {}) {
    try {
      const url = new URL(API_BASE + endpoint, window.location.origin)
      Object.entries(params).forEach(([k, v]) => {
        if (v !== null && v !== undefined) url.searchParams.append(k, v)
      })
      const res = await fetch(url.toString(), { headers: getHeaders(false) })
      return await handleResponse(res)
    } catch (error) {
      handleAuthError(error)
      throw error
    }
  }

  async function post(endpoint, data = {}) {
    try {
      const res = await fetch(API_BASE + endpoint, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(data)
      })
      return await handleResponse(res)
    } catch (error) {
      handleAuthError(error)
      throw error
    }
  }

  async function put(endpoint, data = {}) {
    try {
      const res = await fetch(API_BASE + endpoint, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify(data)
      })
      return await handleResponse(res)
    } catch (error) {
      handleAuthError(error)
      throw error
    }
  }

  async function del(endpoint) {
    try {
      const res = await fetch(API_BASE + endpoint, {
        method: 'DELETE',
        headers: getHeaders(false)
      })
      return await handleResponse(res)
    } catch (error) {
      handleAuthError(error)
      throw error
    }
  }

  async function postFormData(endpoint, formData) {
    try {
      const auth = useAuthStore()
      const headers = {}
      if (auth.token) headers['Authorization'] = `Bearer ${auth.token}`
      const res = await fetch(API_BASE + endpoint, {
        method: 'POST',
        headers,
        body: formData
      })
      return await handleResponse(res)
    } catch (error) {
      handleAuthError(error)
      throw error
    }
  }

  async function download(endpoint, filename) {
    const auth = useAuthStore()
    const res = await fetch(API_BASE + endpoint, {
      headers: { Authorization: `Bearer ${auth.token}` }
    })
    if (!res.ok) throw new Error(`Error ${res.status}`)
    const blob = await res.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  }

  return { get, post, put, del, postFormData, download }
}
