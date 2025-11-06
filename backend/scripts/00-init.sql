-- Script de inicialización completa de Base de Datos
-- Sistema OCR Fiscalía - PostgreSQL con Docker

-- Habilitar extensión pg_trgm para búsquedas avanzadas
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Configurar zona horaria
SET timezone = 'America/Mexico_City';

-- Configurar encoding
SET client_encoding = 'UTF8';

\echo '✅ Extensiones habilitadas correctamente'
\echo '📊 Ejecutando script principal de esquema...'

-- El resto de scripts se ejecutarán en orden alfabético desde /docker-entrypoint-initdb.d/
