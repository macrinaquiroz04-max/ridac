<template>
  <div class="page-wrapper">
    <AppHeader titulo="OCR Profesional" icono="fas fa-file-pdf" />

    <div class="main-container">
      <!-- Encabezado estilo PDF24 -->
      <div class="pdf24-header mb-4">
        <div class="pdf24-logo">OCR Pro</div>
        <p class="text-muted">Extrae texto de documentos con tecnología avanzada de reconocimiento</p>
      </div>

      <!-- Selector de velocidad/modelo -->
      <div class="config-section mb-4">
        <h5 class="mb-3"><i class="fas fa-sliders-h me-2"></i>Modelo de procesamiento</h5>
        <div class="speed-model-cards">
          <div v-for="m in modelos" :key="m.key"
            class="speed-card"
            :class="{ selected: modeloSeleccionado === m.key }"
            @click="modeloSeleccionado = m.key">
            <div class="fw-bold">{{ m.nombre }}</div>
            <div class="text-muted small mt-1">{{ m.descripcion }}</div>
            <span v-if="m.recomendado" class="badge bg-success mt-2">Recomendado</span>
            <div class="check-icon" v-if="modeloSeleccionado === m.key">✓</div>
          </div>
        </div>
      </div>

      <!-- Selector de tomo existente -->
      <div class="config-section mb-4">
        <h5 class="mb-3"><i class="fas fa-folder-open me-2"></i>Procesar tomo existente</h5>
        <div class="row g-3 align-items-end">
          <div class="col-md-8">
            <select v-model="tomoId" class="form-select" :disabled="cargandoTomos">
              <option value="">— Seleccione un tomo —</option>
              <option v-for="t in tomos" :key="t.id" :value="t.id">{{ t.nombre }}</option>
            </select>
          </div>
          <div class="col-md-4">
            <button class="btn btn-primary w-100" @click="iniciarOCR" :disabled="!tomoId || procesando">
              <span v-if="procesando"><i class="fas fa-spinner fa-spin me-2"></i>Procesando…</span>
              <span v-else><i class="fas fa-play me-2"></i>Iniciar OCR</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Progreso -->
      <div v-if="procesando || progreso > 0" class="config-section mb-4">
        <div class="d-flex justify-content-between mb-2">
          <span class="fw-semibold">{{ mensajeProgreso }}</span>
          <span class="fw-bold">{{ progreso }}%</span>
        </div>
        <div class="progress" style="height: 14px; border-radius: 10px;">
          <div class="progress-bar bg-success progress-bar-striped progress-bar-animated"
            :style="{ width: progreso + '%' }"></div>
        </div>
        <div class="mt-2 text-muted small">Modelo: <strong>{{ modeloSeleccionado }}</strong></div>
      </div>

      <!-- Resultado -->
      <div v-if="resultado" class="config-section">
        <div class="alert" :class="resultado.ok ? 'alert-success' : 'alert-danger'">
          <i :class="resultado.ok ? 'fas fa-check-circle' : 'fas fa-times-circle'" class="me-2"></i>
          <template v-if="resultado.ok">
            OCR completado: <strong>{{ resultado.paginas_procesadas ?? 0 }}</strong> páginas procesadas,
            confianza promedio <strong>{{ resultado.confianza_promedio ?? 0 }}%</strong>.
          </template>
          <template v-else>{{ resultado.mensaje }}</template>
        </div>
        <div v-if="resultado.texto_muestra" class="mt-3">
          <label class="form-label fw-semibold">Muestra del texto extraído:</label>
          <pre class="texto-muestra">{{ resultado.texto_muestra }}</pre>
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

const { get, post } = useApi()
const { showToast } = useToast()

const modelos = [
  { key: 'rapido', nombre: 'Rápido', descripcion: 'Menor precisión, ideal para textos claros.', recomendado: false },
  { key: 'balanceado', nombre: 'Balanceado', descripcion: 'Equilibrio entre velocidad y precisión.', recomendado: true },
  { key: 'preciso', nombre: 'Preciso', descripcion: 'Máxima precisión, más tiempo de procesamiento.', recomendado: false }
]

const tomos = ref([])
const tomoId = ref('')
const cargandoTomos = ref(false)
const procesando = ref(false)
const progreso = ref(0)
const mensajeProgreso = ref('Iniciando…')
const resultado = ref(null)
const modeloSeleccionado = ref('balanceado')

onMounted(async () => {
  cargandoTomos.value = true
  try {
    const data = await get('/tomos')
    tomos.value = data?.items ?? data ?? []
  } catch {
    showToast('Error al cargar tomos', 'error')
  } finally {
    cargandoTomos.value = false
  }
})

async function iniciarOCR() {
  if (!tomoId.value) return
  procesando.value = true
  progreso.value = 0
  resultado.value = null
  mensajeProgreso.value = 'Iniciando OCR…'

  const interval = setInterval(() => {
    if (progreso.value < 80) {
      progreso.value += 10
      const pasos = ['Leyendo páginas', 'Preprocesando imágenes', 'Aplicando OCR', 'Generando texto']
      mensajeProgreso.value = pasos[Math.floor(progreso.value / 25)] || 'Procesando…'
    }
  }, 900)

  try {
    const data = await post(`/tomos/${tomoId.value}/ocr-pdf24`, { modelo: modeloSeleccionado.value })
    clearInterval(interval)
    progreso.value = 100
    mensajeProgreso.value = 'Completado'
    resultado.value = { ok: true, ...data }
    showToast('OCR completado con éxito', 'success')
  } catch (e) {
    clearInterval(interval)
    progreso.value = 0
    resultado.value = { ok: false, mensaje: e.message || 'Error al procesar' }
    showToast('Error en el OCR', 'error')
  } finally {
    procesando.value = false
  }
}
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; }
.main-container { background: rgba(255,255,255,.95); backdrop-filter: blur(10px); border-radius: 20px; max-width: 1000px; margin: 0 auto; padding: 32px; box-shadow: 0 20px 40px rgba(0,0,0,.12); }
.pdf24-header { text-align: center; }
.pdf24-logo { font-size: 2.2rem; font-weight: 800; background: linear-gradient(45deg, #FF6B35, #F7931E); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.config-section { background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius: 14px; padding: 24px; border: 1px solid #dee2e6; }
.speed-model-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
.speed-card { background: white; border: 2px solid #e9ecef; border-radius: 12px; padding: 20px; cursor: pointer; transition: all .3s; position: relative; }
.speed-card:hover { border-color: #007bff; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,123,255,.15); }
.speed-card.selected { border-color: #28a745; background: #f0fff4; }
.check-icon { position: absolute; top: 12px; right: 14px; color: #28a745; font-size: 1.2rem; font-weight: 800; }
.texto-muestra { background: #f8f9fa; border-radius: 8px; padding: 14px; font-size: .82rem; max-height: 250px; overflow: auto; white-space: pre-wrap; }
</style>
