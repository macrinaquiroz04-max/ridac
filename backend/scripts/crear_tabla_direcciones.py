"""
Script para crear la tabla de direcciones corregidas
Sistema OCR - RIDAC
"""

from sqlalchemy import create_engine, text
from app.config import settings
from app.utils.logger import logger

def crear_tabla_direcciones():
    """Crea la tabla direcciones_corregidas en la base de datos"""
    
    # Conectar a la base de datos
    engine = create_engine(settings.DATABASE_URL)
    
    sql = """
    CREATE TABLE IF NOT EXISTS direcciones_corregidas (
        id SERIAL PRIMARY KEY,
        tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
        pagina INTEGER NOT NULL,
        linea INTEGER DEFAULT 0,
        
        -- Texto original del OCR (INMUTABLE)
        texto_original TEXT NOT NULL,
        
        -- Componentes de la dirección corregida
        calle VARCHAR(200),
        numero VARCHAR(20),
        colonia VARCHAR(200),
        codigo_postal VARCHAR(5),
        alcaldia VARCHAR(100),
        
        -- Metadatos de validación
        validada_sepomex BOOLEAN DEFAULT FALSE,
        editada_manualmente BOOLEAN DEFAULT FALSE,
        ignorada BOOLEAN DEFAULT FALSE,
        notas TEXT,
        
        -- Auditoría
        usuario_revision_id INTEGER REFERENCES usuarios(id),
        fecha_revision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Índices para mejorar rendimiento
    CREATE INDEX IF NOT EXISTS idx_direcciones_tomo_id ON direcciones_corregidas(tomo_id);
    CREATE INDEX IF NOT EXISTS idx_direcciones_pagina ON direcciones_corregidas(pagina);
    CREATE INDEX IF NOT EXISTS idx_direcciones_cp ON direcciones_corregidas(codigo_postal);
    CREATE INDEX IF NOT EXISTS idx_direcciones_alcaldia ON direcciones_corregidas(alcaldia);
    CREATE INDEX IF NOT EXISTS idx_direcciones_validada ON direcciones_corregidas(validada_sepomex);
    
    -- Trigger para actualizar fecha_modificacion
    CREATE OR REPLACE FUNCTION actualizar_fecha_modificacion()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.fecha_modificacion = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    DROP TRIGGER IF EXISTS trigger_actualizar_fecha_modificacion ON direcciones_corregidas;
    CREATE TRIGGER trigger_actualizar_fecha_modificacion
        BEFORE UPDATE ON direcciones_corregidas
        FOR EACH ROW
        EXECUTE FUNCTION actualizar_fecha_modificacion();
    
    COMMENT ON TABLE direcciones_corregidas IS 'Almacena direcciones detectadas y corregidas del OCR con validación SEPOMEX';
    COMMENT ON COLUMN direcciones_corregidas.texto_original IS 'Texto original extraído por OCR (inmutable para trazabilidad)';
    COMMENT ON COLUMN direcciones_corregidas.validada_sepomex IS 'Indica si la dirección fue validada contra el catálogo SEPOMEX';
    COMMENT ON COLUMN direcciones_corregidas.editada_manualmente IS 'Indica si el usuario editó manualmente la dirección';
    COMMENT ON COLUMN direcciones_corregidas.ignorada IS 'Indica si el usuario marcó esta detección como no dirección';
    """
    
    try:
        with engine.connect() as conn:
            # Ejecutar el script SQL
            conn.execute(text(sql))
            conn.commit()
            
        logger.info("✅ Tabla 'direcciones_corregidas' creada exitosamente")
        print("✅ Tabla 'direcciones_corregidas' creada exitosamente")
        print("✅ Índices creados")
        print("✅ Trigger de fecha_modificacion configurado")
        print("\n📊 La tabla está lista para usar")
        
        # Verificar
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'direcciones_corregidas' ORDER BY ordinal_position"
            ))
            
            print("\n📋 Columnas creadas:")
            for row in result:
                print(f"   - {row[0]}: {row[1]}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando tabla: {e}")
        print(f"❌ Error creando tabla: {e}")
        return False
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("=" * 80)
    print("🗄️  CREACIÓN DE TABLA: direcciones_corregidas")
    print("Sistema OCR - RIDAC")
    print("=" * 80)
    print()
    
    input("Presiona ENTER para continuar...")
    
    print("\n🔨 Creando tabla...")
    exito = crear_tabla_direcciones()
    
    if exito:
        print("\n" + "=" * 80)
        print("✅ TABLA CREADA EXITOSAMENTE")
        print("=" * 80)
        print("\n📝 Próximos pasos:")
        print("   1. Reiniciar el sistema Docker")
        print("   2. Agregar los endpoints en main.py")
        print("   3. Probar con un documento")
        print("\n💡 Consulta: docs/GUIA_DETECCION_DIRECCIONES.md")
    else:
        print("\n" + "=" * 80)
        print("❌ ERROR EN LA CREACIÓN")
        print("=" * 80)
        print("\n📝 Revisa los logs para más detalles")
    
    print()
    input("Presiona ENTER para salir...")
