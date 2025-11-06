-- Script SQL para crear tablas de análisis jurídico
-- Sistema de extracción OCR y análisis de documentos legales mexicanos

-- Tabla de diligencias
CREATE TABLE IF NOT EXISTS diligencias (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    carpeta_id INTEGER NOT NULL REFERENCES carpetas(id) ON DELETE CASCADE,
    
    -- Información de la diligencia
    tipo_diligencia VARCHAR(200) NOT NULL,
    fecha_diligencia DATE,
    fecha_diligencia_texto VARCHAR(100),
    responsable VARCHAR(300),
    numero_oficio VARCHAR(100),
    
    -- Contexto
    descripcion TEXT,
    texto_contexto TEXT,
    numero_pagina INTEGER,
    
    -- Metadatos de extracción
    confianza FLOAT DEFAULT 0.0,
    verificado BOOLEAN DEFAULT FALSE,
    corregido_por_id INTEGER REFERENCES usuarios(id),
    
    -- Ordenamiento
    orden_cronologico INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_diligencia_tomo ON diligencias(tomo_id);
CREATE INDEX idx_diligencia_carpeta ON diligencias(carpeta_id);
CREATE INDEX idx_diligencia_tipo ON diligencias(tipo_diligencia);
CREATE INDEX idx_diligencia_fecha ON diligencias(fecha_diligencia);
CREATE INDEX idx_diligencia_carpeta_fecha ON diligencias(carpeta_id, fecha_diligencia);
CREATE INDEX idx_diligencia_tipo_fecha ON diligencias(tipo_diligencia, fecha_diligencia);
CREATE INDEX idx_diligencia_oficio ON diligencias(numero_oficio);
CREATE INDEX idx_diligencia_orden ON diligencias(orden_cronologico);


-- Tabla de personas identificadas
CREATE TABLE IF NOT EXISTS personas_identificadas (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    carpeta_id INTEGER NOT NULL REFERENCES carpetas(id) ON DELETE CASCADE,
    
    -- Información personal
    nombre_completo VARCHAR(500) NOT NULL,
    nombre_normalizado VARCHAR(500),
    alias VARCHAR(300),
    
    -- Datos de contacto
    direccion TEXT,
    colonia VARCHAR(200),
    municipio VARCHAR(200),
    estado VARCHAR(100),
    codigo_postal VARCHAR(10),
    telefono VARCHAR(100),
    telefono_adicional VARCHAR(100),
    
    -- Rol en el caso
    rol VARCHAR(100),
    
    -- Estadísticas
    total_menciones INTEGER DEFAULT 0,
    total_declaraciones INTEGER DEFAULT 0,
    
    -- Contexto
    primera_mencion_pagina INTEGER,
    texto_contexto TEXT,
    
    -- Metadatos
    confianza FLOAT DEFAULT 0.0,
    verificado BOOLEAN DEFAULT FALSE,
    corregido_por_id INTEGER REFERENCES usuarios(id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_persona_tomo ON personas_identificadas(tomo_id);
CREATE INDEX idx_persona_carpeta ON personas_identificadas(carpeta_id);
CREATE INDEX idx_persona_nombre ON personas_identificadas(nombre_completo);
CREATE INDEX idx_persona_normalizado ON personas_identificadas(nombre_normalizado);
CREATE INDEX idx_persona_rol ON personas_identificadas(rol);
CREATE INDEX idx_persona_carpeta_nombre ON personas_identificadas(carpeta_id, nombre_normalizado);
CREATE INDEX idx_persona_carpeta_rol ON personas_identificadas(carpeta_id, rol);


-- Tabla de declaraciones de personas
CREATE TABLE IF NOT EXISTS declaraciones_personas (
    id SERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL REFERENCES personas_identificadas(id) ON DELETE CASCADE,
    diligencia_id INTEGER REFERENCES diligencias(id) ON DELETE SET NULL,
    
    fecha_declaracion DATE,
    tipo_declaracion VARCHAR(100),
    numero_pagina INTEGER,
    resumen TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_declaracion_persona ON declaraciones_personas(persona_id);
CREATE INDEX idx_declaracion_fecha ON declaraciones_personas(fecha_declaracion);
CREATE INDEX idx_declaracion_persona_fecha ON declaraciones_personas(persona_id, fecha_declaracion);


-- Tabla de lugares identificados
CREATE TABLE IF NOT EXISTS lugares_identificados (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    carpeta_id INTEGER NOT NULL REFERENCES carpetas(id) ON DELETE CASCADE,
    
    -- Información del lugar
    nombre_lugar TEXT NOT NULL,
    tipo_lugar VARCHAR(100),
    direccion_completa TEXT,
    
    -- Componentes de dirección
    calle VARCHAR(300),
    numero VARCHAR(50),
    colonia VARCHAR(200),
    municipio VARCHAR(200),
    estado VARCHAR(100),
    codigo_postal VARCHAR(10),
    
    -- Contexto
    contexto TEXT,
    tipo_relevancia VARCHAR(100),
    frecuencia_menciones INTEGER DEFAULT 0,
    numero_pagina INTEGER,
    
    -- Coordenadas
    latitud FLOAT,
    longitud FLOAT,
    
    -- Metadatos
    confianza FLOAT DEFAULT 0.0,
    verificado BOOLEAN DEFAULT FALSE,
    corregido_por_id INTEGER REFERENCES usuarios(id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lugar_tomo ON lugares_identificados(tomo_id);
CREATE INDEX idx_lugar_carpeta ON lugares_identificados(carpeta_id);
CREATE INDEX idx_lugar_tipo ON lugares_identificados(tipo_lugar);
CREATE INDEX idx_lugar_carpeta_tipo ON lugares_identificados(carpeta_id, tipo_lugar);


-- Tabla de fechas importantes
CREATE TABLE IF NOT EXISTS fechas_importantes (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    carpeta_id INTEGER NOT NULL REFERENCES carpetas(id) ON DELETE CASCADE,
    
    -- Información de la fecha
    fecha DATE NOT NULL,
    fecha_texto_original VARCHAR(200),
    tipo_fecha VARCHAR(100),
    
    -- Descripción
    descripcion TEXT NOT NULL,
    texto_contexto TEXT,
    numero_pagina INTEGER,
    
    -- Clasificación
    es_actuacion_mp BOOLEAN DEFAULT FALSE,
    es_fecha_hechos BOOLEAN DEFAULT FALSE,
    es_audiencia BOOLEAN DEFAULT FALSE,
    
    -- Metadatos
    confianza FLOAT DEFAULT 0.0,
    verificado BOOLEAN DEFAULT FALSE,
    corregido_por_id INTEGER REFERENCES usuarios(id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fecha_tomo ON fechas_importantes(tomo_id);
CREATE INDEX idx_fecha_carpeta ON fechas_importantes(carpeta_id);
CREATE INDEX idx_fecha_fecha ON fechas_importantes(fecha);
CREATE INDEX idx_fecha_tipo ON fechas_importantes(tipo_fecha);
CREATE INDEX idx_fecha_actuacion_mp ON fechas_importantes(es_actuacion_mp);
CREATE INDEX idx_fecha_carpeta_tipo ON fechas_importantes(carpeta_id, fecha, tipo_fecha);


-- Tabla de alertas del MP
CREATE TABLE IF NOT EXISTS alertas_mp (
    id SERIAL PRIMARY KEY,
    carpeta_id INTEGER NOT NULL REFERENCES carpetas(id) ON DELETE CASCADE,
    
    -- Tipo de alerta
    tipo_alerta VARCHAR(100) NOT NULL,
    prioridad VARCHAR(20) DEFAULT 'media',
    
    -- Descripción
    titulo VARCHAR(300) NOT NULL,
    descripcion TEXT NOT NULL,
    
    -- Datos de inactividad
    fecha_ultima_actuacion DATE,
    fecha_siguiente_esperada DATE,
    dias_inactividad INTEGER DEFAULT 0,
    
    -- Diligencias relacionadas
    ultima_diligencia_id INTEGER REFERENCES diligencias(id) ON DELETE SET NULL,
    
    -- Estado
    estado VARCHAR(50) DEFAULT 'activa',
    resuelta_fecha TIMESTAMP,
    resuelta_por_id INTEGER REFERENCES usuarios(id),
    notas_resolucion TEXT,
    
    -- Notificaciones
    notificada BOOLEAN DEFAULT FALSE,
    fecha_notificacion TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerta_carpeta ON alertas_mp(carpeta_id);
CREATE INDEX idx_alerta_tipo ON alertas_mp(tipo_alerta);
CREATE INDEX idx_alerta_prioridad ON alertas_mp(prioridad);
CREATE INDEX idx_alerta_estado ON alertas_mp(estado);
CREATE INDEX idx_alerta_dias ON alertas_mp(dias_inactividad);
CREATE INDEX idx_alerta_carpeta_prioridad ON alertas_mp(carpeta_id, prioridad, estado);
CREATE INDEX idx_alerta_estado_fecha ON alertas_mp(estado, created_at);
CREATE INDEX idx_alerta_created ON alertas_mp(created_at);


-- Tabla de estadísticas de carpetas
CREATE TABLE IF NOT EXISTS estadisticas_carpetas (
    id SERIAL PRIMARY KEY,
    carpeta_id INTEGER NOT NULL UNIQUE REFERENCES carpetas(id) ON DELETE CASCADE,
    
    -- Contadores generales
    total_diligencias INTEGER DEFAULT 0,
    total_personas INTEGER DEFAULT 0,
    total_lugares INTEGER DEFAULT 0,
    total_fechas INTEGER DEFAULT 0,
    total_alertas_activas INTEGER DEFAULT 0,
    
    -- Estadísticas de tiempo
    fecha_primera_actuacion DATE,
    fecha_ultima_actuacion DATE,
    dias_totales_investigacion INTEGER DEFAULT 0,
    promedio_dias_entre_actuaciones FLOAT DEFAULT 0.0,
    
    -- Contadores por tipo
    total_declaraciones INTEGER DEFAULT 0,
    total_pericias INTEGER DEFAULT 0,
    total_comparecencias INTEGER DEFAULT 0,
    total_oficios INTEGER DEFAULT 0,
    
    -- Calidad de datos
    porcentaje_verificado FLOAT DEFAULT 0.0,
    confianza_promedio FLOAT DEFAULT 0.0,
    
    -- Actualización
    ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_por_id INTEGER REFERENCES usuarios(id)
);

CREATE INDEX idx_estadistica_carpeta ON estadisticas_carpetas(carpeta_id);


-- Triggers para actualizar timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_diligencias_updated_at BEFORE UPDATE ON diligencias
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_personas_updated_at BEFORE UPDATE ON personas_identificadas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lugares_updated_at BEFORE UPDATE ON lugares_identificados
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fechas_updated_at BEFORE UPDATE ON fechas_importantes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alertas_updated_at BEFORE UPDATE ON alertas_mp
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Comentarios en las tablas
COMMENT ON TABLE diligencias IS 'Diligencias extraídas de documentos jurídicos';
COMMENT ON TABLE personas_identificadas IS 'Personas identificadas en expedientes con datos de contacto';
COMMENT ON TABLE declaraciones_personas IS 'Registro de declaraciones de cada persona';
COMMENT ON TABLE lugares_identificados IS 'Lugares y direcciones mencionados en documentos';
COMMENT ON TABLE fechas_importantes IS 'Fechas relevantes de actuaciones y narrativas';
COMMENT ON TABLE alertas_mp IS 'Alertas de inactividad e irregularidades del Ministerio Público';
COMMENT ON TABLE estadisticas_carpetas IS 'Estadísticas generales de carpetas de investigación';
