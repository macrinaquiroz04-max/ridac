"""
Script para encontrar las colonias que NO se importaron
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from sqlalchemy import create_engine, text
import sys
sys.path.insert(0, str(Path(__file__).parent / "backend"))
from app.config import settings

archivo = Path.home() / "Downloads" / "Ciudad de México.xml"

print("=" * 80)
print("🔍 BUSCANDO COLONIAS NO IMPORTADAS")
print("=" * 80)
print()

# Leer XML
tree = ET.parse(archivo)
root = tree.getroot()
filas = [child for child in root if 'schema' not in child.tag.lower()]

# Extraer todas las colonias del XML
colonias_xml = set()
registros_xml = []

for fila in filas:
    cp = None
    colonia = None
    
    for child in fila:
        if 'd_codigo' in child.tag and child.text:
            cp = child.text.strip()
        if 'd_asenta' in child.tag and child.text:
            colonia = child.text.strip()
    
    if cp and colonia:
        colonias_xml.add(colonia.upper())
        registros_xml.append((cp, colonia))

print(f"📊 Colonias en XML: {len(colonias_xml):,}")

# Leer PostgreSQL
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT DISTINCT UPPER(colonia) as colonia
        FROM sepomex_codigos_postales
    """))
    colonias_pg = set(row[0] for row in result)

print(f"📊 Colonias en PostgreSQL: {len(colonias_pg):,}")
print()

# Encontrar diferencias
faltantes = colonias_xml - colonias_pg

if faltantes:
    print(f"❌ Colonias faltantes: {len(faltantes)}")
    print()
    print("🔍 Lista de colonias NO importadas:")
    for i, colonia in enumerate(sorted(faltantes)[:30], 1):
        # Buscar CP de esta colonia
        cps = [cp for cp, col in registros_xml if col.upper() == colonia]
        cps_str = ", ".join(sorted(set(cps))[:3])
        print(f"   {i:2}. {colonia:<50} CPs: {cps_str}")
    
    if len(faltantes) > 30:
        print(f"   ... y {len(faltantes) - 30} más")
    
    print()
    print("=" * 80)
    print("🔍 ANÁLISIS DE CAUSA")
    print("=" * 80)
    print()
    
    # Verificar si hay problema con acentos o caracteres especiales
    problemas_acentos = []
    for colonia in sorted(faltantes)[:10]:
        # Buscar similar en PostgreSQL
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT colonia 
                FROM sepomex_codigos_postales 
                WHERE similarity(UPPER(colonia), :colonia) > 0.8
                LIMIT 1
            """), {"colonia": colonia})
            similar = result.scalar()
            
            if similar:
                if similar.upper() != colonia:
                    problemas_acentos.append((colonia, similar))
    
    if problemas_acentos:
        print("⚠️  Se detectaron problemas con acentos/caracteres:")
        for xml_col, pg_col in problemas_acentos[:5]:
            print(f"   XML: {xml_col}")
            print(f"   PG:  {pg_col}")
            print()
    
    # Verificar si son duplicados (misma colonia, diferentes CPs)
    print("🔄 Verificando duplicados por nombre...")
    contador_xml = {}
    for cp, colonia in registros_xml:
        col_upper = colonia.upper()
        if col_upper not in contador_xml:
            contador_xml[col_upper] = []
        contador_xml[col_upper].append(cp)
    
    duplicados_xml = {col: cps for col, cps in contador_xml.items() if len(cps) > 1}
    print(f"   Colonias con múltiples CPs en XML: {len(duplicados_xml)}")
    
    # Mostrar algunos ejemplos
    print()
    print("   Ejemplos de colonias con múltiples CPs:")
    for i, (colonia, cps) in enumerate(sorted(duplicados_xml.items())[:5], 1):
        print(f"   {i}. {colonia}: {len(set(cps))} CPs diferentes")
        print(f"      CPs: {', '.join(sorted(set(cps))[:5])}")

else:
    print("✅ ¡Todas las colonias del XML están en PostgreSQL!")

print()
