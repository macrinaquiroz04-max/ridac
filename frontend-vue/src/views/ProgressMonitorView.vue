<template>
  <div class="page-wrapper">
    <AppHeader titulo="Monitor de Progreso en Tiempo Real" icono="fas fa-chart-line" />

    <div class="container">
      <!-- Stats globales -->
      <div class="row g-3 mb-4">
        <div class="col-md-3" v-for="s in statGlobal" :key="s.label">
          <div class="stat-box">
            <div class="stat-value">{{ s.valor }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </div>

      <!-- Controles -->
      <div class="card mb-4">
        <div class="card-body d-flex gap-3 align-items-center flex-wrap">
          <div class="flex-grow-1">
            <label class="form-label mb-1">Carpeta</label>
            <select v-model="carpetaId" class="form-select" @change="cargarTomos">
              <option value="">Todas las carpetas</option>
              <option v-for="c in carpetas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
            </select>
          </div>
          <div class="flex-grow-1">
            <label class="form-label mb-1">Tipo de proceso</label>
            <select v-model="tipoProceso" class="form-select">
              <option value="ocr">OCR</option>
              <option value="analisis">Análisis</option>
              <option value="embeddings">Embeddings</option>
            </select>
          </div>
          <div class="d-flex gap-2 mt-3">
            <button class="btn" :class="autoRefresh ? 'btn-danger' : 'btn-success'" @click="toggleAutoRefresh">
              <i :class="autoRefresh ? 'fas fa-stop' : 'fas fa-play'" class="me-2"></i>
              {{ autoRefresh ? 'Detener' : 'Auto-refresh' }}
            </button>
            <button class="btn btn-outline-primary" @click="refrescarTodo">
              <i class="fas fa-sync-alt"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Lista de tomos con progreso -->
      <div v-if="cargando" class="text-center py-5">
        <i class="fas fa-spinner fa-spin fa-3x text-primary"></i>
        <p class="mt-3 text-muted">Cargando tomos…</p>
      </div>

      <div v-else-if="tomos.length === 0" class="text-center py-5 text-muted">
        <p>No hay tomos para monitorear.</p>
      </div>

      <div v-for="t in tomos" :key="t.id" class="tomo-card mb-3" @click="seleccionarTomo(t)">
        <div class="tomo-header">
          <div>
            <strong>{{ t.nombre }}</strong>
            <span class="badge ms-2" :class="estadoBadge(t.estado_ocr)">{{ t.estado_ocr || 'pendiente' }}</span>
          </div>
          <small class="text-muted">{{ t.total_paginas ?? 0 }} págs.</small>
        </div>
        <div class="progress-label">
          <span>{{ t.paginas_procesadas ?? 0 }} / {{ t.total_paginas ?? 0 }} páginas procesadas</span>
          <span class="fw-bold">{{ calcularPorcentaje(t) }}%</span>
        </div>
        <div class="progress tomo-progress">
          <div class="progress-bar"
            :class="barClass(t)"
            :style="{ width: calcularPorcentaje(t) + '%' }"></div>
        </div>
        <div v-if="tomoActivo === t.id && streamLogs.length" class="stream-logs mt-2">
          <div v-for="(l, i) in streamLogs" :key="i" class="stream-log">{{ l }}</div>
        </div>
      </div>
    </div>

    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import AppHeader from '@/components/AppHeader.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const { get } = useApi()
const { showToast } = useToast()
const auth = useAuthStore()

const carpetas = ref([])
const tomos = ref([])
const carpetaId = ref('')
const tipoProceso = ref('ocr')
const cargando = ref(false)
const autoRefresh = ref(false)
const tomoActivo = ref(null)
const streamLogs = ref([])

let refreshInterval = null
let eventSource = null

const statGlobal = computed(() => {
  const total = tomos.value.length
  const completos = tomos.value.filter(t => t.estado_ocr === 'completado').length
  const enProceso = tomos.value.filter(t => t.estado_ocr === 'procesando').length
  const pendientes = total - completos - enProceso
  return [
    { label: 'Total', valor: total },
    { label: 'Completados', valor: completos },
    { label: 'En proceso', valor: enProceso },
    { label: 'Pendientes', valor: pendientes }
  ]
})

onMounted(async () => {
  try {
    carpetas.value = await get('/carpetas')
  } catch { /* continuar */ }
  await refrescarTodo()
})

onUnmounted(() => {
  detenerAutoRefresh()
  if (eventSource) eventSource.close()
})

async function cargarTomos() {
  cargando.value = true
  try {
    let data
    if (carpetaId.value) {
      data = await get(`/tomos/${carpetaId.value}`)
      tomos.value = Array.isArray(data) ? data : (data?.tomos ?? [])
    } else {
      data = await get('/carpetas')
      const todos = []
      if (Array.isArray(data)) {
        for (const c of data) {
          try {
            const t = await get(`/tomos/${c.id}`)
            todos.push(...(Array.isArray(t) ? t : (t?.tomos ?? [])))
          } catch { /* skip */ }
        }
      }
      tomos.value = todos
    }
  } catch {
    showToast('Error al cargar tomos', 'error')
  } finally {
    cargando.value = false
  }
}

async function refrescarTodo() {
  await cargarTomos()
}

function toggleAutoRefresh() {
  if (autoRefresh.value) {
    detenerAutoRefresh()
  } else {
    autoRefresh.value = true
    refreshInterval = setInterval(refrescarTodo, 5000)
    showToast('Auto-refresh activado (5s)', 'info')
  }
}

function detenerAutoRefresh() {
  autoRefresh.value = false
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

function seleccionarTomo(t) {
  if (tomoActivo.value === t.id) {
    tomoActivo.value = null
    streamLogs.value = []
    if (eventSource) { eventSource.close(); eventSource = null }
    return
  }
  tomoActivo.value = t.id
  streamLogs.value = []
  if (eventSource) eventSource.close()

  const apiUrl = import.meta.env.VITE_API_URL || '/api'
  const url = `${apiUrl}/progress/${tipoProceso.value}/${t.id}?token=${encodeURIComponent(auth.token || '')}`
  eventSource = new EventSource(url)
  eventSource.onmessage = (e) => {
    streamLogs.value.push(e.data)
    if (streamLogs.value.length > 50) streamLogs.value.shift()
  }
  eventSource.onerror = () => {
    eventSource.close()
    eventSource = null
  }
}

function calcularPorcentaje(t) {
  if (!t.total_paginas) return 0
  return Math.round(((t.paginas_procesadas ?? 0) / t.total_paginas) * 100)
}

function estadoBadge(estado) {
  const map = { completado: 'bg-success', procesando: 'bg-warning text-dark', error: 'bg-danger', pendiente: 'bg-secondary' }
  return map[estado] ?? 'bg-secondary'
}

function barClass(t) {
  const p = calcularPorcentaje(t)
  if (t.estado_ocr === 'error') return 'bg-danger'
  if (p === 100) return 'bg-success'
  if (p > 50) return 'bg-primary progress-bar-striped progress-bar-animated'
  return 'bg-warning progress-bar-striped progress-bar-animated'
}
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: #1a1a2e; }
.container { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }
.stat-box { background: linear-gradient(135deg, #6a11cb, #2575fc); color: white; border-radius: 12px; padding: 22px; text-align: center; }
.stat-value { font-size: 2.4rem; font-weight: 700; }
.stat-label { font-size: .82rem; opacity: .85; margin-top: 2px; }
.card { background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1); border-radius: 12px; color: white; }
.card-body { padding: 20px 24px; }
.form-select, .form-control { background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.2); color: white; }
.form-select option { background: #1a237e; color: white; }
.form-label { color: rgba(255,255,255,.8); font-size: .85rem; }
.tomo-card { background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1); border-radius: 12px; padding: 20px; cursor: pointer; transition: background .2s; }
.tomo-card:hover { background: rgba(255,255,255,.12); }
.tomo-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; color: white; }
.progress-label { display: flex; justify-content: space-between; color: rgba(255,255,255,.7); font-size: .85rem; margin-bottom: 6px; }
.tomo-progress { height: 18px; border-radius: 10px; background: rgba(255,255,255,.15); }
.stream-logs { background: rgba(0,0,0,.3); border-radius: 8px; padding: 10px 12px; max-height: 120px; overflow-y: auto; }
.stream-log { font-size: .78rem; color: #a8d8a8; font-family: monospace; }
</style>
