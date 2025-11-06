# backend/app/services/file_service.py

from pathlib import Path
import shutil
from typing import Optional
from datetime import datetime
from app.config import settings
from app.utils.logger import logger
from app.utils.validators import sanitize_filename

class FileService:
    """Servicio de gestión de archivos locales"""

    def __init__(self):
        self.base_path = Path(settings.UPLOAD_PATH)
        self.export_path = Path(settings.EXPORT_PATH)
        self.temp_path = Path(settings.TEMP_PATH)

        # Crear directorios si no existen
        self._ensure_directories()

    def _ensure_directories(self):
        """Asegurar que existan los directorios necesarios"""
        for path in [self.base_path, self.export_path, self.temp_path]:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creando directorio {path}: {e}")

    def guardar_archivo(self, file_data: bytes, carpeta_nombre: str, tomo_numero: int, filename: str) -> tuple[str, float]:
        """
        Guardar archivo PDF en el sistema de archivos

        Returns:
            tuple: (ruta_completa, tamaño_mb)
        """
        try:
            # Sanitizar nombre de archivo
            filename_safe = sanitize_filename(filename)

            # Crear estructura de carpetas: UPLOAD_PATH/carpeta_nombre/
            carpeta_path = self.base_path / carpeta_nombre
            carpeta_path.mkdir(parents=True, exist_ok=True)

            # Nombre final: tomo_001.pdf, tomo_002.pdf, etc.
            nombre_final = f"tomo_{tomo_numero:03d}_{filename_safe}"
            ruta_completa = carpeta_path / nombre_final

            # Guardar archivo
            with open(ruta_completa, 'wb') as f:
                f.write(file_data)

            # Calcular tamaño en MB
            tamaño_mb = len(file_data) / (1024 * 1024)

            logger.info(f"✓ Archivo guardado: {ruta_completa} ({tamaño_mb:.2f} MB)")

            return str(ruta_completa), round(tamaño_mb, 2)

        except Exception as e:
            logger.error(f"Error guardando archivo: {e}")
            raise

    def eliminar_archivo(self, ruta: str) -> bool:
        """Eliminar archivo del sistema"""
        try:
            file_path = Path(ruta)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"✓ Archivo eliminado: {ruta}")
                return True
            else:
                logger.warning(f"⚠ Archivo no existe: {ruta}")
                return False
        except Exception as e:
            logger.error(f"Error eliminando archivo: {e}")
            return False

    def eliminar_carpeta(self, carpeta_nombre: str) -> bool:
        """Eliminar carpeta completa con todos sus archivos"""
        try:
            carpeta_path = self.base_path / carpeta_nombre
            if carpeta_path.exists():
                shutil.rmtree(carpeta_path)
                logger.info(f"✓ Carpeta eliminada: {carpeta_path}")
                return True
            else:
                logger.warning(f"⚠ Carpeta no existe: {carpeta_path}")
                return False
        except Exception as e:
            logger.error(f"Error eliminando carpeta: {e}")
            return False

    def obtener_archivo(self, ruta: str) -> Optional[bytes]:
        """Leer archivo del sistema"""
        try:
            file_path = Path(ruta)
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return f.read()
            else:
                logger.warning(f"⚠ Archivo no existe: {ruta}")
                return None
        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}")
            return None

    def verificar_espacio_disponible(self, tamaño_mb: float) -> tuple[bool, str]:
        """Verificar si hay espacio suficiente"""
        try:
            stat = shutil.disk_usage(self.base_path)
            espacio_libre_mb = stat.free / (1024 * 1024)

            # Requerir al menos 1GB libre además del archivo
            espacio_requerido = tamaño_mb + 1024

            if espacio_libre_mb >= espacio_requerido:
                return True, f"Espacio disponible: {espacio_libre_mb:.2f} MB"
            else:
                return False, f"Espacio insuficiente. Disponible: {espacio_libre_mb:.2f} MB, Requerido: {espacio_requerido:.2f} MB"

        except Exception as e:
            logger.error(f"Error verificando espacio: {e}")
            return False, str(e)

    def get_storage_stats(self) -> dict:
        """Obtener estadísticas de almacenamiento"""
        try:
            stat = shutil.disk_usage(self.base_path)

            return {
                "total_gb": round(stat.total / (1024**3), 2),
                "usado_gb": round(stat.used / (1024**3), 2),
                "libre_gb": round(stat.free / (1024**3), 2),
                "porcentaje_uso": round((stat.used / stat.total) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
