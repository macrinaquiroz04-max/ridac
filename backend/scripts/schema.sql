-- ============================================================================
-- Sistema OCR - Schema SQL
-- Base de datos: sistema_ocr
-- Encoding: UTF-8
-- ============================================================================

-- Configuración inicial UTF-8
SET client_encoding = 'UTF8';

-- Eliminar base de datos si existe y crear nueva
DROP DATABASE IF EXISTS sistema_ocr;
CREATE DATABASE sistema_ocr
    WITH
    ENCODING = 'UTF8'
    LC_COLLATE = 'es_MX.UTF-8'
    LC_CTYPE = 'es_MX.UTF-8'
    TEMPLATE = template0;

\c sistema_ocr

SET client_encoding = 'UTF8';

-- ============================================================================
-- TABLA: roles
-- Descripción: Define los roles de usuario en el sistema
-- ============================================================================
DROP TABLE IF EXISTS roles CASCADE;
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar roles predefinidos
INSERT INTO roles (nombre, descripcion) VALUES
    ('Admin', 'Administrador del sistema con acceso completo'),
    ('Director', 'Director con permisos de supervisión y gestión'),
    ('Subdirector', 'Subdirector con permisos de gestión limitada'),
    ('analista', 'Usuario analista con permisos básicos');

-- ============================================================================
-- TABLA: usuarios
-- Descripción: Almacena información de usuarios del sistema
-- ============================================================================
DROP TABLE IF EXISTS usuarios CASCADE;
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    nombre_completo VARCHAR(200),
    rol_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    activo BOOLEAN DEFAULT TRUE,
    ultimo_acceso TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLA: tokens_reset
