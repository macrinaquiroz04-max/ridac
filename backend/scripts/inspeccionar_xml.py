"""
Script para inspeccionar la estructura del XML de SEPOMEX
"""
import xml.etree.ElementTree as ET
from pathlib import Path

archivo = Path.home() / "Downloads" / "Ciudad de México.xml"

print("Analizando estructura del XML...")
print()

tree = ET.parse(archivo)
root = tree.getroot()

print(f"Elemento raíz: {root.tag}")
print(f"Atributos raíz: {root.attrib}")
print()

print("Primeros 3 elementos hijo:")
for i, child in enumerate(list(root)[:3]):
    print(f"\n[{i}] Tag: {child.tag}")
    print(f"    Atributos: {child.attrib}")
    
    print(f"    Sub-elementos (primeros 15):")
    for subchild in list(child)[:15]:
        texto = subchild.text[:50] if subchild.text else "(vacío)"
        print(f"      • {subchild.tag}: {texto}")
