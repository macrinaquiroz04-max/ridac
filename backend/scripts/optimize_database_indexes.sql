-- OPTIMIZACIÓN CRÍTICA DE ÍNDICES PARA OCR
-- Estos índices mejorarán dramáticamente el rendimiento

-- Índice compuesto para búsquedas rápidas de páginas procesadas
CREATE INDEX IF NOT EXISTS idx_contenido_ocr_tomo_pagina ON contenido_ocr(tomo_id, numero_pagina);

-- Índice para filtrar por confianza (búsquedas de calidad)
CREATE INDEX IF NOT EXISTS idx_contenido_ocr_confianza ON contenido_ocr(confianza) WHERE confianza IS NOT NULL;

-- Índice para búsquedas de texto (PostgreSQL full-text search)
CREATE INDEX IF NOT EXISTS idx_contenido_ocr_texto_search ON contenido_ocr USING GIN(to_tsvector('spanish', texto_extraido));

-- Índice para estado de tomos (procesar solo pendientes)
CREATE INDEX IF NOT EXISTS idx_tomos_estado ON tomos(estado) WHERE estado IN ('pendiente', 'procesando');

-- Índice para fechas de procesamiento (análisis temporal)
CREATE INDEX IF NOT EXISTS idx_contenido_ocr_created_at ON contenido_ocr(created_at);

-- Índice para datos adicionales JSONB (motores OCR)
CREATE INDEX IF NOT EXISTS idx_contenido_ocr_motor ON contenido_ocr USING GIN((datos_adicionales->'motor'));

-- Particionado de tabla grande (si hay millones de registros)
-- CREATE TABLE contenido_ocr_2024 PARTITION OF contenido_ocr FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

ANALYZE contenido_ocr;
ANALYZE tomos;