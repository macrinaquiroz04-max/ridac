<template>
  <div>
    <AppHeader />
    <div class="container">
      <div class="card">
        <h2><i class="fas fa-search" /> Buscar en Expedientes</h2>

        <div class="search-wrap">
          <input
            v-model="query"
            type="text"
            class="search-input"
            placeholder="Buscar por número de expediente, descripción..."
            @input="filtrar"
          />
          <i class="fas fa-search search-icon" />
        </div>

        <div v-if="loading" class="loading-msg">
          <i class="fas fa-spinner fa-spin" /> Cargando expedientes...
        </div>

        <div v-else-if="!filtrados.length" class="empty-msg">
          <i class="fas fa-folder-open" /> No se encontraron expedientes
        </div>

        <div v-else class="results">
          <div v-for="tomo in filtrados" :key="tomo.id" class="result-item">
            <div class="result-info">
              <h3>
                <i class="fas fa-file-pdf" />
                {{ tomo.numero || tomo.numero_tomo || 'Sin número' }}
              </h3>
              <p>{{ tomo.descripcion || tomo.nombre_archivo || 'Sin descripción' }}</p>
              <small>Subido: {{ formatFecha(tomo.fecha_subida) }}</small>
            </div>
            <button class="btn-primary" @click="irAlTomo(tomo)">
              <i class="fas fa-eye" /> Revisar
            </button>
          </div>
        </div>

        <RouterLink to="/dashboard" class="btn-back">
          <i class="fas fa-arrow-left" /> Volver al Dashboard
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useApi } from '@/composables/useApi'

const router = useRouter()
const { get } = useApi()

const todos = ref([])
const filtrados = ref([])
const query = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    todos.value = await get('/analisis/tomos')
    filtrados.value = todos.value
  } catch {
    // error manejado por useApi
  } finally {
    loading.value = false
  }
})

function filtrar() {
  const q = query.value.toLowerCase()
  filtrados.value = todos.value.filter(t =>
    (t.numero?.toLowerCase().includes(q)) ||
    (t.numero_tomo?.toString().includes(q)) ||
    (t.descripcion?.toLowerCase().includes(q)) ||
    (t.nombre_archivo?.toLowerCase().includes(q))
  )
}

function irAlTomo(tomo) {
  router.push({ name: 'visor-pdf', query: { tomo_id: tomo.id } })
}

function formatFecha(f) {
  if (!f) return 'N/A'
  return new Date(f).toLocaleDateString('es-MX')
}
</script>

<style scoped>
.container { max-width: 1200px; margin: 40px auto; padding: 0 30px; }

.card {
  background: #fff;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.07);
}

.card h2 { color: #1a365d; margin-bottom: 24px; font-size: 22px; }

.search-wrap { position: relative; margin-bottom: 24px; }

.search-input {
  width: 100%;
  padding: 14px 24px 14px 48px;
  border: 2px solid #e9ecef;
  border-radius: 30px;
  font-size: 16px;
  transition: border-color 0.2s, box-shadow 0.2s;
  outline: none;
}

.search-input:focus {
  border-color: #2c5aa0;
  box-shadow: 0 0 0 3px rgba(44,90,160,0.1);
}

.search-icon {
  position: absolute;
  left: 18px;
  top: 50%;
  transform: translateY(-50%);
  color: #9ca3af;
  font-size: 16px;
}

.loading-msg, .empty-msg {
  padding: 40px;
  text-align: center;
  color: #6c757d;
  font-size: 16px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #f0f2f5;
  transition: background 0.2s, transform 0.2s;
  border-radius: 8px;
  gap: 16px;
}

.result-item:hover { background: #f8f9fa; transform: translateX(4px); }

.result-info h3 {
  color: #1a365d;
  font-size: 17px;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-info p { color: #6c757d; margin-bottom: 4px; }
.result-info small { color: #9ca3af; }

.btn-primary {
  background: linear-gradient(135deg, #1a365d, #2c5aa0);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: transform 0.2s, box-shadow 0.2s;
  white-space: nowrap;
}

.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(44,90,160,0.3); }

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 24px;
  color: #2c5aa0;
  text-decoration: none;
  font-weight: 600;
  transition: gap 0.2s;
}

.btn-back:hover { gap: 10px; }
</style>
