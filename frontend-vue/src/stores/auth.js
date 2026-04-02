import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(JSON.parse(localStorage.getItem('usuario') || 'null'))
  let refreshTimer = null

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  function setSession(data) {
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('usuario', JSON.stringify(data.user))
    if (data.refresh_token) {
      localStorage.setItem('refresh_token', data.refresh_token)
    }
    startAutoRefresh()
  }

  function clearSession() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('usuario')
    localStorage.removeItem('refresh_token')
    stopAutoRefresh()
  }

  function hasRole(role) {
    return user.value?.rol === role
  }

  function hasAnyRole(...roles) {
    return roles.includes(user.value?.rol)
  }

  function startAutoRefresh() {
    stopAutoRefresh()
    // Refrescar token cada 14 minutos (expira en 15 min por defecto en dev)
    refreshTimer = setInterval(async () => {
      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) return

        const apiBase = import.meta.env.VITE_API_URL || '/api'
        const res = await fetch(`${apiBase}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        })

        if (res.ok) {
          const data = await res.json()
          token.value = data.access_token
          localStorage.setItem('token', data.access_token)
          if (data.user) {
            user.value = data.user
            localStorage.setItem('usuario', JSON.stringify(data.user))
          }
        } else {
          clearSession()
        }
      } catch {
        // Silencioso: si falla el refresh, la próxima petición fallará con 401
      }
    }, 14 * 60 * 1000)
  }

  function stopAutoRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  // Iniciar refresh si ya hay sesión activa al cargar la app
  if (isAuthenticated.value) {
    startAutoRefresh()
  }

  return {
    token,
    user,
    isAuthenticated,
    setSession,
    clearSession,
    hasRole,
    hasAnyRole
  }
})
