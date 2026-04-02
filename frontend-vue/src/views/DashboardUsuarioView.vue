<template>
  <div class="dash-wrap">
    <!-- ══ NAVBAR ══ -->
    <nav class="navbar">
      <div class="brand">
        <span class="brand-title">RIDAC</span>
        <small>Red de Integración de Datos para Análisis y Contexto</small>
      </div>
      <div class="nav-user">
        <div class="user-info">
          <span class="username">{{ user?.nombre || user?.username }}</span>
          <small>{{ user?.rol }}</small>
        </div>
        <button class="btn-ayuda" @click="router.push({ name: 'cambiar-password' })" title="Mi perfil">⚙️</button>
        <button class="btn-logout" @click="logout">
          Cerrar Sesión
        </button>
      </div>
    </nav>

    <div class="container">
      <!-- ══ ESTADÍSTICAS ══ -->
      <div class="stats-grid">
        <div class="stat-card" style="--c1:#28a745;--c2:#20c997">
          <h2>{{ stats.totalTomos }}</h2>
          <p>Tomos Accesibles</p>
          <span class="stat-icon">📚</span>
        </div>
        <div class="stat-card" style="--c1:#007bff;--c2:#0056b3">
          <h2>{{ stats.totalCarpetas }}</h2>
          <p>Carpetas</p>
          <span class="stat-icon">📁</span>
        </div>
        <div class="stat-card" style="--c1:#fd7e14;--c2:#e55a00">
          <h2>{{ stats.permisosCompletos }}</h2>
          <p>Acceso Completo</p>
          <span class="stat-icon">🔑</span>
        </div>
      </div>

      <!-- ══ ACCIONES RÁPIDAS ══ -->
      <div class="quick-actions">
        <button class="qa-btn" @click="router.push({ name: 'busqueda' })">🔍 Búsqueda de Texto</button>
        <button class="qa-btn" @click="router.push({ name: 'busqueda-semantica' })">🧠 Búsqueda Semántica</button>
        <button class="qa-btn" @click="router.push({ name: 'cambiar-password' })">🔑 Cambiar Contraseña</button>
      </div>

      <!-- ══ CARPETAS Y TOMOS ══ -->
      <div class="card card-main">
        <div class="card-header-row">
          <h5>📁 Mis Tomos y Carpetas</h5>
        </div>
        <div class="card-body">
          <div v-if="loading" class="loading-msg">⏳ Cargando expedientes...</div>
          <div v-else-if="!carpetas.length" class="empty-msg">
            📁 No tienes acceso a ningún expediente.<br>
            Contacta al administrador para solicitar permisos.
          </div>

          <div v-else>
            <div v-for="cp in carpetas" :key="cp.id" class="carpeta-section">
              <div class="carpeta-header">
                <h6>📁 {{ cp.nombre || cp.numero_carpeta }}</h6>
                <span>{{ cp.tomos?.length || 0 }} tomo(s)</span>
              </div>
              <div class="tomos-grid">
                <div v-if="!cp.tomos?.length" class="empty-tomos">
                  Sin tomos disponibles
                </div>
                <div v-for="t in cp.tomos" :key="t.id" class="tomo-card">
                  <div class="tomo-header">
                    <span class="tomo-num">Tomo {{ t.numero_tomo }}</span>
                    <span class="estado-badge" :class="estadoClass(t.estado)">
                      {{ estadoIcon(t.estado) }} {{ estadoTexto(t.estado) }}
                    </span>
                  </div>
                  <div class="tomo-nombre">{{ t.nombre_archivo || t.nombre }}</div>
                  <p class="tomo-meta">
                    📑 {{ t.numero_paginas || 'N/A' }} pág.
                    <template v-if="t.confianza_promedio"> · 🎯 {{ t.confianza_promedio }}%</template>
                  </p>
                  <div class="tomo-actions">
                    <button class="ta-btn primary"  @click="verPDF(t)">👁️ Ver PDF</button>
                    <button v-if="t._permisos?.buscar"   class="ta-btn info"    @click="buscarEnTomo(t)">🔍 Buscar</button>
                    <button v-if="t._permisos?.buscar"   class="ta-btn success" @click="analizarJuridico(t)">⚖️ Análisis</button>
                    <button v-if="t._permisos?.buscar"   class="ta-btn purple"  @click="busquedaSemantica(t)">🧠 Semántica</button>
                    <button v-if="t._permisos?.exportar" class="ta-btn export"  @click="descargarTomo(t)">📥 Descargar</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'

const router   = useRouter()
const auth     = useAuthStore()
const { get, download } = useApi()
const { showToast } = useToast()

