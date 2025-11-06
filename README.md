# 🏛️ Sistema OCR - Fiscalía General de Justicia CDMX

Sistema de Procesamiento OCR y Análisis Jurídico para la Fiscalía General de Justicia de la Ciudad de México

---

## 🚀 Inicio Rápido con Docker (RECOMENDADO)

### Instalación en 3 pasos:

#### 1️⃣ Instalar Docker Desktop
```powershell
# Descarga e instala Docker Desktop para Windows
# https://www.docker.com/products/docker-desktop
```
📖 **Guía detallada**: Ver `INSTALACION_DOCKER.md`

#### 2️⃣ Iniciar el Sistema
```powershell
# Simplemente ejecuta:
start-docker.bat
```

#### 3️⃣ Acceder al Sistema
- **Frontend**: http://localhost
- **API Docs**: http://localhost/api/docs
- **PgAdmin**: http://localhost:5050

**¡Listo!** PostgreSQL, Backend y Frontend corriendo automáticamente.

---

## 📚 Documentación Completa

| Documento | Descripción |
|-----------|-------------|
| 📘 **INSTALACION_DOCKER.md** | Guía paso a paso para instalar Docker Desktop |
| 🐳 **README_DOCKER.md** | Uso del sistema con Docker (inicio rápido) |
| 📖 **DOCKER_GUIA_INSTALACION.md** | Guía completa de Docker (comandos, troubleshooting) |
| 📋 **LEEME_PRIMERO.md** | Resumen de funcionalidades implementadas |
| ⚖️ **GUIA_USO_ANALISIS_JURIDICO.md** | Sistema de análisis jurídico con NLP |

---

## 🎯 ¿Qué incluye este sistema?

### ✨ Características Principales

✅ **OCR Multi-Motor**
- Tesseract (español e inglés)
- EasyOCR (opcional)
- PaddleOCR (opcional)
- Preprocesamiento automático de imágenes

✅ **Análisis Jurídico Automatizado**
- Extracción de diligencias judiciales
- Identificación de personas mencionadas
- Detección de lugares y direcciones
- Alertas de inactividad MP
- Timeline de eventos

✅ **Búsqueda Avanzada**
- Búsqueda semántica con IA
- Búsqueda por palabras clave
- Filtros avanzados
- Autocorrector legal mexicano

✅ **Gestión de Carpetas y Tomos**
- Organización por carpetas de investigación
- Tomos con 800-900 páginas
- Permisos granulares por usuario
- Historial de cambios

✅ **Seguridad**
- Autenticación JWT
- Roles y permisos
- Auditoría completa
- Aislamiento de datos por usuario

---

## 🛠️ Stack Tecnológico

### Backend
- **FastAPI** - Framework web moderno
- **PostgreSQL 15** - Base de datos
- **SQLAlchemy** - ORM
- **Tesseract** - OCR principal
- **Sentence Transformers** - Búsqueda semántica
- **spaCy** - NLP para análisis jurídico

### Frontend
- **HTML5 + CSS3 + JavaScript**
- **Bootstrap 5** - UI Framework
- **Chart.js** - Gráficos
- **DataTables** - Tablas interactivas

### Infraestructura
- **Docker** - Contenedores
- **Docker Compose** - Orquestación
- **Nginx** - Servidor web y proxy
- **PgAdmin** - Administración BD

---

## 📦 Scripts Útiles

Todos los scripts están en la raíz del proyecto:

| Script | Descripción |
|--------|-------------|
| `start-docker.bat` | ⭐ Iniciar todo el sistema |
| `stop-docker.bat` | Detener el sistema |
| `ver-estado.bat` | Ver estado de contenedores y recursos |
| `ver-logs.bat` | Ver logs en tiempo real |
| `backup-database.bat` | Crear backup de PostgreSQL |
| `restaurar-backup.bat` | Restaurar backup |
| `consola-postgres.bat` | Abrir consola SQL interactiva |

---

## 👥 Usuarios por Defecto

### Administrador
- **Usuario**: `admin`
- **Contraseña**: `admin123`
- **Rol**: Administrador (acceso completo)

### Usuario de Prueba
- **Usuario**: `eduardo`
- **Contraseña**: `eduardo123`
- **Rol**: Usuario (permisos limitados)

**⚠️ Importante**: Cambia estas contraseñas en producción.

---

## 🗂️ Estructura del Proyecto

```
FJ1/
├── backend/                    # Backend FastAPI
│   ├── app/
│   │   ├── models/            # Modelos de datos
│   │   ├── routes/            # Endpoints API
│   │   ├── controllers/       # Lógica de negocio
│   │   ├── services/          # Servicios (OCR, NLP, etc)
│   │   └── utils/             # Utilidades
│   ├── scripts/               # Scripts SQL
│   ├── Dockerfile             # Imagen Docker backend
│   └── requirements.txt       # Dependencias Python
│
├── frontend/                  # Frontend HTML/JS
│   ├── js/                    # JavaScript modules
│   ├── css/                   # Estilos
│   └── *.html                # Páginas
│
├── docs/                      # Documentación
├── docker-compose.yml         # 🐳 Desarrollo
├── docker-compose.prod.yml    # 🐳 Producción
├── nginx.conf                 # Configuración Nginx
└── *.bat                      # Scripts Windows
```

---

## ✅ Checklist de Despliegue en Fiscalía

- [ ] Docker Desktop instalado y corriendo
- [ ] Proyecto copiado en servidor
- [ ] Archivo `.env` configurado
- [ ] Contraseñas cambiadas
- [ ] Firewall configurado (puertos 80, 443)
- [ ] Sistema iniciado: `start-docker.bat`
- [ ] Verificar estado: `ver-estado.bat`
- [ ] Crear usuario admin con contraseña segura
- [ ] Configurar backups automáticos
- [ ] Probar acceso desde red local
- [ ] Capacitar usuarios finales

---

**¡Sistema listo para usar!** 🎉

Para más información, consulta la documentación en la carpeta `docs/`.  
✓ Gestión de carpetas y tomos  
✓ Auditoría completa  

## Base de datos: sistema_ocr
## Password PostgreSQL: 1234

