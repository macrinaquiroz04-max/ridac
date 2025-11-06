"""
Verificar si el script se está ejecutando dentro de Docker
"""

import os
import sys


def verificar_docker():
    """
    Verifica si el script se está ejecutando dentro de Docker
    """
    # Verificar variables de entorno típicas de Docker
    es_docker = (
        os.path.exists('/.dockerenv') or  # Archivo que indica Docker
        os.environ.get('DOCKER_CONTAINER', '').lower() == 'true' or
        os.environ.get('DB_HOST', '') == 'postgres'  # Variable de Docker Compose
    )
    
    return es_docker


def requerir_docker(script_name: str):
    """
    Requiere que el script se ejecute dentro de Docker
    Si no está en Docker, muestra error y sale
    """
    if not verificar_docker():
        print("\n" + "=" * 80)
        print("⚠️  ERROR: Este script debe ejecutarse DENTRO de Docker")
        print("=" * 80)
        print(f"\n❌ No ejecutar: python {script_name}")
        print(f"✅ Ejecutar:    docker-compose exec backend python {script_name}")
        print("\nRazón: Este script requiere acceso a la base de datos de producción")
        print("       que solo está disponible dentro del contenedor Docker.\n")
        print("Ver: GUIA_BASE_DATOS_DOCKER.md para más información")
        print("=" * 80 + "\n")
        sys.exit(1)
    
    # Mostrar confirmación
    print(f"✅ Ejecutando dentro de Docker")
    print(f"   DB_HOST: {os.environ.get('DB_HOST', 'localhost')}")
    print(f"   DB_NAME: {os.environ.get('DB_NAME', 'sistema_ocr')}\n")
