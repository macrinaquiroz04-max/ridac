<template>
  <div>
    <AppHeader />
    <div class="container">

      <div class="page-header">
        <h2>🔑 Gestión de Permisos por Tomo</h2>
        <p>Asigna acceso granular a los usuarios sobre cada documento</p>
      </div>

      <!-- ══ FILTROS ══ -->
      <div class="filters-card">
        <div class="filters-row">
          <div class="filter-group">
            <label>Carpeta</label>
            <select v-model="filtroCarpeta" class="select-input" @change="filtroCarpeta && cargarTomosCarpeta(filtroCarpeta)">
              <option value="">Todas las carpetas</option>
              <option v-for="c in carpetas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Buscar usuario</label>
            <input v-model="filtroUsuario" type="text" placeholder="🔍 Nombre o usuario..." class="text-input" />
          </div>
        </div>
      </div>

      <!-- ══ DOS PANELES ══ -->
      <div class="two-panels">

        <!-- Panel izquierdo: Usuarios -->
        <div class="panel users-panel">
          <div class="panel-header">👥 Usuarios del Sistema</div>
          <div class="panel-body">
            <div v-if="loadingUsuarios" class="msg-center">⏳ Cargando...</div>
            <div v-else-if="!usuariosFiltrados.length" class="msg-center">Sin usuarios</div>
            <div
              v-for="u in usuariosFiltrados"
              :key="u.id"
              :class="['user-item', { selected: usuarioSeleccionado?.id === u.id }]"
              @click="seleccionarUsuario(u)"
            >
              <div class="user-avatar">{{ (u.nombre || u.username || '?')[0].toUpperCase() }}</div>
              <div class="user-info">
                <div class="user-name">{{ u.nombre || u.username }}</div>
                <div class="user-sub">@{{ u.username }} · {{ u.rol?.nombre || u.rol }}</div>
                <div v-if="conteosPermisos[u.id] !== undefined" class="user-perms-count">
                  <span :class="['perms-badge', classBadge(conteosPermisos[u.id])]">
                    {{ labelBadge(conteosPermisos[u.id]) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Panel derecho: Permisos -->
        <div class="panel perms-panel">
          <div class="panel-header">
            🛡️ Permisos de Acceso
            <span v-if="usuarioSeleccionado" class="selected-badge">{{ usuarioSeleccionado.username }}</span>
          </div>
          <div class="panel-body">

            <!-- Sin usuario seleccionado -->
            <div v-if="!usuarioSeleccionado" class="empty-state">
              <span class="empty-icon">👈</span>
              <p>Selecciona un usuario de la lista para gestionar sus permisos</p>
            </div>

            <!-- Cargando permisos -->
            <div v-else-if="loadingPermisos" class="msg-center">⏳ Cargando permisos...</div>

            <!-- Permisos cargados -->
            <template v-else>
              <!-- Acciones rápidas globales -->
              <div class="quick-actions">
                <button class="btn-quick success" @click="darTodoAcceso">✅ Acceso Total</button>
                <button class="btn-quick danger"  @click="quitarTodoAcceso">❌ Quitar Todo</button>
                <button class="btn-quick warning" @click="guardarCambiosMasivo" :disabled="guardandoMasivo">
                  {{ guardandoMasivo ? '⏳ Guardando...' : '💾 Guardar Cambios' }}
                </button>
              </div>

              <!-- Sin carpetas/tomos -->
              <div v-if="!carpetasConTomos.length" class="msg-center">No hay tomos disponibles</div>

              <!-- Carpeta → Tomos -->
              <div v-for="cp in carpetasConTomos" :key="cp.id" class="carpeta-block">
                <div class="carpeta-name">
                  📁 {{ cp.nombre }}
                  <div class="carpeta-actions">
                    <button class="btn-tiny success" @click="darAccesoCarpeta(cp)">Dar acceso</button>
                    <button class="btn-tiny danger"  @click="quitarAccesoCarpeta(cp)">Quitar</button>
                  </div>
                </div>
                <div class="tomos-list">
                  <div v-for="t in cp.tomos" :key="t.id" class="tomo-row">
                    <div class="tomo-name">📄 {{ t.nombre || `Tomo ${t.numero_tomo}` }}</div>
                    <div class="perms-toggles">
                      <label class="toggle-label" :title="'Ver PDF'">
                        <input type="checkbox" v-model="permisosMap[t.id].ver" @change="onPermisoChange(t.id)" />
                        <span class="toggle-track" :class="{ on: permisosMap[t.id].ver }">👁️ Ver</span>
                      </label>
                      <label class="toggle-label" :title="'Buscar en el tomo'">
                        <input type="checkbox" v-model="permisosMap[t.id].buscar" @change="onPermisoChange(t.id)" />
                        <span class="toggle-track" :class="{ on: permisosMap[t.id].buscar }">🔍 Buscar</span>
                      </label>
                      <label class="toggle-label" :title="'Exportar/Descargar'">
                        <input type="checkbox" v-model="permisosMap[t.id].exportar" @change="onPermisoChange(t.id)" />
                        <span class="toggle-track" :class="{ on: permisosMap[t.id].exportar }">📥 Exportar</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>

      </div>
    </div>

    <!-- Toast -->
    <Teleport to="body">
      <div v-if="toast.visible" :class="['toast', toast.tipo]">{{ toast.mensaje }}</div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { useApi } from '@/composables/useApi'

const { get, post, del } = useApi()

// ── datos ──
const usuarios  = ref([])
const carpetas  = ref([])

// ── filtros ──
const filtroCarpeta = ref('')
const filtroUsuario = ref('')

// ── estado de UI ──
const loadingUsuarios = ref(true)
const loadingPermisos = ref(false)
const guardandoMasivo = ref(false)
const usuarioSeleccionado = ref(null)

// ── permisos ──
const permisosMap = reactive({})          // tomo_id → { ver, buscar, exportar }
const permisosOriginales = reactive({})   // copia para detectar cambios
const tomosCargados = ref([])             // todos los tomos
const conteosPermisos = reactive({})      // user_id → número de tomos con permiso

const toast = ref({ visible: false, tipo: 'success', mensaje: '' })

// ── computed ──
const usuariosFiltrados = computed(() => {
  const q = filtroUsuario.value.toLowerCase()
  return q
    ? usuarios.value.filter(u =>
        (u.username||'').toLowerCase().includes(q) ||
        (u.nombre||'').toLowerCase().includes(q)
      )
    : usuarios.value
})

const carpetasConTomos = computed(() => {
  if (!tomosCargados.value.length) return []
  const filtro = filtroCarpeta.value
  return carpetas.value
    .filter(c => !filtro || c.id === +filtro)
    .map(c => ({ ...c, tomos: tomosCargados.value.filter(t => t.carpeta_id === c.id) }))
    .filter(c => c.tomos.length)
})

// ── init ──
onMounted(async () => {
  await Promise.allSettled([cargarUsuarios(), cargarCarpetasYTomos()])
})

async function cargarUsuarios() {
  loadingUsuarios.value = true
  try {
    const data = await get('/admin/usuarios')
    usuarios.value = (Array.isArray(data) ? data : (data.usuarios || []))
      .filter(u => {
        const rol = u.rol?.nombre ?? u.rol ?? ''
        return rol !== 'admin' && rol !== 'Admin' && rol !== 'administrador'
      })
    // calcular conteos en paralelo (máx 5 a la vez)
    for (const u of usuarios.value) {
      calcularConteoPermisos(u.id)
    }
  } finally {
    loadingUsuarios.value = false
  }
}

async function calcularConteoPermisos(userId) {
  try {
    const data = await get(`/permisos/usuarios/${userId}`)
    const lista = Array.isArray(data) ? data : (data.permisos || data.tomos || [])
    conteosPermisos[userId] = lista.filter(p => p.ver || p.puede_ver).length
  } catch {
    conteosPermisos[userId] = 0
  }
}

async function cargarCarpetasYTomos() {
  try {
    const data = await get('/carpetas')
    carpetas.value = Array.isArray(data) ? data : (data.carpetas || [])
    // cargar todos los tomos de cada carpeta
    const resultados = await Promise.allSettled(carpetas.value.map(c => get(`/tomos/${c.id}`)))
    const todos = []
    resultados.forEach((r, i) => {
      if (r.status === 'fulfilled') {
        const ts = Array.isArray(r.value) ? r.value : (r.value.tomos || [])
        ts.forEach(t => { t.carpeta_id = carpetas.value[i].id; todos.push(t) })
      }
    })
    tomosCargados.value = todos
  } catch {}
}

async function cargarTomosCarpeta(carpetaId) {
  // ya tenemos todos cargados; el computed filter maneja la visualización
}

async function seleccionarUsuario(u) {
  usuarioSeleccionado.value = u
  loadingPermisos.value = true
  try {
    const data = await get(`/permisos/usuarios/${u.id}`)
    const lista = Array.isArray(data) ? data : (data.permisos || data.tomos || [])
    // Inicializar mapa con todos los tomos en false
    for (const t of tomosCargados.value) {
      const perm = lista.find(p => p.tomo_id === t.id || p.id === t.id)
      permisosMap[t.id] = {
        ver:     perm ? !!(perm.ver ?? perm.puede_ver) : false,
        buscar:  perm ? !!(perm.buscar ?? perm.puede_buscar) : false,
        exportar:perm ? !!(perm.exportar ?? perm.puede_exportar) : false,
      }
      permisosOriginales[t.id] = { ...permisosMap[t.id] }
    }
  } catch {
    for (const t of tomosCargados.value) {
      permisosMap[t.id] = { ver: false, buscar: false, exportar: false }
      permisosOriginales[t.id] = { ver: false, buscar: false, exportar: false }
    }
  } finally {
    loadingPermisos.value = false
  }
}

function onPermisoChange(tomoId) {
  // Si se activa buscar o exportar → activar ver automáticamente
  if ((permisosMap[tomoId].buscar || permisosMap[tomoId].exportar) && !permisosMap[tomoId].ver) {
    permisosMap[tomoId].ver = true
  }
}

function darTodoAcceso() {
  for (const t of tomosCargados.value) {
    permisosMap[t.id] = { ver: true, buscar: true, exportar: true }
  }
}

function quitarTodoAcceso() {
  for (const t of tomosCargados.value) {
    permisosMap[t.id] = { ver: false, buscar: false, exportar: false }
  }
}

function darAccesoCarpeta(cp) {
  for (const t of cp.tomos) {
    permisosMap[t.id] = { ver: true, buscar: true, exportar: true }
  }
}

function quitarAccesoCarpeta(cp) {
  for (const t of cp.tomos) {
    permisosMap[t.id] = { ver: false, buscar: false, exportar: false }
  }
}

async function guardarCambiosMasivo() {
  if (!usuarioSeleccionado.value) return
  guardandoMasivo.value = true
  const uid = usuarioSeleccionado.value.id
  try {
    // Determinar qué tomos tenemos que dar/quitar
    const tomosDar   = []
    const tomosQuitar = []
    for (const t of tomosCargados.value) {
      const actual = permisosMap[t.id]
      const original = permisosOriginales[t.id] || { ver: false, buscar: false, exportar: false }
      if (JSON.stringify(actual) !== JSON.stringify(original)) {
        if (actual.ver || actual.buscar || actual.exportar) {
          tomosDar.push({ tomo_id: t.id, ...actual })
        } else {
          tomosQuitar.push(t.id)
        }
      }
    }

    await Promise.allSettled([
      ...tomosDar.map(p => post(`/permisos/usuarios/${uid}/tomos`, p)),
      ...tomosQuitar.map(id => del(`/permisos/usuarios/${uid}/tomos/${id}`))
    ])

    // actualizar originales
    for (const t of tomosCargados.value) {
      permisosOriginales[t.id] = { ...permisosMap[t.id] }
    }
    conteosPermisos[uid] = tomosCargados.value.filter(t => permisosMap[t.id]?.ver).length
    mostrarToast('Permisos guardados correctamente', 'success')
  } catch {
    mostrarToast('Error al guardar permisos', 'error')
  } finally {
    guardandoMasivo.value = false
  }
}

// ── badges ──
function classBadge(n) {
  if (n === 0) return 'sin-acceso'
  if (n >= tomosCargados.value.length && tomosCargados.value.length > 0) return 'completo'
  return 'parcial'
}
function labelBadge(n) {
  if (n === 0) return '❌ Sin acceso'
  if (n >= tomosCargados.value.length && tomosCargados.value.length > 0) return '✅ Acceso completo'
  return `🔶 ${n} tomos`
}

function mostrarToast(mensaje, tipo = 'success') {
  toast.value = { visible: true, tipo, mensaje }
  setTimeout(() => { toast.value.visible = false }, 3500)
}
</script>

<style scoped>
.container { max-width: 1400px; margin: 0 auto; padding: 30px; }

.page-header { margin-bottom: 24px; }
.page-header h2 { color: #1a365d; font-size: 22px; margin: 0 0 4px; }
.page-header p  { color: #6c757d; font-size: 14px; margin: 0; }

/* Filtros */
.filters-card { background: white; border-radius: 14px; padding: 20px; margin-bottom: 24px; box-shadow: 0 3px 12px rgba(0,0,0,.07); }
.filters-row  { display: flex; gap: 16px; flex-wrap: wrap; }
.filter-group { display: flex; flex-direction: column; gap: 6px; min-width: 200px; flex: 1; }
.filter-group label { font-size: 11px; font-weight: 700; color: #495057; text-transform: uppercase; }
.select-input, .text-input { padding: 9px 14px; border: 2px solid #e9ecef; border-radius: 10px; font-size: 14px; outline: none; }
.select-input:focus, .text-input:focus { border-color: #2c5aa0; }

/* Two-panel layout */
.two-panels { display: grid; grid-template-columns: 320px 1fr; gap: 20px; align-items: start; }
@media (max-width: 900px) { .two-panels { grid-template-columns: 1fr; } }

.panel { background: white; border-radius: 16px; box-shadow: 0 4px 16px rgba(0,0,0,.08); overflow: hidden; }
.panel-header { background: linear-gradient(135deg, #1a365d, #2c5aa0); color: white; padding: 14px 18px; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; }
.panel-body { max-height: 680px; overflow-y: auto; }
.selected-badge { background: rgba(255,255,255,.2); padding: 4px 10px; border-radius: 12px; font-size: 12px; }

/* User items */
.user-item { display: flex; align-items: flex-start; gap: 12px; padding: 14px 16px; cursor: pointer; border-bottom: 1px solid #f0f0f0; transition: background .15s; }
.user-item:hover    { background: #f0f4ff; }
.user-item.selected { background: #e3f2fd; border-left: 3px solid #2c5aa0; }
.user-avatar { width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, #2c5aa0, #34a853); color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 16px; flex-shrink: 0; }
.user-name { font-weight: 700; font-size: 14px; color: #1a365d; }
.user-sub  { font-size: 11px; color: #6c757d; }
.perms-badge { display: inline-block; margin-top: 3px; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 700; }
.completo   { background: #d4edda; color: #155724; }
.parcial    { background: #fff3cd; color: #856404; }
.sin-acceso { background: #f8d7da; color: #721c24; }

/* Empty state */
.empty-state { padding: 60px 20px; text-align: center; color: #6c757d; }
.empty-icon  { font-size: 48px; display: block; margin-bottom: 12px; }
.msg-center  { padding: 40px; text-align: center; color: #6c757d; }

/* Quick actions */
.quick-actions { display: flex; flex-wrap: wrap; gap: 8px; padding: 14px 16px; background: #f8f9fa; border-bottom: 1px solid #e9ecef; }

/* Carpeta blocks */
.carpeta-block  { padding: 14px 16px 4px; border-bottom: 1px solid #f0f0f0; }
.carpeta-name   { font-weight: 700; font-size: 14px; color: #1a365d; display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.carpeta-actions { display: flex; gap: 4px; }
.tomos-list     { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.tomo-row       { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 10px; background: #f8f9fa; border-radius: 10px; border-left: 3px solid #dee2e6; flex-wrap: wrap; }
.tomo-name      { font-size: 13px; color: #495057; flex: 1; min-width: 120px; }
.perms-toggles  { display: flex; gap: 6px; flex-wrap: wrap; }

/* Toggle labels */
.toggle-label input { display: none; }
.toggle-track { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; cursor: pointer; background: #e9ecef; color: #6c757d; transition: all .2s; border: 2px solid transparent; }
.toggle-track.on { background: #d4edda; color: #155724; border-color: #c3e6cb; }

/* Buttons */
.btn-quick { border: none; padding: 8px 14px; border-radius: 20px; cursor: pointer; font-size: 12px; font-weight: 700; transition: all .2s; }
.btn-quick:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(0,0,0,.15); }
.btn-quick:disabled { opacity: .6; cursor: not-allowed; }
.btn-quick.success { background: linear-gradient(135deg,#28a745,#20c997); color: white; }
.btn-quick.danger  { background: linear-gradient(135deg,#dc3545,#e57373); color: white; }
.btn-quick.warning { background: linear-gradient(135deg,#1a365d,#2c5aa0); color: white; }

.btn-tiny { border: none; padding: 4px 10px; border-radius: 12px; cursor: pointer; font-size: 11px; font-weight: 700; }
.btn-tiny.success { background: #d4edda; color: #155724; }
.btn-tiny.danger  { background: #f8d7da; color: #721c24; }

/* Toast */
.toast { position: fixed; bottom: 24px; right: 24px; padding: 14px 22px; border-radius: 12px; font-size: 14px; font-weight: 600; z-index: 9999; animation: toastIn .3s ease; box-shadow: 0 6px 20px rgba(0,0,0,.2); }
.toast.success { background: #d4edda; color: #155724; }
.toast.error   { background: #f8d7da; color: #721c24; }
@keyframes toastIn { from { transform: translateX(80px); opacity: 0 } }
</style>
