<template>
  <div class="page-wrapper">
    <AppHeader titulo="Extracción OCR" icono="fas fa-file-alt" />

    <div class="container">
      <!-- Selector de tomo -->
      <div class="card mb-4">
        <div class="card-body">
          <div class="row g-3 align-items-end">
            <div class="col-md-8">
              <label class="form-label">Seleccionar Tomo</label>
              <select v-model="tomoId" class="form-select" :disabled="cargandoTomos">
                <option value="">— Seleccione un tomo —</option>
                <option v-for="t in tomos" :key="t.id" :value="t.id">
                  {{ t.nombre }} ({{ t.total_paginas ?? '?' }} págs.)
                </option>
              </select>
            </div>
            <div class="col-md-4">
              <button class="btn btn-primary w-100" @click="cargarDocumento" :disabled="!tomoId || cargando">
                <span v-if="cargando"><i class="fas fa-spinner fa-spin me-2"></i>Cargando…</span>
                <span v-else><i class="fas fa-download me-2"></i>Cargar Documento</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Área de upload drag & drop -->
      <div
        class="upload-area"
        :class="{ dragover: dragging }"
        @dragover.prevent="dragging = true"
        @dragleave="dragging = false"
        @drop.prevent="onDrop"
        @click="$refs.fileInput.click()"
      >
        <i class="fas fa-cloud-upload-alt upload-icon fa-3x"></i>
        <h5 class="mt-3">Arrastra un PDF aquí o haz clic para seleccionar</h5>
        <p class="text-muted">Extrae texto mediante OCR directamente</p>
        <input ref="fileInput" type="file" accept=".pdf,.png,.jpg,.jpeg" class="d-none" @change="onFileSelect" />
      </div>

      <!-- Progreso -->
      <div v-if="progreso > 0 || procesando" class="card mt-4">
        <div class="card-body">
          <div class="d-flex justify-content-between mb-1">
            <span>Procesando OCR…</span>
            <span>{{ progreso }}%</span>
          </div>
          <div class="progress" style="height: 10px; border-radius: 8px;">
            <div class="progress-bar bg-primary progress-bar-striped progress-bar-animated"
              :style="{ width: progreso + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- Resultado -->
      <div v-if="documento" class="card mt-4">
        <div class="card-header d-flex justify-content-between align-items-center">
          <h5 class="mb-0"><i class="fas fa-file-alt me-2"></i>Documento: {{ documento.nombre }}</h5>
          <div class="d-flex gap-2">
            <span class="badge bg-info">{{ documento.total_paginas }} página(s)</span>
            <button class="btn btn-sm btn-outline-secondary" @click="copiarTexto">
              <i class="fas fa-copy me-2"></i>Copiar texto
            </button>
          </div>
        </div>
        <div class="card-body">
          <div class="info-grid mb-3">
            <div><strong>Estado OCR:</strong> {{ documento.estado_ocr || '—' }}</div>
            <div><strong>Idioma:</strong> {{ documento.idioma || 'es' }}</div>
            <div><strong>Confianza:</strong> {{ documento.confianza_promedio ?? '—' }}%</div>
            <div><strong>Tamaño:</strong> {{ formatBytes(documento.tamanio) }}</div>
          </div>
          <div class="texto-ocr-container">
            <pre class="texto-ocr">{{ documento.texto_completo || 'Sin texto extraído' }}</pre>
          </div>
        </div>
      </div>
    </div>

    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import AppHeader from '@/components/AppHeader.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const { get } = useApi()
const { showToast } = useToast()

const tomos = ref([])
const tomoId = ref('')
const cargandoTomos = ref(false)
const cargando = ref(false)
const procesando = ref(false)
const progreso = ref(0)
const dragging = ref(false)
const documento = ref(null)
const fileInput = ref(null)

onMounted(async () => {
  cargandoTomos.value = true
  try {
    const data = await get('/tomos/usuario/permisos')
    tomos.value = data?.tomos ?? data ?? []
  } catch {
    showToast('Error al cargar tomos', 'error')
  } finally {
    cargandoTomos.value = false
  }
})

async function cargarDocumento() {
  if (!tomoId.value) return
  cargando.value = true
  try {
    const data = await get(`/tomos/${tomoId.value}/documento`)
    documento.value = data
  } catch (e) {
    showToast('Error al cargar documento: ' + (e.message || ''), 'error')
  } finally {
    cargando.value = false
  }
}

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files[0]
  if (file) procesarArchivo(file)
}

function onFileSelect(e) {
  const file = e.target.files[0]
  if (file) procesarArchivo(file)
}

async function procesarArchivo(file) {
  procesando.value = true
  progreso.value = 0

  const interval = setInterval(() => {
    if (progreso.value < 85) progreso.value += 8
  }, 600)

  try {
    const formData = new FormData()
    formData.append('archivo', file)

    const { useAuthStore } = await import('@/stores/auth')
    const auth = useAuthStore()
    const apiUrl = import.meta.env.VITE_API_URL || '/api'

    const resp = await fetch(`${apiUrl}/ocr/extraer`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: formData
    })
    if (!resp.ok) throw new Error('Error al procesar archivo')
    const data = await resp.json()

    clearInterval(interval)
    progreso.value = 100
    documento.value = data
    showToast('Extracción completada', 'success')
  } catch (e) {
    clearInterval(interval)
    progreso.value = 0
    showToast('Error: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}

function copiarTexto() {
  if (!documento.value?.texto_completo) return
  navigator.clipboard.writeText(documento.value.texto_completo)
  showToast('Texto copiado', 'info')
}

function formatBytes(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: linear-gradient(135deg, #1a365d 0%, #2c5aa0 100%); }
.container { max-width: 1100px; margin: 0 auto; padding: 30px 20px; }
.card { background: white; border-radius: 12px; border: none; box-shadow: 0 4px 15px rgba(0,0,0,.12); }
.card-header { background: #f8f9fa; border-bottom: 1px solid #e9ecef; padding: 16px 24px; border-radius: 12px 12px 0 0; }
.card-body { padding: 24px; }
.upload-area { border: 3px dashed #adb5bd; border-radius: 20px; padding: 3rem; text-align: center; background: rgba(255,255,255,.9); cursor: pointer; transition: all .3s; }
.upload-area:hover, .upload-area.dragover { border-color: #007bff; background: rgba(0,123,255,.05); transform: scale(1.01); }
.upload-icon { color: #1a365d; transition: transform .3s; }
.upload-area:hover .upload-icon { transform: scale(1.1) rotateY(180deg); }
.info-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; font-size: .9rem; }
.texto-ocr-container { max-height: 500px; overflow-y: auto; }
.texto-ocr { white-space: pre-wrap; font-size: .85rem; background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 0; }
</style>
