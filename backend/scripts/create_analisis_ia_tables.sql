-- Migración para agregar tablas de análisis IA
-- Archivo: create_analisis_ia_tables.sql

-- Tabla principal de análisis IA
CREATE TABLE IF NOT EXISTS analisis_ia (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    fecha_analisis TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    resultados_json TEXT NOT NULL,
    estado VARCHAR(50) DEFAULT 'pendiente' NOT NULL,
    tiempo_procesamiento INTEGER,
    version_algoritmo VARCHAR(20) DEFAULT '1.0',
    
    -- Campos específicos extraídos para consultas rápidas
    total_diligencias INTEGER DEFAULT 0,
    total_personas INTEGER DEFAULT 0,
    total_lugares INTEGER DEFAULT 0,
    total_alertas INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de resultados detallados del análisis
CREATE TABLE IF NOT EXISTS resultados_analisis (
    id SERIAL PRIMARY KEY,
    analisis_id INTEGER NOT NULL REFERENCES analisis_ia(id) ON DELETE CASCADE,
    tipo_resultado VARCHAR(50) NOT NULL, -- diligencia, persona, lugar, alerta
    
    -- Campos genéricos
    nombre VARCHAR(255),
    descripcion TEXT,
    fecha VARCHAR(20),
    datos_json TEXT,
    
    -- Campos específicos por tipo
    -- Para diligencias
    tipo_diligencia VARCHAR(100),
    responsable VARCHAR(255),
    oficio VARCHAR(100),
    
    -- Para personas
    direccion TEXT,
    telefono VARCHAR(50),
    num_declaraciones INTEGER,
    
    -- Para lugares
    tipo_lugar VARCHAR(100),
    contexto VARCHAR(255),
    frecuencia INTEGER,
    
    -- Para alertas
    prioridad VARCHAR(20), -- baja, media, alta
    dias_transcurridos INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de métricas de análisis
CREATE TABLE IF NOT EXISTS metricas_analisis (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    
    -- Métricas de uso
    total_analisis_realizados INTEGER DEFAULT 0,
    tiempo_promedio_analisis INTEGER DEFAULT 0, -- en segundos
    tomos_analizados INTEGER DEFAULT 0,
    
    -- Métricas de resultados
    diligencias_encontradas INTEGER DEFAULT 0,
    personas_identificadas INTEGER DEFAULT 0,
    lugares_detectados INTEGER DEFAULT 0,
    alertas_generadas INTEGER DEFAULT 0,
    
    -- Métricas de calidad
    precision_estimada INTEGER DEFAULT 0, -- porcentaje
    casos_verificados INTEGER DEFAULT 0,
    casos_correctos INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_analisis_tomo_fecha ON analisis_ia(tomo_id, fecha_analisis);
CREATE INDEX IF NOT EXISTS idx_analisis_usuario_fecha ON analisis_ia(usuario_id, fecha_analisis);
CREATE INDEX IF NOT EXISTS idx_analisis_estado ON analisis_ia(estado);

CREATE INDEX IF NOT EXISTS idx_resultado_analisis_tipo ON resultados_analisis(analisis_id, tipo_resultado);
CREATE INDEX IF NOT EXISTS idx_resultado_tipo ON resultados_analisis(tipo_resultado);
CREATE INDEX IF NOT EXISTS idx_resultado_prioridad ON resultados_analisis(prioridad);

CREATE INDEX IF NOT EXISTS idx_metricas_usuario_fecha ON metricas_analisis(usuario_id, fecha);

-- Trigger para actualizar updated_at en analisis_ia
CREATE OR REPLACE FUNCTION update_analisis_ia_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS trigger_update_analisis_ia_updated_at ON analisis_ia;
CREATE TRIGGER trigger_update_analisis_ia_updated_at
    BEFORE UPDATE ON analisis_ia
    FOR EACH ROW
    EXECUTE FUNCTION update_analisis_ia_updated_at();

-- Comentarios para documentación
COMMENT ON TABLE analisis_ia IS 'Tabla principal para almacenar análisis de IA realizados sobre tomos';
COMMENT ON TABLE resultados_analisis IS 'Tabla detallada con los resultados específicos extraídos del análisis';
COMMENT ON TABLE metricas_analisis IS 'Tabla para tracking de métricas y estadísticas de uso del sistema de análisis';

COMMENT ON COLUMN analisis_ia.resultados_json IS 'JSON completo con todos los resultados del análisis';
COMMENT ON COLUMN analisis_ia.estado IS 'Estado del análisis: pendiente, procesando, completado, error';
COMMENT ON COLUMN analisis_ia.tiempo_procesamiento IS 'Tiempo en segundos que tomó el análisis completo';

COMMENT ON COLUMN resultados_analisis.tipo_resultado IS 'Tipo de resultado: diligencia, persona, lugar, alerta';
COMMENT ON COLUMN resultados_analisis.datos_json IS 'Datos específicos del resultado en formato JSON';

-- Insertar datos de ejemplo (opcional para testing)
-- INSERT INTO analisis_ia (tomo_id, usuario_id, resultados_json, estado, total_diligencias, total_personas, total_lugares, total_alertas)
-- VALUES (1, 1, '{"ejemplo": "datos"}', 'completado', 3, 5, 2, 1);