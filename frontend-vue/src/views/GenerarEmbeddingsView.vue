<template>
  <div class="page-wrapper">
    <AppHeader titulo="Generador de Embeddings" icono="fas fa-brain" />

    <div class="container">
      <div class="card">
        <div class="card-header text-center">
          <h4 class="mb-1"><i class="fas fa-brain me-2"></i>Generador de Embeddings</h4>
          <p class="text-muted mb-0">Procesar documentos para búsqueda semántica con IA</p>
        </div>
        <div class="card-body">
          <!-- Opciones -->
          <div class="row g-3 mb-4">
            <div class="col-md-6">
              <label class="form-label">Carpeta (opcional)</label>
              <select v-model="carpetaId" class="form-select">
                <option value="">Todas las carpetas</option>
                <option v-for="c in carpetas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
              </select>
            </div>
            <div class="col-md-6 d-flex align-items-end">
              <div class="form-check">
                <input class="form-check-input" type="checkbox" id="forzarRegen" v-model="forzarRegenerar" />
                <label class="form-check-label" for="forzarRegen">
                  Regenerar embeddings existentes
                </label>
              </div>
            </div>
          </div>

          <!-- Botón principal -->
          <div class="text-center mb-4">
            <button class="btn btn-generar btn-lg" @click="generarEmbeddings" :disabled="procesando">
              <span v-if="procesando">
                <i class="fas fa-spinner fa-spin me-2"></i>Generando embeddings…
              </span>
              <span v-else>
                <i class="fas fa-magic me-2"></i>Generar Embeddings
              </span>
            </button>
          </div>

          <!-- Progreso -->
          <div v-if="procesando || progreso > 0" class="mb-4">
            <div class="d-flex justify-content-between mb-1">
              <small class="text-muted">Progreso</small>
              <small class="text-muted">{{ progreso }}%</small>
            </div>
            <div class="progress" style="height: 12px; border-radius: 8px;">
              <div class="progress-bar bg-success progress-bar-striped progress-bar-animated"
                :style="{ width: progreso + '%' }"></div>
            </div>
          </div>

          <!-- Log -->
          <div v-if="logs.length" class="log-container">
            <div v-for="(l, i) in logs" :key="i" class="log-entry" :class="'log-' + l.tipo">
              <span class="log-time">{{ l.hora }}</span>
              <span class="ms-2">{{ l.mensaje }}</span>
            </div>
          </div>

          <!-- Resultado -->
          <div v-if="resultado" class="alert mt-4"
            :class="resultado.error ? 'alert-danger' : 'alert-success'">
            <i :class="resultado.error ? 'fas fa-times-circle' : 'fas fa-check-circle'" class="me-2"></i>
            <template v-if="!resultado.error">
              Completado: <strong>{{ resultado.procesados ?? 0 }}</strong> documentos procesados,
              <strong>{{ resultado.embeddings_generados ?? 0 }}</strong> embeddings creados.
            </template>
            <template v-else>{{ resultado.detalle }}</template>
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

const { get, post } = useApi()
const { showToast } = useToast()

const carpetas = ref([])
const carpetaId = ref('')
const forzarRegenerar = ref(false)
const procesando = ref(false)
const progreso = ref(0)
const logs = ref([])
const resultado = ref(null)

onMounted(async () => {
  try {
    carpetas.value = await get('/carpetas')
  } catch {
    showToast('Error al cargar carpetas', 'error')
  }
})

function agregarLog(mensaje, tipo = 'info') {
  const ahora = new Date().toLocaleTimeString()
  logs.value.push({ hora: ahora, mensaje, tipo })
}

async function generarEmbeddings() {
  procesando.value = true
  progreso.value = 0
  logs.value = []
  resultado.value = null

  const params = new URLSearchParams()
  if (carpetaId.value) params.set('carpeta_id', carpetaId.value)
  if (forzarRegenerar.value) params.set('forzar', 'true')

  agregarLog('Iniciando generación de embeddings…')

  // Simulación de progreso visual durante la petición
  const interval = setInterval(() => {
    if (progreso.value < 85) progreso.value += 5
  }, 800)

  try {
    const data = await post(`/admin/generar-embeddings?${params}`, {})
    clearInterval(interval)
    progreso.value = 100
    resultado.value = data
    agregarLog(`Completado: ${data.procesados ?? 0} documentos procesados`, 'success')
    showToast('Embeddings generados correctamente', 'success')
  } catch (e) {
    clearInterval(interval)
    progreso.value = 0
    resultado.value = { error: true, detalle: e.message || 'Error desconocido' }
    agregarLog('Error: ' + (e.message || ''), 'error')
    showToast('Error al generar embeddings', 'error')
  } finally {
    procesando.value = false
  }
}
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.container { max-width: 750px; margin: 0 auto; padding: 40px 20px; }
.card { background: white; border-radius: 16px; border: none; box-shadow: 0 10px 30px rgba(0,0,0,.15); }
.card-header { background: transparent; border-bottom: 1px solid #e9ecef; padding: 28px 32px; }
.card-body { padding: 32px; }
.btn-generar { background: linear-gradient(45deg, #28a745, #20c997); color: white; border: none; border-radius: 10px; padding: 14px 36px; font-weight: 700; transition: all .3s; }
.btn-generar:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(40,167,69,.3); color: white; }
.btn-generar:disabled { opacity: .65; cursor: not-allowed; }
.log-container { max-height: 280px; overflow-y: auto; background: #f8f9fa; border-radius: 10px; padding: 14px; font-family: monospace; font-size: .82rem; }
.log-entry { padding: 2px 0; }
.log-time { color: #6c757d; }
.log-success { color: #28a745; }
.log-error { color: #dc3545; }
</style>
