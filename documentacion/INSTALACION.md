# Instalación — Sistema OCR RIDAC

## Requisitos Previos

| Componente | Versión mínima |
|-----------|----------------|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 15+ |
| Redis | 7+ |
| Tesseract OCR | 5.x |
| Poppler (pdf2image) | Cualquier versión reciente |

---

## 1. Base de Datos PostgreSQL

```sql
-- Crear base de datos y extensiones
CREATE DATABASE sistema_ocr;
\c sistema_ocr
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector para búsqueda semántica
```

---

## 2. Backend (FastAPI)

```bash
cd backend

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/Mac
```

Editar `backend/.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=sistema_ocr
DB_USER=postgres
DB_PASSWORD=TU_PASSWORD

JWT_SECRET_KEY=clave_secreta_larga_y_aleatoria_minimo_32_chars
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

UPLOAD_PATH=C:/FGJCDMX/documentos
EXPORT_PATH=C:/FGJCDMX/exportaciones
LOG_PATH=./logs

OCR_ENABLE_TESSERACT=true
OCR_ENABLE_EASYOCR=false
OCR_ENABLE_PADDLEOCR=false
SERVER_PORT=8001
```

Crear carpetas requeridas:

```bash
mkdir C:\FGJCDMX\documentos
mkdir C:\FGJCDMX\exportaciones
mkdir C:\FGJCDMX\exportaciones\temp
```

Ejecutar migraciones / scripts iniciales:

```bash
# Habilitar pg_trgm (ejecutar una sola vez)
python habilitar_pg_trgm.py

# Scripts de inicialización (roles, admin por defecto, etc.)
# Ubicados en backend/scripts/ — ejecutar según lo indique cada uno
```

Iniciar el servidor:

```bash
# Desarrollo
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# Producción
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

La API queda disponible en: `http://localhost:8001`  
Documentación Swagger: `http://localhost:8001/docs`

---

## 3. Frontend Vue 3

```bash
cd frontend-vue

# Instalar dependencias
npm install

# Desarrollo (con proxy /api → localhost:8000 o 8001)
npm run dev
# Acceder en http://localhost:5173

# Build para producción
npm run build
# Output en frontend-vue/dist/
```

> El archivo `vite.config.js` tiene configurado el proxy `/api` apuntando a `http://localhost:8000`.
> Cambiar el `target` si el backend corre en otro puerto (`8001`).

---

## 4. Mock API (Desarrollo sin Backend)

Para desarrollar el frontend sin necesidad de correr el backend completo:

```bash
node mock-api.js
# Corre en http://localhost:8000
```

Credenciales de prueba del mock:

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin` | cualquiera | Administrador |
| `juan` | cualquiera | Analista (tomos 1, 2, 4) |
| `maria` | cualquiera | Analista (tomos 1, 4, 5) |

---

## 5. Cola de Tareas Celery (Opcional para OCR async)

Requiere Redis corriendo:

```bash
# En otra terminal desde backend/
celery -A app.tasks worker --loglevel=info

# Beat (tareas programadas)
celery -A app.tasks beat --loglevel=info
```

---

## Verificación de Instalación

```bash
# Verificar conexiones y dependencias
cd backend
python verificar_instalacion.py

# Verificar integración entre servicios
python verificar_integracion.py
```

---

## Despliegue en Render.com

El proyecto incluye `render.yaml` con la configuración para despliegue directo en Render.
Conectar el repositorio Git en el panel de Render y configurar las variables de entorno.
