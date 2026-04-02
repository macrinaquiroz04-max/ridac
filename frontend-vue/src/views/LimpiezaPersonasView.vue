<template>
  <div class="page-wrapper">
    <AppHeader titulo="Limpieza de Personas" icono="fas fa-user-clean" />

    <div class="container">
      <!-- Stats -->
      <div class="row g-3 mb-4">
        <div class="col-md-3" v-for="s in stats" :key="s.label">
          <div class="stat-card">
            <div class="stat-number">{{ s.valor }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </div>

      <!-- Filtros -->
      <div class="card mb-4">
        <div class="card-body">
          <div class="row g-3 align-items-end">
            <div class="col-md-3">
              <label class="form-label">Tipo de problema</label>
              <select v-model="filtros.tipo" class="form-select">
                <option value="">Todos</option>
                <option value="duplicado">Duplicados</option>
                <option value="incompleto">Datos incompletos</option>
                <option value="invalido">Datos inválidos</option>
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label">Buscar nombre</label>
              <input v-model="filtros.nombre" type="text" class="form-control" placeholder="Nombre…" />
            </div>
            <div class="col-md-2">
              <label class="form-label">Página</label>
              <input v-model.number="filtros.pagina" type="number" min="1" class="form-control" />
            </div>
            <div class="col-md-4 d-flex gap-2">
              <button class="btn btn-primary flex-fill" @click="cargarPersonas">
                <i class="fas fa-search me-2"></i>Buscar
              </button>
              <button class="btn btn-outline-danger" @click="limpiarAutomatico" :disabled="procesando"
                title="Limpieza automática">
                <i class="fas fa-broom"></i>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Acciones masivas -->
      <div v-if="seleccionados.length" class="alert alert-warning d-flex align-items-center gap-3 mb-3">
        <span>{{ seleccionados.length }} persona(s) seleccionada(s)</span>
        <button class="btn btn-sm btn-danger ms-auto" @click="eliminarSeleccionados" :disabled="procesando">
          <i class="fas fa-trash me-2"></i>Eliminar seleccionadas
        </button>
      </div>

      <!-- Lista -->
      <div v-if="cargando" class="text-center py-5">
        <i class="fas fa-spinner fa-spin fa-2x text-primary"></i>
      </div>

      <div v-else-if="personas.length === 0 && buscado" class="text-center py-5 text-muted">
        <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
        <p>No se encontraron personas problemáticas.</p>
      </div>

      <div v-for="p in personas" :key="p.id" class="card-persona mb-3">
        <div class="d-flex align-items-start gap-3">
          <input type="checkbox" class="form-check-input mt-1" :value="p.id" v-model="seleccionados" />
          <div class="flex-grow-1">
            <div class="d-flex justify-content-between">
              <div>
                <strong>{{ p.nombre }}</strong>
                <span v-for="tag in (p.problemas || [])" :key="tag"
                  class="badge badge-problema ms-2" :class="badgeClass(tag)">{{ tag }}</span>
              </div>
              <div class="d-flex gap-2">
                <button class="btn btn-sm btn-outline-danger btn-action" @click="eliminarUno(p.id)" :disabled="procesando">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </div>
            <small class="text-muted">
              {{ p.email || '—' }} | {{ p.telefono || '—' }} | Doc: {{ p.documento || '—' }}
            </small>
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

    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import AppHeader from '@/components/AppHeader.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const { get, del, post } = useApi()
const { showToast } = useToast()

const personas = ref([])
const seleccionados = ref([])
const cargando = ref(false)
const procesando = ref(false)
const buscado = ref(false)
const totalPaginas = ref(1)

const filtros = reactive({ tipo: '', nombre: '', pagina: 1 })

const stats = ref([
  { label: 'Total personas', valor: '—' },
  { label: 'Duplicados', valor: '—' },
  { label: 'Incompletos', valor: '—' },
  { label: 'Seleccionados', valor: 0 }
])

onMounted(async () => {
  await cargarPersonas()
})

watch(() => filtros.pagina, cargarPersonas)

watch(seleccionados, (v) => {
  stats.value[3].valor = v.length
})

async function cargarPersonas() {
  cargando.value = true
  buscado.value = false
  seleccionados.value = []
  try {
    const params = new URLSearchParams()
    if (filtros.tipo) params.set('tipo', filtros.tipo)
    if (filtros.nombre) params.set('nombre', filtros.nombre)
    params.set('pagina', filtros.pagina)
    const data = await get(`/admin/personas/problematicas?${params}`)
    personas.value = data.items ?? data ?? []
    totalPaginas.value = data.total_paginas ?? 1
    stats.value[0].valor = data.total ?? personas.value.length
    stats.value[1].valor = data.duplicados ?? '—'
    stats.value[2].valor = data.incompletos ?? '—'
    buscado.value = true
  } catch {
    showToast('Error al cargar personas', 'error')
  } finally {
    cargando.value = false
  }
}

function badgeClass(tipo) {
  const map = { duplicado: 'bg-warning text-dark', incompleto: 'bg-secondary', invalido: 'bg-danger' }
  return map[tipo] ?? 'bg-info'
}

async function eliminarUno(id) {
  if (!confirm('¿Eliminar esta persona?')) return
  procesando.value = true
  try {
    await del(`/admin/personas/${id}`)
    showToast('Persona eliminada', 'success')
    await cargarPersonas()
  } catch (e) {
    showToast('Error: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}

async function eliminarSeleccionados() {
  if (!confirm(`¿Eliminar ${seleccionados.value.length} personas?`)) return
  procesando.value = true
  try {
    await post('/admin/personas/eliminar-masivo', { ids: seleccionados.value })
    showToast('Personas eliminadas', 'success')
    await cargarPersonas()
  } catch (e) {
    showToast('Error: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}

async function limpiarAutomatico() {
  if (!confirm('¿Ejecutar limpieza automática? Esto puede eliminar datos sin confirmación manual adicional.')) return
  procesando.value = true
  try {
    const data = await post('/admin/personas/limpiar-automatico', {})
    showToast(`Limpieza completada: ${data.eliminados ?? 0} eliminados`, 'success')
    await cargarPersonas()
  } catch (e) {
    showToast('Error: ' + (e.message || ''), 'error')
  } finally {
    procesando.value = false
  }
}
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.container { max-width: 1200px; margin: 0 auto; padding: 30px 20px; }
.stat-card { background: linear-gradient(135deg, #003d82, #0052ad); color: white; padding: 20px; border-radius: 10px; text-align: center; }
.stat-number { font-size: 2.2rem; font-weight: 700; }
.stat-label { font-size: .85rem; opacity: .85; }
.card { background: white; border-radius: 12px; border: none; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.card-body { padding: 20px 24px; }
.card-persona { background: white; border-radius: 10px; padding: 16px 20px; box-shadow: 0 2px 8px rgba(0,0,0,.08); transition: transform .2s, box-shadow .2s; }
.card-persona:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,.12); }
.badge-problema { font-size: .72rem; }
</style>
