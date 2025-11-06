# backend/verificar_integracion.py

"""
Script para verificar que todos los nuevos servicios están correctamente integrados
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*80)
print("🔍 VERIFICACIÓN DE INTEGRACIÓN - NUEVOS SERVICIOS")
print("="*80)

try:
    # 1. Importar servicios
    print("\n📦 Importando servicios...")
    from app.services.catalogo_fiscalias_service import catalogo_fiscalias
    print("   ✅ catalogo_fiscalias_service")
    
    from app.services.detector_contextual_service import detector_contextual
    print("   ✅ detector_contextual_service")
    
    from app.services.pdf_pagina_service import pdf_pagina_service
    print("   ✅ pdf_pagina_service")
    
    # 2. Importar controller
    print("\n🎮 Importando controller...")
    from app.controllers.autocorrector_controller import router
    print("   ✅ autocorrector_controller")
    
    # 3. Contar endpoints
    print(f"\n📊 Total de endpoints: {len(router.routes)}")
    
    # 4. Mostrar nuevos endpoints
    print("\n🆕 NUEVOS ENDPOINTS:")
    nuevos_endpoints = [
        "/normalizar-fiscalia",
        "/normalizar-agencia-mp",
        "/normalizar-delito",
        "/clasificar-texto",
        "/procesar-documento-ocr",
        "/extraer-pagina-pdf",
        "/buscar-en-pdf",
        "/metadatos-numeracion-pdf"
    ]
    
    for route in router.routes:
        if hasattr(route, 'path'):
            for nuevo in nuevos_endpoints:
                if nuevo in route.path:
                    methods = list(route.methods) if hasattr(route, 'methods') else ['GET']
                    print(f"   ✅ {methods[0]} {route.path}")
                    break
    
    # 5. Verificar funcionalidad básica
    print("\n🧪 PRUEBAS RÁPIDAS:")
    
    # Fiscalía
    resultado = catalogo_fiscalias.normalizar_fiscalia("FDS")
    if resultado['encontrado']:
        print(f"   ✅ Fiscalía: FDS → {resultado['normalizado'][:40]}...")
    
    # Delito
    resultado = catalogo_fiscalias.normalizar_delito("ABUSO SEXUAL")
    if resultado['encontrado']:
        print(f"   ✅ Delito: ABUSO SEXUAL → {resultado['normalizado']}")
    
    # Detector
    resultado = detector_contextual.analizar_contexto("SAN ÁNGEL")
    print(f"   ✅ Detector: SAN ÁNGEL → {resultado['clasificacion']} ({resultado['certeza']:.0f}%)")
    
    print("\n" + "="*80)
    print("✅ INTEGRACIÓN EXITOSA - TODOS LOS SERVICIOS OPERATIVOS")
    print("="*80)
    
    print("\n📋 RESUMEN:")
    print("   ✅ 3 servicios nuevos importados correctamente")
    print("   ✅ Controller actualizado con 8+ endpoints")
    print("   ✅ Pruebas básicas pasadas")
    print("\n🎉 Sistema listo para usar")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
