<template>
  <div class="page-wrapper">
    <AppHeader titulo="Análisis con IA — Gestión de Carpetas" icono="fas fa-brain" />

    <div class="container">
      <!-- Barra de búsqueda -->
      <div class="filtro-bar">
        <input v-model="filtro" type="text" placeholder="🔍 Buscar carpeta..." class="input-filtro" />
        <button class="btn-refresh" @click="cargarCarpetas" :disabled="cargando" title="Actualizar">
          <i :class="cargando ? 'fas fa-spinner fa-spin' : 'fas fa-sync-alt'"></i> Actualizar
        </button>
      </div>

      <!-- Loading inicial -->
      <div v-if="cargando && carpetas.length === 0" class="loading-box">
        <i class="fas fa-spinner fa-spin fa-2x"></i>
        <p>Cargando carpetas...</p>
      </div>

      <!-- Lista de carpetas -->
      <div class="carpetas-grid">
        <div v-for="c in carpetasFiltradas" :key="c.id" class="carpeta-card">
          <!-- Encabezado -->
          <div class="carpeta-header">
            <div>
              <h3 class="carpeta-nombre">📁 {{ c.nombre }}</h3>
              <p class="carpeta-desc">{{ c.descripcion || c.numero_expediente || '' }}</p>
            </div>
            <span :class="['badge-estado', `estado-${c.estado_analisis || 'pendiente'}`]">
              {{ etiquetaEstado(c.estado_analisis) }}
            </span>
          </div>

          <!-- Barra de progreso (solo si procesando) -->
          <div v-if="c.estado_analisis === 'procesando'" class="progress-wrap">
            <div class="progress-bar-track">
              <div class="progress-bar-fill" :style="{ width: (c.progreso || 0) + '%' }"></div>
            </div>
            <span class="progress-pct">{{ c.progreso || 0 }}%</span>
          </div>

          <!-- Stats (solo si hay estadísticas) -->
          <div v-if="c.estadisticas" class="stats-grid">
            <div class="stat-item stat-blue">
              <div class="stat-num">{{ c.estadisticas.total_diligencias || 0 }}</div>
              <div class="stat-lbl">📋 Diligencias</div>
            </div>
            <div class="stat-item stat-pink">
              <div class="stat-num">{{ c.estadisticas.total_personas || 0 }}</div>
              <div class="stat-lbl">👥 Personas</div>
            </div>
            <div class="stat-item stat-cyan">
              <div class="stat-num">{{ c.estadisticas.total_lugares || 0 }}</div>
              <div class="stat-lbl">📍 Lugares</div>
            </div>
            <div class="stat-item stat-orange">
              <div class="stat-num">{{ c.estadisticas.total_fechas || 0 }}</div>
              <div class="stat-lbl">📅 Fechas</div>
            </div>
            <div class="stat-item stat-red">
              <div class="stat-num">{{ c.estadisticas.total_alertas_activas || 0 }}</div>
              <div class="stat-lbl">⚠️ Alertas</div>
            </div>
          </div>

          <!-- Botones -->
          <div class="carpeta-btns">
            <button class="btn-iniciar" @click="abrirModalTomos(c)" :disabled="c.estado_analisis === 'procesando'">
              🔬 Iniciar Análisis
            </button>
            <button v-if="c.estado_analisis === 'completado'" class="btn-resultados" @click="verResultados(c)">
              📊 Ver Resultados
            </button>
          </div>
        </div>
      </div>

      <!-- Sin carpetas -->
      <div v-if="!cargando && carpetasFiltradas.length === 0" class="empty-state">
        <p>No se encontraron carpetas.</p>
      </div>
    </div>

    <!-- ── Modal Selección de Tomos ─────────────────────────────────── -->
    <div v-if="modalTomos" class="modal-backdrop" @click.self="cerrarModalTomos">
      <div class="modal-box">
        <div class="modal-header">
          <h3>🔍 Seleccionar Tomos a Analizar</h3>
          <button class="btn-close-modal" @click="cerrarModalTomos">✕</button>
        </div>
        <p class="modal-sub">Carpeta: <strong>{{ carpetaSeleccionada?.nombre }}</strong></p>

        <div v-if="cargandoTomos" class="loading-box sm">
          <i class="fas fa-spinner fa-spin"></i> Cargando tomos...
        </div>
        <div v-else>
          <label class="check-all-label">
            <input type="checkbox" v-model="todosSeleccionados" @change="toggleTodos" />
            <strong>✅ Seleccionar todos los tomos</strong>
          </label>
          <div class="tomos-lista">
            <label v-for="t in tomosCompletados" :key="t.id" class="tomo-check-label">
              <input type="checkbox" :value="t.id" v-model="tomosElegidos" />
              <div class="tomo-info">
                <div class="tomo-nombre">📄 Tomo {{ t.numero_tomo || t.id }}</div>
                <div class="tomo-meta">{{ t.nombre || t.nombre_archivo || 'Sin nombre' }} • {{ t.total_paginas || 0 }} páginas</div>
              </div>
            </label>
          </div>
          <div v-if="tomosCompletados.length === 0" class="empty-state sm">
            No hay tomos con OCR completado en esta carpeta.
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-analizar-tomos" @click="confirmarAnalisis"
            :disabled="tomosElegidos.length === 0 || iniciando">
            <i :class="iniciando ? 'fas fa-spinner fa-spin' : 'fas fa-play'"></i>
            {{ iniciando ? 'Iniciando...' : '✅ Analizar Seleccionados' }}
          </button>
          <button class="btn-cancelar" @click="cerrarModalTomos">❌ Cancelar</button>
        </div>
      </div>
    </div>

    <!-- ── Modal Resultados ─────────────────────────────────────────── -->
    <div v-if="modalResultados" class="modal-backdrop" @click.self="cerrarModalResultados">
      <div class="modal-box modal-xl">
        <div class="modal-header-grad">
          <div>
            <h2 class="modal-titulo">📊 Análisis Completo de la Carpeta</h2>
            <p class="modal-subtitulo">{{ carpetaResultados?.nombre }}</p>
          </div>
          <button class="btn-close-modal white" @click="cerrarModalResultados">✕</button>
        </div>
        <div class="modal-content-scroll">
          <!-- Stats -->
          <div class="stats-resultados-grid" v-if="analisisResultados">
            <div class="stat-res-card azul">
              <div class="stat-res-num">{{ analisisResultados.total_diligencias || 0 }}</div>
              <div class="stat-res-lbl">📋 Diligencias</div>
            </div>
            <div class="stat-res-card rosa">
              <div class="stat-res-num">{{ analisisResultados.total_personas || 0 }}</div>
              <div class="stat-res-lbl">👥 Personas</div>
            </div>
            <div class="stat-res-card cyan">
              <div class="stat-res-num">{{ analisisResultados.total_lugares || 0 }}</div>
              <div class="stat-res-lbl">📍 Lugares</div>
            </div>
            <div class="stat-res-card naranja">
              <div class="stat-res-num">{{ analisisResultados.total_fechas || 0 }}</div>
              <div class="stat-res-lbl">📅 Fechas</div>
            </div>
            <div class="stat-res-card rojo">
              <div class="stat-res-num">{{ (analisisResultados.alertas_mp || []).length }}</div>
              <div class="stat-res-lbl">⚠️ Alertas</div>
            </div>
          </div>

          <!-- Alertas MP -->
          <div v-if="analisisResultados?.alertas_mp?.length" class="alertas-box">
            <h3 class="alertas-titulo">⚠️ Alertas del Ministerio Público ({{ analisisResultados.alertas_mp.length }})</h3>
            <div v-for="(a, i) in analisisResultados.alertas_mp" :key="i" :class="['alerta-item', `alerta-prioridad-${a.prioridad}`]">
              <div class="alerta-header">
                <span :class="['alerta-badge', `badge-${a.prioridad}`]">{{ a.prioridad?.toUpperCase() }}</span>
                <strong class="alerta-tipo">{{ a.titulo || a.tipo }}</strong>
                <span v-if="a.dias_inactividad" class="alerta-dias">{{ a.dias_inactividad }} días sin actividad</span>
              </div>
              <p class="alerta-desc">{{ a.descripcion }}</p>
              <span v-if="a.fecha_ultima_actuacion" class="alerta-fecha">📅 Última actuación: {{ a.fecha_ultima_actuacion }}</span>
            </div>
          </div>
          <div v-else-if="analisisResultados && !analisisResultados?.alertas_mp?.length" class="alertas-box vacio">
            <p>✅ Sin alertas activas en esta carpeta.</p>
          </div>

          <!-- Diligencias -->
          <div class="diligencias-seccion">
            <h3 class="diligencias-titulo">
              📋 Diligencias Encontradas ({{ (analisisResultados?.diligencias || []).length }})
            </h3>
            <div class="diligencias-scroll">
              <div v-if="!analisisResultados?.diligencias?.length" class="empty-state sm">
                No se encontraron diligencias.
              </div>
              <div v-for="(d, i) in analisisResultados?.diligencias" :key="i" class="diligencia-card">
                <div class="dili-grid">
                  <div class="dili-field"><span class="dili-label">Tipo:</span> {{ d.tipo_diligencia }}</div>
                  <div class="dili-field"><span class="dili-label">Fecha:</span> {{ d.fecha }}</div>
                  <div class="dili-field"><span class="dili-label">Responsable:</span> {{ d.responsable || d.mp_responsable }}</div>
                  <div class="dili-field"><span class="dili-label">Oficio/Folio:</span> {{ d.numero_oficio || d.folio }}</div>
                </div>
                <p class="dili-desc">{{ d.descripcion || d.resumen || '' }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancelar" @click="cerrarModalResultados">Cerrar</button>
        </div>
      </div>
    </div>

    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import AppHeader from '@/components/AppHeader.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const { get, post } = useApi()
const auth = useAuthStore()
const { showToast } = useToast()

const carpetas       = ref([])
const filtro         = ref('')
const cargando       = ref(false)
let intervalo        = null

// Modal tomos
const modalTomos          = ref(false)
const carpetaSeleccionada = ref(null)
const cargandoTomos       = ref(false)
const tomosCompletados    = ref([])
const tomosElegidos       = ref([])
const todosSeleccionados  = ref(false)
const iniciando           = ref(false)

// Modal resultados
const modalResultados    = ref(false)
const carpetaResultados  = ref(null)
const analisisResultados = ref(null)

const carpetasFiltradas = computed(() =>
  carpetas.value.filter(c =>
    c.nombre.toLowerCase().includes(filtro.value.toLowerCase())
  )
)

function etiquetaEstado(estado) {
  const m = { pendiente: '🕐 Pendiente', procesando: '⏳ Procesando', completado: '✅ Completado', error: '❌ Error' }
  return m[estado] || '🕐 Pendiente'
}

async function cargarCarpetas() {
  cargando.value = true
  try {
    const data = await get('/admin/carpetas-analisis')
    carpetas.value = Array.isArray(data) ? data : (data.items ?? [])
    // Auto-refresh si alguna está procesando
    const hayProcesando = carpetas.value.some(c => c.estado_analisis === 'procesando')
    if (hayProcesando && !intervalo) {
      intervalo = setInterval(cargarCarpetas, 10000)
    } else if (!hayProcesando && intervalo) {
      clearInterval(intervalo)
      intervalo = null
    }
  } catch (e) {
    showToast('Error al cargar carpetas: ' + (e.message || ''), 'error')
  } finally {
    cargando.value = false
  }
}

async function abrirModalTomos(carpeta) {
  carpetaSeleccionada.value = carpeta
  tomosCompletados.value = []
  tomosElegidos.value = []
  todosSeleccionados.value = false
  modalTomos.value = true
  cargandoTomos.value = true
  try {
    const data = await get(`/tomos/${carpeta.id}`)
    const lista = Array.isArray(data) ? data : (data.items ?? [])
    tomosCompletados.value = lista.filter(t => t.estado_ocr === 'completado' || t.estado === 'completado')
    // Seleccionar todos por defecto
    tomosElegidos.value = tomosCompletados.value.map(t => t.id)
    todosSeleccionados.value = true
  } catch {
    showToast('Error al cargar tomos', 'error')
  } finally {
    cargandoTomos.value = false
  }
}

function toggleTodos() {
  if (todosSeleccionados.value) {
    tomosElegidos.value = tomosCompletados.value.map(t => t.id)
  } else {
    tomosElegidos.value = []
  }
}

function cerrarModalTomos() {
  modalTomos.value = false
}

async function confirmarAnalisis() {
  if (tomosElegidos.value.length === 0) {
    showToast('Selecciona al menos un tomo', 'warning')
    return
  }
  iniciando.value = true
  try {
    await post(`/admin/carpetas/${carpetaSeleccionada.value.id}/iniciar-analisis`, {
      tomo_ids: tomosElegidos.value,
      generar_alertas: true,
      umbral_inactividad_dias: 60,
    })
    showToast('✅ Análisis iniciado. La página se actualizará cada 10 segundos.', 'success')
    cerrarModalTomos()
    await cargarCarpetas()
  } catch (e) {
    showToast('Error al iniciar análisis: ' + (e.message || ''), 'error')
  } finally {
    iniciando.value = false
  }
}

async function verResultados(carpeta) {
  carpetaResultados.value = carpeta
  analisisResultados.value = null
  modalResultados.value = true
  try {
    const [stats, diligenciasData, alertasData] = await Promise.all([
      get(`/admin/carpetas/${carpeta.id}/estadisticas`),
      get(`/usuario/carpetas/${carpeta.id}/diligencias`),
      get(`/usuario/carpetas/${carpeta.id}/alertas`).catch(() => ({ alertas: [] })),
    ])
    analisisResultados.value = {
      ...(stats.estadisticas ?? stats),
      diligencias: Array.isArray(diligenciasData) ? diligenciasData : (diligenciasData?.diligencias ?? []),
      alertas_mp: alertasData?.alertas ?? [],
    }
  } catch (e) {
    showToast('Error al cargar resultados: ' + (e.message || ''), 'error')
  }
}

function cerrarModalResultados() {
  modalResultados.value = false
}

onMounted(cargarCarpetas)
onUnmounted(() => { if (intervalo) clearInterval(intervalo) })
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: #f0f2f5; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px 20px; }

.filtro-bar {
  display: flex; gap: 12px; margin-bottom: 24px; align-items: center;
}
.input-filtro {
  flex: 1; padding: 12px 16px; border: 2px solid #e9ecef; border-radius: 10px;
  font-size: 15px; outline: none; transition: border-color 0.2s;
}
.input-filtro:focus { border-color: #667eea; }
.btn-refresh {
  padding: 12px 20px; background: #667eea; color: white; border: none;
  border-radius: 10px; cursor: pointer; font-weight: 600; display: flex;
  align-items: center; gap: 8px; transition: background 0.2s;
}
.btn-refresh:hover { background: #5a67d8; }
.btn-refresh:disabled { opacity: 0.6; cursor: not-allowed; }

.carpetas-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; }

.carpeta-card {
  background: white; border-radius: 16px; padding: 24px;
  box-shadow: 0 4px 15px rgba(0,0,0,.07); display: flex; flex-direction: column; gap: 16px;
}
.carpeta-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.carpeta-nombre { margin: 0; font-size: 16px; color: #1a365d; font-weight: 700; }
.carpeta-desc { margin: 4px 0 0; font-size: 13px; color: #6c757d; }

.badge-estado {
  padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700;
  white-space: nowrap; text-transform: uppercase; letter-spacing: .5px;
}
.estado-pendiente  { background: #e9ecef; color: #495057; }
.estado-procesando { background: #fff3cd; color: #856404; }
.estado-completado { background: #d4edda; color: #155724; }
.estado-error      { background: #f8d7da; color: #721c24; }

.progress-wrap { display: flex; align-items: center; gap: 10px; }
.progress-bar-track {
  flex: 1; background: #e9ecef; border-radius: 10px; height: 10px; overflow: hidden;
}
.progress-bar-fill {
  height: 100%; background: linear-gradient(90deg, #28a745, #20c997);
  border-radius: 10px; transition: width 0.5s ease;
}
.progress-pct { font-size: 13px; font-weight: 600; color: #495057; min-width: 36px; text-align: right; }

.stats-grid {
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px;
}
.stat-item { border-radius: 12px; padding: 12px 8px; text-align: center; color: white; }
.stat-blue  { background: linear-gradient(135deg, #667eea, #764ba2); }
.stat-pink  { background: linear-gradient(135deg, #f093fb, #f5576c); }
.stat-cyan  { background: linear-gradient(135deg, #4facfe, #00f2fe); }
.stat-orange { background: linear-gradient(135deg, #fa709a, #fee140); }
.stat-red   { background: linear-gradient(135deg, #ff6b6b, #ee5a6f); }
.stat-num { font-size: 22px; font-weight: 700; }
.stat-lbl { font-size: 11px; opacity: 0.9; margin-top: 2px; }

.carpeta-btns { display: flex; gap: 10px; flex-wrap: wrap; }
.btn-iniciar {
  flex: 1; padding: 12px; background: linear-gradient(135deg, #2c5aa0, #1a365d);
  color: white; border: none; border-radius: 10px; font-weight: 600;
  cursor: pointer; transition: all 0.3s;
}
.btn-iniciar:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(44,90,160,.4); }
.btn-iniciar:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
.btn-resultados {
  flex: 1; padding: 12px; background: linear-gradient(135deg, #28a745, #20c997);
  color: white; border: none; border-radius: 10px; font-weight: 600;
  cursor: pointer; transition: all 0.3s;
}
.btn-resultados:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(40,167,69,.4); }

/* ── Modales ────────────────────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,.7);
  display: flex; align-items: center; justify-content: center; z-index: 9000;
}
.modal-box {
  background: white; border-radius: 16px; width: 90%; max-width: 600px;
  max-height: 90vh; display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,.3);
}
.modal-xl { max-width: 860px; }

.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px; border-bottom: 1px solid #e9ecef;
}
.modal-header h3 { margin: 0; color: #1a365d; }

.modal-header-grad {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px 24px; border-radius: 16px 16px 0 0;
  display: flex; justify-content: space-between; align-items: flex-start;
}
.modal-titulo  { margin: 0; font-size: 22px; color: white; }
.modal-subtitulo { margin: 6px 0 0; color: rgba(255,255,255,.9); font-size: 15px; }

.btn-close-modal {
  background: none; border: none; font-size: 20px; cursor: pointer; color: #6c757d;
  line-height: 1; padding: 4px 8px; border-radius: 6px;
}
.btn-close-modal.white { color: rgba(255,255,255,.9); }
.btn-close-modal:hover { background: rgba(0,0,0,.1); }

.modal-sub { padding: 12px 24px 0; color: #495057; margin: 0; }
.modal-content-scroll { flex: 1; overflow-y: auto; padding: 24px; }
.modal-footer {
  padding: 16px 24px; border-top: 1px solid #e9ecef; display: flex;
  justify-content: flex-end; gap: 12px;
}

.check-all-label {
  display: flex; align-items: center; gap: 12px; padding: 12px;
  background: #f8f9fa; border-radius: 8px; cursor: pointer; margin-bottom: 12px;
}
.tomos-lista { display: flex; flex-direction: column; gap: 10px; max-height: 360px; overflow-y: auto; }
.tomo-check-label {
  display: flex; align-items: center; gap: 14px; padding: 14px;
  border: 2px solid #e9ecef; border-radius: 8px; cursor: pointer;
  transition: all 0.2s;
}
.tomo-check-label:hover { border-color: #667eea; background: #f0f2ff; }
.tomo-nombre { font-weight: 600; color: #1a365d; }
.tomo-meta { font-size: 13px; color: #6c757d; margin-top: 2px; }

/* Stats resultados modal */
.stats-resultados-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px; margin-bottom: 28px;
}
.stat-res-card { border-radius: 16px; padding: 22px 16px; text-align: center; color: white; }
.azul   { background: linear-gradient(135deg, #667eea, #764ba2); box-shadow: 0 8px 16px rgba(102,126,234,.3); }
.rosa   { background: linear-gradient(135deg, #f093fb, #f5576c); box-shadow: 0 8px 16px rgba(240,147,251,.3); }
.cyan   { background: linear-gradient(135deg, #4facfe, #00f2fe); box-shadow: 0 8px 16px rgba(79,172,254,.3); }
.naranja { background: linear-gradient(135deg, #fa709a, #fee140); box-shadow: 0 8px 16px rgba(250,112,154,.3); }
.rojo   { background: linear-gradient(135deg, #ff6b6b, #ee5a6f); box-shadow: 0 8px 16px rgba(255,107,107,.3); }
.stat-res-num { font-size: 42px; font-weight: 700; margin-bottom: 6px; }
.stat-res-lbl { font-size: 13px; opacity: .95; text-transform: uppercase; letter-spacing: 1px; }

.alertas-box {
  background: linear-gradient(to right, #fff3cd, #ffe8a1);
  border-left: 6px solid #ffc107; padding: 18px 20px; border-radius: 12px;
  margin-bottom: 24px;
}
.alertas-box.vacio { background: #f0fff4; border-left-color: #28a745; }
.alertas-box.vacio p { margin: 0; color: #155724; font-weight: 600; }
.alertas-titulo { color: #856404; margin: 0 0 12px; display: flex; align-items: center; gap: 8px; }
.alerta-item {
  background: white; padding: 12px 14px; border-radius: 8px; margin-bottom: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,.08);
}
.alerta-prioridad-crítica { border-left: 4px solid #dc3545; }
.alerta-prioridad-alta    { border-left: 4px solid #fd7e14; }
.alerta-prioridad-media   { border-left: 4px solid #ffc107; }
.alerta-prioridad-baja    { border-left: 4px solid #20c997; }
.alerta-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; flex-wrap: wrap; }
.alerta-badge { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 20px; color: white; }
.badge-crítica { background: #dc3545; }
.badge-alta    { background: #fd7e14; }
.badge-media   { background: #ffc107; color: #333; }
.badge-baja    { background: #20c997; }
.alerta-tipo { font-weight: 700; color: #212529; flex: 1; }
.alerta-dias { font-size: 12px; color: #6c757d; margin-left: auto; white-space: nowrap; }
.alerta-desc { margin: 0 0 4px; font-size: 13px; color: #495057; }
.alerta-fecha { font-size: 12px; color: #6c757d; }

.diligencias-seccion {}
.diligencias-titulo { color: #2c3e50; border-bottom: 3px solid #667eea; padding-bottom: 10px; margin-bottom: 16px; }
.diligencias-scroll { max-height: 520px; overflow-y: auto; padding-right: 6px; display: flex; flex-direction: column; gap: 12px; }
.diligencia-card {
  border-left: 4px solid #667eea; padding: 14px 16px; border-radius: 0 10px 10px 0;
  background: #f8f9fa;
}
.dili-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px; }
.dili-field { font-size: 13px; color: #495057; }
.dili-label { font-weight: 700; color: #1a365d; }
.dili-desc { margin: 0; font-size: 13px; color: #6c757d; font-style: italic; line-height: 1.6; white-space: pre-wrap; }

.btn-analizar-tomos {
  padding: 12px 24px; background: linear-gradient(135deg, #28a745, #20c997);
  color: white; border: none; border-radius: 10px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; gap: 8px;
}
.btn-analizar-tomos:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-cancelar {
  padding: 12px 24px; background: #6c757d; color: white; border: none;
  border-radius: 10px; font-weight: 600; cursor: pointer;
}
.btn-cancelar:hover { background: #5a6268; }

.loading-box {
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  padding: 60px 20px; color: #6c757d; font-size: 16px;
}
.loading-box.sm { padding: 24px; font-size: 14px; flex-direction: row; justify-content: center; }
.empty-state { text-align: center; padding: 40px; color: #6c757d; }
.empty-state.sm { padding: 20px; font-size: 14px; }
</style>