const user    = computed(() => auth.user)
const loading = ref(true)
const carpetas = ref([])
const stats    = ref({ totalTomos: 0, totalCarpetas: 0, permisosCompletos: 0 })

onMounted(async () => {
  if (!auth.isAuthenticated) { router.push({ name: 'login' }); return }
  await cargarDatos()
})

async function cargarDatos() {
  loading.value = true
  try {
    const uid = user.value?.id

    // 1. Cargar todas las carpetas y sus tomos (datos completos)
    const todasCarpetas = await get('/carpetas')
    const tomosPorCarpeta = {}
    await Promise.allSettled(
      todasCarpetas.map(async cp => {
        try {
          const ts = await get(`/tomos/${cp.id}`)
          tomosPorCarpeta[cp.id] = (Array.isArray(ts) ? ts : []).map(t => ({ ...t, carpeta_id: cp.id }))
        } catch { tomosPorCarpeta[cp.id] = [] }
      })
    )

    // 2. Obtener permisos del usuario
    let listaPermisos = []
    try {
      const data = await get(`/permisos/usuarios/${uid}`)
      // Soporta tanto array plano como { tomos: [...] }
      listaPermisos = Array.isArray(data) ? data : (data?.tomos || data?.permisos || [])
    } catch {}

    // 3. Construir mapa de permisos: tomo_id → { ver, buscar, exportar }
    const permisosMap = {}
    for (const p of listaPermisos) {
      const tid = p.tomo_id ?? p.id
      permisosMap[tid] = {
        ver:      !!(p.ver ?? p.puede_ver ?? true),
        buscar:   !!(p.buscar ?? p.puede_buscar ?? false),
        exportar: !!(p.exportar ?? p.puede_exportar ?? false),
      }
    }

    const tienePermisos = Object.keys(permisosMap).length > 0

    // 4. Construir estructura carpetas → tomos filtrados por permiso
    const resultado = []
    for (const cp of todasCarpetas) {
      const tomosCP = tomosPorCarpeta[cp.id] || []
      let tomosFiltrados

      if (tienePermisos) {
        // Mostrar solo tomos donde el admin otorgó permiso de ver
        tomosFiltrados = tomosCP.filter(t => {
          const p = permisosMap[t.id]
          return p && p.ver
        }).map(t => ({ ...t, _permisos: permisosMap[t.id] }))
      } else {
        // Sin permisos configurados → mostrar todos (modo demo / admin)
        tomosFiltrados = tomosCP.map(t => ({ ...t, _permisos: { ver: true, buscar: true, exportar: true } }))
      }

      if (tomosFiltrados.length) {
        resultado.push({ ...cp, tomos: tomosFiltrados })
      }
    }

    carpetas.value = resultado
    const totalTomos = resultado.reduce((s, c) => s + c.tomos.length, 0)
    stats.value.totalTomos    = totalTomos
    stats.value.totalCarpetas = resultado.length
    stats.value.permisosCompletos = resultado.filter(c =>
      c.tomos.some(t => t._permisos?.buscar && t._permisos?.exportar)
    ).length

  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

function verPDF(tomo) {
  router.push({ name: 'visor-pdf', query: { tomo_id: tomo.id, nombre: tomo.nombre_archivo || tomo.nombre } })
}

function buscarEnTomo(tomo) {
  router.push({ name: 'busqueda', query: { tomo_id: tomo.id } })
}

function analizarJuridico(tomo) {
  router.push({ name: 'analisis-avanzado', query: { tomo_id: tomo.id, nombre: tomo.nombre_archivo || tomo.nombre } })
}

function busquedaSemantica(tomo) {
  router.push({ name: 'busqueda-semantica', query: { tomo_id: tomo.id } })
}

async function descargarTomo(tomo) {
  try {
    await download(`/tomos/${tomo.id}/descargar`, tomo.nombre_archivo || tomo.nombre || `tomo-${tomo.id}.pdf`)
  } catch {
    showToast('Error al descargar el tomo', 'error')
  }
}

function logout() {
  auth.clearSession()
  router.push({ name: 'login' })
}

function estadoClass(e) { return { completado: 'ok', procesado: 'ok', procesando: 'proc', pendiente: 'pen', error: 'err' }[e] || 'pen' }
function estadoIcon(e)  { return { completado: '✅', procesado: '✅', procesando: '⏳', pendiente: '⏸️', error: '❌' }[e] || '❓' }
function estadoTexto(e) { return { completado: 'Completado', procesado: 'Procesado', procesando: 'Procesando', pendiente: 'Pendiente', error: 'Error' }[e] || e }
</script>

<style scoped>
.dash-wrap { min-height: 100vh; background: linear-gradient(135deg, #1a365d 0%, #2c5aa0 40%, #1e3a8a 100%); }

/* Navbar */
.navbar {
  background: rgba(255,255,255,0.1);
  backdrop-filter: blur(10px);
  padding: 14px 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255,255,255,0.2);
  position: sticky; top: 0; z-index: 100;
}
.brand-title { font-size: 22px; font-weight: 800; color: white; display: block; }
.brand small { color: rgba(255,255,255,0.8); font-size: 11px; }
.nav-user { display: flex; align-items: center; gap: 12px; }
.user-info { color: white; text-align: right; }
.username { font-weight: 700; font-size: 15px; display: block; }
.user-info small { color: rgba(255,255,255,0.7); font-size: 12px; }
.btn-ayuda { background: rgba(255,255,255,0.1); border: none; color: white; padding: 8px 14px; border-radius: 20px; cursor: pointer; font-size: 18px; }
.btn-logout { background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 9px 18px; border-radius: 25px; cursor: pointer; font-weight: 600; transition: background 0.2s; }
.btn-logout:hover { background: rgba(255,255,255,0.25); }

/* Container */
.container { max-width: 1400px; margin: 0 auto; padding: 30px; }

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 24px; }
.stat-card {
  background: linear-gradient(135deg, var(--c1), var(--c2));
  color: white; padding: 24px; border-radius: 16px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.2); position: relative; overflow: hidden;
}
.stat-card h2 { font-size: 40px; font-weight: 800; margin: 0 0 6px; }
.stat-card p  { font-size: 14px; margin: 0; opacity: 0.9; }
.stat-icon { position: absolute; top: 16px; right: 20px; font-size: 32px; opacity: 0.3; }

/* Acciones rápidas */
.quick-actions { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
.qa-btn {
  background: rgba(255,255,255,0.12); color: white; border: 1px solid rgba(255,255,255,0.25);
  padding: 10px 20px; border-radius: 25px; cursor: pointer; font-weight: 600; font-size: 14px;
  transition: background 0.2s, transform 0.2s;
}
.qa-btn:hover { background: rgba(255,255,255,0.22); transform: translateY(-2px); }

/* Card principal */
.card { background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); overflow: hidden; }
.card-header-row { background: linear-gradient(135deg, #1a365d, #2c5aa0); padding: 18px 24px; }
.card-header-row h5 { color: white; font-size: 18px; font-weight: 700; margin: 0; }
.card-body { padding: 24px; }
.loading-msg, .empty-msg { padding: 40px; text-align: center; color: #6c757d; font-size: 15px; line-height: 1.8; }

/* Sección carpeta */
.carpeta-section {
  background: linear-gradient(135deg, #23527c, #1a4068);
  border-radius: 16px; margin-bottom: 24px; overflow: hidden;
  box-shadow: 0 6px 20px rgba(35,82,124,0.35);
}
.carpeta-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.2);
}
.carpeta-header h6 { color: white; font-size: 16px; font-weight: 800; margin: 0; }
.carpeta-header span { background: rgba(255,255,255,0.9); color: #23527c; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; }
.tomos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; padding: 16px 20px; }
.empty-tomos { color: rgba(255,255,255,0.6); padding: 20px; font-size: 13px; }

/* Tomo card */
.tomo-card { background: rgba(255,255,255,0.95); border-radius: 12px; padding: 16px; }
.tomo-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.tomo-num { font-weight: 700; color: #1a365d; font-size: 13px; }
.estado-badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 12px; }
.ok   { background: #d4edda; color: #155724; }
.proc { background: #fff3cd; color: #856404; }
.pen  { background: #e2e3e5; color: #383d41; }
.err  { background: #f8d7da; color: #721c24; }
.tomo-nombre { font-size: 13px; color: #333; font-weight: 600; margin-bottom: 6px; line-height: 1.4; }
.tomo-meta { font-size: 12px; color: #666; margin-bottom: 12px; }
.tomo-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.ta-btn {
  padding: 6px 12px; border: none; border-radius: 20px; cursor: pointer;
  font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px;
  transition: all 0.2s;
}
.ta-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
.ta-btn.primary { background: linear-gradient(135deg, #1a365d, #2c5aa0); color: white; }
.ta-btn.info    { background: linear-gradient(135deg, #17a2b8, #138496); color: white; }
.ta-btn.success { background: linear-gradient(135deg, #28a745, #20c997); color: white; }
.ta-btn.purple  { background: linear-gradient(135deg, #6f42c1, #5a32a3); color: white; }
.ta-btn.export  { background: linear-gradient(135deg, #17a2b8, #117a8b); color: white; }

@media (max-width: 768px) {
  .container { padding: 16px; }
  .stats-grid { grid-template-columns: 1fr 1fr; }
  .tomos-grid { grid-template-columns: 1fr; }
}
</style>
