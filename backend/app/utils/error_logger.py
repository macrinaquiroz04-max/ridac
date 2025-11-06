# backend/app/utils/error_logger.py

import logging
import traceback
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from functools import wraps
import sys
import os

# Crear directorio de logs si no existe
LOG_DIR = Path("/app/logs")
LOG_DIR.mkdir(exist_ok=True)

# Configuración de límites
MAX_LOG_SIZE_MB = 50  # Tamaño máximo por archivo de log (50 MB)
MAX_LOG_AGE_DAYS = 7  # Mantener logs solo 7 días
MAX_ERRORS_PER_FILE = 1000  # Máximo de errores por archivo antes de rotar

# Configurar logger principal
error_logger = logging.getLogger("sistema_ocr_errors")
error_logger.setLevel(logging.ERROR)

# Handler para archivo de errores críticos con rotación
from logging.handlers import RotatingFileHandler

# Archivo de errores con rotación automática (max 50MB, 3 backups)
error_file_handler = RotatingFileHandler(
    LOG_DIR / "errors.log",
    maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
    backupCount=3,
    encoding='utf-8'
)
error_file_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
error_file_handler.setFormatter(error_formatter)
error_logger.addHandler(error_file_handler)


class ErrorLogger:
    """Clase para registrar errores sin detener el sistema"""
    
    @staticmethod
    def log_error(
        error: Exception,
        context: str = "Unknown",
        user_id: Optional[int] = None,
        request_data: Optional[Dict[str, Any]] = None,
        severity: str = "ERROR"
    ):
        """
        Registra un error con contexto completo
        Solo guarda información esencial para no llenar el disco
        
        Args:
            error: La excepción capturada
            context: Contexto donde ocurrió el error
            user_id: ID del usuario afectado
            request_data: Datos de la petición (limitados)
            severity: Nivel de severidad (ERROR, CRITICAL, WARNING)
        """
        # Limpiar datos de request para no guardar información sensible ni demasiado grande
        safe_request_data = {}
        if request_data:
            safe_request_data = {
                "method": request_data.get("method"),
                "url": request_data.get("url"),
                "client": request_data.get("client")
                # NO guardar headers completos ni body para ahorrar espacio
            }
        
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],  # Limitar mensaje a 500 caracteres
            "user_id": user_id,
            "request": safe_request_data,
        }
        
        # Solo agregar traceback para errores CRITICAL (ahorra mucho espacio)
        if severity == "CRITICAL":
            error_data["traceback"] = traceback.format_exc()[:2000]  # Limitar traceback
        
        # Log en formato texto (rotativo)
        error_logger.error(
            f"[{severity}] {context} - {type(error).__name__}: {str(error)[:200]}"
        )
        
        # Log en formato JSON (con rotación manual)
        try:
            json_file = LOG_DIR / "errors.json"
            
            # Si el archivo es muy grande (>50MB), rotarlo
            if json_file.exists() and json_file.stat().st_size > MAX_LOG_SIZE_MB * 1024 * 1024:
                # Renombrar archivo viejo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_file.rename(LOG_DIR / f"errors_{timestamp}.json")
                
            # Escribir nuevo error
            with open(json_file, "a") as f:
                f.write(json.dumps(error_data, ensure_ascii=False) + "\n")
                
        except Exception as json_error:
            error_logger.error(f"No se pudo escribir error en JSON: {json_error}")
        
        # Si es crítico, escribir en archivo separado (compacto)
        if severity == "CRITICAL":
            try:
                critical_file = LOG_DIR / "critical_errors.log"
                
                # Rotar si es muy grande
                if critical_file.exists() and critical_file.stat().st_size > 10 * 1024 * 1024:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    critical_file.rename(LOG_DIR / f"critical_{timestamp}.log")
                
                with open(critical_file, "a") as f:
                    f.write(f"{datetime.now()} | {context} | {type(error).__name__}: {str(error)[:300]}\n")
                    
            except Exception:
                pass  # Si falla, no importa
        
        # Auto-limpieza: cada 100 errores, limpiar logs antiguos
        if hasattr(ErrorLogger, '_error_count'):
            ErrorLogger._error_count += 1
            if ErrorLogger._error_count >= 100:
                ErrorLogger._error_count = 0
                cleanup_old_logs(days=MAX_LOG_AGE_DAYS)
        else:
            ErrorLogger._error_count = 0
    
    @staticmethod
    def log_warning(message: str, context: str = "Unknown", extra_data: Optional[Dict] = None):
        """Registra una advertencia que no es crítica (compacto)"""
        warning_data = {
            "timestamp": datetime.now().isoformat(),
            "severity": "WARNING",
            "context": context,
            "message": message[:300],  # Limitar tamaño
        }
        
        # Solo log en archivo si es importante
        if extra_data and extra_data.get("important"):
            warning_data["extra"] = str(extra_data)[:200]
        
        error_logger.warning(f"[WARNING] {context} - {message[:200]}")
        
        # No guardar warnings en archivo JSON para ahorrar espacio
        # Solo los críticos van a disco
    
    @staticmethod
    def safe_execute(func):
        """
        Decorador para ejecutar funciones de forma segura
        Si falla, registra el error pero no detiene el sistema
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ErrorLogger.log_error(
                    error=e,
                    context=f"Function: {func.__name__}",
                    severity="ERROR"
                )
                # Retornar None o valor por defecto en lugar de fallar
                return None
        return wrapper
    
    @staticmethod
    async def async_safe_execute(func):
        """Versión async del decorador safe_execute"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                ErrorLogger.log_error(
                    error=e,
                    context=f"Async Function: {func.__name__}",
                    severity="ERROR"
                )
                return None
        return wrapper


