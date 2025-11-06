-- Migración para crear tabla documentos_ocr
-- Fecha: 2025-10-05
-- Descripción: Tabla para almacenar documentos extraídos con OCR

CREATE TABLE IF NOT EXISTS documentos_ocr (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    contenido TEXT NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(50) DEFAULT 'ocr_extract',
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_modificacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_eliminacion TIMESTAMP WITH TIME ZONE,
    activo BOOLEAN DEFAULT TRUE
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_documentos_ocr_tomo_id ON documentos_ocr(tomo_id);
CREATE INDEX IF NOT EXISTS idx_documentos_ocr_usuario_id ON documentos_ocr(usuario_id);
CREATE INDEX IF NOT EXISTS idx_documentos_ocr_activo ON documentos_ocr(activo);
CREATE INDEX IF NOT EXISTS idx_documentos_ocr_fecha_creacion ON documentos_ocr(fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_documentos_ocr_tipo ON documentos_ocr(tipo);

-- Índice para búsqueda de texto completo
CREATE INDEX IF NOT EXISTS idx_documentos_ocr_contenido_gin ON documentos_ocr USING gin(to_tsvector('spanish', contenido));
CREATE INDEX IF NOT EXISTS idx_documentos_ocr_nombre_gin ON documentos_ocr USING gin(to_tsvector('spanish', nombre));

-- Trigger para actualizar fecha_modificacion
CREATE OR REPLACE FUNCTION update_documentos_ocr_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_modificacion = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_documentos_ocr_updated_at_trigger
    BEFORE UPDATE ON documentos_ocr
    FOR EACH ROW
    EXECUTE FUNCTION update_documentos_ocr_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE documentos_ocr IS 'Documentos extraídos con tecnología OCR';
COMMENT ON COLUMN documentos_ocr.tomo_id IS 'ID del tomo al que pertenece el documento';
COMMENT ON COLUMN documentos_ocr.usuario_id IS 'ID del usuario que creó el documento';
COMMENT ON COLUMN documentos_ocr.nombre IS 'Nombre descriptivo del documento';
COMMENT ON COLUMN documentos_ocr.contenido IS 'Texto extraído del documento';
COMMENT ON COLUMN documentos_ocr.descripcion IS 'Descripción opcional del contenido';
COMMENT ON COLUMN documentos_ocr.tipo IS 'Tipo de documento: ocr_extract, manual_upload, etc.';
COMMENT ON COLUMN documentos_ocr.activo IS 'Indica si el documento está activo (soft delete)';

COMMIT;