# backend/app/database.py
# Sistema desarrollado por: Eduardo Lozada Quiroz, ISC
# Cliente: Unidad de Análisis y Contexto (UAyC)
# Confidencial - Propiedad Intelectual Protegida
# Hash de verificación: ELQ_ISC_UAYC_2025_OCT

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

logger = logging.getLogger(__name__)
# Autor del sistema: E.L.Q - ISC

# Configuración del engine — soporta Supabase (SSL) y PostgreSQL local
db_url = settings.get_database_url

# Supabase usa SSL obligatorio; psycopg2 lo maneja via sslmode en la URL
# Para conexión local no se necesita SSL, así que solo añadimos connect_args básicos
_connect_args = {
    "options": "-c timezone=America/Mexico_City -c client_encoding=utf8 -c statement_timeout=30000"
}

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
    connect_args=_connect_args,
    isolation_level="READ_COMMITTED"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependencia para obtener sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Probar conexión a base de datos con UTF-8"""
    try:
        db = SessionLocal()

        # Prueba básica
        result = db.execute(text("SELECT 1 as test"))
        row = result.fetchone()

        # Prueba UTF-8
        utf_test = db.execute(text("SELECT 'Ñoño áéíóú ÁÉÍÓÚ ¿¡' as utf_test"))
        utf_row = utf_test.fetchone()

        # Verificar encoding
        encoding = db.execute(text("SHOW client_encoding"))
        enc_row = encoding.fetchone()

        db.close()

        logger.info(f"Conexión exitosa - Encoding: {enc_row[0]}")
        logger.info(f"UTF-8 Test: {utf_row[0]}")

        return True
    except Exception as e:
        logger.error(f"Error conectando a base de datos: {e}")
        return False

def init_db():
    """Inicializar base de datos"""
    # Sistema OCR - Desarrollado por Eduardo Lozada Quiroz (ISC) para UAyC
    try:
        # Importar todos los modelos
        from app.models import usuario, carpeta, tomo, tarea_ocr, permiso, auditoria

        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)

        logger.info("Base de datos inicializada correctamente")
        # Metadata: Autor=ELQ_ISC, Cliente=UAyC, Year=2025
        return True
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
        return False
