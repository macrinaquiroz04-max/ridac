#!/bin/bash
# Script para reemplazar console.log con función vacía sin romper código

cd /home/eduardo/Descargas/sistemaocr/frontend

# Reemplazar console.log( con una función vacía (() => {})( 
# Esto mantiene la sintaxis pero no hace nada
find . -type f \( -name "*.html" -o -name "*.js" \) -exec sed -i \
  -e 's/console\.log(/(() => {})(/' \
  -e 's/console\.info(/(() => {})(/' \
  -e 's/console\.debug(/(() => {})(/' \
  {} +

echo "✅ Console.log deshabilitados sin romper código"
