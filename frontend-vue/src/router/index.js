import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresGuest: true }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard-usuario',
    name: 'dashboard-usuario',
    component: () => import('@/views/DashboardUsuarioView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/carpetas',
    name: 'carpetas',
    component: () => import('@/views/CarpetasView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/busqueda',
    name: 'busqueda',
    component: () => import('@/views/BusquedaView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/visor-pdf',
    name: 'visor-pdf',
    component: () => import('@/views/VisorPDFView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/usuarios',
    name: 'usuarios',
    component: () => import('@/views/UsuariosView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/auditoria',
    name: 'auditoria',
    component: () => import('@/views/AuditoriaView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/monitor-ocr',
    name: 'monitor-ocr',
    component: () => import('@/views/MonitorOCRView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/analisis-ia',
    name: 'analisis-ia',
    component: () => import('@/views/AnalisisIAView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/busqueda-semantica',
    name: 'busqueda-semantica',
    component: () => import('@/views/BusquedaSemanticaView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/cambiar-password',
    name: 'cambiar-password',
    component: () => import('@/views/CambiarPasswordView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/permisos',
    name: 'permisos',
    component: () => import('@/views/PermisosView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/analisis-avanzado',
    name: 'analisis-avanzado',
    component: () => import('@/views/AnalisisAvanzadoView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/autocorrector-legal',
    name: 'autocorrector-legal',
    component: () => import('@/views/AutocorrectorLegalView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/correccion-diligencias',
    name: 'correccion-diligencias',
    component: () => import('@/views/CorreccionDiligenciasView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/generar-embeddings',
    name: 'generar-embeddings',
    component: () => import('@/views/GenerarEmbeddingsView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/limpieza-personas',
    name: 'limpieza-personas',
    component: () => import('@/views/LimpiezaPersonasView.vue'),
    meta: { requiresAuth: true, roles: ['admin'] }
  },
  {
    path: '/ocr-extraction',
    name: 'ocr-extraction',
    component: () => import('@/views/OcrExtractionView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ocr-pdf24',
    name: 'ocr-pdf24',
    component: () => import('@/views/OcrPdf24View.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/progress-monitor',
    name: 'progress-monitor',
    component: () => import('@/views/ProgressMonitorView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/revision-direcciones',
    name: 'revision-direcciones',
    component: () => import('@/views/RevisionDireccionesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Guard de navegación global
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'login' })
  }

  if (to.meta.requiresGuest && auth.isAuthenticated) {
    return next({ name: auth.user?.rol === 'admin' ? 'dashboard' : 'dashboard-usuario' })
  }

  if (to.meta.roles && !to.meta.roles.includes(auth.user?.rol)) {
    return next({ name: 'dashboard-usuario' })
  }

  next()
})

export default router
