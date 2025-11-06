#!/bin/bash
set -e

echo "🚀 Iniciando Sistema OCR Fiscalía..."

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a PostgreSQL..."
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  echo "PostgreSQL no está listo - esperando..."
  sleep 2
done

echo "✅ PostgreSQL está listo!"

# Ejecutar migraciones si es necesario
echo "📊 Verificando esquema de base de datos..."
python -c "from app.database import init_db; init_db()" || echo "⚠️ Error al inicializar BD"

# Iniciar aplicación
echo "🎯 Iniciando servidor FastAPI..."
# Configuración optimizada para procesos largos de OCR
exec uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --timeout-keep-alive 300 \
  --timeout-graceful-shutdown 60 \
  --limit-concurrency 1000 \
  --backlog 2048 \
  --workers 1
