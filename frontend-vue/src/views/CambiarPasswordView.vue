<template>
  <div>
    <AppHeader />
    <div class="container">
      <div class="card">
        <h2><i class="fas fa-key" /> Cambiar Contraseña</h2>
        <form @submit.prevent="guardar" class="pw-form">
          <div class="form-group">
            <label>Contraseña Actual</label>
            <input v-model="form.current_password" type="password" required />
          </div>
          <div class="form-group">
            <label>Nueva Contraseña</label>
            <input v-model="form.new_password" type="password" required minlength="6" />
          </div>
          <div class="form-group">
            <label>Confirmar Nueva Contraseña</label>
            <input v-model="confirmar" type="password" required />
          </div>
          <p v-if="error" class="error-msg"><i class="fas fa-exclamation-circle" /> {{ error }}</p>
          <div class="form-actions">
            <RouterLink to="/dashboard-usuario" class="btn-cancel">Cancelar</RouterLink>
            <button type="submit" class="btn-primary" :disabled="saving">
              <span v-if="saving"><i class="fas fa-spinner fa-spin" /> Guardando...</span>
              <span v-else><i class="fas fa-save" /> Guardar</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'

const { post } = useApi()
const { showToast } = useToast()
const { clearSession } = useAuthStore()
const router = useRouter()

const form = ref({ current_password: '', new_password: '' })
const confirmar = ref('')
const saving = ref(false)
const error = ref('')

async function guardar() {
  error.value = ''
  if (form.value.new_password !== confirmar.value) {
    error.value = 'Las contraseñas no coinciden'
    return
  }
  saving.value = true
  try {
    await post('/auth/change-password', form.value)
    showToast('Contraseña actualizada. Por favor inicia sesión nuevamente.', 'success')
    clearSession()
    router.push({ name: 'login' })
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.container { max-width: 480px; margin: 60px auto; padding: 0 20px; }
.card { background: #fff; padding: 32px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.07); }
.card h2 { color: #1a365d; margin-bottom: 24px; }
.pw-form { display: flex; flex-direction: column; gap: 4px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-weight: 600; color: #4a5568; font-size: 14px; }
.form-group input { width: 100%; padding: 10px 14px; border: 2px solid #e9ecef; border-radius: 10px; font-size: 14px; outline: none; background: #f8f9fa; transition: border-color 0.2s; }
.form-group input:focus { border-color: #2c5aa0; background: #fff; }
.error-msg { color: #dc3545; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }
.form-actions { display: flex; gap: 10px; justify-content: flex-end; }
.btn-primary { background: linear-gradient(135deg,#1a365d,#2c5aa0); color: white; border: none; padding: 10px 22px; border-radius: 20px; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.btn-primary:disabled { opacity: 0.65; cursor: not-allowed; }
.btn-cancel { padding: 10px 22px; border: 2px solid #e9ecef; border-radius: 20px; text-decoration: none; color: #6c757d; font-weight: 600; }
</style>
