#!/bin/bash
# Script para demostrar la mejora de rendimiento con Redis Cache
# Sistema OCR - FGJCDMX
# Desarrollador: Eduardo Lozada Quiroz, ISC

echo "════════════════════════════════════════════════════════════════"
echo "🚀 DEMOSTRACIÓN DE OPTIMIZACIÓN CON REDIS CACHE"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para medir tiempo de respuesta
measure_time() {
    local url=$1
    local description=$2
    
    echo -e "${BLUE}📊 Probando: $description${NC}"
    
    # Medir tiempo de respuesta
    response_time=$(curl -o /dev/null -s -w '%{time_total}\n' "$url" 2>&1)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}   ⏱️  Tiempo de respuesta: ${response_time}s${NC}"
        echo "$response_time"
    else
        echo -e "${RED}   ❌ Error en la petición${NC}"
        echo "999"
    fi
}

echo -e "${YELLOW}🧪 PRUEBA 1: Lista de tomos${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Primera llamada (sin caché - consulta a BD)
echo -e "${BLUE}🔵 Primera llamada (SIN caché - consulta PostgreSQL)${NC}"
time1=$(measure_time "http://localhost:8000/api/tomos/todos" "GET /api/tomos/todos")
echo ""

# Esperar un segundo
sleep 1

# Segunda llamada (CON caché - Redis)
echo -e "${BLUE}🟢 Segunda llamada (CON caché - Redis)${NC}"
time2=$(measure_time "http://localhost:8000/api/tomos/todos" "GET /api/tomos/todos")
echo ""

# Calcular mejora
if (( $(echo "$time1 > 0" | bc -l) )) && (( $(echo "$time2 > 0" | bc -l) )); then
    improvement=$(echo "scale=2; ($time1 / $time2)" | bc)
    percent=$(echo "scale=0; (($time1 - $time2) / $time1) * 100" | bc)
    
    echo -e "${GREEN}✨ MEJORA DE RENDIMIENTO:${NC}"
    echo -e "   ${YELLOW}▸${NC} ${improvement}x más rápido"
    echo -e "   ${YELLOW}▸${NC} ${percent}% de reducción en tiempo"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Verificar estado de Redis
echo -e "${YELLOW}🧪 PRUEBA 2: Estado de Redis${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo -e "${BLUE}📊 Verificando conexión a Redis...${NC}"
redis_ping=$(docker exec sistema_ocr_redis redis-cli ping 2>&1)

if [ "$redis_ping" = "PONG" ]; then
    echo -e "${GREEN}✅ Redis está operativo${NC}"
    
    # Obtener estadísticas de Redis
    echo ""
    echo -e "${BLUE}📈 Estadísticas de Redis:${NC}"
    
    keys_count=$(docker exec sistema_ocr_redis redis-cli DBSIZE 2>&1 | grep -oP '\d+')
    echo -e "   ${YELLOW}▸${NC} Claves en caché: $keys_count"
    
    memory_used=$(docker exec sistema_ocr_redis redis-cli INFO memory 2>&1 | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
    echo -e "   ${YELLOW}▸${NC} Memoria usada: $memory_used"
    
    hit_rate=$(docker exec sistema_ocr_redis redis-cli INFO stats 2>&1 | grep "keyspace_hits" | cut -d: -f2 | tr -d '\r')
    echo -e "   ${YELLOW}▸${NC} Cache hits: $hit_rate"
    
else
    echo -e "${RED}❌ Redis no está respondiendo${NC}"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

# Ver logs del backend relacionados con caché
echo -e "${YELLOW}🧪 PRUEBA 3: Logs de caché en Backend${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo -e "${BLUE}📋 Últimas operaciones de caché:${NC}"
docker logs sistema_ocr_backend --tail 20 2>&1 | grep -E "✅.*caché|💾.*caché|🔄.*Caché" || echo "   No hay logs recientes de caché"

echo ""
echo "════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ DEMOSTRACIÓN COMPLETADA${NC}"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo -e "${BLUE}📝 RESUMEN:${NC}"
echo -e "   ${YELLOW}▸${NC} El sistema ahora usa Redis para cachear resultados"
echo -e "   ${YELLOW}▸${NC} Endpoints optimizados:"
echo -e "       • GET /api/tomos/todos"
echo -e "       • GET /api/tomos/{carpeta_id}"
echo -e "       • POST /api/busqueda/simple"
echo -e "       • GET /api/carpetas"
echo -e "   ${YELLOW}▸${NC} Tiempo de caché: 5-10 minutos"
echo -e "   ${YELLOW}▸${NC} Invalidación automática al crear/modificar datos"
echo ""
echo -e "${BLUE}🔗 Para ver métricas en tiempo real:${NC}"
echo -e "   • Grafana: http://localhost:3000"
echo -e "   • Prometheus: http://localhost:9090"
echo ""
