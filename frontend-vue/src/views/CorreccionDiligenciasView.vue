<template>
  <div class="page-wrapper">
    <AppHeader titulo="Corrección de Diligencias" icono="fas fa-pen-nib" />

    <div class="container">
      <!-- Filtros -->
      <div class="card mb-4">
        <div class="card-body">
          <div class="row g-3 align-items-end">
            <div class="col-md-4">
              <label class="form-label">Carpeta</label>
              <select v-model="filtros.carpeta_id" class="form-select">
                <option value="">Todas las carpetas</option>
                <option v-for="c in carpetas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label">Tipo de problema</label>
              <select v-model="filtros.tipo" class="form-select">
                <option value="">Todos</option>
                <option value="fecha_invalida">Fecha inválida</option>
                <option value="texto_corrupto">Texto corrupto</option>
                <option value="baja_confianza">Baja confianza</option>
              </select>
            </div>
            <div class="col-md-2">
              <label class="form-label">Página</label>
              <input v-model.number="filtros.pagina" type="number" min="1" class="form-control" />
            </div>
            <div class="col-md-3 d-flex gap-2">
              <button class="btn btn-primary flex-fill" @click="cargarProblemas">
                <i class="fas fa-search me-2"></i>Buscar
              </button>
              <button class="btn btn-outline-warning" @click="autocorregirTodos" :disabled="!problemas.length || procesando">
                <i class="fas fa-magic"></i>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Lista de problemas -->
      <div v-if="cargando" class="text-center py-5">
        <i class="fas fa-spinner fa-spin fa-2x text-primary"></i>
        <p class="mt-2 text-muted">Cargando diligencias problemáticas…</p>
      </div>

      <div v-else-if="!problemas.length && buscado" class="text-center py-5 text-muted">
        <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
        <p>No se encontraron diligencias problemáticas con los filtros aplicados.</p>
      </div>

      <div v-for="p in problemas" :key="p.id" class="card mb-3" :class="'card-' + (p.tipo_problema || 'default')">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <div>
              <span class="badge" :class="badgeClass(p.tipo_problema)">{{ p.tipo_problema || 'problema' }}</span>
              <span class="ms-2 text-muted small">ID: {{ p.id }}</span>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-primary" @click="abrirEdicion(p)">
                <i class="fas fa-edit"></i>
              </button>
              <button class="btn btn-sm btn-outline-success" @click="autocorregir(p.id)" :disabled="procesando">
                <i class="fas fa-magic"></i>
              </button>
              <button class="btn btn-sm btn-outline-danger" @click="eliminar(p.id)" :disabled="procesando">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
          <div class="problema-original p-2 rounded mb-2">
            <small class="text-muted d-block mb-1">Original:</small>
            {{ p.texto_original || p.descripcion || '—' }}
          </div>
          <div v-if="p.texto_sugerido" class="problema-sugerido p-2 rounded">
            <small class="text-muted d-block mb-1">Sugerencia:</small>
            {{ p.texto_sugerido }}
          </div>
        </div>
      </div>

      <!-- Paginación -->
      <div v-if="totalPaginas > 1" class="d-flex justify-content-center gap-2 mt-4">
        <button class="btn btn-outline-secondary" @click="filtros.pagina--" :disabled="filtros.pagina <= 1">
          <i class="fas fa-chevron-left"></i>
        </button>
        <span class="btn btn-light disabled">{{ filtros.pagina }} / {{ totalPaginas }}</span>
        <button class="btn btn-outline-secondary" @click="filtros.pagina++" :disabled="filtros.pagina >= totalPaginas">
          <i class="fas fa-chevron-right"></i>
        </button>
      </div>
    </div>

    <!-- Modal edición -->
    <div v-if="modalEdicion.visible" class="modal-backdrop" @click.self="cerrarModal">
      <div class="modal-card">
        <div class="modal-header">
          <h5>Editar Diligencia #{{ modalEdicion.item?.id }}</h5>
          <button class="btn-close" @click="cerrarModal"></button>
        </div>
        <div class="modal-body">
          <label class="form-label">Texto corregido</label>
          <textarea v-model="modalEdicion.textoEditado" class="form-control" rows="6"></textarea>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="cerrarModal">Cancelar</button>
          <button class="btn btn-primary" @click="guardarEdicion" :disabled="procesando">
            <i class="fas fa-save me-2"></i>Guardar
          </button>
        </div>
      </div>
    </div>

    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import AppHeader from '@/components/AppHeader.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const { get, put, post, del } = useApi()
