"""
Script para eliminar diligencias duplicadas
Mantiene el registro más reciente (ID más alto) cuando hay duplicados
con el mismo carpeta_id y orden_cronologico
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db, engine
from app.models.analisis_juridico import Diligencia
from sqlalchemy import text
from sqlalchemy.orm import Session

def eliminar_duplicados():
    """
    Eliminar diligencias duplicadas manteniendo la más reciente
    """
    db = next(get_db())
    
    try:
        print("=" * 70)
        print("🔍 ELIMINANDO DILIGENCIAS DUPLICADAS")
        print("=" * 70)
        
        # 1. Encontrar duplicados
        print("\n📊 Buscando duplicados...")
        query_duplicados = text("""
            SELECT carpeta_id, orden_cronologico, COUNT(*) as cantidad
            FROM diligencias
            GROUP BY carpeta_id, orden_cronologico
            HAVING COUNT(*) > 1
            ORDER BY carpeta_id, orden_cronologico
        """)
        
        duplicados = db.execute(query_duplicados).fetchall()
        
        if not duplicados:
            print("✅ No se encontraron duplicados")
            return
        
        print(f"⚠️  Encontrados {len(duplicados)} órdenes cronológicos duplicados")
        print()
        
        # Mostrar resumen
        total_registros_duplicados = sum(dup.cantidad - 1 for dup in duplicados)  # -1 porque uno se mantiene
        
        for dup in duplicados[:10]:  # Mostrar primeros 10
            print(f"   Carpeta {dup.carpeta_id}, Orden {dup.orden_cronologico}: {dup.cantidad} registros")
        
        if len(duplicados) > 10:
            print(f"   ... y {len(duplicados) - 10} más")
        
        print(f"\n📝 Total de registros a eliminar: {total_registros_duplicados}")
        
        # 2. Confirmar
        respuesta = input("\n⚠️  ¿Eliminar duplicados manteniendo el más reciente? (S/N): ")
        
        if respuesta.upper() != 'S':
            print("❌ Operación cancelada")
            return
        
        # 3. Eliminar duplicados
        print("\n🗑️  Eliminando duplicados...")
        
        query_eliminar = text("""
            DELETE FROM diligencias
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY carpeta_id, orden_cronologico 
                               ORDER BY id DESC
                           ) as rn
                    FROM diligencias
                ) AS subquery
                WHERE rn > 1
            )
        """)
        
        result = db.execute(query_eliminar)
        db.commit()
        
        print(f"✅ Eliminados {result.rowcount} registros duplicados")
        
        # 4. Verificar
        print("\n🔍 Verificando...")
        duplicados_restantes = db.execute(query_duplicados).fetchall()
        
        if not duplicados_restantes:
            print("✅ ¡Perfecto! No quedan duplicados")
        else:
            print(f"⚠️  Aún quedan {len(duplicados_restantes)} duplicados")
        
        # 5. Mostrar estadísticas finales
        print("\n" + "=" * 70)
        print("📊 ESTADÍSTICAS FINALES")
        print("=" * 70)
        
        stats = text("""
            SELECT 
                carpeta_id,
                COUNT(*) as total_diligencias,
                MIN(orden_cronologico) as min_orden,
                MAX(orden_cronologico) as max_orden
            FROM diligencias
            GROUP BY carpeta_id
            ORDER BY carpeta_id
        """)
        
        for stat in db.execute(stats):
            print(f"Carpeta {stat.carpeta_id}: {stat.total_diligencias} diligencias (orden {stat.min_orden}-{stat.max_orden})")
        
        print("\n✅ Proceso completado exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    eliminar_duplicados()
