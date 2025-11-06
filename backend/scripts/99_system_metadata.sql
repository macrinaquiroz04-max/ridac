-- Script de metadatos de autoría del sistema
-- Desarrollador: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: Octubre 2025
-- Este script inserta metadata de autoría en la base de datos

-- Crear tabla de metadata del sistema (oculta)
CREATE TABLE IF NOT EXISTS _system_metadata (
    id SERIAL PRIMARY KEY,
    metadata_key VARCHAR(100) UNIQUE NOT NULL,
    metadata_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_protected BOOLEAN DEFAULT TRUE
);

-- Insertar datos de autoría (inmutables)
INSERT INTO _system_metadata (metadata_key, metadata_value, is_protected) VALUES
    ('system.author', 'Eduardo Lozada Quiroz', TRUE),
    ('system.author_title', 'Ingeniero en Sistemas Computacionales', TRUE),
    ('system.client', 'Unidad de Análisis y Contexto (UAyC)', TRUE),
    ('system.institution', 'Fiscalía General de Justicia CDMX', TRUE),
    ('system.creation_date', '2025-10-20', TRUE),
    ('system.version', '1.0.0', TRUE),
    ('system.signature', 'ELQ_ISC_UAYC_OCT2025', TRUE),
    ('system.copyright', '© 2025 Eduardo Lozada Quiroz - Todos los derechos reservados', TRUE),
    ('system.contact', 'aduardolozada1958@gmail.com', TRUE),
    ('system.license', 'Propietario - Uso exclusivo UAyC', TRUE)
ON CONFLICT (metadata_key) DO NOTHING;

-- Crear función que impide eliminar metadata de autoría
CREATE OR REPLACE FUNCTION protect_system_metadata()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_protected = TRUE THEN
        RAISE EXCEPTION 'No se puede eliminar metadata protegida del sistema. Autor: Eduardo Lozada Quiroz, ISC';
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Trigger para proteger metadata
DROP TRIGGER IF EXISTS prevent_metadata_deletion ON _system_metadata;
CREATE TRIGGER prevent_metadata_deletion
    BEFORE DELETE ON _system_metadata
    FOR EACH ROW
    EXECUTE FUNCTION protect_system_metadata();

-- Comentarios en la tabla (metadata adicional)
COMMENT ON TABLE _system_metadata IS 'Metadata del sistema - Desarrollado por Eduardo Lozada Quiroz (ISC) para UAyC';
COMMENT ON COLUMN _system_metadata.metadata_key IS 'Clave de metadata - Sistema creado por E.L.Q';
COMMENT ON COLUMN _system_metadata.metadata_value IS 'Valor de metadata';
COMMENT ON COLUMN _system_metadata.is_protected IS 'Protección contra eliminación - Autor: ELQ';

-- Crear índice
CREATE INDEX IF NOT EXISTS idx_system_metadata_key ON _system_metadata(metadata_key);

-- Grant de permisos (solo lectura para usuarios normales)
-- REVOKE DELETE ON _system_metadata FROM PUBLIC;

-- Agregar comentario al esquema principal
COMMENT ON SCHEMA public IS 'Sistema OCR - Autor: Eduardo Lozada Quiroz, ISC - Cliente: UAyC - Año: 2025';
