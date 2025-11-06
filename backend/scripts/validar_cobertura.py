"""
Validar Cobertura Completa de Alcaldías en Diccionario SEPOMEX
===============================================================

Este script verifica la cobertura de todas las 16 alcaldías de la CDMX
en el diccionario local del servicio SEPOMEX.

Autor: Sistema de Análisis Jurídico
Fecha: Diciembre 2024
"""

import sys
import asyncio
from pathlib import Path

# Agregar el directorio app al path
sys.path.append(str(Path(__file__).parent / "app"))

from services.sepomex_service import SepomexService

# Las 16 alcaldías de la Ciudad de México
ALCALDIAS_CDMX = [
    "ÁLVARO OBREGÓN",
    "AZCAPOTZALCO",
    "BENITO JUÁREZ",
    "COYOACÁN",
    "CUAJIMALPA",
    "CUAUHTÉMOC",
    "GUSTAVO A. MADERO",
    "IZTACALCO",
    "IZTAPALAPA",
    "MAGDALENA CONTRERAS",
    "MIGUEL HIDALGO",
    "MILPA ALTA",
    "TLÁHUAC",
    "TLALPAN",
    "VENUSTIANO CARRANZA",
    "XOCHIMILCO"
]

async def main():
    print("\n" + "=" * 80)
    print("🏛️  VALIDACIÓN DE COBERTURA COMPLETA - 16 ALCALDÍAS DE CDMX")
    print("=" * 80 + "\n")
    
    sepomex = SepomexService()
    
    # Análisis del diccionario
    cobertura = {}
    total_cps = 0
    total_colonias = 0
    
    for cp, data in sepomex.diccionario_local.items():
        alcaldia = data["municipio"]
        if alcaldia not in cobertura:
            cobertura[alcaldia] = {
                "cps": [],
                "colonias": []
            }
        
        cobertura[alcaldia]["cps"].append(cp)
        cobertura[alcaldia]["colonias"].extend(data["colonias"])
        total_cps += 1
        total_colonias += len(data["colonias"])
    
    # Mostrar resultados
    print("📊 RESUMEN GENERAL:")
    print(f"   • Total de CPs en diccionario: {total_cps}")
    print(f"   • Total de colonias: {total_colonias}")
    print(f"   • Alcaldías cubiertas: {len(cobertura)}/16\n")
    
    print("-" * 80)
    print(f"{'ALCALDÍA':<30} {'CPs':<8} {'COLONIAS':<12} {'ESTADO':<10}")
    print("-" * 80)
    
    alcaldias_cubiertas = 0
    alcaldias_faltantes = []
    
    for alcaldia in sorted(ALCALDIAS_CDMX):
        if alcaldia in cobertura:
            num_cps = len(cobertura[alcaldia]["cps"])
            num_colonias = len(cobertura[alcaldia]["colonias"])
            estado = "✅ COMPLETA" if num_cps >= 8 else "⚠️  PARCIAL"
            print(f"{alcaldia:<30} {num_cps:<8} {num_colonias:<12} {estado:<10}")
            alcaldias_cubiertas += 1
        else:
            print(f"{alcaldia:<30} {'0':<8} {'0':<12} {'❌ FALTANTE':<10}")
            alcaldias_faltantes.append(alcaldia)
    
    print("-" * 80)
    
    # Detalles de cada alcaldía
    print("\n📍 DETALLE DE CÓDIGOS POSTALES POR ALCALDÍA:\n")
    
    for alcaldia in sorted(cobertura.keys()):
        cps = sorted(cobertura[alcaldia]["cps"])
        print(f"\n🏛️  {alcaldia} ({len(cps)} CPs)")
        print(f"   CPs: {', '.join(cps[:10])}")
        if len(cps) > 10:
            print(f"        {', '.join(cps[10:20])}")
        if len(cps) > 20:
            print(f"        ... y {len(cps) - 20} más")
    
    # Conclusión
    print("\n" + "=" * 80)
    print("📈 RESUMEN DE COBERTURA:")
    print("=" * 80)
    print(f"   ✅ Alcaldías completas: {alcaldias_cubiertas}/16 ({alcaldias_cubiertas*100/16:.1f}%)")
    print(f"   📦 Total de CPs: {total_cps}")
    print(f"   🏘️  Total de colonias: {total_colonias}")
    
    if alcaldias_faltantes:
        print(f"\n   ⚠️  Alcaldías faltantes: {', '.join(alcaldias_faltantes)}")
    else:
        print("\n   🎉 ¡COBERTURA COMPLETA DE LAS 16 ALCALDÍAS!")
    
    print("\n" + "=" * 80)
    print("✅ Validación completada")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
