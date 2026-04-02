# Arquitectura Técnica — Sistema OCR RIDAC

## Diagrama General

```
┌─────────────────────────────────────────────────────────────┐
│                     Navegador (Cliente)                     │
│              Vue 3 SPA — http://localhost:5173              │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP /api/*  (proxy Vite en dev)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI — http://localhost:8001                │
│   JWT Auth · Rate Limiting (slowapi) · CORS middleware      │
└──────┬──────────────────┬────────────────────────┬──────────┘
       │                  │                        │
       ▼                  ▼                        ▼
  PostgreSQL 15       Redis 7               Celery Workers
  (datos + pgvector  (sesiones /           (OCR async,
   + pg_trgm)         caché tokens)         embeddings)
```

---

## Frontend Vue 3

### Estructura `src/`

```
src/
├── main.js              # Bootstrap app: Vue + Pinia + Router
├── App.vue              # Root component con <RouterView>
├── router/
│   └── index.js         # Rutas + guards requiresAuth / roles
├── stores/
│   └── auth.js          # Pinia store: usuario, token, rol
├── composables/
│   ├── useApi.js        # fetch wrapper con JWT automático
│   └── useToast.js      # Notificaciones toast globales
├── components/
│   ├── AppHeader.vue    # Barra superior con nav y logout
│   └── ToastContainer.vue
└── views/               # 22 vistas (ver tabla abajo)
```

### Vistas y Roles

| Vista | Ruta | Rol |
|-------|------|-----|
| `LoginView` | `/` | — |
| `DashboardView` | `/dashboard` | admin |
| `DashboardUsuarioView` | `/dashboard-usuario` | usuario |
| `CarpetasView` | `/carpetas` | admin |
| `UsuariosView` | `/usuarios` | admin |
| `PermisosView` | `/permisos` | admin |
| `AuditoriaView` | `/auditoria` | admin |
| `MonitorOCRView` | `/monitor-ocr` | admin/usuario |
| `AnalisisIAView` | `/analisis-ia` | admin |
| `AutocorrectorLegalView` | `/autocorrector-legal` | admin |
| `CorreccionDiligenciasView` | `/correccion-diligencias` | admin |
| `GenerarEmbeddingsView` | `/generar-embeddings` | admin |
| `LimpiezaPersonasView` | `/limpieza-personas` | admin |
| `BusquedaView` | `/busqueda` | admin/usuario |
| `BusquedaSemanticaView` | `/busqueda-semantica` | admin/usuario |
| `AnalisisAvanzadoView` | `/analisis-avanzado` | usuario |
| `VisorPDFView` | `/visor-pdf` | admin/usuario |
| `OcrExtractionView` | `/ocr-extraction` | admin/usuario |
| `OcrPdf24View` | `/ocr-pdf24` | admin/usuario |
| `RevisionDireccionesView` | `/revision-direcciones` | admin |
| `CambiarPasswordView` | `/cambiar-password` | todos |
| `ProgressMonitorView` | `/progress-monitor` | admin |

### Guard de Navegación

```js
// router/index.js
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) → redirect '/'
  if (to.meta.roles && !to.meta.roles.includes(auth.rol))  → redirect dashboard
})
```

### Comunicación con el Backend

`useApi.js` inyecta automáticamente:
- Header `Authorization: Bearer <token>` en cada request
- Manejo de 401 → logout automático + redirect a login

---

## Backend FastAPI

### Módulos Principales `app/`

```
app/
├── config.py         # Settings desde .env (pydantic-settings)
├── database.py       # Engine SQLAlchemy + get_db dependency
├── redis_config.py   # Pool Redis para sesiones y caché
├── models/           # Modelos ORM
│   ├── usuario.py    # Usuario, Rol
│   ├── tomo.py       # Tomo, ContenidoOCR
│   └── extraccion.py # ExtraccionTomo, DiligenciaTomo, PersonaMencionada, Declaracion, AlertaInactividad
├── routes/           # Routers FastAPI (20+ archivos)
├── controllers/      # Lógica de negocio separada de los endpoints
├── services/         # OCR, embeddings, búsqueda semántica, exportación
├── tasks/            # Tareas Celery async
├── middlewares/      # Auth JWT, rate limiting, logging
└── utils/            # Helpers reutilizables
```

### Endpoints Principales

| Grupo | Prefijo | Descripción |
|-------|---------|-------------|
| Auth | `/api/auth` | Login, refresh token, logout |
| Usuarios | `/api/usuarios` | CRUD usuarios (admin) |
| Carpetas | `/api/carpetas` | CRUD carpetas de investigación |
| Tomos | `/api/tomos` | Carga, listado, procesamiento OCR |
| Permisos | `/api/permisos` | Asignación ver/buscar/exportar por analista |
| Búsqueda | `/api/busqueda` | Búsqueda texto libre con pg_trgm |
| Semántica | `/api/semantica` | Búsqueda vectorial con pgvector |
| Análisis | `/api/admin/analisis` | Análisis IA carpetas (admin) |
| Análisis avanzado | `/api/tomos/:id/analisis-avanzado` | Resultados por tomo |
| Auditoría | `/api/auditoria` | Log de acciones |
| OCR | `/api/ocr` | Extracción manual / por área |
| Stats | `/api/stats` | Estadísticas del sistema |

### Autenticación JWT

- **Access Token**: 15 min — se manda en header `Authorization: Bearer`
- **Refresh Token**: 7 días — almacenado en Redis, se rota en cada refresh
- **Invalidación**: Al hacer logout se borra el refresh del Redis

---

## Base de Datos

### Extensiones PostgreSQL

| Extensión | Uso |
|-----------|-----|
| `pg_trgm` | Búsqueda de texto similar (fuzzy search) |
| `pgvector` | Búsqueda semántica por embedding vectorial |

### Modelos Principales

```
Usuario         → tiene → Rol
Tomo            → pertenece a → Carpeta
                → tiene → ContenidoOCR (texto extraído)
ExtraccionTomo  → tiene → DiligenciaTomo
                       → PersonaMencionada
                       → Declaracion
                       → AlertaInactividad
PermisoUsuario  → [usuario_id, tomo_id, ver, buscar, exportar]
```

---

## Flujo OCR

```
Upload PDF ──► Celery Task ──► Tesseract / EasyOCR / PaddleOCR
                                        │
                               Texto extraído
                                        │
                          Guardar en ContenidoOCR
                                        │
                     ┌──────────────────┴─────────────────────┐
                     │                                         │
             Generar embeddings                       Análisis jurídico
             (pgvector)                             diligencias, personas,
             para búsqueda semántica                fechas, alertas MP
```
