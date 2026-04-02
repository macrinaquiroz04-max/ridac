<template>
  <div class="page-wrapper">
    <AppHeader titulo="Autocorrector Legal" icono="fas fa-spell-check" />

    <div class="container">
      <!-- Tabs -->
      <div class="tabs mb-4">
        <button v-for="t in tabs" :key="t.key"
          class="tab-btn" :class="{ active: tabActiva === t.key }"
          @click="tabActiva = t.key">
          <i :class="t.icono + ' me-2'"></i>{{ t.label }}
        </button>
      </div>

      <!-- Tab: Corregir Texto -->
      <div v-if="tabActiva === 'texto'" class="card">
        <div class="card-header"><h5 class="mb-0">Corrección de Texto Legal</h5></div>
        <div class="card-body">
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label">Texto original</label>
              <textarea v-model="textoOriginal" class="form-control" rows="10"
                placeholder="Pegue aquí el texto a corregir…"></textarea>
            </div>
            <div class="col-md-6">
              <label class="form-label">Texto corregido</label>
              <textarea v-model="textoCorregido" class="form-control" rows="10" readonly
                placeholder="El resultado aparecerá aquí…"></textarea>
            </div>
          </div>
          <div class="mt-3 d-flex gap-2">
            <button class="btn btn-primary" @click="corregirTexto" :disabled="!textoOriginal || procesando">
              <span v-if="procesando"><i class="fas fa-spinner fa-spin me-2"></i>Corrigiendo…</span>
              <span v-else><i class="fas fa-magic me-2"></i>Corregir</span>
            </button>
            <button v-if="textoCorregido" class="btn btn-outline-secondary" @click="copiarTexto">
              <i class="fas fa-copy me-2"></i>Copiar
            </button>
          </div>
          <div v-if="correcciones.length" class="mt-4">
            <h6>Correcciones realizadas ({{ correcciones.length }})</h6>
            <div v-for="(c, i) in correcciones" :key="i" class="correccion-item">
              <span class="texto-original">{{ c.original }}</span>
              <i class="fas fa-arrow-right mx-2 text-muted"></i>
              <span class="texto-nuevo">{{ c.corregido }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: Corregir Dirección -->
      <div v-if="tabActiva === 'direccion'" class="card">
        <div class="card-header"><h5 class="mb-0">Corrección de Dirección</h5></div>
        <div class="card-body">
          <div class="mb-3">
            <label class="form-label">Dirección a corregir</label>
            <input v-model="direccionInput" type="text" class="form-control"
              placeholder="Ej: calle hidalgo 123 col centro" @keyup.enter="corregirDireccion" />
          </div>
          <button class="btn btn-primary" @click="corregirDireccion" :disabled="!direccionInput || procesando">
            <i class="fas fa-map-marker-alt me-2"></i>Corregir Dirección
          </button>
          <div v-if="resultadoDireccion" class="mt-4 p-3 bg-light rounded">
            <h6>Resultado</h6>
            <pre class="mb-0">{{ JSON.stringify(resultadoDireccion, null, 2) }}</pre>
          </div>
        </div>
      </div>

      <!-- Tab: Detectar Duplicados -->
      <div v-if="tabActiva === 'duplicados'" class="card">
        <div class="card-header"><h5 class="mb-0">Detección de Duplicados</h5></div>
        <div class="card-body">
          <div class="mb-3">
            <label class="form-label">Carpeta</label>
            <select v-model="carpetaId" class="form-select">
              <option value="">Todas las carpetas</option>
              <option v-for="c in carpetas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
            </select>
          </div>
          <div class="mb-3">
            <label class="form-label">Umbral de similitud (%)</label>
            <input v-model.number="umbral" type="range" class="form-range" min="50" max="100" step="5" />
            <small class="text-muted">{{ umbral }}%</small>
          </div>
          <button class="btn btn-warning" @click="detectarDuplicados" :disabled="procesando">
            <i class="fas fa-clone me-2"></i>Detectar Duplicados
          </button>
          <div v-if="duplicados.length" class="mt-4">
            <h6>{{ duplicados.length }} grupos de duplicados encontrados</h6>
            <div v-for="(g, i) in duplicados" :key="i" class="duplicado-grupo">
              <small class="text-muted">Grupo {{ i+1 }} — Similitud: {{ g.similitud }}%</small>
              <ul>
                <li v-for="d in g.documentos" :key="d.id">{{ d.nombre }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: Corregir Carpeta -->
      <div v-if="tabActiva === 'carpeta'" class="card">
        <div class="card-header"><h5 class="mb-0">Corrección Masiva de Carpeta</h5></div>
        <div class="card-body">
          <div class="mb-3">
            <label class="form-label">Seleccionar Carpeta</label>
            <select v-model="carpetaIdMasivo" class="form-select">
              <option value="">— Seleccione —</option>
              <option v-for="c in carpetas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
            </select>
          </div>
          <button class="btn btn-success" @click="corregirCarpeta" :disabled="!carpetaIdMasivo || procesando">
            <span v-if="procesando"><i class="fas fa-spinner fa-spin me-2"></i>Procesando…</span>
            <span v-else><i class="fas fa-magic me-2"></i>Iniciar Corrección Masiva</span>
          </button>
          <div v-if="resultadoCarpeta" class="mt-4 alert alert-success">
            <i class="fas fa-check-circle me-2"></i>
            Procesado: {{ resultadoCarpeta.procesados ?? 0 }} documentos corregidos.
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

const tabs = [
  { key: 'texto', label: 'Texto Legal', icono: 'fas fa-align-left' },
  { key: 'direccion', label: 'Dirección', icono: 'fas fa-map-marker-alt' },
  { key: 'duplicados', label: 'Duplicados', icono: 'fas fa-clone' },
  { key: 'carpeta', label: 'Carpeta Completa', icono: 'fas fa-folder' }
]
const tabActiva = ref('texto')
const procesando = ref(false)

const carpetas = ref([])
const carpetaId = ref('')
const carpetaIdMasivo = ref('')
const umbral = ref(85)

const textoOriginal = ref('')
const textoCorregido = ref('')
const correcciones = ref([])

const direccionInput = ref('')
const resultadoDireccion = ref(null)

const duplicados = ref([])
const resultadoCarpeta = ref(null)

onMounted(async () => {
  try {
    carpetas.value = await get('/carpetas')
  } catch {
    showToast('Error al cargar carpetas', 'error')
  }
})

async function corregirTexto() {
  procesando.value = true
  try {
    const data = await post('/autocorrector/corregir-texto', { texto: textoOriginal.value })
    textoCorregido.value = data.texto_corregido ?? data.resultado ?? ''
    correcciones.value = data.correcciones ?? []
    showToast('Texto corregido', 'success')
  } catch (e) {
    showToast('Error: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}

function copiarTexto() {
  navigator.clipboard.writeText(textoCorregido.value)
  showToast('Copiado al portapapeles', 'info')
}

async function corregirDireccion() {
  if (!direccionInput.value) return
  procesando.value = true
  try {
    const data = await post('/autocorrector/corregir-direccion', { direccion: direccionInput.value })
    resultadoDireccion.value = data
  } catch (e) {
    showToast('Error: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}

async function detectarDuplicados() {
  procesando.value = true
  try {
    const payload = { umbral: umbral.value }
    if (carpetaId.value) payload.carpeta_id = carpetaId.value
    const data = await post('/autocorrector/detectar-duplicados', payload)
    duplicados.value = data.grupos ?? data ?? []
  } catch (e) {
    showToast('Error: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}

async function corregirCarpeta() {
  if (!carpetaIdMasivo.value) return
  procesando.value = true
  try {
    const data = await post('/autocorrector/corregir-carpeta', { carpeta_id: carpetaIdMasivo.value })
    resultadoCarpeta.value = data
    showToast('Corrección masiva completada', 'success')
  } catch (e) {
    showToast('Error: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: #f8f9fa; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px 20px; }
.tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.tab-btn { padding: 10px 20px; border: none; border-radius: 8px; background: white; color: #6c757d; font-weight: 600; cursor: pointer; box-shadow: 0 2px 6px rgba(0,0,0,.07); transition: all .2s; }
.tab-btn.active { background: #007bff; color: white; }
.tab-btn:hover:not(.active) { background: #e9ecef; }
.card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.08); border: none; }
.card-header { background: #f8f9fa; border-bottom: 1px solid #e9ecef; padding: 16px 24px; border-radius: 12px 12px 0 0; }
.card-body { padding: 24px; }
.correccion-item { display: flex; align-items: center; padding: 6px 12px; background: #f8f9fa; border-radius: 6px; margin-bottom: 6px; font-size: .9rem; }
.texto-original { color: #dc3545; text-decoration: line-through; }
.texto-nuevo { color: #28a745; font-weight: 600; }
.duplicado-grupo { background: #fff3cd; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; }
</style>
