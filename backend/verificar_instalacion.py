"""
Script de Verificación del Sistema de Análisis Jurídico
========================================================
Verifica que todos los componentes estén correctamente instalados
"""

import os
import sys

def check_file(filepath, description):
    """Verifica que un archivo exista"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists

def check_directory(dirpath, description):
    """Verifica que un directorio exista"""
    exists = os.path.isdir(dirpath)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {dirpath}")
    return exists

def main():
    print("\n" + "="*70)
    print("  VERIFICACIÓN DEL SISTEMA DE ANÁLISIS JURÍDICO")
    print("="*70 + "\n")
    
    all_ok = True
    
    # Backend - Modelos
    print("📦 MODELOS (Backend):")
    all_ok &= check_file("app/models/analisis_juridico.py", "Modelos de análisis jurídico")
    print()
    
    # Backend - Servicios
    print("⚙️  SERVICIOS (Backend):")
    all_ok &= check_file("app/services/legal_ocr_service.py", "Servicio de OCR legal")
    all_ok &= check_file("app/services/legal_nlp_analysis_service.py", "Servicio de análisis NLP")
    print()
    
    # Backend - Controladores
    print("🎮 CONTROLADORES (Backend):")
    all_ok &= check_file("app/controllers/analisis_admin_controller.py", "Controlador admin")
    all_ok &= check_file("app/controllers/analisis_usuario_controller.py", "Controlador usuario")
    print()
    
    # Backend - Rutas
    print("🛣️  RUTAS (Backend):")
    all_ok &= check_file("app/routes/analisis_admin.py", "Rutas admin")
    all_ok &= check_file("app/routes/analisis_usuario.py", "Rutas usuario")
    print()
    
    # Scripts SQL
    print("📊 SCRIPTS SQL:")
    all_ok &= check_file("scripts/create_analisis_juridico_tables.sql", "Script de migración")
    print()
    
    # Frontend - JavaScript
    print("📜 JAVASCRIPT (Frontend):")
    all_ok &= check_file("../frontend/js/analisis-juridico.js", "Módulo JavaScript")
    print()
    
    # Frontend - CSS
    print("🎨 ESTILOS (Frontend):")
    all_ok &= check_file("../frontend/css/analisis-juridico.css", "Estilos CSS")
    print()
    
    # Frontend - HTML
    print("📄 HTML (Frontend):")
    all_ok &= check_file("../frontend/dashboard-usuario.html", "Dashboard de usuario")
    print()
    
    # Verificar imports en main.py
    print("🔗 INTEGRACIÓN:")
    main_py = "main.py"
    if os.path.exists(main_py):
        with open(main_py, 'r', encoding='utf-8') as f:
            content = f.read()
            has_admin = 'analisis_admin' in content
            has_usuario = 'analisis_usuario' in content
            
            status = "✅" if (has_admin and has_usuario) else "❌"
            print(f"{status} Rutas registradas en main.py")
            all_ok &= (has_admin and has_usuario)
    else:
        print("❌ main.py no encontrado")
        all_ok = False
    print()
    
    # Resultado final
    print("="*70)
    if all_ok:
        print("✅ ¡TODOS LOS COMPONENTES ESTÁN INSTALADOS!")
        print("\n📋 PRÓXIMOS PASOS:")
        print("   1. Ejecutar script SQL: psql -U postgres -d tu_db -f scripts/create_analisis_juridico_tables.sql")
        print("   2. Iniciar servidor: python main.py")
        print("   3. Abrir dashboard-usuario.html en navegador")
        print("   4. Hacer click en 'Ver Análisis' en una carpeta")
        return 0
    else:
        print("❌ FALTAN ALGUNOS COMPONENTES")
        print("\n⚠️  Revisa los archivos marcados con ❌ arriba")
        print("   Verifica que estés en el directorio 'backend/'")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        sys.exit(1)
