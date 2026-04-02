<template>
  <div>
    <AppHeader />
    <div class="container">
      <div class="card">
        <h2><i class="fas fa-search-plus" /> Auditoría del Sistema</h2>
        <div class="filters">
          <input v-model="filtros.usuario" type="text" placeholder="Usuario..." @input="cargar" />
          <input v-model="filtros.fecha_desde" type="date" @change="cargar" />
          <input v-model="filtros.fecha_hasta" type="date" @change="cargar" />
          <button class="btn-primary" @click="exportar"><i class="fas fa-download" /> Exportar CSV</button>
        </div>

        <div v-if="loading" class="msg"><i class="fas fa-spinner fa-spin" /> Cargando...</div>
        <table v-else class="table">
          <thead>
            <tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Detalle</th></tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id">
              <td>{{ formatFecha(log.fecha) }}</td>
              <td>{{ log.usuario }}</td>
              <td><span class="badge">{{ log.accion }}</span></td>
              <td>{{ log.detalle }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'

const { get, download } = useApi()
const { showToast } = useToast()

const logs = ref([])
const loading = ref(true)
const filtros = ref({ usuario: '', fecha_desde: '', fecha_hasta: '' })

onMounted(() => cargar())

async function cargar() {
  loading.value = true
  try {
    const params = {}
    if (filtros.value.usuario) params.usuario = filtros.value.usuario
    if (filtros.value.fecha_desde) params.fecha_desde = filtros.value.fecha_desde
    if (filtros.value.fecha_hasta) params.fecha_hasta = filtros.value.fecha_hasta
    logs.value = await get('/auditoria', params)
  } finally {
    loading.value = false
  }
}

async function exportar() {
  try {
    await download('/auditoria/exportar', 'auditoria.csv')
  } catch (err) {
    showToast(err.message, 'error')
  }
}

function formatFecha(f) {
  if (!f) return 'N/A'
  return new Date(f).toLocaleString('es-MX')
}
</script>

<style scoped>
.container { max-width: 1300px; margin: 40px auto; padding: 0 30px; }
.card { background: #fff; padding: 28px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.07); }
.card h2 { color: #1a365d; margin-bottom: 20px; }
.filters { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; align-items: center; }
.filters input { padding: 9px 14px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px; outline: none; }
.filters input:focus { border-color: #2c5aa0; }
.msg { padding: 30px; text-align: center; color: #6c757d; }
.table { width: 100%; border-collapse: collapse; }
.table th { background: #f8f9fa; padding: 11px 14px; text-align: left; color: #1a365d; font-weight: 700; border-bottom: 2px solid #e9ecef; }
.table td { padding: 11px 14px; border-bottom: 1px solid #f0f2f5; color: #4a5568; font-size: 13px; }
.table tr:hover td { background: #f8f9fa; }
.badge { background: #2c5aa0; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.btn-primary { background: linear-gradient(135deg,#1a365d,#2c5aa0); color: white; border: none; padding: 9px 18px; border-radius: 20px; cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
</style>
