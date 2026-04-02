<template>
  <div>
    <AppHeader />
    <div class="container">

      <!-- ══ STATS ══ -->
      <div class="stats-grid">
        <div class="stat-card" style="--c1:#1a365d;--c2:#2c5aa0">
          <h2>{{ stats.carpetas }}</h2>
          <p>📁 Carpetas</p>
        </div>
        <div class="stat-card" style="--c1:#28a745;--c2:#20c997">
          <h2>{{ stats.tomos }}</h2>
          <p>📄 Tomos Totales</p>
        </div>
        <div class="stat-card" style="--c1:#ffc107;--c2:#e0a800">
          <h2>{{ stats.ocrPendiente }}</h2>
          <p>⏳ OCR Pendiente</p>
        </div>
        <div class="stat-card" style="--c1:#34a853;--c2:#2d8f47">
          <h2>{{ stats.ocrCompletado }}</h2>
          <p>✅ OCR Completado</p>
        </div>
        <div class="stat-card" style="--c1:#6f42c1;--c2:#5a32a3">
          <h2>{{ stats.usuarios }}</h2>
          <p>👤 Usuarios</p>
        </div>
      </div>

      <!-- ══ ACCESOS RÁPIDOS ══ -->
      <h3 class="section-title">🚀 Accesos Rápidos</h3>
      <div class="quick-grid">
        <div class="quick-card" @click="router.push({ name: 'carpetas' })">
          <span class="qc-icon">📁</span>
          <div>
            <h4>Expedientes</h4>
            <p>Gestionar carpetas y tomos</p>
          </div>
        </div>
        <div class="quick-card" @click="router.push({ name: 'usuarios' })">
          <span class="qc-icon">👥</span>
          <div>
            <h4>Usuarios</h4>
            <p>Crear y administrar analistas</p>
          </div>
        </div>
        <div class="quick-card" @click="router.push({ name: 'permisos' })">
          <span class="qc-icon">🔑</span>
          <div>
            <h4>Permisos</h4>
            <p>Control de acceso a tomos</p>
          </div>
        </div>
        <div class="quick-card" @click="router.push({ name: 'busqueda' })">
          <span class="qc-icon">🔍</span>
          <div>
            <h4>Búsqueda</h4>
            <p>Buscar en todos los documentos</p>
          </div>
        </div>
        <div class="quick-card" @click="router.push({ name: 'auditoria' })">
          <span class="qc-icon">📋</span>
          <div>
            <h4>Auditoría</h4>
            <p>Log de acciones del sistema</p>
          </div>
        </div>
        <div class="quick-card" @click="router.push({ name: 'monitor-ocr' })">
          <span class="qc-icon">⚙️</span>
          <div>
            <h4>Monitor OCR</h4>
            <p>Estado del procesamiento</p>
          </div>
        </div>
        <div class="quick-card" @click="router.push({ name: 'busqueda-semantica' })">
          <span class="qc-icon">🧠</span>
          <div>
            <h4>Búsqueda Semántica</h4>
            <p>Búsqueda con IA</p>
          </div>
        </div>
        <div class="quick-card" @click="router.push({ name: 'analisis-ia' })">
          <span class="qc-icon">⚖️</span>
          <div>
            <h4>Análisis Jurídico</h4>
            <p>IA para análisis de texto</p>
          </div>
        </div>
      </div>

      <!-- ══ ACTIVIDAD RECIENTE ══ -->
      <div class="card mt-24">
        <div class="card-header">
          <h3>📋 Actividad Reciente</h3>
          <button class="btn-sm" @click="router.push({ name: 'auditoria' })">Ver todo →</button>
        </div>
        <div class="card-body">
          <div v-if="loadingAuditoria" class="msg-center">⏳ Cargando...</div>
          <div v-else-if="!auditoria.length" class="msg-center">Sin actividad reciente</div>
          <table v-else class="activity-table">
            <thead>
              <tr><th>Usuario</th><th>Acción</th><th>IP</th><th>Fecha</th></tr>
            </thead>
            <tbody>
              <tr v-for="a in auditoria.slice(0, 10)" :key="a.id">
                <td><strong>{{ a.usuario }}</strong></td>
                <td><span class="action-badge">{{ a.accion }}</span></td>
                <td>{{ a.ip }}</td>
                <td>{{ formatFecha(a.fecha) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useApi } from '@/composables/useApi'

const router = useRouter()
const { get } = useApi()

const stats = ref({ carpetas: 0, tomos: 0, ocrPendiente: 0, ocrCompletado: 0, usuarios: 0 })
const auditoria = ref([])
const loadingAuditoria = ref(true)

onMounted(async () => {
  await Promise.allSettled([cargarStats(), cargarAuditoria()])
})

async function cargarStats() {
  try {
    const carpetas = await get('/carpetas')
    stats.value.carpetas = carpetas.length
    let total = 0, completados = 0, pendientes = 0
    for (const cp of carpetas) {
      try {
        const tomos = await get(`/tomos/${cp.id}`)
        total += tomos.length
        completados += tomos.filter(t => t.estado === 'completado' || t.estado === 'procesado').length
        pendientes  += tomos.filter(t => t.estado === 'pendiente' || t.estado === 'procesando').length
      } catch {}
    }
    stats.value.tomos = total
    stats.value.ocrCompletado = completados
    stats.value.ocrPendiente  = pendientes
  } catch {}

  try {
    const usuarios = await get('/admin/usuarios')
    stats.value.usuarios = Array.isArray(usuarios) ? usuarios.length : 0
  } catch {}
}

async function cargarAuditoria() {
  loadingAuditoria.value = true
  try {
    const data = await get('/auditoria')
    auditoria.value = data.items || data || []
  } catch {
    auditoria.value = []
  } finally {
    loadingAuditoria.value = false
  }
}

function formatFecha(f) {
  if (!f) return 'N/A'
  return new Date(f).toLocaleString('es-MX', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.container { max-width: 1400px; margin: 0 auto; padding: 30px; }
.section-title { color: #1a365d; font-size: 18px; margin: 30px 0 16px; }
.mt-24 { margin-top: 24px; }

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 8px; }
.stat-card {
  background: linear-gradient(135deg, var(--c1), var(--c2));
  color: white; padding: 24px; border-radius: 14px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.15); text-align: center;
  transition: transform 0.2s;
}
.stat-card:hover { transform: translateY(-3px); }
.stat-card h2 { font-size: 38px; font-weight: 800; margin: 0 0 6px; }
.stat-card p  { font-size: 13px; margin: 0; opacity: 0.9; }

/* Quick grid */
.quick-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.quick-card {
  background: white; border-radius: 14px; padding: 20px;
  display: flex; align-items: center; gap: 16px; cursor: pointer;
  box-shadow: 0 3px 12px rgba(0,0,0,0.08); border: 2px solid transparent;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
.quick-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.12); border-color: #2c5aa0; }
.qc-icon { font-size: 32px; flex-shrink: 0; }
.quick-card h4 { color: #1a365d; font-size: 15px; margin: 0 0 4px; }
.quick-card p  { color: #6c757d; font-size: 12px; margin: 0; }

/* Card */
.card { background: white; border-radius: 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); overflow: hidden; }
.card-header { background: linear-gradient(135deg, #1a365d, #2c5aa0); padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }
.card-header h3 { color: white; margin: 0; font-size: 16px; }
.btn-sm { background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 6px 14px; border-radius: 20px; cursor: pointer; font-size: 13px; }
.btn-sm:hover { background: rgba(255,255,255,0.25); }
.card-body { padding: 20px; }
.msg-center { padding: 30px; text-align: center; color: #6c757d; }

/* Tabla */
.activity-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.activity-table th { background: #f8f9fa; padding: 10px 14px; text-align: left; color: #495057; font-weight: 600; font-size: 12px; text-transform: uppercase; }
.activity-table td { padding: 10px 14px; border-bottom: 1px solid #f0f0f0; }
.activity-table tr:hover td { background: #f8f9fa; }
.action-badge { background: #e3f2fd; color: #1565c0; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; }
</style>
