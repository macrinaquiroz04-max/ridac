#!/bin/bash
set -e

echo "🚀 Iniciando Sistema OCR Fiscalía..."

# Si se pasaron argumentos de Celery, ejecutarlos directamente
if [ "$1" = "celery" ]; then
  echo "🔄 Iniciando Celery: $@"
  # Esperar a Redis
  echo "⏳ Esperando a Redis..."
  until redis-cli -h redis ping 2>/dev/null; do
    echo "Redis no está listo - esperando..."
    sleep 2
  done
  echo "✅ Redis está listo!"
  exec "$@"
fi

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

# Iniciar aplicación FastAPI
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
