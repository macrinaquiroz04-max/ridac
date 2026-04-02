import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/sistema.css'
import { initSecurityGuard } from './utils/security-guard'

// Activar guardia de seguridad (anti-devtools + consola falsa)
initSecurityGuard()

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
