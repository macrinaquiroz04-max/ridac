-- ============================================================================
-- Script SQL para crear tabla direcciones_corregidas
-- Sistema OCR - FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 29 de Octubre de 2025
-- ============================================================================

-- Tabla para almacenar direcciones detectadas y corregidas con validación SEPOMEX
CREATE TABLE IF NOT EXISTS direcciones_corregidas (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    
    -- Ubicación en el documento
    pagina INTEGER NOT NULL,
    linea INTEGER DEFAULT 0,
    
    -- Texto original del OCR
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
    usuario_revision_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_revision TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_modificacion TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_direcciones_tomo ON direcciones_corregidas(tomo_id);
CREATE INDEX IF NOT EXISTS idx_direcciones_pagina ON direcciones_corregidas(pagina);
CREATE INDEX IF NOT EXISTS idx_direcciones_validada ON direcciones_corregidas(validada_sepomex);
CREATE INDEX IF NOT EXISTS idx_direcciones_cp ON direcciones_corregidas(codigo_postal);
CREATE INDEX IF NOT EXISTS idx_direcciones_alcaldia ON direcciones_corregidas(alcaldia);
CREATE INDEX IF NOT EXISTS idx_direcciones_usuario ON direcciones_corregidas(usuario_revision_id);

-- Trigger para actualizar fecha_modificacion
CREATE OR REPLACE FUNCTION update_direcciones_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_modificacion = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_direcciones_updated_at ON direcciones_corregidas;
CREATE TRIGGER trigger_update_direcciones_updated_at
    BEFORE UPDATE ON direcciones_corregidas
    FOR EACH ROW
    EXECUTE FUNCTION update_direcciones_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE direcciones_corregidas IS 'Direcciones detectadas y corregidas con validación SEPOMEX';
COMMENT ON COLUMN direcciones_corregidas.texto_original IS 'Texto original extraído por OCR';
COMMENT ON COLUMN direcciones_corregidas.validada_sepomex IS 'Indica si la dirección fue validada con el servicio SEPOMEX';
COMMENT ON COLUMN direcciones_corregidas.editada_manualmente IS 'Indica si un usuario editó manualmente la dirección';
COMMENT ON COLUMN direcciones_corregidas.ignorada IS 'Marca la dirección como ignorada para no procesarla';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
