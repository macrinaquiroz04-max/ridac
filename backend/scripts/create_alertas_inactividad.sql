-- ============================================================================
-- Script SQL para crear tabla alertas_inactividad
-- Sistema OCR - FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 29 de Octubre de 2025
-- ============================================================================

-- Tabla para alertas de inactividad en tomos
CREATE TABLE IF NOT EXISTS alertas_inactividad (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER REFERENCES tomos(id) ON DELETE CASCADE,
    ultima_diligencia TIMESTAMP WITH TIME ZONE,
    dias_inactividad INTEGER,
    estado VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS ix_alertas_inactividad_id ON alertas_inactividad(id);
CREATE INDEX IF NOT EXISTS idx_alertas_inactividad_tomo ON alertas_inactividad(tomo_id);
CREATE INDEX IF NOT EXISTS idx_alertas_inactividad_estado ON alertas_inactividad(estado);
CREATE INDEX IF NOT EXISTS idx_alertas_inactividad_dias ON alertas_inactividad(dias_inactividad);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_alertas_inactividad_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_alertas_inactividad_updated_at ON alertas_inactividad;
CREATE TRIGGER trigger_update_alertas_inactividad_updated_at
    BEFORE UPDATE ON alertas_inactividad
    FOR EACH ROW
    EXECUTE FUNCTION update_alertas_inactividad_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE alertas_inactividad IS 'Alertas de inactividad en tomos basadas en días sin diligencias';
COMMENT ON COLUMN alertas_inactividad.ultima_diligencia IS 'Fecha de la última diligencia registrada';
COMMENT ON COLUMN alertas_inactividad.dias_inactividad IS 'Número de días transcurridos sin actividad';
COMMENT ON COLUMN alertas_inactividad.estado IS 'Estado de la alerta: activa, resuelta, etc.';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
