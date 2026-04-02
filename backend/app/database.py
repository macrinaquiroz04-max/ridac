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
    """Inicializar base de datos: crea tablas y siembra datos iniciales"""
    try:
        # Importar todos los modelos para que create_all los detecte
        from app.models import usuario, carpeta, tomo, tarea_ocr, permiso, auditoria

        # Crear todas las tablas — checkfirst=True para tablas e índices ya existentes
        try:
            Base.metadata.create_all(bind=engine, checkfirst=True)
            logger.info("Tablas creadas / verificadas correctamente")
        except Exception as e_create:
            # DuplicateTable/DuplicateObject es normal en reinicios — ignorar y continuar
            err_str = str(e_create)
            if "already exists" in err_str or "DuplicateTable" in err_str or "DuplicateObject" in err_str:
                logger.info("Tablas e índices ya existen — omitiendo creación")
            else:
                raise

        # --- Seed inicial: roles y usuario admin ---
        _seed_initial_data()

        return True
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")
        return False


def _seed_initial_data():
    """Crea roles base y usuario admin si no existen (idempotente)."""
    from app.models.usuario import Rol, Usuario
    from app.utils.password_hash import hash_password
    import os

    db = SessionLocal()
    try:
        # 1. Roles base — solo admin; el rol usuario se eliminó (todo lo hace el admin)
        roles_base = [
            ("admin", "Administrador del sistema con acceso completo"),
        ]
        for nombre, descripcion in roles_base:
            existe = db.query(Rol).filter(Rol.nombre == nombre).first()
            if not existe:
                db.add(Rol(nombre=nombre, descripcion=descripcion))
                logger.info(f"Rol '{nombre}' creado")
        db.commit()

        # 2. Usuario admin inicial
        admin_user = db.query(Usuario).filter(Usuario.username == "admin").first()
        if not admin_user:
            rol_admin = db.query(Rol).filter(Rol.nombre == "admin").first()
            # Contraseña desde env o default solo para primer arranque
            pwd = os.environ.get("ADMIN_INITIAL_PASSWORD", "Ridac2026!")
            db.add(Usuario(
                username="admin",
                email="admin@ridac.gob.mx",
                password=hash_password(pwd),
                nombre_completo="Administrador",
                rol_id=rol_admin.id,
                activo=True,
                debe_cambiar_password=True,  # Fuerza cambio en primer login
            ))
            db.commit()
            logger.info(f"Usuario 'admin' creado — contraseña inicial: {pwd}")
            logger.info("⚠️  Cambia la contraseña en el primer acceso")
    except Exception as e:
        db.rollback()
        logger.error(f"Error en seed inicial: {e}")
    finally:
        db.close()
