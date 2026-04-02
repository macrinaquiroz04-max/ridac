#!/bin/bash
# start.sh — Script de inicio para Render.com
# Ejecuta migraciones Alembic y luego inicia uvicorn

set -e

echo "🚀 Iniciando Sistema OCR RIDAC en Render..."

# Crear directorios temporales necesarios
mkdir -p /tmp/ridac/documentos \
         /tmp/ridac/exportaciones \
         /tmp/ridac/temp \
         /tmp/ridac/logs \
         /tmp/ridac/uploads

echo "📁 Directorios /tmp creados"

# Ejecutar migraciones de base de datos (Supabase)
echo "🗄️  Ejecutando migraciones Alembic..."
alembic upgrade head
echo "✅ Migraciones completadas"

# Iniciar la API
echo "🌐 Iniciando FastAPI en puerto $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
