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

# Configuración del engine optimizada para 20 usuarios simultáneos
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verificar conexión antes de usar
    pool_size=15,  # Aumentado para 20 usuarios simultáneos
    max_overflow=25,  # Pool más grande para picos de carga
    pool_timeout=30,  # Timeout para obtener conexión
    pool_recycle=3600,  # Reciclar conexiones cada hora
    echo=False,  # Cambiar a True para debug SQL
    connect_args={
        "client_encoding": "utf8",
        "options": "-c timezone=America/Mexico_City -c client_encoding=utf8 -c statement_timeout=30000"  # Timeout de 30 segundos
    },
    # Configuraciones adicionales para concurrencia
    isolation_level="READ_COMMITTED"  # Nivel de aislamiento optimizado
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
