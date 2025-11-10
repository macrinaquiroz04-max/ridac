#!/bin/bash
# Script para probar el sistema de tutoriales

echo "╔═══════════════════════════════════════════════════════╗"
echo "║   🎓 PRUEBA DE SISTEMA DE TUTORIALES                  ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Verificar archivos de tutorial
echo "📁 Verificando archivos del tutorial..."
if [ -f "frontend/js/tutorial.js" ]; then
    SIZE=$(du -h frontend/js/tutorial.js | cut -f1)
    echo "   ✅ tutorial.js encontrado ($SIZE)"
else
    echo "   ❌ tutorial.js NO encontrado"
    exit 1
fi

if [ -f "frontend/js/tutorial-admin.js" ]; then
    SIZE=$(du -h frontend/js/tutorial-admin.js | cut -f1)
    echo "   ✅ tutorial-admin.js encontrado ($SIZE)"
else
    echo "   ❌ tutorial-admin.js NO encontrado"
    exit 1
fi

if [ -f "frontend/js/tutorial-usuario.js" ]; then
    SIZE=$(du -h frontend/js/tutorial-usuario.js | cut -f1)
    echo "   ✅ tutorial-usuario.js encontrado ($SIZE)"
else
    echo "   ❌ tutorial-usuario.js NO encontrado"
    exit 1
fi

echo ""
echo "🔍 Verificando integración en dashboards..."

# Verificar dashboard.html
if grep -q "tutorial.js" frontend/dashboard.html && grep -q "tutorial-admin.js" frontend/dashboard.html; then
    echo "   ✅ Dashboard Admin integrado"
else
    echo "   ❌ Dashboard Admin NO integrado"
    exit 1
fi

# Verificar dashboard-usuario.html
if grep -q "tutorial.js" frontend/dashboard-usuario.html && grep -q "tutorial-usuario.js" frontend/dashboard-usuario.html; then
    echo "   ✅ Dashboard Usuario integrado"
else
    echo "   ❌ Dashboard Usuario NO integrado"
    exit 1
fi

echo ""
echo "🔘 Verificando botones de ayuda..."

# Verificar botón en dashboard admin
if grep -q "reiniciarTutorial()" frontend/dashboard.html; then
    echo "   ✅ Botón de ayuda en Dashboard Admin"
else
    echo "   ⚠️  Botón de ayuda NO encontrado en Dashboard Admin"
fi

# Verificar botón en dashboard usuario
if grep -q "reiniciarTutorial()" frontend/dashboard-usuario.html; then
    echo "   ✅ Botón de ayuda en Dashboard Usuario"
else
    echo "   ⚠️  Botón de ayuda NO encontrado en Dashboard Usuario"
fi

echo ""
echo "🐳 Verificando contenedores Docker..."
if docker compose ps | grep -q "sistema_ocr_nginx.*Up"; then
    echo "   ✅ Nginx activo"
else
    echo "   ❌ Nginx NO activo"
    exit 1
fi

if docker compose ps | grep -q "sistema_ocr_backend.*Up"; then
    echo "   ✅ Backend activo"
else
    echo "   ❌ Backend NO activo"
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✅ TODOS LOS TESTS PASARON                          ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Accede al sistema:"
echo "   → http://sistema-ocr.local"
echo "   → http://172.22.134.61"
echo ""
echo "📖 Para probar el tutorial:"
echo "   1. Borra localStorage en el navegador (F12 → Application → Local Storage → Clear)"
echo "   2. Recarga la página"
echo "   3. El tutorial debería aparecer automáticamente"
echo ""
echo "🔄 Para volver a ver el tutorial:"
echo "   → Haz clic en el botón '❓ Ayuda' en la esquina superior derecha"
echo ""
