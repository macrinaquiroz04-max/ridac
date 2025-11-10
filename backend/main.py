# backend/main.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Organización: Unidad de Análisis y Contexto (UAyC)
# Año: 2025 - Propiedad Intelectual Registrada
# Firma Digital: ELQ-ISC-UAYC-27102025

import warnings
import os

# === CONFIGURACIÓN GLOBAL DE ADVERTENCIAS ===
warnings.filterwarnings("ignore", category=DeprecationWarning, module="cryptography")
warnings.filterwarnings("ignore", message="ARC4 has been moved to cryptography.hazmat.decrepit")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="Neither CUDA nor MPS are available")
warnings.filterwarnings("ignore", message="Some weights of VisionEncoderDecoderModel were not initialized")
warnings.filterwarnings("ignore", message="resume_download.*deprecated")

# 🔇 WARNINGS ESPECÍFICOS DE CCACHE Y PADDLEX
warnings.filterwarnings("ignore", category=UserWarning, message=".*ccache.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*No ccache found.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*recompiling.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*source files may be required.*")

# Configurar variables de entorno para suprimir logs
os.environ['FLAGS_logging_level'] = '3'  # PaddleOCR
os.environ['FLAGS_call_stack_level'] = '3'  # PaddleOCR stack traces
os.environ['GLOG_minloglevel'] = '3'  # Google logging (PaddleOCR)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'  # Transformers
# Metadata autor: E.Lozada.Q (ISC)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Agregar el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))

# Importar modelos en el orden correcto para evitar dependencias circulares
from app.models.usuario import Usuario, Rol
from app.models.tomo import Tomo, ContenidoOCR
from app.models.extraccion import ExtraccionTomo, DiligenciaTomo, PersonaMencionada, Declaracion, AlertaInactividad
from app.models.permiso_tomo import PermisoTomo

from app.routes import auth, admin, carpetas, tomos, busqueda, test, permisos, busqueda_tomos, notificaciones, usuarios, desarrollo, ocr_quality, analisis_admin, analisis_usuario, auditoria, ocr_area, system_health
from app.controllers import ocr_controller, correccion_controller
# 🚀 CONTROLADORES AVANZADOS
try:
    from app.controllers import table_analysis_controller
    TABLE_ANALYSIS_AVAILABLE = True
except ImportError:
    TABLE_ANALYSIS_AVAILABLE = False
from app.utils.logger import logger
from app.utils.error_logger import ErrorLogger, cleanup_old_logs
from app.database import test_connection
from app.config import settings
from app.middlewares.error_handler_middleware import ErrorHandlerMiddleware, RequestLoggingMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Startup: Iniciar servicios
    logger.info("="*60)
    logger.info("INICIANDO SISTEMA OCR - FGJCDMX")
    logger.info("="*60)

    # Verificar conexión a base de datos
    logger.info("Verificando conexion a base de datos...")
    if test_connection():
        logger.info("Base de datos conectada")
    else:
        logger.error("Error conectando a base de datos")
        logger.warning("El sistema continuara pero puede haber problemas")

    # Iniciar worker OCR
    # logger.info("Iniciando worker de procesamiento OCR...")
    # background_service.start()

    logger.info("="*60)
    logger.info("🏛️  SISTEMA OCR FGJCDMX INICIADO CORRECTAMENTE")
    logger.info("="*60)
    logger.info("")
    logger.info("🌐 Endpoints disponibles:")
    logger.info(f"   - Frontend:        http://sistema-ocr.local/")
    logger.info(f"   - API Docs:        http://sistema-ocr.local/docs")
    logger.info(f"   - API Redoc:       http://sistema-ocr.local/redoc")
    logger.info(f"   - Health Check:    http://sistema-ocr.local/health")
    logger.info(f"   - System Errors:   http://sistema-ocr.local/api/system/errors/stats")
    logger.info("")
    logger.info("🔗 Acceso alternativo por IP:")
    logger.info(f"   - Frontend IP:     http://172.22.134.61/")
    logger.info(f"   - API Docs IP:     http://172.22.134.61/docs")
    logger.info("")
    logger.info("🔗 Acceso legacy:")
    logger.info(f"   - Frontend:        http://fgj-ocr.local/")
    logger.info("")
    logger.info("👤 Usuario administrador:")
    logger.info("   - Username: eduardo")
    logger.info("   - Password: lalo1998c33")
    logger.info("")
    logger.info("🛡️  Sistema de logging de errores activado")
    logger.info("   - Solo guarda errores y warnings REALES")
    logger.info("   - Límite por archivo: 50 MB con rotación automática")
    logger.info("   - Retención: 7 días (auto-limpieza)")
    logger.info("   - Logs en: /app/logs/")
    logger.info("")
    logger.info("="*60)
    
    # Limpiar logs antiguos al iniciar (más de 7 días)
    try:
        cleanup_old_logs(days=7)
        logger.info("✅ Limpieza de logs antiguos completada")
    except Exception as e:
        logger.warning(f"No se pudieron limpiar logs antiguos: {e}")

    yield

    # Shutdown: Detener servicios
    logger.info("Deteniendo servicios...")
    # background_service.stop()
    logger.info("Sistema detenido correctamente")

