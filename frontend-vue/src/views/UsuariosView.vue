<template>
  <div>
    <AppHeader />
    <div class="container">

      <!-- Barra de acciones -->
      <div class="toolbar">
        <h2>👥 Gestión de Usuarios</h2>
        <button class="btn-primary" @click="abrirModalCrear">➕ Crear Usuario</button>
      </div>

      <!-- Spinner / Tabla -->
      <div class="card">
        <div v-if="loading" class="msg-center">⏳ Cargando usuarios...</div>
        <div v-else-if="error" class="msg-center"  style="color:#dc3545">❌ {{ error }}</div>
        <template v-else>
          <!-- Buscador -->
          <div class="search-bar">
            <input v-model="busqueda" type="text" placeholder="🔍 Buscar usuario, nombre o email..." class="input-search" />
            <span class="total-badge">{{ usuariosFiltrados.length }} usuarios</span>
          </div>

          <div class="table-wrap">
            <table class="tabla">
              <thead>
                <tr>
                  <th>#</th><th>Usuario</th><th>Nombre</th><th>Email</th><th>Rol</th><th>Estado</th><th>Último Acceso</th><th>Acciones</th>
                </tr>
              </thead>
              <tbody v-if="usuariosFiltrados.length">
                <tr v-for="(u, i) in usuariosPagina" :key="u.id">
                  <td>{{ (pagina - 1) * porPagina + i + 1 }}</td>
                  <td><strong>{{ u.username }}</strong></td>
                  <td>{{ u.nombre }}</td>
                  <td>{{ u.email }}</td>
                  <td><span class="rol-badge">{{ u.rol?.nombre || u.rol || 'Sin rol' }}</span></td>
                  <td>
                    <span :class="['estado-badge', u.activo ? 'activo' : 'inactivo']">
                      {{ u.activo ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>
                  <td class="text-sm">{{ u.ultimo_acceso ? formatFecha(u.ultimo_acceso) : 'Nunca' }}</td>
                  <td class="acciones-col">
                    <button class="btn-sm warning" @click="editarUsuario(u)">✏️ Editar</button>
                    <button class="btn-sm" :class="u.activo ? 'secondary' : 'success'" @click="toggleEstado(u)">
                      {{ u.activo ? 'Desactivar' : 'Activar' }}
                    </button>
                    <button class="btn-sm danger" @click="eliminarUsuario(u)" :disabled="u.id === usuarioActual?.id">🗑️</button>
                  </td>
                </tr>
              </tbody>
              <tbody v-else>
                <tr><td colspan="8" class="msg-center">Sin resultados</td></tr>
              </tbody>
            </table>
          </div>

          <!-- Paginación -->
          <div v-if="totalPaginas > 1" class="paginacion">
            <button @click="pagina--" :disabled="pagina === 1" class="btn-sm secondary">← Anterior</button>
            <span>Página {{ pagina }} / {{ totalPaginas }}</span>
            <button @click="pagina++" :disabled="pagina === totalPaginas" class="btn-sm secondary">Siguiente →</button>
          </div>
        </template>
      </div>

    </div>

    <!-- ══ MODAL CREAR / EDITAR ══ -->
    <Teleport to="body">
      <div v-if="modal.visible" class="modal-overlay" @click.self="cerrarModal">
        <div class="modal-box">
          <div class="modal-header">
            <h3>{{ modal.editando ? '✏️ Editar Usuario' : '➕ Crear Usuario' }}</h3>
            <button class="close-btn" @click="cerrarModal">✕</button>
          </div>
          <form @submit.prevent="guardarUsuario" class="form-grid">
            <div class="form-group">
              <label>Usuario *</label>
              <input v-model="form.username" type="text" required class="input" :disabled="modal.editando" />
            </div>
            <div class="form-group">
              <label>Nombre Completo *</label>
              <input v-model="form.nombre" type="text" required class="input" />
            </div>
            <div class="form-group full">
              <label>Email *</label>
              <input v-model="form.email" type="email" required class="input" />
            </div>
            <div class="form-group full">
              <label>Contraseña {{ modal.editando ? '(dejar vacío para no cambiar)' : '*' }}</label>
              <div class="password-row">
                <input v-model="form.password" :type="mostrarPassword ? 'text' : 'password'" class="input" :required="!modal.editando" />
                <button type="button" class="btn-sm secondary" @click="mostrarPassword = !mostrarPassword">{{ mostrarPassword ? '🙈' : '👁️' }}</button>
                <button type="button" class="btn-sm secondary" @click="generarPassword">🔑</button>
              </div>
            </div>
            <div class="form-group">
              <label>Rol *</label>
              <select v-model="form.rol" required class="input">
                <option value="">Seleccione...</option>
                <option v-for="r in roles" :key="r.id ?? r" :value="r.nombre ?? r">{{ r.nombre ?? r }}</option>
              </select>
            </div>
            <div class="form-group">
              <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                <input type="checkbox" v-model="form.activo" /> Usuario Activo
              </label>
            </div>
            <div class="form-footer">
              <button type="button" class="btn-sm secondary" @click="cerrarModal">Cancelar</button>
              <button type="submit" class="btn-primary" :disabled="guardando">
                {{ guardando ? 'Guardando...' : (modal.editando ? 'Guardar Cambios' : 'Crear Usuario') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ══ TOAST ══ -->
    <Teleport to="body">
      <div v-if="toast.visible" :class="['toast', toast.tipo]">{{ toast.mensaje }}</div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import AppHeader from '@/components/AppHeader.vue'
import { useApi } from '@/composables/useApi'
import { useAuthStore } from '@/stores/auth'

const { get, post, put, del } = useApi()
const auth = useAuthStore()

const loading   = ref(true)
const error     = ref(null)
const usuarios  = ref([])
const roles     = ref([])
const busqueda  = ref('')
const pagina    = ref(1)
const porPagina = 10
const guardando = ref(false)
const mostrarPassword = ref(false)

const usuarioActual = computed(() => auth.user)

const modal = ref({ visible: false, editando: false, userId: null })
const form  = ref({ username:'', nombre:'', email:'', password:'', rol:'', activo:true })
const toast = ref({ visible: false, tipo: 'success', mensaje: '' })

let refreshTimer = null

const usuariosFiltrados = computed(() => {
  const q = busqueda.value.toLowerCase()
  return q
    ? usuarios.value.filter(u =>
        (u.username||'').toLowerCase().includes(q) ||
        (u.nombre||'').toLowerCase().includes(q) ||
        (u.email||'').toLowerCase().includes(q)
      )
    : usuarios.value
})

const totalPaginas = computed(() => Math.max(1, Math.ceil(usuariosFiltrados.value.length / porPagina)))

const usuariosPagina = computed(() => {
  const start = (pagina.value - 1) * porPagina
  return usuariosFiltrados.value.slice(start, start + porPagina)
})

onMounted(async () => {
  await Promise.allSettled([cargarUsuarios(), cargarRoles()])
  refreshTimer = setInterval(cargarUsuarios, 15000)
})

onUnmounted(() => clearInterval(refreshTimer))

async function cargarUsuarios() {
  try {
    const data = await get('/admin/usuarios')
    usuarios.value = Array.isArray(data) ? data : (data.usuarios || [])
    usuarios.value.sort((a, b) => a.id - b.id)
  } catch (e) {
    error.value = 'No se pudieron cargar los usuarios'
  } finally {
    loading.value = false
  }
}

async function cargarRoles() {
  try {
    const data = await get('/admin/roles')
    roles.value = Array.isArray(data) ? data : [{ nombre: 'admin' }]
  } catch {
    roles.value = [{ nombre: 'admin' }]
  }
}

function abrirModalCrear() {
  form.value = { username:'', nombre:'', email:'', password:'', rol:'usuario', activo: true }
  modal.value = { visible: true, editando: false, userId: null }
  mostrarPassword.value = false
}

function editarUsuario(u) {
  form.value = { username: u.username, nombre: u.nombre, email: u.email, password: '', rol: u.rol?.nombre ?? u.rol ?? '', activo: u.activo }
  modal.value = { visible: true, editando: true, userId: u.id }
  mostrarPassword.value = false
}

function cerrarModal() {
  modal.value.visible = false
}

function generarPassword() {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%'
  let pwd = ''
  for (let i = 0; i < 12; i++) pwd += chars[Math.floor(Math.random() * chars.length)]
  form.value.password = pwd
  mostrarPassword.value = true
}

async function guardarUsuario() {
  guardando.value = true
  try {
    const payload = {
      username: form.value.username,
      nombre: form.value.nombre,
      email: form.value.email,
      rol: form.value.rol,
      activo: form.value.activo
    }
    if (form.value.password) payload.password = form.value.password

    if (modal.value.editando) {
      await put(`/admin/usuarios/${modal.value.userId}`, payload)
      mostrarToast('Usuario actualizado correctamente', 'success')
    } else {
      await post('/admin/usuarios', payload)
      mostrarToast('Usuario creado correctamente', 'success')
    }
    cerrarModal()
    await cargarUsuarios()
  } catch (e) {
    mostrarToast('Error al guardar: ' + (e.message || 'Intente de nuevo'), 'error')
  } finally {
    guardando.value = false
  }
}

async function toggleEstado(u) {
  try {
    await put(`/admin/usuarios/${u.id}`, { ...u, activo: !u.activo })
    u.activo = !u.activo
    mostrarToast(`Usuario ${u.activo ? 'activado' : 'desactivado'}`, 'success')
  } catch {
    mostrarToast('Error al cambiar estado', 'error')
  }
}

async function eliminarUsuario(u) {
  if (!confirm(`¿Eliminar permanentemente al usuario "${u.username}"? Esta acción no se puede deshacer.`)) return
  try {
    await del(`/admin/usuarios/${u.id}`)
    mostrarToast('Usuario eliminado', 'success')
    await cargarUsuarios()
  } catch {
    mostrarToast('Error al eliminar usuario', 'error')
  }
}

function mostrarToast(mensaje, tipo = 'success') {
  toast.value = { visible: true, tipo, mensaje }
  setTimeout(() => { toast.value.visible = false }, 3500)
}

function formatFecha(f) {
  return new Date(f).toLocaleString('es-MX', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })
}
</script>

<style scoped>
.container { max-width: 1400px; margin: 0 auto; padding: 30px; }

.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.toolbar h2 { color: #1a365d; font-size: 22px; margin: 0; }

.card { background: white; border-radius: 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); overflow: hidden; padding: 24px; }
.msg-center { padding: 40px; text-align: center; color: #6c757d; font-size: 15px; }

.search-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.input-search { flex: 1; padding: 10px 16px; border: 2px solid #e9ecef; border-radius: 25px; font-size: 14px; outline: none; }
.input-search:focus { border-color: #2c5aa0; }
.total-badge { background: #e3f2fd; color: #1565c0; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; white-space: nowrap; }

.table-wrap { overflow-x: auto; }
.tabla { width: 100%; border-collapse: collapse; font-size: 14px; }
.tabla th { background: linear-gradient(135deg, #1a365d, #2c5aa0); color: white; padding: 12px 14px; text-align: left; font-size: 12px; text-transform: uppercase; }
.tabla td { padding: 12px 14px; border-bottom: 1px solid #f0f0f0; }
.tabla tr:hover td { background: #f8f9fa; }
.text-sm { font-size: 12px; color: #6c757d; }

.rol-badge { background: #e8f4fd; color: #1565c0; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; text-transform: capitalize; }
.estado-badge { padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 700; }
.activo   { background: #d4edda; color: #155724; }
.inactivo { background: #f8d7da; color: #721c24; }

.acciones-col { white-space: nowrap; }

.btn-primary { background: linear-gradient(135deg, #1a365d, #2c5aa0); color: white; border: none; padding: 10px 20px; border-radius: 22px; cursor: pointer; font-weight: 600; font-size: 14px; transition: all .2s; }
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(44,90,160,.4); }
.btn-primary:disabled { opacity: .6; cursor: not-allowed; transform: none; }

.btn-sm { border: none; padding: 6px 12px; border-radius: 16px; cursor: pointer; font-size: 12px; font-weight: 600; margin: 2px; transition: all .2s; }
.btn-sm:hover:not(:disabled) { transform: translateY(-1px); }
.btn-sm:disabled { opacity: .5; cursor: not-allowed; }
.btn-sm.warning   { background: linear-gradient(135deg, #ffc107, #ffb347); color: #333; }
.btn-sm.success   { background: linear-gradient(135deg, #28a745, #20c997); color: white; }
.btn-sm.secondary { background: linear-gradient(135deg, #6c757d, #545b62); color: white; }
.btn-sm.danger    { background: linear-gradient(135deg, #dc3545, #e57373); color: white; }

.paginacion { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 20px; font-size: 14px; color: #495057; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(4px); z-index: 2000; display: flex; align-items: center; justify-content: center; }
.modal-box { background: white; border-radius: 16px; width: 95%; max-width: 520px; box-shadow: 0 20px 60px rgba(0,0,0,.3); animation: slideIn .25s ease; overflow: hidden; }
@keyframes slideIn { from { opacity:0; transform: translateY(-30px) } }
.modal-header { background: linear-gradient(135deg, #1a365d, #2c5aa0); padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; }
.modal-header h3 { color: white; margin: 0; font-size: 17px; }
.close-btn { background: rgba(255,255,255,.15); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer; font-size: 14px; display: flex; align-items: center; justify-content: center; }
.close-btn:hover { background: rgba(255,255,255,.3); }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 24px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group.full { grid-column: 1 / -1; }
.form-group label { font-size: 12px; font-weight: 700; color: #495057; text-transform: uppercase; }
.input { width: 100%; padding: 10px 14px; border: 2px solid #e9ecef; border-radius: 10px; font-size: 14px; outline: none; box-sizing: border-box; }
.input:focus { border-color: #2c5aa0; }
.input:disabled { background: #f0f0f0; }
.password-row { display: flex; gap: 6px; }
.password-row .input { flex: 1; }
.form-footer { grid-column: 1 / -1; display: flex; justify-content: flex-end; gap: 10px; padding-top: 8px; border-top: 1px solid #f0f0f0; }

/* Toast */
.toast { position: fixed; bottom: 24px; right: 24px; padding: 14px 22px; border-radius: 12px; font-size: 14px; font-weight: 600; z-index: 9999; animation: toastIn .3s ease; box-shadow: 0 6px 20px rgba(0,0,0,.2); }
.toast.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.toast.error   { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
@keyframes toastIn { from { transform: translateX(80px); opacity: 0 } }
</style>
