-- ============================================================================
-- Script SQL para crear tabla notificaciones
-- Sistema OCR - FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 29 de Octubre de 2025
-- ============================================================================

-- Tabla de notificaciones para usuarios
CREATE TABLE IF NOT EXISTS notificaciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    
    -- Contenido de la notificación
    titulo VARCHAR(255) NOT NULL,
    mensaje TEXT NOT NULL,
    tipo VARCHAR(50) DEFAULT 'info', -- info, warning, error, success, TOMO_ELIMINADO, CARPETA_ELIMINADA
    
    -- Estado
    leida BOOLEAN DEFAULT FALSE,
    leida_at TIMESTAMP WITH TIME ZONE,
    
    -- Acción relacionada
    url_accion VARCHAR(500),
    datos_extra JSONB, -- Información adicional en formato JSON
    
    -- Auditoría
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario ON notificaciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_notificaciones_leida ON notificaciones(leida);
CREATE INDEX IF NOT EXISTS idx_notificaciones_created ON notificaciones(created_at);
CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario_leida ON notificaciones(usuario_id, leida);
CREATE INDEX IF NOT EXISTS idx_notificaciones_tipo ON notificaciones(tipo);

-- Comentarios para documentación
COMMENT ON TABLE notificaciones IS 'Notificaciones del sistema para usuarios';
COMMENT ON COLUMN notificaciones.tipo IS 'Tipo de notificación: info, warning, error, success, TOMO_ELIMINADO, CARPETA_ELIMINADA';
COMMENT ON COLUMN notificaciones.datos_extra IS 'Información adicional en formato JSON';
COMMENT ON COLUMN notificaciones.url_accion IS 'URL opcional para redirigir al hacer clic';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
