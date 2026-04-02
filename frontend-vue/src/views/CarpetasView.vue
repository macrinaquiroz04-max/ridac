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
          <li v-for="t in tomos" :key="t.id" class="folder-item">
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

onMounted(async () => {
  await cargarCarpetas()
  autoRefresh = setInterval(async () => {
    if (!carpetaActual.value) await cargarCarpetas()
    else await cargarTomos(carpetaActual.value.id)
  }, 15000)
})

onUnmounted(() => {
  if (autoRefresh) clearInterval(autoRefresh)
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
    await post(`/tomos/${tomo.id}/procesar-ocr`, {})
    showToast('OCR iniciado. Puede demorar varios minutos.', 'success')
    await cargarTomos(carpetaActual.value.id)
  } catch (e) {
    showToast(e.message, 'error')
  }
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
    cerrarModalTomo()
    await cargarTomos(carpetaActual.value.id)
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
  box-shadow: 0 3px 10px rgba(0,0,0,0.07); display: flex; justify-content: space-between;
  align-items: center; gap: 16px; transition: transform 0.2s, box-shadow 0.2s;
}
.folder-item:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.12); }
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
</style>
