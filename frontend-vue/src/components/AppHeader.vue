<template>
  <header class="header">
    <div class="header-brand">
      <h1>RIDAC</h1>
      <span>Red de Integración de Datos para Análisis y Contexto</span>
    </div>
    <div class="header-actions">
      <RouterLink v-if="!esDashboard" to="/dashboard" class="btn-back-dash">
        <i class="fas fa-arrow-left" /> Dashboard
      </RouterLink>
      <span class="user-label">
        <i class="fas fa-user-circle" />
        {{ auth.user?.username }} ({{ auth.user?.rol }})
      </span>
      <button class="btn-logout" @click="handleLogout">
        <i class="fas fa-sign-out-alt" /> Cerrar Sesión
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute, RouterLink } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const esDashboard = computed(() =>
  ['dashboard', 'login', 'dashboard-usuario'].includes(route.name)
)

function handleLogout() {
  auth.clearSession()
  router.push({ name: 'login' })
}
</script>

<style scoped>
.header {
  background: linear-gradient(135deg, #1a365d 0%, #2c5aa0 100%);
  color: white;
  padding: 16px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  position: relative;
  overflow: hidden;
}

.header::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="g" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/></pattern></defs><rect width="100" height="100" fill="url(%23g)"/></svg>');
  pointer-events: none;
}

.header-brand {
  position: relative;
  z-index: 1;
}

.header-brand h1 {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 1px;
  margin-bottom: 2px;
}

.header-brand span {
  font-size: 12px;
  opacity: 0.8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
  z-index: 1;
}

.user-label {
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-back-dash {
  background: rgba(255,255,255,0.12);
  color: white;
  border: 1.5px solid rgba(255,255,255,0.35);
  padding: 7px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s;
}
.btn-back-dash:hover {
  background: rgba(255,255,255,0.25);
  transform: translateX(-2px);
}

.btn-logout {
  background: rgba(255,255,255,0.15);
  color: white;
  border: 2px solid rgba(255,255,255,0.3);
  padding: 8px 18px;
  border-radius: 25px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.2s, border-color 0.2s, transform 0.2s;
}

.btn-logout:hover {
  background: rgba(255,255,255,0.25);
  border-color: rgba(255,255,255,0.5);
  transform: translateY(-1px);
}
</style>
