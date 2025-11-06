-- ============================================================================
-- Script SQL para crear tabla permisos_tomo
-- Sistema OCR - FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 29 de Octubre de 2025
-- ============================================================================

-- Tabla de permisos específicos por tomo
CREATE TABLE IF NOT EXISTS permisos_tomo (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    
    -- Permisos individuales
    puede_ver BOOLEAN DEFAULT TRUE,
    puede_buscar BOOLEAN DEFAULT FALSE,
    puede_ver_sellos BOOLEAN DEFAULT FALSE,
    puede_extraer_texto BOOLEAN DEFAULT FALSE,
    busqueda_cronologica BOOLEAN DEFAULT FALSE,
    puede_exportar BOOLEAN DEFAULT FALSE,
    
    -- Periodo de acceso (opcional)
    fecha_inicio_acceso TIMESTAMP WITH TIME ZONE,
    fecha_fin_acceso TIMESTAMP WITH TIME ZONE,
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraint para evitar duplicados
    CONSTRAINT uq_usuario_tomo UNIQUE(usuario_id, tomo_id)
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_permisos_tomo_usuario ON permisos_tomo(usuario_id);
CREATE INDEX IF NOT EXISTS idx_permisos_tomo_tomo ON permisos_tomo(tomo_id);
CREATE INDEX IF NOT EXISTS idx_permisos_tomo_usuario_tomo ON permisos_tomo(usuario_id, tomo_id);
CREATE INDEX IF NOT EXISTS idx_permisos_tomo_puede_ver ON permisos_tomo(puede_ver);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_permisos_tomo_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_permisos_tomo_updated_at ON permisos_tomo;
CREATE TRIGGER trigger_update_permisos_tomo_updated_at
    BEFORE UPDATE ON permisos_tomo
    FOR EACH ROW
    EXECUTE FUNCTION update_permisos_tomo_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE permisos_tomo IS 'Permisos específicos de usuarios sobre tomos individuales';
COMMENT ON COLUMN permisos_tomo.puede_ver IS 'Permite ver y visualizar el tomo';
COMMENT ON COLUMN permisos_tomo.puede_buscar IS 'Permite buscar en el contenido OCR del tomo';
COMMENT ON COLUMN permisos_tomo.puede_ver_sellos IS 'Permite ver sellos en vista previa';
COMMENT ON COLUMN permisos_tomo.puede_extraer_texto IS 'Permite extraer texto específico';
COMMENT ON COLUMN permisos_tomo.busqueda_cronologica IS 'Permite realizar búsqueda cronológica';
COMMENT ON COLUMN permisos_tomo.puede_exportar IS 'Permite exportar el tomo (solo administradores)';
COMMENT ON COLUMN permisos_tomo.fecha_inicio_acceso IS 'Fecha de inicio del periodo de acceso';
COMMENT ON COLUMN permisos_tomo.fecha_fin_acceso IS 'Fecha de fin del periodo de acceso';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