def get_error_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de errores desde los logs"""
    stats = {
        "total_errors": 0,
        "critical_errors": 0,
        "warnings": 0,
        "errors_by_type": {},
        "errors_by_context": {},
        "last_24h_errors": 0
    }
    
    try:
        errors_file = LOG_DIR / "errors.json"
        if errors_file.exists():
            with open(errors_file, "r") as f:
                for line in f:
                    try:
                        error_data = json.loads(line)
                        stats["total_errors"] += 1
                        
                        if error_data.get("severity") == "CRITICAL":
                            stats["critical_errors"] += 1
                        
                        error_type = error_data.get("error_type", "Unknown")
                        stats["errors_by_type"][error_type] = stats["errors_by_type"].get(error_type, 0) + 1
                        
                        context = error_data.get("context", "Unknown")
                        stats["errors_by_context"][context] = stats["errors_by_context"].get(context, 0) + 1
                        
                        # Contar errores de últimas 24 horas
                        error_time = datetime.fromisoformat(error_data.get("timestamp", ""))
                        if (datetime.now() - error_time).total_seconds() < 86400:
                            stats["last_24h_errors"] += 1
                    except Exception:
                        continue
        
        # Contar warnings
        warnings_file = LOG_DIR / "warnings.json"
        if warnings_file.exists():
            with open(warnings_file, "r") as f:
                stats["warnings"] = sum(1 for _ in f)
    
    except Exception as e:
        error_logger.error(f"Error al obtener estadísticas: {e}")
    
    return stats


def get_recent_errors(limit: int = 50) -> list:
    """Obtiene los errores más recientes"""
    errors = []
    
    try:
        errors_file = LOG_DIR / "errors.json"
        if errors_file.exists():
            with open(errors_file, "r") as f:
                lines = f.readlines()
                # Obtener las últimas N líneas
                for line in lines[-limit:]:
                    try:
                        error_data = json.loads(line)
                        errors.append(error_data)
                    except Exception:
                        continue
    except Exception as e:
        error_logger.error(f"Error al obtener errores recientes: {e}")
    
    return errors


# Función para limpiar logs antiguos (ejecutar periódicamente)
def cleanup_old_logs(days: int = 7):
    """
    Limpia logs de más de X días para no llenar el disco
    Por defecto mantiene solo 7 días
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        files_deleted = 0
        bytes_freed = 0
        
        for log_file in LOG_DIR.glob("*.log*"):
            try:
                # Obtener fecha de modificación del archivo
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if mtime < cutoff_date:
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    files_deleted += 1
                    bytes_freed += file_size
            except Exception:
                continue
        
        # También limpiar archivos JSON antiguos
        for json_file in LOG_DIR.glob("errors_*.json"):
            try:
                mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
                if mtime < cutoff_date:
                    file_size = json_file.stat().st_size
                    json_file.unlink()
                    files_deleted += 1
                    bytes_freed += file_size
            except Exception:
                continue
        
        if files_deleted > 0:
            mb_freed = bytes_freed / (1024 * 1024)
            error_logger.info(
                f"Limpieza de logs: {files_deleted} archivos eliminados, "
                f"{mb_freed:.2f} MB liberados"
            )
            
    except Exception as e:
        error_logger.error(f"Error al limpiar logs antiguos: {e}")


# Función para obtener tamaño total de logs
def get_logs_disk_usage() -> Dict[str, Any]:
    """Obtiene el uso de disco de los logs"""
    try:
        total_size = 0
        file_count = 0
        
        for log_file in LOG_DIR.glob("*"):
            if log_file.is_file():
                total_size += log_file.stat().st_size
                file_count += 1
        
        return {
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "log_dir": str(LOG_DIR),
            "max_size_mb": MAX_LOG_SIZE_MB * 4  # Estimado con backups
        }
    except Exception:
        return {"error": "No se pudo obtener uso de disco"}