# Crear aplicación FastAPI
app = FastAPI(
    title="Sistema OCR - FGJCDMX",
    description="Sistema de Procesamiento OCR para la Fiscalía General de Justicia de la Ciudad de México",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar límites para archivos grandes
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Limite de 500MB para archivos PDF grandes
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB en bytes

# Configurar CORS - Priorizar sistema-ocr.local como dominio principal
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://sistema-ocr.local",
        "https://sistema-ocr.local",
        "http://fgj-ocr.local",
        "https://fgj-ocr.local",
        "http://172.22.134.61",
        "https://172.22.134.61",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost",
        "http://127.0.0.1",
        "*"  # Permite cualquier origen (solo para desarrollo)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 🛡️ Middleware de manejo de errores - NUNCA detiene el sistema
# Solo registra errores REALES, no peticiones normales
app.add_middleware(ErrorHandlerMiddleware)

# 📝 Middleware de logging de peticiones DESACTIVADO para no llenar logs
# Solo se activa para debugging temporal
# app.add_middleware(RequestLoggingMiddleware)

# Incluir rutas de la API
app.include_router(system_health.router)  # Sistema de monitoreo de errores
app.include_router(test.router, prefix="/api/test", tags=["Pruebas del Sistema"])
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticacion"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administracion"])
app.include_router(usuarios.router, prefix="/api/usuarios", tags=["👤 Usuarios"])
app.include_router(carpetas.router, prefix="/api/carpetas", tags=["Carpetas"])
app.include_router(tomos.router, prefix="/api/tomos", tags=["Tomos"])
app.include_router(permisos.router, prefix="/api/permisos", tags=["Permisos"])
app.include_router(auditoria.router, prefix="/api", tags=["📋 Auditoría"])
app.include_router(busqueda_tomos.router, prefix="/api/busqueda-tomos", tags=["🔍 Búsqueda en Tomos"])
app.include_router(ocr_quality.router, tags=["🔍 Calidad OCR"])
app.include_router(ocr_area.router, tags=["🔍 OCR Área Seleccionada"])
app.include_router(busqueda.router, prefix="/api/busqueda", tags=["🔎 Búsqueda"])
app.include_router(ocr_controller.router, prefix="/api", tags=["📄 OCR"])
app.include_router(desarrollo.router, prefix="/api", tags=["🔧 Desarrollo"])

# Análisis Jurídico (OCR + NLP para documentos legales mexicanos)
app.include_router(analisis_admin.router, prefix="/api", tags=["⚖️ Análisis Jurídico - Admin"])
app.include_router(analisis_usuario.router, prefix="/api", tags=["📊 Análisis Jurídico - Usuario"])
app.include_router(correccion_controller.router, prefix="/api", tags=["✏️ Corrección de Diligencias"])

# Corrección de personas
from app.controllers import correccion_personas_controller
app.include_router(correccion_personas_controller.router, prefix="/api", tags=["👥 Corrección de Personas"])

# Progreso en tiempo real
from app.controllers import progress_controller
app.include_router(progress_controller.router, prefix="", tags=["📊 Progreso en Tiempo Real"])

# Incluir el nuevo controlador de análisis IA
from app.controllers.analisis_controller import router as analisis_router
app.include_router(analisis_router, prefix="", tags=["🧠 Análisis IA"])

# 📊 ANÁLISIS AVANZADO DE TABLAS
if TABLE_ANALYSIS_AVAILABLE:
    app.include_router(table_analysis_controller.router, prefix="", tags=["📊 Análisis de Tablas"])
    logger.info("✅ Endpoint de análisis de tablas habilitado")

# 🚀 OCR PROFESIONAL ESTILO PDF24
try:
    from app.controllers.pdf24_controller import router as pdf24_router
    app.include_router(pdf24_router, prefix="", tags=["🚀 OCR PDF24"])
    logger.info("✅ OCR Profesional PDF24 habilitado")
except ImportError:
    logger.warning("⚠️ OCR PDF24 no disponible")

# ✍️ AUTOCORRECTOR LEGAL
try:
    from app.controllers.autocorrector_controller import router as autocorrector_router
    app.include_router(autocorrector_router, prefix="/api", tags=["✍️ Autocorrector Legal"])
    logger.info("✅ Autocorrector Legal habilitado")
