#!/bin/bash
# Script de prueba para exportación de auditoría
# Sistema OCR FGJCDMX - UAyC

echo "🧪 Iniciando pruebas de exportación de auditoría..."
echo ""

# URL del API
API_URL="${API_URL:-http://localhost:8000}"

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para mostrar resultados
show_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# 1. Login para obtener token
echo "1️⃣  Obteniendo token de autenticación..."
read -p "Usuario: " USERNAME
read -sp "Password: " PASSWORD
echo ""

LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Error al obtener token. Verifica credenciales.${NC}"
    echo "Respuesta: $LOGIN_RESPONSE"
    exit 1
fi

show_result 0 "Token obtenido correctamente"
echo ""

# 2. Verificar permisos
echo "2️⃣  Verificando permisos de auditoría..."
PERMISOS=$(curl -s -X GET "$API_URL/auditoria/estadisticas" \
  -H "Authorization: Bearer $TOKEN")

if echo "$PERMISOS" | grep -q "No tienes permisos"; then
    show_result 1 "Usuario sin permisos de auditoría"
    exit 1
fi

show_result 0 "Usuario tiene permisos de auditoría"
echo ""

# 3. Prueba de exportación - Todos los registros
echo "3️⃣  Probando exportación: Todos los registros..."
curl -X GET "$API_URL/auditoria/exportar?periodo=all" \
  -H "Authorization: Bearer $TOKEN" \
  -o "test_export_all.csv" \
  -w "\nHTTP Status: %{http_code}\n"

if [ -f "test_export_all.csv" ] && [ -s "test_export_all.csv" ]; then
    LINEAS=$(wc -l < test_export_all.csv)
    show_result 0 "Exportación completa: $LINEAS líneas (incluyendo header)"
    echo "   📄 Archivo: test_export_all.csv"
    echo "   Primeras líneas:"
    head -n 3 test_export_all.csv
else
    show_result 1 "Exportación completa falló"
fi
echo ""

# 4. Prueba de exportación - Última semana
echo "4️⃣  Probando exportación: Última semana..."
curl -s -X GET "$API_URL/auditoria/exportar?periodo=week" \
  -H "Authorization: Bearer $TOKEN" \
  -o "test_export_week.csv"

if [ -f "test_export_week.csv" ] && [ -s "test_export_week.csv" ]; then
    LINEAS=$(wc -l < test_export_week.csv)
    show_result 0 "Exportación semanal: $LINEAS líneas"
    echo "   📄 Archivo: test_export_week.csv"
else
    show_result 1 "Exportación semanal falló"
fi
echo ""

# 5. Prueba de exportación - Hoy
echo "5️⃣  Probando exportación: Eventos de hoy..."
curl -s -X GET "$API_URL/auditoria/exportar?periodo=today" \
  -H "Authorization: Bearer $TOKEN" \
  -o "test_export_today.csv"

if [ -f "test_export_today.csv" ] && [ -s "test_export_today.csv" ]; then
    LINEAS=$(wc -l < test_export_today.csv)
    show_result 0 "Exportación diaria: $LINEAS líneas"
    echo "   📄 Archivo: test_export_today.csv"
else
    show_result 1 "Exportación diaria falló"
fi
echo ""

# 6. Prueba de exportación - Filtro por usuario
echo "6️⃣  Probando exportación: Filtrado por usuario actual..."
curl -s -X GET "$API_URL/auditoria/exportar?usuario=$USERNAME&periodo=all" \
  -H "Authorization: Bearer $TOKEN" \
  -o "test_export_usuario.csv"

if [ -f "test_export_usuario.csv" ] && [ -s "test_export_usuario.csv" ]; then
    LINEAS=$(wc -l < test_export_usuario.csv)
    show_result 0 "Exportación por usuario: $LINEAS líneas"
    echo "   📄 Archivo: test_export_usuario.csv"
else
    show_result 1 "Exportación por usuario falló"
fi
echo ""

# 7. Prueba de exportación - Filtro por acción
echo "7️⃣  Probando exportación: Filtrado por acción LOGIN_EXITOSO..."
curl -s -X GET "$API_URL/auditoria/exportar?accion=LOGIN_EXITOSO&periodo=all" \
  -H "Authorization: Bearer $TOKEN" \
  -o "test_export_logins.csv"

if [ -f "test_export_logins.csv" ] && [ -s "test_export_logins.csv" ]; then
    LINEAS=$(wc -l < test_export_logins.csv)
    show_result 0 "Exportación por acción: $LINEAS líneas"
    echo "   📄 Archivo: test_export_logins.csv"
else
    show_result 1 "Exportación por acción falló"
fi
echo ""

# 8. Verificar que se registró la exportación en auditoría
echo "8️⃣  Verificando registro de exportación en auditoría..."
sleep 2  # Esperar a que se registre

AUDIT_CHECK=$(curl -s -X GET "$API_URL/auditoria/eventos?accion=EXPORTAR_DATOS&limit=5" \
  -H "Authorization: Bearer $TOKEN")

if echo "$AUDIT_CHECK" | grep -q "EXPORTAR_DATOS"; then
    show_result 0 "Exportaciones registradas correctamente en auditoría"
    EXPORT_COUNT=$(echo "$AUDIT_CHECK" | grep -o "EXPORTAR_DATOS" | wc -l)
    echo "   📊 Encontradas $EXPORT_COUNT exportaciones en auditoría reciente"
else
    show_result 1 "No se encontraron registros de exportación en auditoría"
fi
echo ""

# 9. Validar formato CSV
echo "9️⃣  Validando formato CSV..."
VALID=true

# Verificar que tenga headers
HEADER=$(head -n 1 test_export_all.csv)
if echo "$HEADER" | grep -q "ID,Fecha/Hora,Usuario"; then
    show_result 0 "Headers CSV correctos"
else
    show_result 1 "Headers CSV incorrectos"
    VALID=false
fi

# Verificar que tenga datos
if [ $(wc -l < test_export_all.csv) -gt 1 ]; then
    show_result 0 "CSV contiene datos"
else
    show_result 1 "CSV no contiene datos"
    VALID=false
fi

# Verificar codificación UTF-8
if file test_export_all.csv | grep -q "UTF-8"; then
    show_result 0 "Codificación UTF-8 correcta"
else
    echo -e "${YELLOW}⚠️  Advertencia: Codificación no es UTF-8${NC}"
fi
echo ""

# Resumen
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 RESUMEN DE PRUEBAS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Archivos generados:"
ls -lh test_export_*.csv 2>/dev/null | awk '{print "  📄", $9, "-", $5}'
echo ""
echo "Total de archivos CSV: $(ls test_export_*.csv 2>/dev/null | wc -l)"
echo ""

if $VALID; then
    echo -e "${GREEN}✅ Todas las pruebas completadas exitosamente${NC}"
    echo ""
    echo "Puedes abrir los archivos CSV con:"
    echo "  • Excel/LibreOffice Calc"
    echo "  • cat test_export_all.csv"
    echo "  • less test_export_all.csv"
    echo ""
    echo "Para limpiar archivos de prueba:"
    echo "  rm test_export_*.csv"
else
    echo -e "${RED}❌ Algunas pruebas fallaron${NC}"
    echo "Revisa los logs del backend para más detalles"
fi
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
