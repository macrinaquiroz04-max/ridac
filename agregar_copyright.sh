#!/bin/bash
# Script para agregar headers de copyright a todos los archivos del proyecto

COPYRIGHT_HEADER="# Copyright (c) 2025 Eduardo Lozada <aduardolozada1958@gmail.com>
# Todos los derechos reservados.
# 
# Este código es propiedad exclusiva del autor.
# Prohibida su reproducción, distribución o modificación sin autorización escrita.
# Sistema OCR con Análisis Jurídico - Propietario: Eduardo Lozada
# Fecha de creación: Octubre 2025
# 
# AVISO: Este software está protegido por derechos de autor.
# Cualquier uso no autorizado constituye violación de la Ley Federal del Derecho de Autor (México)
"

echo "Agregando headers de copyright a archivos Python..."

# Función para agregar header si no existe
add_header() {
    local file="$1"
    if ! grep -q "Copyright (c) 2025 Eduardo Lozada" "$file"; then
        # Crear respaldo
        cp "$file" "$file.bak"
        
        # Agregar header
        {
            echo "$COPYRIGHT_HEADER"
            cat "$file"
        } > "$file.tmp"
        
        mv "$file.tmp" "$file"
        echo "✅ Header agregado a: $file"
    else
        echo "⏭️  Ya tiene header: $file"
    fi
}

# Agregar a archivos principales de Python
find backend/app -name "*.py" -type f | while read file; do
    add_header "$file"
done

echo ""
echo "Headers de JavaScript..."

JS_HEADER="/**
 * Copyright (c) 2025 Eduardo Lozada <aduardolozada1958@gmail.com>
 * Todos los derechos reservados.
 * 
 * Este código es propiedad exclusiva del autor.
 * Prohibida su reproducción, distribución o modificación sin autorización escrita.
 * Sistema OCR con Análisis Jurídico - Propietario: Eduardo Lozada
 * Fecha de creación: Octubre 2025
 * 
 * AVISO: Este software está protegido por derechos de autor.
 * Cualquier uso no autorizado constituye violación de la Ley Federal del Derecho de Autor (México)
 */
"

# Función para JS
add_js_header() {
    local file="$1"
    if ! grep -q "Copyright (c) 2025 Eduardo Lozada" "$file"; then
        cp "$file" "$file.bak"
        {
            echo "$JS_HEADER"
            cat "$file"
        } > "$file.tmp"
        mv "$file.tmp" "$file"
        echo "✅ Header agregado a: $file"
    else
        echo "⏭️  Ya tiene header: $file"
    fi
}

find frontend/js -name "*.js" -type f | while read file; do
    add_js_header "$file"
done

echo ""
echo "✅ Proceso completado!"
echo ""
echo "IMPORTANTE: Los archivos .bak son respaldos."
echo "Verifica que todo funcione correctamente y luego:"
echo "  find . -name '*.bak' -delete"
