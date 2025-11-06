# backend/tests/test_connections.py

import sys
import os
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Probar que se pueden importar los módulos necesarios"""
    print("\n=== Prueba 1: Imports ===")
    try:
        import fastapi
        print("✓ FastAPI instalado")
    except ImportError:
        print("✗ FastAPI no instalado")
        return False

    try:
        import sqlalchemy
        print("✓ SQLAlchemy instalado")
    except ImportError:
        print("✗ SQLAlchemy no instalado")
        return False

    try:
        import psycopg2
        print("✓ psycopg2 instalado")
    except ImportError:
        print("✗ psycopg2 no instalado")
        return False

    try:
        import jose
        print("✓ python-jose instalado")
    except ImportError:
        print("✗ python-jose no instalado")
        return False

    try:
        import passlib
        print("✓ passlib instalado")
    except ImportError:
        print("✗ passlib no instalado")
        return False

    return True

def test_environment():
    """Probar variables de entorno"""
    print("\n=== Prueba 2: Variables de Entorno ===")

    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        print("✗ Archivo .env no existe")
        return False

    print("✓ Archivo .env existe")

    # Leer .env
    from dotenv import load_dotenv
    load_dotenv(env_file)

    required_vars = [
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
        'JWT_SECRET_KEY', 'UPLOAD_PATH', 'EXPORT_PATH', 'TEMP_PATH'
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print(f"✗ Variables faltantes: {', '.join(missing)}")
        return False

    print("✓ Todas las variables de entorno configuradas")
    return True

def test_database():
    """Probar conexión a base de datos"""
    print("\n=== Prueba 3: Base de Datos ===")

    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")

        from sqlalchemy import create_engine, text

        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        db_name = os.getenv('DB_NAME')
        db_user = os.getenv('DB_USER')
        db_pass = os.getenv('DB_PASSWORD')

        DATABASE_URL = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Conexión a PostgreSQL exitosa")

            # Verificar encoding UTF-8
            result = conn.execute(text("SHOW client_encoding"))
            encoding = result.scalar()
            print(f"✓ Encoding: {encoding}")

            # Probar caracteres UTF-8
            result = conn.execute(text("SELECT 'Ñoño áéíóú ÁÉÍÓÚ ¿¡' as test"))
            utf_test = result.scalar()
            print(f"✓ Prueba UTF-8: {utf_test}")

            # Verificar tablas
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]

            required_tables = [
                'usuarios', 'roles', 'carpetas', 'tomos',
                'contenido_ocr', 'tareas_ocr', 'permisos_carpeta',
                'permisos_sistema', 'auditoria'
            ]

            missing_tables = [t for t in required_tables if t not in tables]

            if missing_tables:
                print(f"✗ Tablas faltantes: {', '.join(missing_tables)}")
                return False

            print(f"✓ Todas las tablas existen ({len(tables)} tablas)")

            # Verificar usuario admin
            result = conn.execute(text("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'"))
            count = result.scalar()

            if count == 0:
                print("✗ Usuario admin no existe")
                return False

            print("✓ Usuario admin existe")

        return True

    except Exception as e:
        print(f"✗ Error de base de datos: {e}")
        return False

def test_filesystem():
    """Probar acceso al sistema de archivos"""
    print("\n=== Prueba 4: Sistema de Archivos ===")

    base_path = Path("C:/FGJCDMX")

    dirs = {
        "documentos": base_path / "documentos",
        "exportaciones": base_path / "exportaciones",
        "temp": base_path / "temp",
        "logs": base_path / "logs"
    }

    all_ok = True

    for name, path in dirs.items():
        if not path.exists():
            print(f"✗ Carpeta {name} no existe: {path}")
            all_ok = False
        elif not os.access(str(path), os.W_OK):
            print(f"✗ Carpeta {name} no es escribible: {path}")
            all_ok = False
        else:
            print(f"✓ Carpeta {name} OK: {path}")

    # Probar escritura
    test_file = base_path / "temp" / "test_write.txt"
    try:
        test_file.write_text("test", encoding='utf-8')
        test_file.unlink()
        print("✓ Prueba de escritura exitosa")
    except Exception as e:
        print(f"✗ No se puede escribir: {e}")
        all_ok = False

    return all_ok

def test_ocr_engines():
    """Probar motores OCR"""
    print("\n=== Prueba 5: Motores OCR ===")

    # Tesseract
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract {version} instalado")
    except Exception as e:
        print(f"✗ Tesseract no disponible: {e}")
        print("  El sistema funcionará pero sin OCR")

    # EasyOCR
    try:
        import easyocr
        print(f"✓ EasyOCR instalado")
    except:
        print("⚠ EasyOCR no instalado (opcional)")

    # PaddleOCR
    try:
        from paddleocr import PaddleOCR
        print(f"✓ PaddleOCR instalado")
    except:
        print("⚠ PaddleOCR no instalado (opcional)")

    # TrOCR
    try:
        from transformers import TrOCRProcessor
        print(f"✓ TrOCR (transformers) instalado")
    except:
        print("⚠ TrOCR no instalado (opcional)")

    return True

def test_api_config():
    """Probar configuración de la API"""
    print("\n=== Prueba 6: Configuración API ===")

    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / ".env")

        from app.config import settings

        print(f"✓ Config cargada correctamente")
        print(f"  - Puerto: {settings.SERVER_PORT}")
        print(f"  - Base de datos: {settings.DB_NAME}")
        print(f"  - Upload path: {settings.UPLOAD_PATH}")

        return True
    except Exception as e:
        print(f"✗ Error cargando configuración: {e}")
        return False

def main():
    print("\n" + "="*50)
    print("  PRUEBAS DEL SISTEMA OCR - FGJCDMX")
    print("="*50)

    tests = [
        ("Imports", test_imports),
        ("Variables de entorno", test_environment),
        ("Base de datos", test_database),
        ("Sistema de archivos", test_filesystem),
        ("Motores OCR", test_ocr_engines),
        ("Configuración API", test_api_config),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Error ejecutando prueba '{name}': {e}")
            results.append((name, False))

    # Resumen
    print("\n" + "="*50)
    print("  RESUMEN")
    print("="*50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nResultado: {passed}/{total} pruebas exitosas")

    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron! El sistema está listo.")
        return 0
    else:
        print(f"\n⚠ {total - passed} prueba(s) fallaron. Revisa los errores arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