-- Descripción: Tokens para reseteo de contraseña
-- ============================================================================
DROP TABLE IF EXISTS tokens_reset CASCADE;
CREATE TABLE tokens_reset (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expiracion TIMESTAMP NOT NULL,
    usado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLA: carpetas
-- Descripción: Carpetas o expedientes principales
-- ============================================================================
DROP TABLE IF EXISTS carpetas CASCADE;
CREATE TABLE carpetas (
    id SERIAL PRIMARY KEY,
    numero_expediente VARCHAR(100) NOT NULL UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    ubicacion_fisica VARCHAR(255),
    anio INTEGER,
    estado VARCHAR(50) DEFAULT 'activo',
    usuario_creador_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLA: tomos
-- Descripción: Tomos asociados a carpetas (archivos PDF)
-- ============================================================================
DROP TABLE IF EXISTS tomos CASCADE;
CREATE TABLE tomos (
    id SERIAL PRIMARY KEY,
    carpeta_id INTEGER NOT NULL REFERENCES carpetas(id) ON DELETE CASCADE,
    numero_tomo INTEGER NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo VARCHAR(500) NOT NULL,
    tamanio_bytes BIGINT,
    numero_paginas INTEGER,
    estado VARCHAR(50) DEFAULT 'pendiente', -- pendiente, procesando, completado, error
    fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_procesamiento TIMESTAMP,
    usuario_subida_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(carpeta_id, numero_tomo)
);

-- ============================================================================
-- TABLA: contenido_ocr
-- Descripción: Almacena el contenido extraído por OCR
-- ============================================================================
DROP TABLE IF EXISTS contenido_ocr CASCADE;
CREATE TABLE contenido_ocr (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    numero_pagina INTEGER NOT NULL,
    texto_extraido TEXT,
    confianza DECIMAL(5,2), -- Porcentaje de confianza del OCR
    datos_adicionales JSONB, -- Información adicional (coordenadas, idioma detectado, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tomo_id, numero_pagina)
);

-- ============================================================================
-- TABLA: tareas_ocr
-- Descripción: Cola de tareas para procesamiento OCR
-- ============================================================================
DROP TABLE IF EXISTS tareas_ocr CASCADE;
CREATE TABLE tareas_ocr (
    id SERIAL PRIMARY KEY,
    tomo_id INTEGER NOT NULL REFERENCES tomos(id) ON DELETE CASCADE,
    estado VARCHAR(50) DEFAULT 'pendiente', -- pendiente, en_proceso, completado, error
    prioridad INTEGER DEFAULT 5, -- 1 (más alta) a 10 (más baja)
    intentos INTEGER DEFAULT 0,
    max_intentos INTEGER DEFAULT 3,
    error_mensaje TEXT,
    fecha_inicio TIMESTAMP,
    fecha_fin TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLA: permisos_carpeta
-- Descripción: Permisos de usuarios sobre carpetas específicas
-- ============================================================================
DROP TABLE IF EXISTS permisos_carpeta CASCADE;
CREATE TABLE permisos_carpeta (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    carpeta_id INTEGER NOT NULL REFERENCES carpetas(id) ON DELETE CASCADE,
    puede_leer BOOLEAN DEFAULT TRUE,
    puede_escribir BOOLEAN DEFAULT FALSE,
    puede_eliminar BOOLEAN DEFAULT FALSE,
    puede_compartir BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, carpeta_id)
);

-- ============================================================================
-- TABLA: permisos_sistema
-- Descripción: Permisos generales del sistema por usuario
-- ============================================================================
DROP TABLE IF EXISTS permisos_sistema CASCADE;
CREATE TABLE permisos_sistema (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    gestionar_usuarios BOOLEAN DEFAULT FALSE,
    gestionar_roles BOOLEAN DEFAULT FALSE,
    gestionar_carpetas BOOLEAN DEFAULT FALSE,
    procesar_ocr BOOLEAN DEFAULT FALSE,
    ver_auditoria BOOLEAN DEFAULT FALSE,
    configurar_sistema BOOLEAN DEFAULT FALSE,
    exportar_datos BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLA: auditoria
-- Descripción: Registro de auditoría del sistema
-- ============================================================================
DROP TABLE IF EXISTS auditoria CASCADE;
CREATE TABLE auditoria (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    accion VARCHAR(100) NOT NULL, -- login, logout, crear, editar, eliminar, etc.
    entidad VARCHAR(100), -- usuarios, carpetas, tomos, etc.
    entidad_id INTEGER,
    descripcion TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    datos_adicionales JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- ÍNDICES
-- Descripción: Índices para optimizar búsquedas y rendimiento
-- ============================================================================

-- Índices para usuarios
CREATE INDEX idx_usuarios_username ON usuarios(username);
CREATE INDEX idx_usuarios_email ON usuarios(email);

-- Índices para carpetas
CREATE INDEX idx_carpetas_numero_expediente ON carpetas(numero_expediente);

-- Índices para tomos
CREATE INDEX idx_tomos_carpeta ON tomos(carpeta_id);
CREATE INDEX idx_tomos_estado ON tomos(estado);

-- Índices para tareas OCR
CREATE INDEX idx_tareas_ocr_estado_prioridad ON tareas_ocr(estado, prioridad);

-- Índices para contenido OCR
CREATE INDEX idx_contenido_ocr_tomo ON contenido_ocr(tomo_id);

-- Índice GIN para búsqueda full-text en texto extraído (CRÍTICO)
CREATE INDEX idx_contenido_ocr_texto ON contenido_ocr USING GIN(to_tsvector('spanish', texto_extraido));

-- Índices para permisos
CREATE INDEX idx_permisos_carpeta_usuario ON permisos_carpeta(usuario_id);

-- Índices para auditoría
CREATE INDEX idx_auditoria_usuario_fecha ON auditoria(usuario_id, created_at);

-- ============================================================================
-- USUARIO ADMINISTRADOR POR DEFECTO
-- Descripción: Crea usuario admin con permisos completos
-- Username: admin
-- Password: admin123 (hash bcrypt)
-- ============================================================================

-- Insertar usuario administrador
INSERT INTO usuarios (username, password, email, nombre_completo, rol_id, activo)
VALUES (
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEg7Im',
    'admin@fgjcdmx.gob.mx',
    'Administrador del Sistema',
    (SELECT id FROM roles WHERE nombre = 'Admin'),
    TRUE
);

-- Insertar permisos completos para el administrador
INSERT INTO permisos_sistema (
    usuario_id,
    gestionar_usuarios,
    gestionar_roles,
    gestionar_carpetas,
    procesar_ocr,
    ver_auditoria,
    configurar_sistema,
    exportar_datos
) VALUES (
    (SELECT id FROM usuarios WHERE username = 'admin'),
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE
);

-- Registrar creación del usuario admin en auditoría
INSERT INTO auditoria (usuario_id, accion, entidad, descripcion)
VALUES (
    (SELECT id FROM usuarios WHERE username = 'admin'),
    'crear_usuario',
    'usuarios',
    'Usuario administrador creado por script de inicialización'
);

-- ============================================================================
-- TRIGGERS
-- Descripción: Triggers para actualización automática de timestamps
-- ============================================================================

-- Función para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger a tablas relevantes
CREATE TRIGGER update_usuarios_updated_at BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_carpetas_updated_at BEFORE UPDATE ON carpetas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tomos_updated_at BEFORE UPDATE ON tomos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contenido_ocr_updated_at BEFORE UPDATE ON contenido_ocr
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tareas_ocr_updated_at BEFORE UPDATE ON tareas_ocr
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_permisos_carpeta_updated_at BEFORE UPDATE ON permisos_carpeta
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_permisos_sistema_updated_at BEFORE UPDATE ON permisos_sistema
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMENTARIOS EN TABLAS Y COLUMNAS
-- Descripción: Documentación en la base de datos
-- ============================================================================

COMMENT ON DATABASE sistema_ocr IS 'Sistema de gestión de carpetas con procesamiento OCR';

COMMENT ON TABLE roles IS 'Roles de usuario del sistema';
COMMENT ON TABLE usuarios IS 'Usuarios del sistema';
COMMENT ON TABLE tokens_reset IS 'Tokens para reseteo de contraseñas';
COMMENT ON TABLE carpetas IS 'Carpetas o expedientes del sistema';
COMMENT ON TABLE tomos IS 'Tomos (archivos PDF) asociados a carpetas';
COMMENT ON TABLE contenido_ocr IS 'Contenido extraído mediante OCR';
COMMENT ON TABLE tareas_ocr IS 'Cola de tareas para procesamiento OCR';
COMMENT ON TABLE permisos_carpeta IS 'Permisos de usuarios sobre carpetas específicas';
COMMENT ON TABLE permisos_sistema IS 'Permisos generales del sistema';
COMMENT ON TABLE auditoria IS 'Registro de auditoría de acciones del sistema';

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================

VACUUM ANALYZE;

\echo '========================================='
\echo 'Schema creado exitosamente'
\echo 'Base de datos: sistema_ocr'
\echo 'Usuario admin creado:'
\echo '  Username: admin'
\echo '  Password: admin123'
\echo '  Email: admin@fgjcdmx.gob.mx'
\echo '========================================='
