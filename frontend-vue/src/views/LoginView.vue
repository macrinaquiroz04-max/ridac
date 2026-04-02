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

      <form @submit.prevent="handleLogin" autocomplete="on" novalidate>
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
            maxlength="50"
            spellcheck="false"
            required
            :class="{ 'input-error': usernameError }"
            @input="onUsernameInput"
            @keydown="blockForbiddenKeys"
            @paste="onUsernamePaste"
          />
          <span v-if="usernameError" class="field-error">{{ usernameError }}</span>
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
              maxlength="128"
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

        <button type="submit" class="btn-login" :disabled="loading || !!usernameError || !canSubmit">
          <span v-if="loading"><i class="fas fa-spinner fa-spin" /> Ingresando...</span>
          <span v-else><i class="fas fa-sign-in-alt" /> Ingresar</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
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
const usernameError = ref('')
// Cooldown anti-fuerza-bruta en cliente: bloquea N segundos tras error
const failCount = ref(0)
const blockedUntil = ref(0)

const canSubmit = computed(() => Date.now() >= blockedUntil.value)

// Caracteres prohibidos en el campo usuario:
// espacios, guiones, comillas, puntos y coma, operadores SQL, barras, ángulos, etc.
const FORBIDDEN_CHARS_RE = /[\s'"`;=\-\\/|<>(){}[\]!@#$%^&*+~,?]/
const SQL_KEYWORDS_RE = /\b(select|insert|update|delete|drop|union|where|or|and|exec|xp_|cast|convert|declare|char|nchar|varchar)\b/i

function validateUsername(val) {
  if (!val) return ''
  if (FORBIDDEN_CHARS_RE.test(val)) return 'El usuario no puede contener espacios, guiones ni caracteres especiales'
  if (SQL_KEYWORDS_RE.test(val)) return 'Contenido no permitido en el usuario'
  if (val.length > 50) return 'Máximo 50 caracteres'
  return ''
}

function onUsernameInput() {
  usernameError.value = validateUsername(form.value.username)
}

function blockForbiddenKeys(e) {
  // Bloquear espacio y caracteres clave de inyección en tiempo real
  const forbidden = [' ', "'", '"', ';', '=', '-', '/', '\\', '<', '>', '(', ')', '`', '|', '+']
  if (forbidden.includes(e.key)) {
    e.preventDefault()
  }
}

function onUsernamePaste(e) {
  e.preventDefault()
  const pasted = (e.clipboardData || window.clipboardData).getData('text')
  // Eliminar todos los caracteres prohibidos del texto pegado
  const cleaned = pasted.replace(/[\s'"`;=\-\\/|<>(){}[\]!@#$%^&*+~,?]/g, '').slice(0, 50)
  form.value.username = cleaned
  usernameError.value = validateUsername(cleaned)
}

async function handleLogin() {
  // Verificar cooldown anti-fuerza-bruta
  if (!canSubmit.value) {
    const secs = Math.ceil((blockedUntil.value - Date.now()) / 1000)
    errorMsg.value = `Demasiados intentos. Espera ${secs} segundos.`
    return
  }

  // Validación final antes de enviar
  usernameError.value = validateUsername(form.value.username)
  if (usernameError.value) return

  if (!form.value.username.trim() || !form.value.password) {
    errorMsg.value = 'Completa todos los campos'
    return
  }

  errorMsg.value = ''
  loading.value = true
  try {
    const data = await post('/auth/login', {
      username: form.value.username.trim(),
      password: form.value.password
    })
    auth.setSession(data)
    failCount.value = 0

    if (data.user?.debe_cambiar_password) {
      router.push({ name: 'cambiar-password' })
    } else {
      router.push({ name: 'dashboard' })
    }
  } catch (err) {
    failCount.value++
    // Cooldown exponencial: 5s, 15s, 30s tras 3+ errores consecutivos
    if (failCount.value >= 3) {
      const delay = Math.min(30, 5 * (failCount.value - 2)) * 1000
      blockedUntil.value = Date.now() + delay
    }
    // Nunca revelar si el error es de usuario vs contraseña (A07)
    errorMsg.value = 'Credenciales incorrectas. Verifica tu usuario y contraseña.'
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

/* Validación en tiempo real */
.field-error {
  display: block;
  color: #dc3545;
  font-size: 12px;
  margin-top: 5px;
}

.form-group input.input-error {
  border-color: #dc3545;
  box-shadow: 0 0 0 3px rgba(220,53,69,0.12);
}
</style>
