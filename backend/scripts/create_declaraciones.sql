-- ============================================================================
-- Script SQL para crear tabla declaraciones
-- Sistema OCR - FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 29 de Octubre de 2025
-- ============================================================================

-- Tabla para almacenar declaraciones de personas
CREATE TABLE IF NOT EXISTS declaraciones (
    id SERIAL PRIMARY KEY,
    persona_id INTEGER REFERENCES personas_mencionadas(id) ON DELETE CASCADE,
    tomo_id INTEGER REFERENCES tomos(id) ON DELETE CASCADE,
    fecha TIMESTAMP WITH TIME ZONE,
    tipo VARCHAR(50),
    contenido TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS ix_declaraciones_id ON declaraciones(id);
CREATE INDEX IF NOT EXISTS idx_declaraciones_persona ON declaraciones(persona_id);
CREATE INDEX IF NOT EXISTS idx_declaraciones_tomo ON declaraciones(tomo_id);
CREATE INDEX IF NOT EXISTS idx_declaraciones_fecha ON declaraciones(fecha);
CREATE INDEX IF NOT EXISTS idx_declaraciones_tipo ON declaraciones(tipo);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_declaraciones_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_declaraciones_updated_at ON declaraciones;
CREATE TRIGGER trigger_update_declaraciones_updated_at
    BEFORE UPDATE ON declaraciones
    FOR EACH ROW
    EXECUTE FUNCTION update_declaraciones_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE declaraciones IS 'Declaraciones realizadas por personas mencionadas en los tomos';
COMMENT ON COLUMN declaraciones.tipo IS 'Tipo de declaración: testimonial, ministerial, etc.';
COMMENT ON COLUMN declaraciones.contenido IS 'Contenido completo de la declaración';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