const { showToast } = useToast()

const carpetas = ref([])
const problemas = ref([])
const cargando = ref(false)
const procesando = ref(false)
const buscado = ref(false)
const totalPaginas = ref(1)

const filtros = ref({ carpeta_id: '', tipo: '', pagina: 1 })

const modalEdicion = ref({ visible: false, item: null, textoEditado: '' })

onMounted(async () => {
  try {
    carpetas.value = await get('/carpetas')
  } catch {
    showToast('Error al cargar carpetas', 'error')
  }
  await cargarProblemas()
})

watch(() => filtros.value.pagina, cargarProblemas)

async function cargarProblemas() {
  cargando.value = true
  buscado.value = false
  try {
    const params = new URLSearchParams()
    if (filtros.value.carpeta_id) params.set('carpeta_id', filtros.value.carpeta_id)
    if (filtros.value.tipo) params.set('tipo', filtros.value.tipo)
    params.set('pagina', filtros.value.pagina)
    const data = await get(`/admin/diligencias/problematicas?${params}`)
    problemas.value = data.items ?? data ?? []
    totalPaginas.value = data.total_paginas ?? 1
    buscado.value = true
  } catch {
    showToast('Error al cargar diligencias', 'error')
  } finally {
    cargando.value = false
  }
}

function badgeClass(tipo) {
  const map = { fecha_invalida: 'bg-warning text-dark', texto_corrupto: 'bg-danger', baja_confianza: 'bg-secondary' }
  return map[tipo] ?? 'bg-info'
}

function abrirEdicion(item) {
  modalEdicion.value = { visible: true, item, textoEditado: item.texto_corregido || item.texto_original || '' }
}

function cerrarModal() {
  modalEdicion.value.visible = false
}

async function guardarEdicion() {
  procesando.value = true
  try {
    await put(`/admin/diligencias/${modalEdicion.value.item.id}`, {
      texto_corregido: modalEdicion.value.textoEditado
    })
    showToast('Diligencia actualizada', 'success')
    cerrarModal()
    await cargarProblemas()
  } catch (e) {
    showToast('Error al guardar: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}

async function autocorregir(id) {
  procesando.value = true
  try {
    await post(`/admin/diligencias/autocorregir/${id}`, {})
    showToast('Autocorrección aplicada', 'success')
    await cargarProblemas()
  } catch (e) {
    showToast('Error: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}

async function eliminar(id) {
  if (!confirm('¿Eliminar este registro?')) return
  procesando.value = true
  try {
    await del(`/admin/diligencias/${id}`)
    showToast('Eliminado', 'success')
    await cargarProblemas()
  } catch (e) {
    showToast('Error al eliminar: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}

async function autocorregirTodos() {
  if (!confirm('¿Autocorregir todas las diligencias listadas?')) return
  procesando.value = true
  let ok = 0
  for (const p of problemas.value) {
    try {
      await post(`/admin/diligencias/autocorregir/${p.id}`, {})
      ok++
    } catch { /* continuar */ }
  }
  showToast(`${ok} diligencias autocorregidas`, 'success')
  await cargarProblemas()
  procesando.value = false
}
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: #f8f9fa; }
.container { max-width: 1100px; margin: 0 auto; padding: 24px 20px; }
.card { background: white; border-radius: 12px; border: none; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.card-body { padding: 20px 24px; }
.card-fecha_invalida { border-left: 4px solid #ffc107; }
.card-texto_corrupto { border-left: 4px solid #dc3545; }
.card-baja_confianza { border-left: 4px solid #6c757d; }
.problema-original { background: #fff3cd; }
.problema-sugerido { background: #d4edda; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { background: white; border-radius: 12px; width: 90%; max-width: 600px; }
.modal-header { padding: 16px 24px; border-bottom: 1px solid #e9ecef; display: flex; justify-content: space-between; align-items: center; }
.modal-body { padding: 24px; }
.modal-footer { padding: 16px 24px; border-top: 1px solid #e9ecef; display: flex; justify-content: flex-end; gap: 8px; }
</style>
