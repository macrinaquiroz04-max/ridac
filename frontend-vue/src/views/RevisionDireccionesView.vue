<template>
  <div class="page-wrapper">
    <AppHeader titulo="Revisión de Direcciones" icono="fas fa-map-marked-alt" />

    <div class="container">
      <!-- Selector de tomo -->
      <div class="card mb-4">
        <div class="card-body">
          <div class="row g-3 align-items-end">
            <div class="col-md-7">
              <label class="form-label">Seleccionar Tomo para detectar direcciones</label>
              <select v-model="tomoId" class="form-select">
                <option value="">— Seleccione un tomo —</option>
                <option v-for="t in tomos" :key="t.id" :value="t.id">{{ t.nombre }}</option>
              </select>
            </div>
            <div class="col-md-5 d-flex gap-2">
              <button class="btn btn-primary flex-fill" @click="detectarDirecciones" :disabled="!tomoId || cargando">
                <span v-if="cargando"><i class="fas fa-spinner fa-spin me-2"></i>Detectando…</span>
                <span v-else><i class="fas fa-search-location me-2"></i>Detectar Direcciones</span>
              </button>
              <button v-if="detecciones.length" class="btn btn-success" @click="guardarDirecciones" :disabled="guardando">
                <i class="fas fa-save me-2"></i>Guardar
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Validador de CP -->
      <div class="card mb-4">
        <div class="card-header"><h6 class="mb-0"><i class="fas fa-map-pin me-2"></i>Validar Código Postal</h6></div>
        <div class="card-body">
          <div class="input-group" style="max-width: 350px;">
            <input v-model="cpInput" type="text" class="form-control" placeholder="Ej: 06600" maxlength="5"
              @keyup.enter="validarCP" />
            <button class="btn btn-outline-primary" @click="validarCP" :disabled="cpInput.length !== 5 || validandoCP">
              <i class="fas fa-check"></i>
            </button>
          </div>
          <div v-if="resultadoCP" class="mt-2">
            <span v-if="resultadoCP.valido" class="badge bg-success">
              <i class="fas fa-check-circle me-1"></i>{{ resultadoCP.colonia }}, {{ resultadoCP.municipio }}, {{ resultadoCP.estado }}
            </span>
            <span v-else class="badge bg-danger">
              <i class="fas fa-times-circle me-1"></i>Código postal no encontrado
            </span>
          </div>
        </div>
      </div>

      <!-- Lista de detecciones -->
      <div v-if="!detecciones.length && !cargando" class="text-center py-4 text-muted">
        <i class="fas fa-map-marked-alt fa-3x mb-3" style="opacity:.3"></i>
        <p>Selecciona un tomo y detecta las direcciones extraídas por OCR.</p>
      </div>

      <div v-if="cargando" class="text-center py-5">
        <i class="fas fa-spinner fa-spin fa-2x text-primary"></i>
        <p class="mt-2 text-muted">Detectando direcciones con IA…</p>
      </div>

      <div v-for="(d, i) in detecciones" :key="i" class="detection-card mb-3">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <span class="badge" :class="confianzaBadge(d.confianza)">
            Confianza: {{ d.confianza ?? '?' }}%
          </span>
          <span class="badge bg-secondary">Pág. {{ d.pagina ?? '?' }}</span>
        </div>

        <div class="detection-original mb-2">
          <small class="fw-semibold text-muted">Texto original (OCR):</small>
          <p class="mb-0 mt-1">{{ d.original }}</p>
        </div>

        <div v-if="d.sugerencia" class="detection-suggestion mb-2">
          <small class="fw-semibold text-muted">Sugerencia normalizada:</small>
          <p class="mb-0 mt-1">{{ d.sugerencia }}</p>
        </div>

        <div v-if="d.error" class="detection-error mb-2">
          <small class="fw-semibold text-muted">Problema detectado:</small>
          <p class="mb-0 mt-1">{{ d.error }}</p>
        </div>

        <!-- Editor inline -->
        <div class="mt-2">
          <input v-model="d.texto_final" type="text" class="form-control form-control-sm"
            placeholder="Texto final validado…" />
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

const tomos = ref([])
const tomoId = ref('')
const detecciones = ref([])
const cargando = ref(false)
const guardando = ref(false)

const cpInput = ref('')
const validandoCP = ref(false)
const resultadoCP = ref(null)

onMounted(async () => {
  try {
    const data = await get('/carpetas')
    // Cargar primeros tomos de la primera carpeta
    if (Array.isArray(data) && data.length) {
      try {
        const t = await get(`/tomos/${data[0].id}`)
        tomos.value = Array.isArray(t) ? t : (t?.tomos ?? [])
      } catch { /* skip */ }
    }
  } catch {
    showToast('Error al cargar tomos', 'error')
  }
})

async function detectarDirecciones() {
  if (!tomoId.value) return
  cargando.value = true
  detecciones.value = []
  try {
    const data = await get(`/tomos/${tomoId.value}/detectar-direcciones`)
    const lista = data?.detecciones ?? data ?? []
    // Agregar campo editable
    detecciones.value = lista.map(d => ({ ...d, texto_final: d.sugerencia || d.original }))
    if (!lista.length) showToast('No se encontraron direcciones en este tomo', 'info')
    else showToast(`${lista.length} dirección(es) detectada(s)`, 'success')
  } catch (e) {
    showToast('Error al detectar: ' + (e.message || ''), 'error')
  } finally {
    cargando.value = false
  }
}

async function guardarDirecciones() {
  guardando.value = true
  try {
    await post(`/tomos/${tomoId.value}/guardar-direcciones`, {
      direcciones: detecciones.value.map(d => ({ ...d }))
    })
    showToast('Direcciones guardadas correctamente', 'success')
  } catch (e) {
    showToast('Error al guardar: ' + (e.message || ''), 'error')
  } finally {
    guardando.value = false
  }
}

async function validarCP() {
  if (cpInput.value.length !== 5) return
  validandoCP.value = true
  resultadoCP.value = null
  try {
    const data = await get(`/sepomex/validar-cp/${cpInput.value}`)
    resultadoCP.value = data
  } catch {
    resultadoCP.value = { valido: false }
  } finally {
    validandoCP.value = false
  }
}

function confianzaBadge(confianza) {
  if (!confianza || confianza < 50) return 'bg-danger'
  if (confianza < 75) return 'bg-warning text-dark'
  return 'bg-success'
}
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.container { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }
.card { background: white; border-radius: 12px; border: none; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.card-header { background: #f8f9fa; border-bottom: 1px solid #e9ecef; padding: 14px 20px; border-radius: 12px 12px 0 0; }
.card-body { padding: 20px 24px; }
.detection-card { background: white; border-radius: 10px; padding: 18px 20px; box-shadow: 0 2px 8px rgba(0,0,0,.08); transition: transform .2s, box-shadow .2s; }
.detection-card:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,.12); }
.detection-original { background: #fff3cd; padding: 12px; border-radius: 6px; border-left: 4px solid #ffc107; }
.detection-suggestion { background: #d4edda; padding: 12px; border-radius: 6px; border-left: 4px solid #28a745; }
.detection-error { background: #f8d7da; padding: 12px; border-radius: 6px; border-left: 4px solid #dc3545; }
</style>
