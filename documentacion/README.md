# Sistema OCR RIDAC

Sistema de digitalización, extracción OCR y análisis jurídico de documentos para la
Unidad de Análisis y Contexto (UAyC) — FGJ CDMX.

---

## Descripción

Plataforma web que permite al personal de la UAyC:

- **Digitalizar** tomos físicos escaneados (PDF) mediante OCR (Tesseract / EasyOCR / PaddleOCR)
- **Organizar** documentos en carpetas de investigación con control de acceso por analista
- **Buscar** texto libre e inteligente (búsqueda semántica con embeddings vectoriales)
- **Analizar** jurídicamente cada tomo: diligencias, personas, fechas, lugares, alertas de inactividad MP
- **Auditar** todas las acciones del sistema por usuario y fecha

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | Vue 3.4 + Vite 5 + Vue Router 4 + Pinia |
| Backend | FastAPI 0.104.1 + Uvicorn |
| Base de datos | PostgreSQL 15+ con extensión `pg_trgm` y `pgvector` |
| Cola de tareas | Celery + Redis |
| OCR | Tesseract (base) · EasyOCR · PaddleOCR (opcional) |
| Auth | JWT — python-jose + passlib/bcrypt |

---

## Estructura del Proyecto

```
sistemaocr/
├── backend/             # API FastAPI (Python)
│   ├── app/             # Código principal
│   │   ├── controllers/ # Lógica de negocio
│   │   ├── models/      # Modelos SQLAlchemy
│   │   ├── routes/      # Endpoints REST
│   │   ├── services/    # Servicios (OCR, embeddings, etc.)
│   │   └── tasks/       # Tareas Celery (procesamiento async)
│   ├── scripts/         # Scripts SQL y migraciones
│   ├── uploads/         # Archivos subidos (PDFs)
│   ├── main.py          # Punto de entrada FastAPI
│   └── .env             # Variables de entorno (NO subir a git)
├── frontend-vue/        # SPA Vue 3
│   ├── src/
│   │   ├── views/       # Vistas (22 pantallas)
│   │   ├── stores/      # Estado global Pinia
│   │   ├── router/      # Vue Router con guards de rol
│   │   └── composables/ # useApi, useToast
│   └── vite.config.js   # Proxy /api → localhost:8000 (dev)
├── backups/             # Respaldos de base de datos
├── logs/                # Logs del sistema (ver logs/README.md)
├── mock-api.js          # API mock Node.js para desarrollo sin backend
└── render.yaml          # Configuracion despliegue Render.com
```

---

## Roles de Usuario

| Rol | Acceso |
|-----|--------|
| `admin` | Dashboard completo, gestión de carpetas/tomos/usuarios, análisis IA, auditoría, configuración |
| `usuario` | Dashboard analista, tomos asignados (ver/buscar/exportar según permisos), análisis jurídico avanzado |

---

## Documentación disponible

| Archivo | Contenido |
|---------|-----------|
| [INSTALACION.md](./INSTALACION.md) | Requisitos e instalación paso a paso |
| [ARQUITECTURA.md](./ARQUITECTURA.md) | Arquitectura técnica, endpoints, modelos de datos |
| [GUIA_USO.md](./GUIA_USO.md) | Guía de uso por rol: admin y analista |
| [../logs/README.md](../logs/README.md) | Estructura y uso de los logs |

---

## Inicio Rápido (Desarrollo)

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# 2. Frontend
cd frontend-vue
npm install
npm run dev          # http://localhost:5173

# 3. Mock API (sin backend real)
node mock-api.js     # http://localhost:8000
```

---

*Desarrollado por Eduardo Lozada Quiroz, ISC — UAyC · FGJ CDMX · 2025*
