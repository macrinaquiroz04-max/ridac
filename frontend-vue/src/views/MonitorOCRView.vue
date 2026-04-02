<template>
  <div>
    <AppHeader />
    <div class="container">
      <div class="card">
        <h2><i class="fas fa-tasks" /> Monitor de Procesamiento OCR</h2>
        <div class="toolbar">
          <button class="btn-primary" @click="cargar"><i class="fas fa-sync" /> Actualizar</button>
          <label class="auto-label">
            <input v-model="autoRefresh" type="checkbox" @change="toggleAuto" /> Auto-actualizar (5s)
          </label>
        </div>

        <div v-if="loading" class="msg"><i class="fas fa-spinner fa-spin" /> Cargando tareas...</div>

        <div v-else class="tasks">
          <div v-if="!tareas.length" class="msg">No hay tareas activas</div>
          <div v-for="tarea in tareas" :key="tarea.id" class="task-card">
            <div class="task-header">
              <strong>{{ tarea.nombre_archivo || tarea.tomo_id }}</strong>
              <span :class="`estado-${tarea.estado}`">{{ tarea.estado }}</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: (tarea.progreso || 0) + '%' }" />
            </div>
            <small>{{ tarea.progreso || 0 }}% · {{ tarea.paginas_procesadas || 0 }} / {{ tarea.total_paginas || '?' }} páginas</small>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { useApi } from '@/composables/useApi'

const { get } = useApi()
const tareas = ref([])
const loading = ref(true)
const autoRefresh = ref(false)
let timer = null

onMounted(() => cargar())
onUnmounted(() => clearInterval(timer))

async function cargar() {
  loading.value = true
  try {
    tareas.value = await get('/tasks/ocr-status')
  } catch {
    tareas.value = []
  } finally {
    loading.value = false
  }
}

function toggleAuto() {
  if (autoRefresh.value) {
    timer = setInterval(cargar, 5000)
  } else {
    clearInterval(timer)
  }
}
</script>

<style scoped>
.container { max-width: 1000px; margin: 40px auto; padding: 0 30px; }
.card { background: #fff; padding: 28px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.07); }
.card h2 { color: #1a365d; margin-bottom: 20px; }
.toolbar { display: flex; gap: 16px; align-items: center; margin-bottom: 20px; }
.auto-label { display: flex; align-items: center; gap: 6px; font-size: 14px; color: #4a5568; cursor: pointer; }
.msg { padding: 30px; text-align: center; color: #6c757d; }
.tasks { display: flex; flex-direction: column; gap: 14px; }
.task-card { background: #f8f9fa; padding: 16px 20px; border-radius: 10px; border: 1px solid #e9ecef; }
.task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.task-header strong { color: #1a365d; }
.progress-bar { background: #e9ecef; border-radius: 10px; height: 8px; overflow: hidden; margin-bottom: 6px; }
.progress-fill { background: linear-gradient(135deg,#28a745,#34ce57); height: 100%; transition: width 0.4s ease; }
.task-card small { color: #6c757d; font-size: 12px; }
.estado-procesando { color: #ffc107; font-weight: 600; font-size: 13px; }
.estado-completado { color: #28a745; font-weight: 600; font-size: 13px; }
.estado-error { color: #dc3545; font-weight: 600; font-size: 13px; }
.estado-pendiente { color: #6c757d; font-weight: 600; font-size: 13px; }
.btn-primary { background: linear-gradient(135deg,#1a365d,#2c5aa0); color: white; border: none; padding: 9px 18px; border-radius: 20px; cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
</style>
