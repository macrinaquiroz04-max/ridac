#!/bin/bash
# start.sh — Script de inicio para Render.com

set -e

echo "🚀 Iniciando Sistema OCR RIDAC en Render..."

# Crear directorios temporales necesarios
mkdir -p /tmp/ridac/documentos \
         /tmp/ridac/exportaciones \
         /tmp/ridac/temp \
         /tmp/ridac/logs \
         /tmp/ridac/uploads

echo "📁 Directorios /tmp creados"

# Crear tablas en la base de datos (SQLAlchemy create_all)
echo "🗄️  Inicializando base de datos..."
python -c "
from app.database import init_db
result = init_db()
if result:
    print('✅ Base de datos inicializada correctamente')
else:
    print('⚠️  Advertencia: init_db() reportó error — revisa los logs')
"

# Iniciar la API
echo "🌐 Iniciando FastAPI en puerto $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
