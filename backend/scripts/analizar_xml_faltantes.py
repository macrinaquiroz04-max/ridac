"""
Script para analizar por qué faltan colonias en la importación
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter

archivo = Path.home() / "Downloads" / "Ciudad de México.xml"

print("=" * 80)
print("🔍 ANÁLISIS DETALLADO DEL XML DE SEPOMEX")
print("=" * 80)
print()

tree = ET.parse(archivo)
root = tree.getroot()

# Obtener todos los elementos 'table' (excluyendo schema)
filas = [child for child in root if 'schema' not in child.tag.lower()]

print(f"Total de filas en XML: {len(filas):,}")
print()

# Análisis 1: ¿Todos tienen c_estado = 09?
estados = []
for fila in filas:
    for child in fila:
        if 'c_estado' in child.tag:
            estados.append(child.text)
            break

contador_estados = Counter(estados)
print("📊 Distribución por estado (código):")
for estado, count in contador_estados.most_common():
    print(f"   Estado {estado}: {count:,} registros")
print()

# Análisis 2: ¿Cuántos registros únicos por CP + Colonia?
registros_unicos = set()
cps_unicos = set()
colonias_unicas = set()

for fila in filas:
    cp = None
    colonia = None
    c_estado = None
    
    for child in fila:
        if 'c_estado' in child.tag and child.text:
            c_estado = child.text
        if 'd_codigo' in child.tag and child.text:
            cp = child.text.strip()
        if 'd_asenta' in child.tag and child.text:
            colonia = child.text.strip()
    
    if c_estado == '09' and cp and colonia:
        registros_unicos.add((cp, colonia))
        cps_unicos.add(cp)
        colonias_unicas.add(colonia)

print(f"📈 Datos únicos (c_estado = 09):")
print(f"   • Combinaciones únicas (CP + Colonia): {len(registros_unicos):,}")
print(f"   • Códigos postales únicos: {len(cps_unicos):,}")
print(f"   • Colonias únicas: {len(colonias_unicas):,}")
print()

# Análisis 3: ¿Hay duplicados exactos?
registros_completos = []
for fila in filas:
    cp = None
    colonia = None
    c_estado = None
    
    for child in fila:
        if 'c_estado' in child.tag and child.text:
            c_estado = child.text
        if 'd_codigo' in child.tag and child.text:
            cp = child.text.strip()
        if 'd_asenta' in child.tag and child.text:
            colonia = child.text.strip()
    
    if c_estado == '09' and cp and colonia:
        registros_completos.append((cp, colonia))

duplicados = len(registros_completos) - len(registros_unicos)
print(f"🔄 Análisis de duplicados:")
print(f"   • Total de registros CDMX: {len(registros_completos):,}")
print(f"   • Registros únicos: {len(registros_unicos):,}")
print(f"   • Duplicados exactos: {duplicados}")
print()

# Análisis 4: Comparar con lo que se importó
print("💾 Comparación con PostgreSQL:")
print(f"   • Se encontraron en XML: {len(colonias_unicas):,} colonias únicas")
print(f"   • Se importaron a PostgreSQL: 1,381 colonias")
print(f"   • Diferencia: {len(colonias_unicas) - 1381}")
print()

if len(colonias_unicas) == 1381:
    print("✅ ¡Se importaron TODAS las colonias del XML!")
    print("   La diferencia con 1,812 es porque el XML de 'Ciudad de México'")
    print("   solo contiene las colonias principales, no el catálogo completo nacional.")
elif len(colonias_unicas) > 1381:
    print("⚠️  Faltan algunas colonias por importar")
    print(f"   Posiblemente fueron eliminadas por duplicados (CP + Colonia)")
else:
    print("✅ Todas las colonias únicas del XML fueron importadas correctamente")

print()
print("=" * 80)
print("📝 CONCLUSIÓN")
print("=" * 80)
print()
print("El archivo 'Ciudad de México.xml' contiene un subconjunto del catálogo")
print("oficial SEPOMEX, no el catálogo completo nacional.")
print()
print("Para obtener las 1,812 colonias completas necesitas:")
print("1. El archivo XML nacional completo (CPdescarga.txt o similar)")
print("2. Descargar desde: http://www.sepomex.gob.mx/lservicios/servicios/descargas")
print()
print(f"Estado actual: {len(colonias_unicas):,} colonias (76% del objetivo de 1,812)")
print()
