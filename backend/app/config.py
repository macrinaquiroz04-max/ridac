# backend/app/config.py
# Sistema OCR con Análisis Jurídico
# Ingeniero: Eduardo Lozada Quiroz, ISC
# Cliente: Unidad de Análisis y Contexto (UAyC) - RIDAC
# Confidencial - Propiedad Intelectual Protegida
# Firma Digital: ELQ_ISC_UAYC_27102025

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

# Metadata del sistema - Autor: E.Lozada.Q (ISC)
class Settings(BaseSettings):
    # --- Base de datos ---
    # Opción 1: URL completa (recomendado para Supabase/Render)
    DATABASE_URL: Optional[str] = None

    # Opción 2: variables separadas (desarrollo local)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "sistema_ocr"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "1234"

    # --- CORS ---
    # Para producción: URL de Cloudflare Pages, separadas por comas si hay varias
    FRONTEND_URL: str = "http://localhost:5173"

    # Seguridad
    JWT_SECRET_KEY: str = "default-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas para red local
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 días

    # Rutas
    UPLOAD_PATH: str = "C:/RIDAC/documentos"
    EXPORT_PATH: str = "C:/RIDAC/exportaciones"
    TEMP_PATH: str = "C:/RIDAC/temp"
    LOG_PATH: str = "C:/RIDAC/logs"

    # OCR
    OCR_ENABLE_TESSERACT: bool = True
    OCR_ENABLE_EASYOCR: bool = False
    OCR_ENABLE_PADDLEOCR: bool = False
    OCR_ENABLE_TROCR: bool = False
    
    # Configuraciones OCR mejoradas
    OCR_MAX_IMAGE_SIZE: int = 4000  # Tamaño máximo de imagen para OCR
    OCR_MIN_CONFIDENCE: float = 30.0  # Confianza mínima para aceptar resultado
    OCR_PREPROCESSING_ENABLED: bool = True  # Habilitar preprocesamiento
    OCR_TEXT_CORRECTION_ENABLED: bool = True  # Habilitar corrección automática
    OCR_ENSEMBLE_ENABLED: bool = True  # Habilitar ensemble de motores
    OCR_PARALLEL_PROCESSING: bool = False  # Procesamiento paralelo (experimental)
    
    # Configuraciones específicas de Tesseract
    TESSERACT_CONFIG_DEFAULT: str = "--oem 3 --psm 6"
    TESSERACT_LANGUAGES: str = "spa+eng"
    
    # Configuraciones de calidad
    OCR_HIGH_QUALITY_MODE: bool = True  # Usar configuraciones de alta calidad
    OCR_SAVE_INTERMEDIATE_IMAGES: bool = False  # Guardar imágenes intermedias para debug
    OCR_MAX_WORKERS: int = 2

    # Servidor
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000  # Puerto público (login)
    SECURE_PORT: int = 8443  # Puerto seguro (usuarios autenticados)

    @property
    def get_database_url(self) -> str:
        """
        Retorna la URL de conexión a PostgreSQL.
        Prioriza DATABASE_URL (Supabase/Render), si no la construye desde las variables separadas.
        Supabase requiere sslmode=require en el connection string.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?client_encoding=utf8"

    @property
    def cors_origins(self) -> list:
        """Lista de orígenes permitidos para CORS"""
        origins = [
            "http://localhost:5173",   # Vue dev server
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]
        if self.FRONTEND_URL:
            for url in self.FRONTEND_URL.split(","):
                url = url.strip()
                if url and url not in origins:
                    origins.append(url)
        return origins

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()
