"""
Habilitar extensión pg_trgm en PostgreSQL
para búsqueda fuzzy (similitud de texto)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "app"))

from database import SessionLocal
from sqlalchemy import text

def habilitar_pg_trgm():
    print("=" * 70)
    print("🔧 HABILITANDO EXTENSIÓN pg_trgm EN POSTGRESQL")
    print("=" * 70)
    print("\nEsta extensión permite búsqueda fuzzy (similitud de texto)")
    print("Necesaria para corregir errores ortográficos automáticamente\n")
    
    db = SessionLocal()
    
    try:
        # Habilitar extensión
        print("📦 Instalando extensión pg_trgm...")
        db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        db.commit()
        print("✅ Extensión pg_trgm habilitada")
        
        # Verificar
        print("\n🔍 Verificando instalación...")
        result = db.execute(text("""
            SELECT * FROM pg_extension WHERE extname = 'pg_trgm';
        """))
        
        if result.fetchone():
            print("✅ Extensión pg_trgm instalada correctamente")
            
            # Probar función similarity
            print("\n🧪 Probando función similarity()...")
            result = db.execute(text("""
                SELECT similarity('Condeza', 'CONDESA') as similitud;
            """))
            similitud = result.scalar()
            print(f"✅ similarity('Condeza', 'CONDESA') = {similitud:.2f}")
            
            if similitud > 0.5:
                print("✅ Búsqueda fuzzy funcionando correctamente!")
            
        else:
            print("❌ Error: Extensión no encontrada")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Solución:")
        print("   Ejecuta este comando como superusuario de PostgreSQL:")
        print("   CREATE EXTENSION pg_trgm;")
    finally:
        db.close()
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    habilitar_pg_trgm()
