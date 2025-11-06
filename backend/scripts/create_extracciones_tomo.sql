-- ============================================================================
-- Script SQL para crear tabla extracciones_tomo
-- Sistema OCR - FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 29 de Octubre de 2025
-- ============================================================================

-- Tabla para almacenar extracciones estructuradas de tomos
CREATE TABLE IF NOT EXISTS extracciones_tomo (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER REFERENCES tomos(id) ON DELETE CASCADE,
    pagina INTEGER,
    tipo_extraccion VARCHAR(50),
    contenido JSONB,
    fecha_documento TIMESTAMP WITH TIME ZONE,
    fecha_extraccion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS ix_extracciones_tomo_id ON extracciones_tomo(id);
CREATE INDEX IF NOT EXISTS ix_extracciones_tomo_tomo_id ON extracciones_tomo(tomo_id);
CREATE INDEX IF NOT EXISTS idx_extracciones_tomo_tipo ON extracciones_tomo(tipo_extraccion);
CREATE INDEX IF NOT EXISTS idx_extracciones_tomo_pagina ON extracciones_tomo(pagina);
CREATE INDEX IF NOT EXISTS idx_extracciones_tomo_fecha_doc ON extracciones_tomo(fecha_documento);

-- Índice GIN para búsqueda en contenido JSONB
CREATE INDEX IF NOT EXISTS idx_extracciones_tomo_contenido ON extracciones_tomo USING GIN(contenido);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_extracciones_tomo_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_extracciones_tomo_updated_at ON extracciones_tomo;
CREATE TRIGGER trigger_update_extracciones_tomo_updated_at
    BEFORE UPDATE ON extracciones_tomo
    FOR EACH ROW
    EXECUTE FUNCTION update_extracciones_tomo_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE extracciones_tomo IS 'Extracciones estructuradas de información de tomos';
COMMENT ON COLUMN extracciones_tomo.tipo_extraccion IS 'Tipo de extracción: datos_personales, fechas, direcciones, etc.';
COMMENT ON COLUMN extracciones_tomo.contenido IS 'Contenido extraído en formato JSON estructurado';
COMMENT ON COLUMN extracciones_tomo.fecha_documento IS 'Fecha del documento original extraído';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
