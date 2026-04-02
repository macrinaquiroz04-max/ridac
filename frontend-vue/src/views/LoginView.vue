<template>
  <div class="login-page">
    <div class="login-container">
      <div class="logo">
        <div class="logo-icon">
          <i class="fas fa-file-alt" />
        </div>
        <h1>RIDAC</h1>
        <p>Sistema OCR de Análisis Jurídico</p>
      </div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username">
            <i class="fas fa-user" /> Usuario
          </label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            placeholder="Ingresa tu usuario"
            autocomplete="username"
            required
          />
        </div>

        <div class="form-group">
          <label for="password">
            <i class="fas fa-lock" /> Contraseña
          </label>
          <div class="input-password">
            <input
              id="password"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="Ingresa tu contraseña"
              autocomplete="current-password"
              required
            />
            <button type="button" class="toggle-pw" @click="showPassword = !showPassword">
              <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'" />
            </button>
          </div>
        </div>

        <p v-if="errorMsg" class="error-msg">
          <i class="fas fa-exclamation-circle" /> {{ errorMsg }}
        </p>

        <button type="submit" class="btn-login" :disabled="loading">
          <span v-if="loading"><i class="fas fa-spinner fa-spin" /> Ingresando...</span>
          <span v-else><i class="fas fa-sign-in-alt" /> Ingresar</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useApi } from '@/composables/useApi'

const router = useRouter()
const auth = useAuthStore()
const { post } = useApi()

const form = ref({ username: '', password: '' })
const loading = ref(false)
const showPassword = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    const data = await post('/auth/login', form.value)
    auth.setSession(data)

    if (data.user?.debe_cambiar_password) {
      router.push({ name: 'cambiar-password' })
    } else {
      router.push({ name: 'dashboard' })
    }
  } catch (err) {
    errorMsg.value = err.message || 'Credenciales incorrectas'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8eaed 0%, #d8dce0 100%);
}

.login-container {
  background: #f7f8fa;
  padding: 45px 40px;
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.08);
  width: 90%;
  max-width: 420px;
  border: 1px solid rgba(212,216,221,0.4);
  animation: slideUp 0.4s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(30px); }
  to   { opacity: 1; transform: translateY(0); }
}

.logo {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #1a365d, #2c5aa0);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  font-size: 32px;
  color: white;
  box-shadow: 0 6px 20px rgba(44,90,160,0.3);
}

.logo h1 {
  font-size: 30px;
  font-weight: 800;
  background: linear-gradient(135deg, #1a365d, #2c5aa0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 4px;
}

.logo p {
  color: #6c757d;
  font-size: 14px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #4a5568;
  font-size: 14px;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #d4d8dd;
  border-radius: 10px;
  font-size: 15px;
  background: #eef0f3;
  color: #4a5568;
  transition: border-color 0.2s, box-shadow 0.2s;
  outline: none;
}

.form-group input:focus {
  border-color: #2c5aa0;
  box-shadow: 0 0 0 3px rgba(44,90,160,0.12);
  background: #fff;
}

.input-password {
  position: relative;
}

.input-password input {
  padding-right: 46px;
}

.toggle-pw {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #6c757d;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
}

.error-msg {
  color: #dc3545;
  font-size: 14px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-login {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, #1a365d, #2c5aa0);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-login:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
}

.btn-login:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
