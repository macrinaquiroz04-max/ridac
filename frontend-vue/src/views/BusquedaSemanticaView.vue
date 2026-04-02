<template>
  <div>
    <AppHeader />
    <div class="container">
      <div class="card">
        <h2><i class="fas fa-satellite-dish" /> Búsqueda Semántica</h2>
        <div class="search-wrap">
          <input v-model="query" type="text" placeholder="Busca conceptos relacionados, no solo palabras exactas..." @keyup.enter="buscar" />
          <button class="btn-primary" @click="buscar" :disabled="loading">
            <i class="fas fa-search" /> Buscar
          </button>
        </div>
        <div v-if="loading" class="msg"><i class="fas fa-spinner fa-spin" /> Analizando...</div>
        <div v-else-if="resultados.length" class="results">
          <div v-for="r in resultados" :key="r.id" class="result-item">
            <h4>{{ r.titulo || r.nombre_archivo }}</h4>
            <p>{{ r.fragmento }}</p>
            <small>Similitud: {{ (r.score * 100).toFixed(1) }}%</small>
          </div>
        </div>
        <div v-else-if="buscado" class="msg">Sin resultados para "{{ query }}"</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { useApi } from '@/composables/useApi'

const { post } = useApi()
const query = ref('')
const resultados = ref([])
const loading = ref(false)
const buscado = ref(false)

async function buscar() {
  if (!query.value.trim()) return
  loading.value = true
  buscado.value = false
  try {
    const data = await post('/busqueda/semantica', { consulta: query.value })
    resultados.value = data.resultados || data || []
    buscado.value = true
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.container { max-width: 900px; margin: 40px auto; padding: 0 30px; }
.card { background: #fff; padding: 28px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.07); }
.card h2 { color: #1a365d; margin-bottom: 20px; }
.search-wrap { display: flex; gap: 10px; margin-bottom: 24px; }
.search-wrap input { flex: 1; padding: 12px 18px; border: 2px solid #e9ecef; border-radius: 10px; font-size: 15px; outline: none; }
.search-wrap input:focus { border-color: #6f42c1; }
.msg { padding: 30px; text-align: center; color: #6c757d; }
.results { display: flex; flex-direction: column; gap: 12px; }
.result-item { background: #f8f9fa; padding: 18px; border-radius: 10px; border-left: 4px solid #6f42c1; }
.result-item h4 { color: #1a365d; margin-bottom: 6px; }
.result-item p { color: #4a5568; font-size: 14px; margin-bottom: 4px; }
.result-item small { color: #6f42c1; font-weight: 600; }
.btn-primary { background: linear-gradient(135deg,#6f42c1,#5a32a3); color: white; border: none; padding: 12px 22px; border-radius: 10px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.btn-primary:disabled { opacity: 0.65; cursor: not-allowed; }
</style>
