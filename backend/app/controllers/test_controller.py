# backend/app/controllers/test_controller.py

from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import os
import sys

from app.utils.logger import logger
from app.config import settings


class TestController:
    """Controlador para pruebas de integridad del sistema"""

    def test_health(self) -> Dict[str, Any]:
        """
        Prueba de salud básica del servidor

        Returns:
            dict: Estado del servidor con timestamp
        """
        try:
            return {
                "success": True,
                "message": "Servidor OK",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "environment": "production" if os.getenv("PRODUCTION") else "development"
            }
        except Exception as e:
            logger.error(f"Error en test_health: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def test_database(self, db: Session) -> Dict[str, Any]:
        """
        Prueba de conexión a PostgreSQL con UTF-8

        Args:
            db: Sesión de base de datos SQLAlchemy

        Returns:
            dict: Estado de la conexión y encoding
        """
        try:
            # Verificar conexión básica
            result = db.execute(text("SELECT 1")).scalar()

            if result != 1:
                raise Exception("Respuesta inesperada de la base de datos")

            # Verificar encoding UTF-8
            encoding = db.execute(text("SHOW client_encoding")).scalar()

            # Verificar versión de PostgreSQL
            version = db.execute(text("SELECT version()")).scalar()

            # Contar tablas en el esquema
            tables_count = db.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )).scalar()

            # Verificar que existan las tablas principales
            expected_tables = ['usuarios', 'carpetas', 'tomos', 'contenido_ocr', 'permisos_carpeta', 'permisos_sistema']
            existing_tables = []

            for table in expected_tables:
                exists = db.execute(text(
                    f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')"
                )).scalar()
                if exists:
                    existing_tables.append(table)

            missing_tables = [t for t in expected_tables if t not in existing_tables]

            logger.info(f"Test de base de datos exitoso. Encoding: {encoding}, Tablas: {tables_count}")

            return {
                "success": True,
                "message": "Conexión a PostgreSQL exitosa",
                "timestamp": datetime.now().isoformat(),
                "database": {
                    "encoding": encoding,
                    "version": version.split(',')[0] if version else "Unknown",
                    "total_tables": tables_count,
                    "expected_tables": len(expected_tables),
                    "existing_tables": len(existing_tables),
                    "missing_tables": missing_tables if missing_tables else None
                }
            }

        except Exception as e:
            logger.error(f"Error en test_database: {str(e)}")
            return {
                "success": False,
                "message": f"Error de conexión a base de datos: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def test_filesystem(self) -> Dict[str, Any]:
        """
        Prueba de acceso al sistema de archivos C:/RIDAC/*

        Returns:
            dict: Estado de los directorios y permisos
        """
        try:
            paths_to_check = {
                "documentos": settings.UPLOAD_PATH,
                "exportaciones": settings.EXPORT_PATH,
                "temporal": settings.TEMP_PATH,
                "logs": settings.LOG_PATH
            }

            results = {}
            all_ok = True

            for name, path_str in paths_to_check.items():
                path = Path(path_str)

                path_info = {
                    "path": str(path),
                    "exists": path.exists(),
                    "is_directory": path.is_dir() if path.exists() else False,
                    "readable": False,
                    "writable": False,
                    "error": None
                }

                try:
                    # Intentar crear el directorio si no existe
                    if not path.exists():
                        path.mkdir(parents=True, exist_ok=True)
                        logger.info(f"Directorio creado: {path}")
                        path_info["exists"] = True
                        path_info["is_directory"] = True
                        path_info["created"] = True

                    # Probar lectura
                    if path.exists():
                        list(path.iterdir())
                        path_info["readable"] = True

                    # Probar escritura
                    test_file = path / ".test_write"
                    test_file.write_text("test", encoding='utf-8')
                    test_file.unlink()
                    path_info["writable"] = True

                except Exception as e:
                    path_info["error"] = str(e)
                    all_ok = False
                    logger.error(f"Error en filesystem test para {name}: {str(e)}")

                results[name] = path_info

            return {
                "success": all_ok,
                "message": "Acceso al sistema de archivos verificado" if all_ok else "Algunos directorios tienen problemas",
                "timestamp": datetime.now().isoformat(),
                "paths": results
            }

        except Exception as e:
            logger.error(f"Error en test_filesystem: {str(e)}")
            return {
                "success": False,
                "message": f"Error al verificar sistema de archivos: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def test_ocr(self) -> Dict[str, Any]:
        """
        Prueba de motores OCR disponibles

        Returns:
            dict: Estado de los motores OCR instalados
        """
        try:
            engines = {}
            available_count = 0

            # Tesseract OCR
            tesseract_available = False
            tesseract_version = None
            tesseract_error = None

            try:
                import pytesseract
                from PIL import Image

                # Intentar obtener versión
                version = pytesseract.get_tesseract_version()
                tesseract_version = str(version)
                tesseract_available = True
                available_count += 1

            except ImportError:
                tesseract_error = "pytesseract no instalado"
            except Exception as e:
                tesseract_error = str(e)

            engines["tesseract"] = {
                "enabled": settings.OCR_ENABLE_TESSERACT,
                "available": tesseract_available,
                "version": tesseract_version,
                "error": tesseract_error
            }

            # EasyOCR
            easyocr_available = False
            easyocr_error = None

            try:
                import easyocr
                easyocr_available = True
                available_count += 1
            except ImportError:
                easyocr_error = "easyocr no instalado"
            except Exception as e:
                easyocr_error = str(e)

            engines["easyocr"] = {
                "enabled": settings.OCR_ENABLE_EASYOCR,
                "available": easyocr_available,
                "error": easyocr_error
            }

            # PaddleOCR
            paddleocr_available = False
            paddleocr_error = None

            try:
                from paddleocr import PaddleOCR
                paddleocr_available = True
                available_count += 1
            except ImportError:
                paddleocr_error = "paddleocr no instalado"
            except Exception as e:
                paddleocr_error = str(e)

            engines["paddleocr"] = {
                "enabled": settings.OCR_ENABLE_PADDLEOCR,
                "available": paddleocr_available,
                "error": paddleocr_error
            }

            # TrOCR
            trocr_available = False
            trocr_error = None

            try:
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel
                trocr_available = True
                available_count += 1
            except ImportError:
                trocr_error = "transformers no instalado"
            except Exception as e:
                trocr_error = str(e)

            engines["trocr"] = {
                "enabled": settings.OCR_ENABLE_TROCR,
                "available": trocr_available,
                "error": trocr_error
            }

            # Verificar dependencias comunes
            dependencies = {}

            for lib_name in ['PIL', 'cv2', 'numpy', 'pdf2image']:
                try:
                    __import__(lib_name)
                    dependencies[lib_name] = {"installed": True}
                except ImportError:
                    dependencies[lib_name] = {"installed": False, "error": "No instalado"}

            success = available_count > 0

            logger.info(f"Test OCR completado. Motores disponibles: {available_count}/4")

            return {
                "success": success,
                "message": f"{available_count} motor(es) OCR disponible(s)" if success else "No hay motores OCR disponibles",
                "timestamp": datetime.now().isoformat(),
                "engines": engines,
                "available_engines": available_count,
                "total_engines": 4,
                "dependencies": dependencies,
                "max_workers": settings.OCR_MAX_WORKERS
            }

        except Exception as e:
            logger.error(f"Error en test_ocr: {str(e)}")
            return {
                "success": False,
                "message": f"Error al verificar motores OCR: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def test_complete(self, db: Session) -> Dict[str, Any]:
        """
        Ejecuta todas las pruebas del sistema

        Args:
            db: Sesión de base de datos SQLAlchemy

        Returns:
            dict: Resultados agregados de todas las pruebas
        """
        try:
            logger.info("Iniciando test completo del sistema")

            # Ejecutar todas las pruebas
            health_result = self.test_health()
            db_result = self.test_database(db)
            fs_result = self.test_filesystem()
            ocr_result = self.test_ocr()

            # Calcular resultado general
            all_success = (
                health_result.get("success", False) and
                db_result.get("success", False) and
                fs_result.get("success", False) and
                ocr_result.get("success", False)
            )

            passed_tests = sum([
                health_result.get("success", False),
                db_result.get("success", False),
                fs_result.get("success", False),
                ocr_result.get("success", False)
            ])

            logger.info(f"Test completo finalizado. Aprobadas: {passed_tests}/4")

            return {
                "success": all_success,
                "message": f"Pruebas completadas: {passed_tests}/4 exitosas",
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tests": 4,
                    "passed": passed_tests,
                    "failed": 4 - passed_tests
                },
                "results": {
                    "health": health_result,
                    "database": db_result,
                    "filesystem": fs_result,
                    "ocr": ocr_result
                }
            }

        except Exception as e:
            logger.error(f"Error en test_complete: {str(e)}")
            return {
                "success": False,
                "message": f"Error al ejecutar pruebas completas: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }


# Instancia global del controlador
test_controller = TestController()
