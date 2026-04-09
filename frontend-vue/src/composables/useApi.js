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
      const err = new Error(data.detail || data.message || `Error ${res.status}`)
      err.status = res.status
      throw err
    }
    return data
  }

  const text = await res.text()
  if (!res.ok) {
    const err = new Error(text || `Error ${res.status}`)
    err.status = res.status
    throw err
  }
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

// ── Auto-refresh en 401: intenta refrescar el token y reintentar ─────────
let isRefreshing = false
let refreshPromise = null

async function tryRefreshToken() {
  if (isRefreshing) return refreshPromise
  isRefreshing = true
  refreshPromise = (async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) return false
      const headers = { 'Content-Type': 'application/json' }
      if (ACCESS_TOKEN) headers['X-Access-Token'] = ACCESS_TOKEN
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ refresh_token: refreshToken })
      })
      if (res.ok) {
        const data = await res.json()
        const auth = useAuthStore()
        auth.token = data.access_token
        localStorage.setItem('token', data.access_token)
        if (data.user) {
          auth.user = data.user
          localStorage.setItem('usuario', JSON.stringify(data.user))
        }
        return true
      }
      // refresh_token expirado/inválido: limpiar para que no se reintente
      localStorage.removeItem('refresh_token')
      return false
    } catch { return false }
    finally { isRefreshing = false }
  })()
  return refreshPromise
}

async function fetchWithRetry(url, options = {}) {
  let res = await fetch(url, options)
  if (res.status !== 401) return res

  // Intentar renovar el token
  const refreshed = await tryRefreshToken()
  if (!refreshed) {
    // Refresh falló — señalizar que la sesión expiró de verdad
    const err = new Error('Sesión expirada. Por favor inicie sesión nuevamente.')
    err.status = 401
    err.isAuthFailed = true
    throw err
  }

  // Reintentar con el nuevo token
  const newHeaders = { ...options.headers }
  const auth = useAuthStore()
  if (auth.token) newHeaders['Authorization'] = `Bearer ${auth.token}`
  return fetch(url, { ...options, headers: newHeaders })
}

function handleAuthError(error) {
  const { showToast } = useToast()
  const auth = useAuthStore()

  // Solo limpiar sesión y redirigir si el refresh realmente falló
  if (error?.isAuthFailed) {
    showToast('Sesión expirada. Por favor inicie sesión nuevamente.', 'error')
    setTimeout(() => {
      auth.clearSession()
      router.push({ name: 'login' })
    }, 1500)
  }
  // Para otros errores 401 (retry después de refresh también falló),
  // NO borrar la sesión — el componente maneja el error normalmente
}

export function useApi() {
  async function get(endpoint, params = {}) {
    try {
      const url = new URL(API_BASE + endpoint, window.location.origin)
      Object.entries(params).forEach(([k, v]) => {
        if (v !== null && v !== undefined) url.searchParams.append(k, v)
      })
      const res = await fetchWithRetry(url.toString(), { headers: getHeaders(false) })
      return await handleResponse(res)
    } catch (error) {
      handleAuthError(error)
      throw error
    }
  }

  async function post(endpoint, data = {}) {
    try {
      const res = await fetchWithRetry(API_BASE + endpoint, {
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
      const res = await fetchWithRetry(API_BASE + endpoint, {
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
      const res = await fetchWithRetry(API_BASE + endpoint, {
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
      if (ACCESS_TOKEN) headers['X-Access-Token'] = ACCESS_TOKEN
      const res = await fetchWithRetry(API_BASE + endpoint, {
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
    // Usa fetchWithRetry para manejar token expirado igual que get/post/put
    const res = await fetchWithRetry(API_BASE + endpoint, {
      headers: getHeaders(false)
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
