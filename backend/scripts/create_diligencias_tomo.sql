-- ============================================================================
-- Script SQL para crear tabla diligencias_tomo
-- Sistema OCR - FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 29 de Octubre de 2025
-- ============================================================================

-- Tabla para almacenar diligencias extraídas de tomos
CREATE TABLE IF NOT EXISTS diligencias_tomo (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER REFERENCES tomos(id) ON DELETE CASCADE,
    pagina INTEGER,
    tipo_diligencia VARCHAR(100),
    fecha TIMESTAMP WITH TIME ZONE,
    responsable VARCHAR(200),
    numero_oficio VARCHAR(100),
    contenido TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS ix_diligencias_tomo_id ON diligencias_tomo(id);
CREATE INDEX IF NOT EXISTS ix_diligencias_tomo_tomo_id ON diligencias_tomo(tomo_id);
CREATE INDEX IF NOT EXISTS idx_diligencias_tomo_tipo ON diligencias_tomo(tipo_diligencia);
CREATE INDEX IF NOT EXISTS idx_diligencias_tomo_fecha ON diligencias_tomo(fecha);
CREATE INDEX IF NOT EXISTS idx_diligencias_tomo_pagina ON diligencias_tomo(pagina);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_diligencias_tomo_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_diligencias_tomo_updated_at ON diligencias_tomo;
CREATE TRIGGER trigger_update_diligencias_tomo_updated_at
    BEFORE UPDATE ON diligencias_tomo
    FOR EACH ROW
    EXECUTE FUNCTION update_diligencias_tomo_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE diligencias_tomo IS 'Diligencias extraídas de tomos mediante análisis de documentos';
COMMENT ON COLUMN diligencias_tomo.tipo_diligencia IS 'Tipo de diligencia: comparecencia, pericia, oficio, etc.';
COMMENT ON COLUMN diligencias_tomo.numero_oficio IS 'Número de oficio asociado a la diligencia';
COMMENT ON COLUMN diligencias_tomo.contenido IS 'Resumen del contenido de la diligencia';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