except ImportError:
    logger.warning("⚠️ OCR PDF24 no disponible - faltan dependencias")

# 🎯 MIDDLEWARE PARA URLs LIMPIAS (sin .html)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import FileResponse, RedirectResponse

class CleanURLMiddleware(BaseHTTPMiddleware):
    """Middleware para URLs limpias sin .html - Solo afecta páginas HTML"""
    
    # Extensiones de archivos estáticos que NO deben procesarse
    STATIC_EXTENSIONS = {
        '.css', '.js', '.json', '.jpg', '.jpeg', '.png', '.gif', '.svg', 
        '.ico', '.woff', '.woff2', '.ttf', '.eot', '.mp4', '.webm', 
        '.pdf', '.zip', '.txt', '.xml'
    }
    
    async def dispatch(self, request, call_next):
        path = request.url.path
        
        # Ignorar rutas API
        if path.startswith("/api"):
            return await call_next(request)
        
        # Ignorar archivos estáticos (CSS, JS, imágenes, etc.)
        file_extension = Path(path).suffix.lower()
        if file_extension in self.STATIC_EXTENSIONS:
            return await call_next(request)
        
        # Si es la raíz, servir index.html
        if path == "/":
            frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
            if frontend_path.exists():
                return FileResponse(frontend_path)
        
        # Si la URL no tiene extensión, intentar agregar .html
        if not file_extension and path != "/":
            frontend_path = Path(__file__).parent.parent / "frontend"
            html_file = frontend_path / f"{path.strip('/')}.html"
            
            if html_file.exists():
                return FileResponse(html_file)
        
        # Si accede con .html, redirigir a URL limpia
        if path.endswith(".html"):
            clean_path = path[:-5]  # Quitar .html
            return RedirectResponse(url=clean_path, status_code=301)
        
        response = await call_next(request)
        return response

# Agregar middleware de URLs limpias
app.add_middleware(CleanURLMiddleware)

# Servir archivos estáticos del frontend
try:
    frontend_path = Path(__file__).parent.parent / "frontend"
    if frontend_path.exists():
        app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
        logger.info(f"✓ Frontend montado desde: {frontend_path}")
    else:
        logger.warning(f"⚠ Directorio frontend no encontrado: {frontend_path}")
except Exception as e:
    logger.error(f"✗ Error montando frontend: {e}")

# Endpoint raíz de la API
@app.get("/api")
async def root():
    """Información de la API"""
    return {
        "nombre": "Sistema OCR - FGJCDMX",
        "version": "1.0.0",
        "descripcion": "Sistema de Procesamiento OCR para la Fiscalía General de Justicia de la Ciudad de México",
        "documentacion": "/docs",
        "frontend": "/",
        "pruebas": "/test.html"
    }

# Endpoint de salud para Docker
@app.get("/health")
async def health_check():
    """
    Verificar salud del servicio
    Health check inteligente que considera procesamiento OCR activo
    """
    try:
        from datetime import datetime, timedelta
        
        # Verificar conexión a base de datos
        db_status = test_connection()
        
        # Importar estado de procesamiento
        try:
            from app.controllers.analisis_admin_controller import procesamiento_estado, ultimo_heartbeat
            
            # Verificar si hay procesamiento activo
            procesos_activos = sum(
                1 for estado in procesamiento_estado.values() 
                if estado.get("estado") == "procesando"
            )
            
            # Verificar último heartbeat (si hay actividad reciente, está vivo)
            tiempo_desde_heartbeat = (datetime.now() - ultimo_heartbeat["timestamp"]).total_seconds()
            
            response = {
                "status": "healthy" if db_status else "degraded",
                "service": "Sistema OCR - FGJCDMX",
                "version": "2.1.0",
                "database": "connected" if db_status else "disconnected",
                "procesos_activos": procesos_activos,
                "ultimo_heartbeat_segundos": int(tiempo_desde_heartbeat)
            }
            
            # Si hay procesos activos y heartbeat reciente, definitivamente está vivo
            if procesos_activos > 0 and tiempo_desde_heartbeat < 120:
                response["note"] = "Procesamiento OCR activo - sistema operativo"
            
            return response
            
        except Exception:
            # Si falla la importación, usar health check básico
            return {
                "status": "healthy" if db_status else "degraded",
                "service": "Sistema OCR - FGJCDMX",
                "version": "2.1.0",
                "database": "connected" if db_status else "disconnected"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn

    # Configuración del servidor
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=False,  # Desactivado para evitar problemas de carga
        log_level="info",
        access_log=True,
        timeout_keep_alive=300,  # 5 minutos para uploads grandes
        timeout_graceful_shutdown=60  # 1 minuto para shutdown graceful
    )
