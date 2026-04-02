# backend/app/routes/test.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db, test_connection
from app.config import settings
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Test"]
)


@router.get("/health", response_model=Dict[str, Any])
async def test_health():
    """
    GET /test/health
    Verifica el estado general del servicio.
    Health check inteligente que considera procesamiento OCR activo.
    """
    from datetime import datetime, timedelta
    
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
        
        status_info = {
            "success": True,
            "status": "healthy",
            "service": "Sistema OCR RIDAC",
            "version": "2.1.0",
            "environment": "development",
            "procesos_activos": procesos_activos,
            "ultimo_heartbeat_segundos": int(tiempo_desde_heartbeat)
        }
        
        # Si hay procesos activos y heartbeat reciente, definitivamente está vivo
        if procesos_activos > 0 and tiempo_desde_heartbeat < 120:
            status_info["note"] = "Procesamiento OCR activo - sistema operativo"
        
        return status_info
        
    except Exception as e:
        # Si falla la importación, usar health check básico
        return {
            "success": True,
            "status": "healthy",
            "service": "Sistema OCR RIDAC",
            "version": "2.1.0",
            "environment": "development"
        }


@router.get("/database", response_model=Dict[str, Any])
async def test_database(db: Session = Depends(get_db)):
    """
    GET /test/database
    Verifica la conexión a la base de datos.
    """
    try:
        # Realizar consulta de prueba
        from sqlalchemy import text
        result = db.execute(text("SELECT 1 as test"))
        row = result.fetchone()

        # Prueba UTF-8
        utf_test = db.execute(text("SELECT 'Ñoño áéíóú' as utf_test"))
        utf_row = utf_test.fetchone()

        # Verificar encoding
        encoding = db.execute(text("SHOW client_encoding"))
        enc_row = encoding.fetchone()

        return {
            "success": True,
            "status": "connected",
            "database": settings.DB_NAME,
            "host": settings.DB_HOST,
            "encoding": enc_row[0] if enc_row else "unknown",
            "utf8_test": utf_row[0] if utf_row else "failed",
            "test_query": "passed"
        }

    except Exception as e:
        logger.error(f"Error en test de base de datos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error conectando a base de datos: {str(e)}"
        )


@router.get("/filesystem", response_model=Dict[str, Any])
async def test_filesystem():
    """
    GET /test/filesystem
    Verifica el acceso al sistema de archivos.
    """
    paths_to_check = {
        "upload_path": settings.UPLOAD_PATH,
        "export_path": settings.EXPORT_PATH,
        "temp_path": settings.TEMP_PATH,
        "log_path": settings.LOG_PATH
    }

    results = {}

    for name, path in paths_to_check.items():
        try:
            # Verificar si existe
            exists = os.path.exists(path)

            # Verificar permisos
            can_read = os.access(path, os.R_OK) if exists else False
            can_write = os.access(path, os.W_OK) if exists else False

            results[name] = {
                "path": path,
                "exists": exists,
                "readable": can_read,
                "writable": can_write,
                "status": "ok" if (exists and can_read and can_write) else "error"
            }

        except Exception as e:
            results[name] = {
                "path": path,
                "status": "error",
                "error": str(e)
            }

    # Determinar estado general
    all_ok = all(r.get("status") == "ok" for r in results.values())

    return {
        "success": all_ok,
        "status": "ok" if all_ok else "error",
        "paths": results
    }


@router.get("/ocr", response_model=Dict[str, Any])
async def test_ocr():
    """
    GET /test/ocr
    Verifica la disponibilidad de motores OCR.
    """
    ocr_engines = {}

    # Tesseract
    if settings.OCR_ENABLE_TESSERACT:
        try:
            import pytesseract
            version = pytesseract.get_tesseract_version()
            ocr_engines["tesseract"] = {
                "enabled": True,
                "available": True,
                "version": str(version)
            }
        except Exception as e:
            ocr_engines["tesseract"] = {
                "enabled": True,
                "available": False,
                "error": str(e)
            }
    else:
        ocr_engines["tesseract"] = {
            "enabled": False,
            "available": False
        }

    # EasyOCR
    if settings.OCR_ENABLE_EASYOCR:
        try:
            import easyocr
            ocr_engines["easyocr"] = {
                "enabled": True,
                "available": True,
                "version": easyocr.__version__ if hasattr(easyocr, '__version__') else "unknown"
            }
        except Exception as e:
            ocr_engines["easyocr"] = {
                "enabled": True,
                "available": False,
                "error": str(e)
            }
    else:
        ocr_engines["easyocr"] = {
            "enabled": False,
            "available": False
        }

    # PaddleOCR
    if settings.OCR_ENABLE_PADDLEOCR:
        try:
            from paddleocr import PaddleOCR
            ocr_engines["paddleocr"] = {
                "enabled": True,
                "available": True
            }
        except Exception as e:
            ocr_engines["paddleocr"] = {
                "enabled": True,
                "available": False,
                "error": str(e)
            }
    else:
        ocr_engines["paddleocr"] = {
            "enabled": False,
            "available": False
        }

    # TrOCR
    if settings.OCR_ENABLE_TROCR:
        try:
            from transformers import TrOCRProcessor
            ocr_engines["trocr"] = {
                "enabled": True,
                "available": True
            }
        except Exception as e:
            ocr_engines["trocr"] = {
                "enabled": True,
                "available": False,
                "error": str(e)
            }
    else:
        ocr_engines["trocr"] = {
            "enabled": False,
            "available": False
        }

    # Determinar si hay al menos un motor disponible
    any_available = any(
        engine.get("available", False)
        for engine in ocr_engines.values()
    )

    return {
        "success": any_available,
        "status": "ok" if any_available else "error",
        "message": "Al menos un motor OCR disponible" if any_available else "Ningún motor OCR disponible",
        "engines": ocr_engines,
        "max_workers": settings.OCR_MAX_WORKERS
    }


