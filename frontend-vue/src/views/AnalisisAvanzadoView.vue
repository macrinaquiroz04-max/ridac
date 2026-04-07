<template>
  <div class="page-wrapper">
    <AppHeader titulo="Análisis Avanzado de Documentos" icono="fas fa-microscope" />

    <div class="container">
      <!-- Selector de Tomo -->
      <div class="card selector-card">
        <div class="card-header">
          <span>📄 Seleccionar Documento</span>
        </div>
        <div class="card-body">
          <div class="form-row">
            <select v-model="tomoSeleccionado" class="tomo-select" :disabled="cargandoTomos">
              <option value="">Seleccione un documento para analizar...</option>
              <option v-for="t in tomos" :key="t.id" :value="t.id">
                {{ t.nombre || t.nombre_archivo }} ({{ t.total_paginas || '?' }} páginas)
                {{ t.carpeta_nombre ? ` — ${t.carpeta_nombre}` : '' }}
              </option>
            </select>
            <button class="btn-analizar" @click="cargarAnalisis"
              :disabled="!tomoSeleccionado || cargando">
              <i :class="cargando ? 'fas fa-spinner fa-spin' : 'fas fa-search'"></i>
              {{ cargando ? 'Analizando…' : 'Analizar Documento' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="cargando" class="loading-box">
        <div class="loading-icon">⏳</div>
        <h3>Analizando documento...</h3>
        <p>Detectando fechas, nombres, direcciones y lugares con alta precisión</p>
      </div>

      <!-- Resultados -->
      <template v-if="analisis && !cargando">
        <!-- Estadísticas resumen -->
        <div class="stats-grid">
          <div class="stat-box">
            <div class="stat-number">{{ analisis.resumen?.total_fechas ?? 0 }}</div>
            <div class="stat-label">Fechas Detectadas</div>
          </div>
          <div class="stat-box">
            <div class="stat-number">{{ analisis.resumen?.total_nombres ?? 0 }}</div>
            <div class="stat-label">Nombres Completos</div>
          </div>
          <div class="stat-box">
            <div class="stat-number">{{ analisis.resumen?.total_direcciones ?? 0 }}</div>
            <div class="stat-label">Direcciones</div>
          </div>
          <div class="stat-box">
            <div class="stat-number">{{ analisis.resumen?.total_lugares ?? 0 }}</div>
            <div class="stat-label">Lugares</div>
          </div>
          <div class="stat-box">
            <div class="stat-number">{{ analisis.resumen?.total_diligencias ?? 0 }}</div>
            <div class="stat-label">Diligencias</div>
          </div>
          <div class="stat-box">
            <div class="stat-number">{{ analisis.resumen?.total_alertas ?? 0 }}</div>
            <div class="stat-label">Alertas</div>
          </div>
          <div class="stat-box">
            <div class="stat-number">{{ analisis.resumen?.paginas_analizadas ?? 0 }}</div>
            <div class="stat-label">Páginas Analizadas</div>
          </div>
        </div>

        <!-- Tabs -->
        <div class="card tabs-card">
          <div class="card-header">
            <span>🔍 Resultados Detallados</span>
          </div>
          <div class="card-body">
            <div class="tabs">
              <button v-for="tab in tabs" :key="tab.key"
                :class="['tab', { active: tabActual === tab.key }]"
                @click="tabActual = tab.key">
                {{ tab.label }}
              </button>
            </div>

            <!-- Fechas -->
            <div v-if="tabActual === 'fechas'" class="results-section">
              <div v-if="!analisis.resultados?.fechas?.length" class="empty-tab">No se encontraron fechas</div>
              <div v-for="(f, i) in analisis.resultados?.fechas" :key="i" class="result-item">
                <div class="result-type">📅 {{ formatTipo(f.tipo, 'FECHA') }}</div>
                <div class="result-text">{{ f.texto }}</div>
                <div class="result-meta">
                  <span>📍 Día: {{ f.dia || 'N/A' }}</span>
                  <span>📍 Mes: {{ f.mes || 'N/A' }}</span>
                  <span>📍 Año: {{ f.año || 'N/A' }}</span>
                  <span v-if="f.numero_pagina" class="page-tag">Página {{ f.numero_pagina }}</span>
                </div>
              </div>
            </div>

            <!-- Nombres -->
            <div v-if="tabActual === 'nombres'" class="results-section">
              <div v-if="!analisis.resultados?.nombres?.length" class="empty-tab">No se encontraron nombres</div>
              <div v-for="(n, i) in analisis.resultados?.nombres" :key="i" class="result-item">
                <div class="result-type">👤 {{ formatTipo(n.tipo, 'NOMBRE') }}</div>
                <div class="result-text">{{ n.texto_completo || n.texto }}</div>
                <div class="nombre-completa">
                  <template v-if="n.titulo"><span class="nombre-parte">Título:</span><span>{{ n.titulo }}</span></template>
                  <span class="nombre-parte">Nombres:</span><span>{{ n.nombres || (n.texto_completo || n.texto || '').split(' ')[0] || 'N/A' }}</span>
                  <span class="nombre-parte">Paterno:</span><span>{{ n.apellido_paterno || (n.texto_completo || n.texto || '').split(' ')[1] || 'N/A' }}</span>
                  <span class="nombre-parte">Materno:</span><span>{{ n.apellido_materno || (n.texto_completo || n.texto || '').split(' ')[2] || '' }}</span>
                </div>
                <div class="result-meta">
                  <span v-if="n.numero_pagina || n.pagina" class="page-tag">Página {{ n.numero_pagina || n.pagina }}</span>
                </div>
              </div>
            </div>

            <!-- Direcciones -->
            <div v-if="tabActual === 'direcciones'" class="results-section">
              <div v-if="!analisis.resultados?.direcciones?.length" class="empty-tab">No se encontraron direcciones</div>
              <div v-for="(d, i) in analisis.resultados?.direcciones" :key="i" class="result-item">
                <div class="result-type">🏠 {{ formatTipo(d.tipo, 'DIRECCIÓN') }}</div>
                <div class="result-text">{{ d.texto_completo || d.texto }}</div>
                <div class="direccion-completa">
                  <span class="dir-parte">Vía:</span><span>{{ d.tipo_via || '' }} {{ d.nombre_via || d.nombre || 'N/A' }}</span>
                  <span class="dir-parte">Número:</span><span>{{ d.numero || 'N/A' }}</span>
                  <template v-if="d.colonia"><span class="dir-parte">Colonia:</span><span>{{ d.colonia }}</span></template>
                  <template v-if="d.codigo_postal"><span class="dir-parte">C.P.:</span><span>{{ d.codigo_postal }}</span></template>
                </div>
                <div class="result-meta">
                  <span v-if="d.numero_pagina || d.pagina" class="page-tag">Página {{ d.numero_pagina || d.pagina }}</span>
                </div>
              </div>
            </div>

            <!-- Lugares -->
            <div v-if="tabActual === 'lugares'" class="results-section">
              <div v-if="!analisis.resultados?.lugares?.length" class="empty-tab">No se encontraron lugares</div>
              <div v-for="(l, i) in analisis.resultados?.lugares" :key="i" class="result-item">
                <div class="result-type">🌍 {{ formatTipo(l.tipo, 'LUGAR') }}</div>
                <div class="result-text">{{ l.texto_completo || l.texto }}</div>
                <div class="result-meta">
                  <span>📍 {{ l.nombre || l.texto || 'N/A' }}</span>
                  <span v-if="l.numero_pagina || l.pagina" class="page-tag">Página {{ l.numero_pagina || l.pagina }}</span>
                </div>
              </div>
            </div>

            <!-- Diligencias -->
            <div v-if="tabActual === 'diligencias'" class="results-section">
              <div v-if="!analisis.resultados?.diligencias?.length" class="empty-tab">No se encontraron diligencias</div>
              <div v-for="(d, i) in analisis.resultados?.diligencias" :key="i" class="result-item">
                <div class="result-type">⚖️ {{ formatTipo(d.tipo, 'DILIGENCIA') }}</div>
                <div class="result-text">{{ d.texto_encontrado }}</div>
                <div class="result-meta">
                  <span>📋 Contexto: {{ d.contexto ? d.contexto.slice(0, 100) + '...' : 'Sin contexto' }}</span>
                  <span v-if="d.numero_pagina" class="page-tag">Página {{ d.numero_pagina }}</span>
                </div>
              </div>
            </div>

            <!-- Alertas -->
            <div v-if="tabActual === 'alertas'" class="results-section">
              <div v-if="!analisis.resultados?.alertas?.length" class="empty-tab">No se encontraron alertas</div>
              <div v-for="(a, i) in analisis.resultados?.alertas" :key="i"
                class="result-item result-alerta">
                <div class="result-type">🚨 {{ (a.tipo || 'ALERTA').toUpperCase() }}</div>
                <div class="result-text">{{ a.descripcion }}</div>
                <div class="result-text result-cita">"{{ a.texto_encontrado }}"</div>
                <div class="result-meta">
                  <span v-if="a.numero_pagina" class="page-tag">Página {{ a.numero_pagina }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <ToastContainer />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import ToastContainer from '@/components/ToastContainer.vue'

const { get } = useApi()
const auth = useAuthStore()
const { showToast } = useToast()
const route = useRoute()

const tomos           = ref([])
const tomoSeleccionado = ref('')
const cargandoTomos   = ref(false)
const cargando        = ref(false)
const analisis        = ref(null)
const tabActual       = ref('fechas')

const tabs = [
  { key: 'fechas',      label: '📅 Fechas'       },
  { key: 'nombres',     label: '👤 Nombres'      },
  { key: 'direcciones', label: '🏠 Direcciones'  },
  { key: 'lugares',     label: '🌍 Lugares'      },
  { key: 'diligencias', label: '⚖️ Diligencias'  },
  { key: 'alertas',     label: '🚨 Alertas'      },
]

function formatTipo(tipo, fallback) {
  if (!tipo) return fallback
  return tipo.replace(/_/g, ' ').toUpperCase()
}

onMounted(async () => {
  cargandoTomos.value = true
  try {
    const uid = auth.user?.id
    const data = uid
      ? await get(`/permisos/usuarios/${uid}`)
      : await get('/permisos/usuarios/me/tomos-accesibles')
    // Filtrar solo los que tienen ver=true
    const lista = Array.isArray(data) ? data : (data?.tomos ?? [])
    tomos.value = lista.filter(t => t.ver !== false)
  } catch {
    showToast('Error al cargar documentos', 'error')
  } finally {
    cargandoTomos.value = false
  }

  // Auto-cargar si llega con ?tomo_id desde el dashboard
  const tid = route.query.tomo_id
  if (tid) {
    tomoSeleccionado.value = parseInt(tid)
    await cargarAnalisis()
  }
})

async function cargarAnalisis() {
  if (!tomoSeleccionado.value) return
  cargando.value = true
  analisis.value = null
  tabActual.value = 'fechas'
  try {
    const data = await get(`/tomos/${tomoSeleccionado.value}/analisis-avanzado`)
    analisis.value = data
  } catch (e) {
    showToast('Error al cargar análisis: ' + (e.message || ''), 'error')
  } finally {
    cargando.value = false
  }
}
</script>

<style scoped>
.page-wrapper { min-height: 100vh; background: #f0f2f5; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px 20px; display: flex; flex-direction: column; gap: 20px; }

.card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.07); overflow: hidden; }
.card-header {
  background: linear-gradient(135deg, #1a365d, #2c5aa0); color: white;
  padding: 14px 20px; font-weight: 600; font-size: 15px;
}
.card-body { padding: 20px; }

.form-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.tomo-select {
  flex: 1; padding: 12px 16px; border: 2px solid #e9ecef;
  border-radius: 10px; font-size: 15px; background: white; outline: none;
  transition: border-color .2s; min-width: 200px;
}
.tomo-select:focus { border-color: #2c5aa0; }
.btn-analizar {
  padding: 12px 22px; background: linear-gradient(135deg, #2c5aa0, #1a365d);
  color: white; border: none; border-radius: 10px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; gap: 8px;
  transition: all .3s; white-space: nowrap;
}
.btn-analizar:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(44,90,160,.4); }
.btn-analizar:disabled { opacity: 0.6; cursor: not-allowed; }

.loading-box {
  text-align: center; padding: 60px 20px; color: #6c757d;
  background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.07);
}
.loading-icon { font-size: 56px; margin-bottom: 12px; }
.loading-box h3 { color: #1a365d; margin-bottom: 8px; }

.stats-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 14px;
}
.stat-box {
  background: white; border-radius: 12px; padding: 18px 12px; text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,.07); transition: transform .2s;
}
.stat-box:hover { transform: translateY(-3px); }
.stat-number { font-size: 28px; font-weight: 700; color: #1a365d; }
.stat-label { font-size: 12px; color: #6c757d; margin-top: 4px; text-transform: uppercase; letter-spacing: .5px; }

.tabs-card {}
.tabs {
  display: flex; border-bottom: 3px solid #e9ecef; margin-bottom: 20px;
  background: rgba(248,249,250,.8); border-radius: 8px 8px 0 0; overflow: hidden; overflow-x: auto;
}
.tab {
  padding: 13px 18px; background: none; border: none; border-bottom: 3px solid transparent;
  cursor: pointer; font-weight: 600; font-size: 13px; color: #495057; flex: 1;
  text-align: center; transition: all .3s; white-space: nowrap;
}
.tab.active { border-bottom-color: #17a2b8; color: #17a2b8; background: rgba(23,162,184,.1); }
.tab:hover:not(.active) { background: rgba(23,162,184,.05); color: #17a2b8; }

.results-section { display: flex; flex-direction: column; gap: 14px; }
.empty-tab { text-align: center; color: #7f8c8d; padding: 30px; font-style: italic; }

.result-item {
  border: 1px solid #e9ecef; border-radius: 10px; padding: 14px 16px;
  background: #fafafa; transition: box-shadow .2s;
}
.result-item:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); }
.result-alerta { border-left: 4px solid #e74c3c; }
.result-type { font-size: 13px; font-weight: 700; color: #1a365d; margin-bottom: 6px; }
.result-text { color: #2c3e50; margin-bottom: 8px; line-height: 1.5; }
.result-cita { font-style: italic; color: #e74c3c; }
.result-meta {
  display: flex; flex-wrap: wrap; gap: 10px; font-size: 12px; color: #6c757d;
  align-items: center;
}
.page-tag {
  background: #17a2b8; color: white; padding: 2px 10px; border-radius: 20px;
  font-size: 11px; font-weight: 700;
}
.nombre-completa {
  display: grid; grid-template-columns: auto 1fr; gap: 6px 10px;
  margin: 6px 0 8px; font-size: 13px; align-items: center;
}
.nombre-parte {
  background: rgba(23,162,184,.1); color: #17a2b8; padding: 2px 8px;
  border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase;
}
.direccion-completa {
  display: grid; grid-template-columns: auto 1fr; gap: 6px 10px;
  margin: 6px 0 8px; font-size: 13px; align-items: center;
}
.dir-parte {
  background: rgba(255,193,7,.1); color: #856404; padding: 2px 8px;
  border-radius: 3px; font-size: 11px; font-weight: 600;
}
</style>
