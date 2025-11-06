-- ============================================================================
-- Script SQL para crear tabla personas_mencionadas
-- Sistema OCR - FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 29 de Octubre de 2025
-- ============================================================================

-- Tabla para almacenar personas mencionadas en tomos
CREATE TABLE IF NOT EXISTS personas_mencionadas (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER REFERENCES tomos(id) ON DELETE CASCADE,
    nombre VARCHAR(200),
    tipo VARCHAR(50),
    direccion TEXT,
    telefono VARCHAR(50),
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS ix_personas_mencionadas_id ON personas_mencionadas(id);
CREATE INDEX IF NOT EXISTS ix_personas_mencionadas_tomo_id ON personas_mencionadas(tomo_id);
CREATE INDEX IF NOT EXISTS idx_personas_mencionadas_nombre ON personas_mencionadas(nombre);
CREATE INDEX IF NOT EXISTS idx_personas_mencionadas_tipo ON personas_mencionadas(tipo);

-- Índice para búsqueda de texto en nombre
CREATE INDEX IF NOT EXISTS idx_personas_mencionadas_nombre_gin ON personas_mencionadas USING gin(to_tsvector('spanish', nombre));

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_personas_mencionadas_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_personas_mencionadas_updated_at ON personas_mencionadas;
CREATE TRIGGER trigger_update_personas_mencionadas_updated_at
    BEFORE UPDATE ON personas_mencionadas
    FOR EACH ROW
    EXECUTE FUNCTION update_personas_mencionadas_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE personas_mencionadas IS 'Personas identificadas y mencionadas en los tomos procesados';
COMMENT ON COLUMN personas_mencionadas.tipo IS 'Tipo de persona: testigo, acusado, víctima, perito, etc.';
COMMENT ON COLUMN personas_mencionadas.lat IS 'Latitud de la dirección (si está disponible)';
COMMENT ON COLUMN personas_mencionadas.lon IS 'Longitud de la dirección (si está disponible)';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