@router.get("/auth", response_model=Dict[str, Any])
async def test_auth(db: Session = Depends(get_db)):
    """
    GET /test/auth
    Verifica el sistema de autenticación.
    """
    try:
        # Verificar que el usuario admin existe
        from app.models.usuario import Usuario
        admin_user = db.query(Usuario).filter(Usuario.username == "admin").first()
        
        if not admin_user:
            return {
                "success": False,
                "status": "error",
                "message": "Usuario admin no existe",
                "details": "El usuario administrador no fue creado en la base de datos"
            }
        
        # Verificar que la contraseña es correcta
        from app.utils.security import verify_password
        password_ok = verify_password("admin123", admin_user.password)
        
        if not password_ok:
            return {
                "success": False,
                "status": "error", 
                "message": "Contraseña admin incorrecta",
                "details": "El hash de la contraseña no coincide con 'admin123'"
            }
        
        # Verificar que el usuario está activo
        if not admin_user.activo:
            return {
                "success": False,
                "status": "error",
                "message": "Usuario admin inactivo",
                "details": "El usuario admin existe pero está marcado como inactivo"
            }
        
        # Verificar configuración JWT
        from app.config import settings
        jwt_config = {
            "secret_key_set": bool(settings.JWT_SECRET_KEY),
            "algorithm": settings.JWT_ALGORITHM,
            "access_token_expire": settings.ACCESS_TOKEN_EXPIRE_MINUTES
        }
        
        return {
            "success": True,
            "status": "ok",
            "message": "Sistema de autenticación configurado correctamente",
            "admin_user": {
                "id": admin_user.id,
                "username": admin_user.username,
                "email": admin_user.email,
                "active": admin_user.activo,
                "role_id": admin_user.rol_id
            },
            "jwt_config": jwt_config
        }
        
    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "message": f"Error verificando autenticación: {str(e)}",
            "details": "Excepción durante la verificación del sistema de autenticación"
        }


@router.get("/complete", response_model=Dict[str, Any])
async def test_complete(db: Session = Depends(get_db)):
    """
    GET /test/complete
    Ejecuta todas las pruebas y devuelve un resumen completo.
    """
    results = {}

    # Test health
    try:
        health_result = await test_health()
        results["health"] = {"status": "passed", "data": health_result}
    except Exception as e:
        results["health"] = {"status": "failed", "error": str(e)}

    # Test database
    try:
        db_result = await test_database(db)
        results["database"] = {"status": "passed", "data": db_result}
    except Exception as e:
        results["database"] = {"status": "failed", "error": str(e)}

    # Test filesystem
    try:
        fs_result = await test_filesystem()
        results["filesystem"] = {
            "status": "passed" if fs_result["status"] == "ok" else "failed",
            "data": fs_result
        }
    except Exception as e:
        results["filesystem"] = {"status": "failed", "error": str(e)}

    # Test OCR
    try:
        ocr_result = await test_ocr()
        results["ocr"] = {
            "status": "passed" if ocr_result["status"] == "ok" else "warning",
            "data": ocr_result
        }
    except Exception as e:
        results["ocr"] = {"status": "failed", "error": str(e)}

    # Resumen general
    all_passed = all(
        r["status"] == "passed"
        for r in results.values()
        if r["status"] != "warning"
    )

    return {
        "success": all_passed,
        "status": "ok" if all_passed else "error",
        "summary": {
            "total_tests": len(results),
            "passed": sum(1 for r in results.values() if r["status"] == "passed"),
            "failed": sum(1 for r in results.values() if r["status"] == "failed"),
            "warnings": sum(1 for r in results.values() if r["status"] == "warning")
        },
        "results": results
    }
