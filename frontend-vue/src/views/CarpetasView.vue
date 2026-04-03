<template>
  <div class="page-wrap">
    <AppHeader />
    <div class="container">

      <!-- ══ VISTA: LISTA DE CARPETAS ══ -->
      <div v-if="!carpetaActual">
        <div class="page-header">
          <h2>📁 Gestión de Expedientes</h2>
          <button v-if="esAdmin" class="btn-primary" @click="abrirModalCarpeta()">➕ Nueva Carpeta</button>
        </div>

        <div class="search-wrap">
          <input v-model="queryCarpetas" type="text" placeholder="Buscar carpetas..." @input="filtrarCarpetas" />
        </div>

        <div v-if="loading" class="msg-center">⏳ Cargando carpetas...</div>
        <div v-else-if="!carpetasFiltradas.length" class="msg-center">
          📁 No hay carpetas
          <br />
          <button v-if="esAdmin" class="btn-primary mt-12" @click="abrirModalCarpeta()">Crear primera carpeta</button>
        </div>

        <ul v-else class="folder-list">
          <li v-for="c in carpetasFiltradas" :key="c.id" class="folder-item">
            <div class="folder-info">
              <span class="folder-icon">📁</span>
              <div class="folder-details">
                <h4>{{ c.nombre || c.numero_carpeta }}</h4>
                <p>{{ c.descripcion || 'Sin descripción' }} · {{ c.total_tomos || 0 }} tomos · Creado por {{ c.creador || 'N/A' }}</p>
              </div>
            </div>
            <div class="folder-actions">
              <button class="btn-sm btn-success" @click="verAnalisisAdmin(c)">⚖️ Ver Análisis</button>
              <button class="btn-sm btn-info" @click="verTomos(c)">📄 Ver Tomos</button>
              <template v-if="esAdmin">
                <button class="btn-sm btn-edit" @click="abrirModalCarpeta(c)">✏️ Editar</button>
                <button class="btn-sm btn-danger" @click="eliminarCarpeta(c)">🗑️ Eliminar</button>
              </template>
            </div>
          </li>
        </ul>
      </div>

      <!-- ══ VISTA: TOMOS DE UNA CARPETA ══ -->
      <div v-else>
        <div class="breadcrumb">
          <span class="bc-link" @click="volverACarpetas">🏠 Carpetas</span>
          <span> → 📁 {{ carpetaActual.nombre || carpetaActual.numero_carpeta }}</span>
        </div>

        <div class="page-header">
          <h2>📄 Tomos del Expediente</h2>
          <div class="header-actions">
            <button v-if="esAdmin && seleccionados.length > 0" class="btn-sm btn-danger" @click="eliminarSeleccionados">
              🗑️ Eliminar ({{ seleccionados.length }})
            </button>
            <button v-if="esAdmin" class="btn-primary" @click="abrirModalTomo">⬆️ Subir Tomo</button>
          </div>
        </div>

        <div v-if="loadingTomos" class="msg-center">⏳ Cargando tomos...</div>
        <div v-else-if="!tomos.length" class="msg-center">
          📄 No hay tomos en este expediente
          <br />
          <button v-if="esAdmin" class="btn-primary mt-12" @click="abrirModalTomo">Subir primer tomo</button>
        </div>

        <ul v-else class="folder-list">
          <li v-for="t in tomos" :key="t.id" :class="['folder-item', { 'folder-item--processing': t.estado === 'procesando' }]">
            <div class="folder-item-row">
              <div class="folder-info">
                <input v-if="esAdmin" type="checkbox" class="tomo-check" :value="t.id" v-model="seleccionados" />
                <span class="folder-icon">📄</span>
                <div class="folder-details">
                  <h4>Tomo {{ t.numero_tomo }}: {{ t.nombre_archivo || t.nombre }}</h4>
                  <p>
                    📦 {{ formatMB(t.tamanio_bytes) }} MB ·
                    📑 {{ t.numero_paginas || 'N/A' }} páginas ·
                    <span :class="estadoClass(t.estado)">{{ estadoIcon(t.estado) }} {{ estadoTexto(t.estado) }}</span>
                  </p>
                  <p class="fecha-info">📅 Subido el {{ formatFecha(t.fecha_subida) }} por {{ t.usuario_subida || 'N/A' }}</p>
                </div>
              </div>
              <div class="folder-actions">
                <button v-if="esAdmin" class="btn-sm btn-info" @click="descargarTomo(t)">⬇️ Descargar</button>
                <button class="btn-sm btn-info" @click="verOCR(t)">👁️ Ver PDF</button>
                <template v-if="esAdmin">
                  <button class="btn-sm btn-primary-sm" @click="procesarOCR(t)">⚙️ Procesar OCR</button>
                  <button class="btn-sm btn-success" @click="analizarIA(t)">🤖 Analizar IA</button>
                  <button class="btn-sm btn-danger" @click="eliminarTomo(t)">🗑️</button>
                </template>
              </div>
            </div>

            <!-- ══ PANEL OCR EN VIVO ══ -->
            <transition name="ocr-expand">
              <div v-if="t.estado === 'procesando'" class="ocr-live-panel">
                <div class="ocr-scanner-wrap">

                  <!-- Documento animado con rayo de escaneo -->
                  <div class="doc-scan">
                    <div class="doc-body">
                      <div class="doc-line" v-for="n in 7" :key="n" :style="{ width: (35 + n * 8) + '%' }"></div>
                      <div class="scan-beam"></div>
                    </div>
                    <div class="doc-label">OCR</div>
                  </div>

                  <!-- Anillo de progreso circular -->
                  <div class="ocr-ring-wrap">
                    <svg class="ocr-ring" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
                      <circle class="ring-track" cx="60" cy="60" r="48" />
                      <circle class="ring-progress" cx="60" cy="60" r="48"
                        stroke-dasharray="301.6"
                        :stroke-dashoffset="301.6 - 301.6 * (t.progreso_ocr || 0) / 100"
                        transform="rotate(-90 60 60)"
                      />
                    </svg>
                    <div class="ring-center-text">
                      <span class="ring-pct">{{ t.progreso_ocr || 0 }}%</span>
                      <span class="ring-sub">completo</span>
                    </div>
                  </div>

                  <!-- Columna de información -->
                  <div class="ocr-info-col">
                    <div class="ocr-stat-row">
                      <span class="ocr-stat-icon">📑</span>
                      <span>Aprox. <strong>{{ Math.round((t.progreso_ocr || 0) * (t.numero_paginas || 100) / 100) }}</strong> de <strong>{{ t.numero_paginas || '…' }}</strong> páginas</span>
                    </div>
                    <div class="ocr-stat-row">
                      <span class="ocr-stat-icon">⚙️</span>
                      <span>Tesseract · CLAHE · Multi-PSM</span>
                    </div>
                    <div class="ocr-msg-row">
                      <span class="ocr-dot-pulse"></span>
                      <span class="ocr-msg-text">{{ mensajeActual }}</span>
                    </div>
                  </div>

                </div>
                <!-- Barra de progreso inferior -->
                <div class="ocr-progress-bar">
                  <div class="ocr-bar-fill" :style="{ width: (t.progreso_ocr || 0) + '%' }"></div>
                  <span class="ocr-bar-label">Procesando OCR...</span>
                </div>
                <div class="ocr-actions-row">
                  <button class="btn-stop-ocr" @click="detenerOCR(t)">⏹ Detener</button>
                </div>
              </div>
            </transition>
          </li>
        </ul>
      </div>
    </div>

    <!-- ══ MODAL: NUEVA / EDITAR CARPETA ══ -->
    <div v-if="modalCarpeta" class="modal-overlay" @click.self="cerrarModalCarpeta">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editandoCarpeta ? 'Editar Carpeta' : 'Nueva Carpeta' }}</h3>
          <button class="btn-close" @click="cerrarModalCarpeta">✕</button>
        </div>
        <form @submit.prevent="guardarCarpeta">
          <div class="form-group">
            <label>Nombre / Número de Carpeta *</label>
            <input v-model="formCarpeta.nombre" type="text" required placeholder="Ej: Carpeta 001 — Homicidios 2024" />
          </div>
          <div class="form-group">
            <label>Descripción</label>
            <textarea v-model="formCarpeta.descripcion" rows="3" placeholder="Descripción del expediente..."></textarea>
          </div>
          <p v-if="errorCarpeta" class="error-msg">{{ errorCarpeta }}</p>
          <div class="modal-actions">
            <button type="button" class="btn-cancel" @click="cerrarModalCarpeta">Cancelar</button>
            <button type="submit" class="btn-primary" :disabled="savingCarpeta">
              {{ savingCarpeta ? '⏳ Guardando...' : (editandoCarpeta ? '💾 Guardar Cambios' : '➕ Crear Carpeta') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ══ MODAL: SUBIR TOMO ══ -->
    <div v-if="modalTomo" class="modal-overlay" @click.self="cerrarModalTomo">
      <div class="modal">
        <div class="modal-header">
          <h3>⬆️ Subir Tomo</h3>
          <button class="btn-close" @click="cerrarModalTomo">✕</button>
        </div>
        <form @submit.prevent="subirTomo">
          <div class="form-group">
            <label>Número de Tomo *</label>
            <input v-model.number="formTomo.numero_tomo" type="number" min="1" required />
          </div>
          <div class="form-group">
            <label>Nombre del Tomo *</label>
            <input v-model="formTomo.nombre" type="text" required placeholder="Ej: Tomo 1 — Declaración inicial" />
          </div>
          <div class="form-group">
            <label>Descripción</label>
            <textarea v-model="formTomo.descripcion" rows="2" placeholder="Descripción opcional..."></textarea>
          </div>
          <div class="form-group">
            <label>Archivo PDF *</label>
            <input type="file" accept=".pdf" required @change="onArchivoSeleccionado" />
          </div>
          <div v-if="subiendoTomo" class="progreso-wrap">
            <p>{{ progresoTexto }}</p>
            <div class="barra-fondo"><div class="barra-fill" :style="{ width: progresoPct + '%' }"></div></div>
          </div>
          <p v-if="errorTomo" class="error-msg">{{ errorTomo }}</p>
          <div class="modal-actions">
            <button type="button" class="btn-cancel" @click="cerrarModalTomo" :disabled="subiendoTomo">Cancelar</button>
            <button type="submit" class="btn-primary" :disabled="subiendoTomo">
              {{ subiendoTomo ? '⏳ Subiendo...' : '⬆️ Subir Tomo' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'

const { get, post, put, del, postFormData, download } = useApi()
const { showToast } = useToast()
const router = useRouter()
const auth = useAuthStore()

const esAdmin = computed(() => auth.hasAnyRole('admin', 'Admin', 'administrador', 'Administrador'))

// Estado carpetas
const todasCarpetas = ref([])
const carpetasFiltradas = ref([])
const queryCarpetas = ref('')
const loading = ref(true)
let autoRefresh = null

// Estado tomos
const carpetaActual = ref(null)
const tomos = ref([])
const loadingTomos = ref(false)
const seleccionados = ref([])

// Modal carpeta
const modalCarpeta = ref(false)
const editandoCarpeta = ref(null)
const formCarpeta = ref({ nombre: '', descripcion: '' })
const savingCarpeta = ref(false)
const errorCarpeta = ref('')

// Modal tomo
const modalTomo = ref(false)
const formTomo = ref({ numero_tomo: 1, nombre: '', descripcion: '' })
const archivoTomo = ref(null)
const subiendoTomo = ref(false)
const progresoTexto = ref('Subiendo archivo...')
const progresoPct = ref(0)
const errorTomo = ref('')

// OCR en vivo
const mensajesOCR = [
  '🔍 Escaneando páginas del expediente...',
  '🎨 Ajustando contraste y nitidez de imagen...',
  '🔤 Reconociendo caracteres con Tesseract...',
  '📅 Identificando fechas y acuerdos judiciales...',
  '👤 Detectando nombres y personas involucradas...',
  '📍 Localizando entidades geográficas mexicanas...',
  '⚖️ Aplicando corrector legal inteligente...',
  '🧹 Eliminando ruido del escáner...',
  '📊 Indexando contenido para búsqueda avanzada...',
  '✨ Optimizando calidad del texto extraído...',
]
const mensajeIdx = ref(0)
const mensajeActual = computed(() => mensajesOCR[mensajeIdx.value % mensajesOCR.length])
let msgInterval = null
let fastRefreshInterval = null

onMounted(async () => {
  await cargarCarpetas()
  msgInterval = setInterval(() => {
    mensajeIdx.value = (mensajeIdx.value + 1) % mensajesOCR.length
  }, 2800)
  autoRefresh = setInterval(async () => {
    try {
      if (!carpetaActual.value) await cargarCarpetas()
      else await cargarTomos(carpetaActual.value.id)
    } catch (e) {
      if (e.status === 401 || e.status === 403) {
        clearInterval(autoRefresh)
        autoRefresh = null
      }
    }
  }, 15000)
})

onUnmounted(() => {
  if (autoRefresh) clearInterval(autoRefresh)
  if (msgInterval) clearInterval(msgInterval)
  if (fastRefreshInterval) clearInterval(fastRefreshInterval)
})

async function cargarCarpetas() {
  loading.value = true
  try {
    todasCarpetas.value = await get('/carpetas')
    filtrarCarpetas()
  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

function filtrarCarpetas() {
  const q = queryCarpetas.value.toLowerCase()
  carpetasFiltradas.value = q
    ? todasCarpetas.value.filter(c =>
        (c.nombre || c.numero_carpeta || '').toLowerCase().includes(q) ||
        (c.descripcion || '').toLowerCase().includes(q)
      )
    : [...todasCarpetas.value]
}

async function verTomos(carpeta) {
  carpetaActual.value = carpeta
  seleccionados.value = []
  await cargarTomos(carpeta.id)
  if (tomos.value.some(t => t.estado === 'procesando')) iniciarFastRefresh()
}

async function cargarTomos(carpetaId) {
  loadingTomos.value = true
  try {
    tomos.value = await get(`/tomos/${carpetaId}`)
  } catch (e) {
    showToast(e.message, 'error')
  } finally {
    loadingTomos.value = false
  }
}

function volverACarpetas() {
  carpetaActual.value = null
  seleccionados.value = []
}

function verOCR(tomo) {
  router.push({ name: 'visor-pdf', query: { tomo_id: tomo.id, nombre: tomo.nombre_archivo || tomo.nombre } })
}

async function descargarTomo(tomo) {
  try {
    await download(`/tomos/${tomo.id}/descargar`, tomo.nombre_archivo || tomo.nombre)
    showToast('Descarga iniciada', 'success')
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function procesarOCR(tomo) {
  if (!confirm(`¿Iniciar procesamiento OCR del tomo "${tomo.nombre_archivo || tomo.nombre}"?`)) return
  try {
    await put(`/tomos/${tomo.id}/reanalizar`, {})
    showToast('OCR iniciado. Procesando en segundo plano...', 'success')
    await cargarTomos(carpetaActual.value.id)
    iniciarFastRefresh()
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function detenerOCR(tomo) {
  if (!confirm(`¿Detener el OCR del tomo "${tomo.nombre_archivo || tomo.nombre}"?`)) return
  try {
    await del(`/tomos/${tomo.id}/cancelar-ocr`)
    showToast('OCR detenido. El tomo volvió a estado pendiente.', 'success')
    clearFastRefresh()
    await cargarTomos(carpetaActual.value.id)
  } catch (e) {
    showToast(e.message, 'error')
  }
}

function iniciarFastRefresh() {
  if (fastRefreshInterval) return
  fastRefreshInterval = setInterval(async () => {
    if (!carpetaActual.value) { clearFastRefresh(); return }
    try {
      await cargarTomos(carpetaActual.value.id)
      if (!tomos.value.some(t => t.estado === 'procesando')) clearFastRefresh()
    } catch (e) {
      if (e.status === 401 || e.status === 403) clearFastRefresh()
    }
  }, 3000)
}

function clearFastRefresh() {
  if (fastRefreshInterval) { clearInterval(fastRefreshInterval); fastRefreshInterval = null }
}

function analizarIA(tomo) {
  router.push({ name: 'analisis-ia', query: { tomo_id: tomo.id, nombre: tomo.nombre_archivo || tomo.nombre } })
}

async function eliminarTomo(tomo) {
  if (!confirm(`¿Eliminar el tomo "${tomo.nombre_archivo || tomo.nombre}"?`)) return
  try {
    await del(`/tomos/${tomo.id}`)
    showToast('Tomo eliminado', 'success')
    await cargarTomos(carpetaActual.value.id)
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function eliminarSeleccionados() {
  if (!confirm(`¿Eliminar ${seleccionados.value.length} tomo(s) seleccionados?`)) return
  try {
    for (const id of seleccionados.value) await del(`/tomos/${id}`)
    seleccionados.value = []
    showToast('Tomos eliminados', 'success')
    await cargarTomos(carpetaActual.value.id)
  } catch (e) {
    showToast(e.message, 'error')
  }
}

function verAnalisisAdmin(carpeta) {
  router.push({ name: 'analisis-ia', query: { carpeta_id: carpeta.id, carpeta_nombre: carpeta.nombre || carpeta.numero_carpeta } })
}

// Modal carpeta
function abrirModalCarpeta(carpeta = null) {
  editandoCarpeta.value = carpeta
  formCarpeta.value = carpeta
    ? { nombre: carpeta.nombre || carpeta.numero_carpeta || '', descripcion: carpeta.descripcion || '' }
    : { nombre: '', descripcion: '' }
  errorCarpeta.value = ''
  modalCarpeta.value = true
}

function cerrarModalCarpeta() { modalCarpeta.value = false; editandoCarpeta.value = null }

async function guardarCarpeta() {
  if (!formCarpeta.value.nombre.trim()) { errorCarpeta.value = 'El nombre es requerido'; return }
  savingCarpeta.value = true
  errorCarpeta.value = ''
  try {
    if (editandoCarpeta.value) {
      await put(`/carpetas/${editandoCarpeta.value.id}`, formCarpeta.value)
      showToast('Carpeta actualizada', 'success')
    } else {
      await post('/carpetas', formCarpeta.value)
      showToast('Carpeta creada', 'success')
    }
    cerrarModalCarpeta()
    await cargarCarpetas()
  } catch (e) {
    errorCarpeta.value = e.message
  } finally {
    savingCarpeta.value = false
  }
}

async function eliminarCarpeta(carpeta) {
  if (!confirm(`¿Eliminar la carpeta "${carpeta.nombre || carpeta.numero_carpeta}"?\nSe eliminarán todos sus tomos.`)) return
  try {
    await del(`/carpetas/${carpeta.id}`)
    showToast('Carpeta eliminada', 'success')
    await cargarCarpetas()
  } catch (e) {
    showToast(e.message, 'error')
  }
}

// Modal tomo
async function abrirModalTomo() {
  const sig = tomos.value.length > 0 ? Math.max(...tomos.value.map(t => t.numero_tomo || 0)) + 1 : 1
  const nombreCarpeta = carpetaActual.value?.nombre || carpetaActual.value?.numero_carpeta || ''
  formTomo.value = { numero_tomo: sig, nombre: `${nombreCarpeta}_Tomo ${sig}`, descripcion: '' }
  archivoTomo.value = null
  errorTomo.value = ''
  progresoPct.value = 0
  modalTomo.value = true
}

function cerrarModalTomo() {
  if (subiendoTomo.value) return
  modalTomo.value = false
}

function onArchivoSeleccionado(e) { archivoTomo.value = e.target.files[0] || null }

async function subirTomo() {
  if (!archivoTomo.value) { errorTomo.value = 'Selecciona un archivo PDF'; return }
  subiendoTomo.value = true
  errorTomo.value = ''
  progresoPct.value = 20
  progresoTexto.value = 'Subiendo archivo...'
  try {
    const fd = new FormData()
    fd.append('archivo', archivoTomo.value)
    fd.append('numero_tomo', formTomo.value.numero_tomo)
    fd.append('nombre', formTomo.value.nombre)
    fd.append('descripcion', formTomo.value.descripcion || '')
    fd.append('carpeta_id', carpetaActual.value.id)
    progresoPct.value = 50
    progresoTexto.value = 'Procesando...'
    await postFormData('/tomos/subir', fd)
    progresoPct.value = 100
    showToast('Tomo subido. El OCR se procesará en segundo plano.', 'success')
    // Cerrar modal directamente (subiendoTomo aún es true aquí)
    modalTomo.value = false
    await cargarTomos(carpetaActual.value.id)
    // Arrancar polling de progreso si algún tomo está procesando
    iniciarFastRefresh()
  } catch (e) {
    errorTomo.value = e.message
    progresoPct.value = 0
  } finally {
    subiendoTomo.value = false
  }
}

// Helpers
function formatFecha(f) { return f ? new Date(f).toLocaleDateString('es-MX') : 'N/A' }
function formatMB(bytes) { return bytes ? (bytes / 1048576).toFixed(1) : 'N/A' }
function estadoClass(e) { return { completado: 'ok', procesado: 'ok', procesando: 'proc', pendiente: 'pen', error: 'err' }[e] || 'pen' }
function estadoIcon(e)  { return { completado: '✅', procesado: '✅', procesando: '⏳', pendiente: '⏸️', error: '❌' }[e] || '❓' }
function estadoTexto(e) { return { completado: 'Completado', procesado: 'Procesado', procesando: 'Procesando', pendiente: 'Pendiente', error: 'Error' }[e] || e }
</script>

<style scoped>
.page-wrap { min-height: 100vh; background: #f8f9fa; }
.container { max-width: 1200px; margin: 0 auto; padding: 30px; }

.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { color: #1a365d; font-size: 22px; }
.header-actions { display: flex; gap: 10px; align-items: center; }
.mt-12 { margin-top: 12px; display: inline-block; }

.breadcrumb { margin-bottom: 16px; font-size: 15px; color: #666; }
.bc-link { color: #2c5aa0; cursor: pointer; font-weight: 600; }
.bc-link:hover { text-decoration: underline; }

.search-wrap { margin-bottom: 20px; }
.search-wrap input {
  width: 100%; padding: 12px 20px; border: 2px solid #e9ecef;
  border-radius: 25px; font-size: 15px; outline: none; transition: border-color 0.2s;
}
.search-wrap input:focus { border-color: #2c5aa0; }

.msg-center { padding: 40px; text-align: center; color: #6c757d; font-size: 16px; }
.folder-list { list-style: none; }

.folder-item {
  background: #fff; margin: 12px 0; padding: 20px 24px; border-radius: 12px;
  box-shadow: 0 3px 10px rgba(0,0,0,0.07); display: block;
  transition: transform 0.2s, box-shadow 0.2s;
}
.folder-item:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.12); }
.folder-item--processing {
  border-left: 4px solid #f6ad55;
  animation: ocr-glow 2.5s ease-in-out infinite alternate;
}
@keyframes ocr-glow {
  from { box-shadow: 0 3px 10px rgba(0,0,0,0.07); }
  to   { box-shadow: 0 8px 25px rgba(44,90,160,0.25); }
}
.folder-item-row { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.folder-info { display: flex; align-items: center; gap: 16px; flex: 1; }
.folder-icon { font-size: 28px; }
.folder-details h4 { color: #1a365d; font-size: 16px; font-weight: 700; margin-bottom: 4px; }
.folder-details p { color: #6c757d; font-size: 13px; margin-bottom: 2px; }
.fecha-info { font-size: 12px !important; color: #999 !important; }
.tomo-check { width: 18px; height: 18px; cursor: pointer; }
.folder-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.btn-sm { padding: 8px 14px; border: none; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600; transition: opacity 0.2s, transform 0.2s; color: white; }
.btn-sm:hover { opacity: 0.85; transform: translateY(-1px); }
.btn-success   { background: linear-gradient(135deg, #28a745, #20c997); }
.btn-info      { background: #2c5aa0; }
.btn-edit      { background: #ffc107; color: #333; }
.btn-danger    { background: #dc3545; }
.btn-primary-sm { background: linear-gradient(135deg, #1a365d, #2c5aa0); }

.btn-primary {
  background: linear-gradient(135deg, #1a365d, #2c5aa0); color: white; border: none;
  padding: 11px 22px; border-radius: 25px; cursor: pointer; font-weight: 600; font-size: 14px;
  transition: opacity 0.2s, transform 0.2s;
}
.btn-primary:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.65; cursor: not-allowed; }
.btn-cancel { background: #6c757d; color: white; border: none; padding: 11px 22px; border-radius: 25px; cursor: pointer; font-weight: 600; }

.ok   { color: #28a745; font-weight: 700; }
.proc { color: #ffc107; font-weight: 700; }
.pen  { color: #6c757d; font-weight: 700; }
.err  { color: #dc3545; font-weight: 700; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #fff; border-radius: 16px; padding: 28px; width: 92%; max-width: 480px; max-height: 95vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.25); animation: popIn 0.2s ease-out; }
@keyframes popIn { from { opacity:0; transform:scale(0.95); } to { opacity:1; transform:scale(1); } }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.modal-header h3 { color: #1a365d; font-size: 18px; }
.btn-close { background: none; border: none; font-size: 22px; cursor: pointer; color: #666; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-weight: 600; color: #333; font-size: 13px; }
.form-group input, .form-group textarea { width: 100%; padding: 10px 14px; border: 2px solid #e9ecef; border-radius: 10px; font-size: 14px; transition: border-color 0.2s; }
.form-group input:focus, .form-group textarea:focus { outline: none; border-color: #2c5aa0; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }
.error-msg { color: #dc3545; font-size: 13px; margin-top: 8px; }
.progreso-wrap { margin: 12px 0; }
.progreso-wrap p { font-size: 13px; color: #666; margin-bottom: 6px; }
.barra-fondo { background: #e9ecef; border-radius: 10px; height: 8px; overflow: hidden; }
.barra-fill { background: linear-gradient(135deg, #28a745, #20c997); height: 100%; transition: width 0.3s; }
/* ══ OCR LIVE PANEL ══ */
.ocr-live-panel {
  margin-top: 16px;
  background: linear-gradient(135deg, rgba(26,54,93,0.04), rgba(44,90,160,0.08));
  border: 1px solid rgba(44,90,160,0.18);
  border-radius: 12px;
  padding: 18px 20px 12px;
  overflow: hidden;
}
.ocr-scanner-wrap {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

/* Documento animado */
.doc-scan {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.doc-body {
  position: relative;
  width: 60px;
  height: 76px;
  background: #fff;
  border-radius: 4px 10px 4px 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
}
.doc-body::before {
  content: '';
  position: absolute;
  top: 0; right: 0;
  width: 14px; height: 14px;
  background: linear-gradient(225deg, #e9ecef 48%, transparent 52%);
  border-bottom-left-radius: 4px;
}
.doc-line {
  height: 4px;
  background: #d0d7e3;
  border-radius: 2px;
  min-width: 20%;
}
.scan-beam {
  position: absolute;
  left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent, rgba(44,90,160,0.9), rgba(100,160,255,1), rgba(44,90,160,0.9), transparent);
  box-shadow: 0 0 8px 2px rgba(44,90,160,0.5);
  animation: scan-sweep 1.6s ease-in-out infinite;
  top: 0;
}
@keyframes scan-sweep {
  0%   { top: 0; opacity: 0.9; }
  50%  { top: calc(100% - 3px); opacity: 1; }
  100% { top: 0; opacity: 0.9; }
}
.doc-label {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 2px;
  color: #2c5aa0;
  text-transform: uppercase;
}

/* Anillo SVG */
.ocr-ring-wrap {
  position: relative;
  width: 90px;
  height: 90px;
  flex-shrink: 0;
}
.ocr-ring {
  width: 90px;
  height: 90px;
  animation: ring-spin-glow 3s ease-in-out infinite alternate;
}
@keyframes ring-spin-glow {
  from { filter: drop-shadow(0 0 3px rgba(44,90,160,0.3)); }
  to   { filter: drop-shadow(0 0 10px rgba(44,90,160,0.7)); }
}
.ring-track {
  fill: none;
  stroke: #e9ecef;
  stroke-width: 10;
}
.ring-progress {
  fill: none;
  stroke: url(#ring-gradient);
  stroke: #2c5aa0;
  stroke-width: 10;
  stroke-linecap: round;
  transition: stroke-dashoffset 1s ease-out;
}
.ring-center-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.ring-pct {
  font-size: 20px;
  font-weight: 800;
  color: #1a365d;
  line-height: 1;
}
.ring-sub {
  font-size: 9px;
  color: #6c757d;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Columna de info */
.ocr-info-col {
  flex: 1;
  min-width: 180px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ocr-stat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #444;
}
.ocr-stat-icon { font-size: 15px; }
.ocr-msg-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}
.ocr-dot-pulse {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: #2c5aa0;
  border-radius: 50%;
  flex-shrink: 0;
  animation: dot-pulse 1.4s ease-in-out infinite;
}
@keyframes dot-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.5); opacity: 0.5; }
}
.ocr-msg-text {
  font-size: 12px;
  color: #2c5aa0;
  font-weight: 600;
  animation: msg-fadein 0.5s ease;
}
@keyframes msg-fadein {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Barra de progreso inferior */
.ocr-progress-bar {
  position: relative;
  margin-top: 14px;
  background: rgba(44,90,160,0.12);
  border-radius: 10px;
  height: 10px;
  overflow: hidden;
}
.ocr-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #1a365d, #2c5aa0, #4a9ad4);
  border-radius: 10px;
  transition: width 1.2s ease-out;
  position: relative;
  overflow: hidden;
}
.ocr-bar-fill::after {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 60%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent);
  animation: bar-shimmer 2s ease-in-out infinite;
}
@keyframes bar-shimmer {
  0%   { left: -60%; }
  100% { left: 120%; }
}
.ocr-bar-label {
  display: none;
}

/* Transición de apertura del panel */
.ocr-expand-enter-active { transition: all 0.4s ease-out; }
.ocr-expand-leave-active { transition: all 0.3s ease-in; }
.ocr-expand-enter-from,
.ocr-expand-leave-to { max-height: 0; opacity: 0; margin-top: 0; padding: 0 20px; }
.ocr-expand-enter-to,
.ocr-expand-leave-from { max-height: 200px; opacity: 1; }

/* Botón detener OCR */
.ocr-actions-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}
.btn-stop-ocr {
  background: none;
  border: 1px solid #dc3545;
  color: #dc3545;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.btn-stop-ocr:hover {
  background: #dc3545;
  color: #fff;
}
</style>
