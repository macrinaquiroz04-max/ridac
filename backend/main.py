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

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Rate Limiting para proteger contra abuso
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Agregar el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))

# Importar modelos en el orden correcto para evitar dependencias circulares
from app.models.usuario import Usuario, Rol
from app.models.tomo import Tomo, ContenidoOCR
from app.models.extraccion import ExtraccionTomo, DiligenciaTomo, PersonaMencionada, Declaracion, AlertaInactividad
from app.models.permiso_tomo import PermisoTomo

from app.routes import auth, admin, carpetas, tomos, busqueda, test, permisos, busqueda_tomos, notificaciones, usuarios, desarrollo, ocr_quality, analisis_admin, analisis_usuario, auditoria, ocr_area, system_health, tasks, stats
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
    logger.info("INICIANDO SISTEMA OCR - RIDAC")
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
    logger.info("🏛️  SISTEMA OCR RIDAC INICIADO CORRECTAMENTE")
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
    logger.info("👤 Usuario administrador: ver variable ADMIN_INITIAL_PASSWORD")
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

    # ── Detectar tomos cuyos PDFs desaparecieron (ej. reinicio de contenedor en HF Spaces) ──
    # /tmp se borra con cada reinicio. Resetear esos tomos a 'pendiente' para que el usuario
    # sepa que debe volver a subir el PDF, en vez de quedarse en estado 'procesando' o 'error'
    # con un archivo fantasma que nunca va a poder procesarse.
    try:
        from app.database import SessionLocal as _SL
        from app.models.tomo import Tomo as _Tomo
        _db = _SL()
        try:
            tomos_afectados = (
                _db.query(_Tomo)
                .filter(_Tomo.estado.in_(["procesando", "error", "completado"]))
                .all()
            )
            _resetados = 0
            for _t in tomos_afectados:
                if _t.ruta_archivo and not os.path.exists(_t.ruta_archivo):
                    _t.estado = "pendiente"
                    _resetados += 1
            if _resetados:
                _db.commit()
                logger.warning(
                    f"⚠️  {_resetados} tomo(s) reseteados a 'pendiente' porque su PDF "
                    f"no existe en disco (el contenedor se reinició y /tmp fue limpiado). "
                    f"Los usuarios deben volver a subir esos archivos."
                )
            else:
                logger.info("✅ Todos los PDFs registrados están presentes en disco")
        finally:
            _db.close()
    except Exception as _e:
        logger.warning(f"No se pudo verificar integridad de archivos PDF: {_e}")

    # A06: auditoría de dependencias (CVE check) — solo registra, no bloquea inicio
    try:
        import subprocess, json as _json
        _audit = subprocess.run(
            ["pip-audit", "--format=json", "-q", "--skip-editable"],
            capture_output=True, text=True, timeout=60
        )
        if _audit.returncode != 0 and _audit.stdout:
            try:
                _vulns = _json.loads(_audit.stdout)
                _count = sum(len(p.get("vulns", [])) for p in _vulns.get("dependencies", []))
                if _count:
                    logger.warning(f"⚠️  A06: pip-audit encontró {_count} vulnerabilidades en dependencias. "
                                   "Revisar con: pip-audit --format=columns")
                    for _pkg in _vulns.get("dependencies", []):
                        for _v in _pkg.get("vulns", []):
                            logger.warning(f"   📦 {_pkg['name']}=={_pkg.get('version','?')}: "
                                           f"{_v.get('id','?')} — {_v.get('description','')[:120]}")
            except Exception:
                pass
        else:
            logger.info("✅ A06: pip-audit — sin vulnerabilidades conocidas en dependencias")
    except FileNotFoundError:
        logger.warning("A06: pip-audit no disponible. Instálalo con: pip install pip-audit")
    except Exception as _e:
        logger.warning(f"A06: pip-audit falló: {_e}")

    yield

    # Shutdown: Detener servicios
    logger.info("Deteniendo servicios...")
    # background_service.stop()
    logger.info("Sistema detenido correctamente")

# Crear aplicación FastAPI
# A05: /docs y /redoc solo accesibles en desarrollo local (nunca en producción)
# HF Spaces inyecta SPACE_ID automáticamente — úsalo para detectar producción
_IS_PRODUCTION = bool(os.environ.get("SPACE_ID"))
app = FastAPI(
    title="Sistema OCR - RIDAC",
    description="Sistema de Procesamiento OCR para la RIDAC",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _IS_PRODUCTION else "/docs",
    redoc_url=None if _IS_PRODUCTION else "/redoc",
    openapi_url=None if _IS_PRODUCTION else "/openapi.json"
)

# 🛡️ Configurar Rate Limiting (protección para 20+ usuarios concurrentes)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configurar límites para archivos grandes
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Limite de 500MB para archivos PDF grandes
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB en bytes

# Configurar CORS — usa settings.cors_origins para soportar Cloudflare Pages + desarrollo local
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 🛡️ Middleware de manejo de errores - NUNCA detiene el sistema
# Solo registra errores REALES, no peticiones normales
app.add_middleware(ErrorHandlerMiddleware)

# Seguridad real: CORS estricto + JWT + rate limiting (sin token compartido en cliente)

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

# 🚀 Nuevas rutas - Tareas asíncronas y estadísticas
app.include_router(tasks.router, tags=["⚡ Tareas Asíncronas"])
app.include_router(stats.router, tags=["📊 Estadísticas del Sistema"])

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

# Endpoint raíz — responde 200 para health checks de HF Spaces / proxies
@app.get("/")
async def root_health():
    return {"status": "ok", "service": "RIDAC API"}

@app.get("/api")
async def root():
    """Información de la API"""
    return {
        "nombre": "Sistema OCR - RIDAC",
        "version": "1.0.0",
        "descripcion": "Sistema de Procesamiento OCR para la RIDAC - Red de Integración de Datos para Análisis y Contexto",
        "documentacion": "/docs",
        "frontend": "/",
        "pruebas": "/test.html"
    }

# Endpoint de salud para Docker
@app.api_route("/health", methods=["GET", "HEAD"])
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
                "service": "Sistema OCR - RIDAC",
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
                "service": "Sistema OCR - RIDAC",
                "version": "2.1.0",
                "database": "connected" if db_status else "disconnected"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/metrics")
async def metrics():
    """Endpoint de métricas para Prometheus"""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from starlette.responses import Response
        
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Error generando métricas: {e}")
        return {"error": str(e)}

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
