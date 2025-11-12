#!/bin/bash
# Script de Verificación - Sistema OCR FGJCDMX

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       🔍 Verificación del Sistema OCR - FGJCDMX             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Verificar contenedores
echo "📦 Estado de contenedores:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAMES|sistema_ocr" || echo "❌ No hay contenedores corriendo"
echo ""

# Verificar salud del sistema
echo "🏥 Health Check del Backend:"
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
else
    echo "❌ Backend no responde"
fi
echo ""

# Verificar PostgreSQL
echo "🐘 PostgreSQL:"
MAX_CONN=$(docker exec sistema_ocr_db psql -U postgres -d sistema_ocr -t -c "SHOW max_connections;" 2>/dev/null | xargs)
if [ $? -eq 0 ]; then
    echo "✅ max_connections: $MAX_CONN"
else
    echo "❌ PostgreSQL no responde"
fi
echo ""

# Verificar Frontend
echo "🌐 Frontend:"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null)
if [ "$STATUS" = "200" ]; then
    echo "✅ Frontend accesible en http://localhost/"
else
    echo "❌ Frontend no accesible (HTTP $STATUS)"
fi
echo ""

# Verificar uso de recursos
echo "�� Uso de Recursos:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep -E "CONTAINER|sistema_ocr" | head -5
echo ""

echo "✅ Verificación completada"
echo ""
