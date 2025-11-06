-- ============================================================================
-- Script SQL para actualizar tabla auditoria
-- Sistema OCR - FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 29 de Octubre de 2025
-- ============================================================================

-- Tabla de auditoría del sistema (estructura actualizada)
CREATE TABLE IF NOT EXISTS auditoria (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    accion VARCHAR(100) NOT NULL,
    tabla_afectada VARCHAR(50),
    registro_id INTEGER,
    valores_anteriores JSONB,
    valores_nuevos JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_id ON auditoria(usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria(created_at);
CREATE INDEX IF NOT EXISTS idx_auditoria_accion ON auditoria(accion);
CREATE INDEX IF NOT EXISTS idx_auditoria_tabla ON auditoria(tabla_afectada);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_fecha ON auditoria(usuario_id, created_at);
CREATE INDEX IF NOT EXISTS idx_auditoria_tabla_registro ON auditoria(tabla_afectada, registro_id);

-- Índice GIN para búsquedas en campos JSONB
CREATE INDEX IF NOT EXISTS idx_auditoria_valores_anteriores ON auditoria USING GIN(valores_anteriores);
CREATE INDEX IF NOT EXISTS idx_auditoria_valores_nuevos ON auditoria USING GIN(valores_nuevos);

-- Comentarios para documentación
COMMENT ON TABLE auditoria IS 'Registro completo de auditoría del sistema con seguimiento de cambios';
COMMENT ON COLUMN auditoria.accion IS 'Acción realizada: LOGIN_EXITOSO, CREAR_USUARIO, EDITAR_TOMO, OCR_AREA_EXTRAIDO, etc.';
COMMENT ON COLUMN auditoria.tabla_afectada IS 'Tabla afectada por la acción';
COMMENT ON COLUMN auditoria.registro_id IS 'ID del registro afectado';
COMMENT ON COLUMN auditoria.valores_anteriores IS 'Valores antes del cambio en formato JSON';
COMMENT ON COLUMN auditoria.valores_nuevos IS 'Valores después del cambio en formato JSON';
COMMENT ON COLUMN auditoria.ip_address IS 'Dirección IP del usuario que realizó la acción';
COMMENT ON COLUMN auditoria.user_agent IS 'User agent del navegador utilizado';

-- ============================================================================
-- TIPOS DE ACCIONES COMUNES EN EL SISTEMA
-- ============================================================================
-- Autenticación:
--   - LOGIN_EXITOSO, LOGIN_FALLIDO, LOGOUT
-- Usuarios:
--   - CREAR_USUARIO, EDITAR_USUARIO, ELIMINAR_USUARIO, CAMBIAR_PASSWORD
-- Carpetas:
--   - CREAR_CARPETA, EDITAR_CARPETA, ELIMINAR_CARPETA
-- Tomos:
--   - SUBIR_TOMO, EDITAR_TOMO, ELIMINAR_TOMO, PROCESAR_TOMO_OCR
-- Permisos:
--   - ASIGNAR_PERMISO, REVOCAR_PERMISO, EDITAR_PERMISO
-- Búsquedas:
--   - BUSQUEDA_TEXTO, BUSQUEDA_SEMANTICA, BUSQUEDA_CRONOLOGICA
-- OCR y Análisis:
--   - OCR_AREA_EXTRAIDO (Google Lens), ANALISIS_IA_EJECUTADO
-- Auditoría:
--   - ACCEDER_AUDITORIA, EXPORTAR_AUDITORIA
-- Notificaciones:
--   - CREAR_NOTIFICACION, MARCAR_LEIDA_NOTIFICACION

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
