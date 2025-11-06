# backend/scripts/generar_embeddings.py

"""
Script para generar y actualizar embeddings vectoriales para búsqueda semántica
"""

import sys
import os
from pathlib import Path

# Agregar el directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.tomo import ContenidoOCR
from app.controllers.busqueda_controller import busqueda_controller
from app.utils.logger import logger


def main():
    """Función principal para generar embeddings"""
    
    print("🔍 GENERADOR DE EMBEDDINGS PARA BÚSQUEDA SEMÁNTICA")
    print("=" * 60)
    
    try:
        # Crear conexión a la base de datos
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with SessionLocal() as db:
            # Contar registros sin embeddings
            total_sin_embeddings = db.query(ContenidoOCR).filter(
                ContenidoOCR.embeddings.is_(None)
            ).count()
            
            total_con_texto = db.query(ContenidoOCR).filter(
                ContenidoOCR.texto_extraido.isnot(None),
                ContenidoOCR.texto_extraido != ""
            ).count()
            
            print(f"📊 Estadísticas:")
            print(f"   - Total registros con texto: {total_con_texto}")
            print(f"   - Registros sin embeddings: {total_sin_embeddings}")
            print()
            
            if total_sin_embeddings == 0:
                print("✅ Todos los registros ya tienen embeddings")
                return
            
            # Confirmar antes de proceder
            respuesta = input(f"¿Generar embeddings para {total_sin_embeddings} registros? (s/n): ")
            if respuesta.lower() != 's':
                print("❌ Operación cancelada")
                return
            
            print()
            print("🚀 Iniciando generación de embeddings...")
            print("   (Este proceso puede tomar varios minutos)")
            print()
            
            # Generar embeddings
            resultado = busqueda_controller.actualizar_embeddings_contenido(db)
            
            if resultado["success"]:
                print(f"✅ Embeddings generados exitosamente")
                print(f"   - Registros actualizados: {resultado['total_actualizado']}")
                print()
                print("🎯 La búsqueda semántica ya está disponible!")
            else:
                print(f"❌ Error generando embeddings: {resultado['message']}")
                
    except ImportError as e:
        print(f"❌ Error de dependencias: {e}")
        print("📝 Instale las dependencias requeridas:")
        print("   pip install sentence-transformers scikit-learn")
        
    except Exception as e:
        logger.error(f"Error en generación de embeddings: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()