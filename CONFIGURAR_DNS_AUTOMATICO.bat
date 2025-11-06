@echo off
:: ========================================
:: CONFIGURACION DNS AUTOMATICA
:: Sistema OCR - FGJCDMX
:: Desarrollador: Eduardo Lozada Quiroz, ISC
:: ========================================

:: Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ╔══════════════════════════════════════════════╗
    echo ║  ERROR: Se requieren permisos de Admin      ║
    echo ║                                              ║
    echo ║  Haz clic derecho en el archivo y           ║
    echo ║  selecciona "Ejecutar como administrador"   ║
    echo ╚══════════════════════════════════════════════╝
    echo.
    pause
    exit /b 1
)

color 0A
title Configuracion DNS - Sistema OCR

cls
echo.
echo ╔══════════════════════════════════════════════════╗
echo ║       CONFIGURACION DNS - SISTEMA OCR           ║
echo ║          Unidad de Analisis y Contexto          ║
echo ║                  FGJCDMX 2025                    ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo 🔧 Configurando DNS automaticamente...
echo.

:: Detectar el nombre de la interfaz de red activa
for /f "tokens=1,2,3*" %%a in ('netsh interface show interface ^| findstr /i "conectado"') do (
    set "INTERFACE=%%d"
    goto :found
)

:found
if not defined INTERFACE (
    echo ❌ No se pudo detectar la interfaz de red activa
    pause
    exit /b 1
)

echo 📡 Interfaz detectada: %INTERFACE%
echo.
echo 🌐 Configurando servidor DNS: 172.22.134.61
echo.

:: Configurar DNS primario
netsh interface ip set dns "%INTERFACE%" static 172.22.134.61 primary

:: Agregar DNS secundarios
netsh interface ip add dns "%INTERFACE%" 172.19.19.42 index=2
netsh interface ip add dns "%INTERFACE%" 8.8.8.8 index=3

echo.
echo ✅ DNS configurado correctamente
echo.
echo 🧪 Probando resolucion de dominio...
echo.

:: Probar resolucion
nslookup fgj-ocr.local 172.22.134.61

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║           ✅ CONFIGURACION COMPLETADA            ║
echo ║                                                  ║
echo ║  Ahora puedes acceder al sistema usando:        ║
echo ║                                                  ║
echo ║  👉 http://fgj-ocr.local                         ║
echo ║                                                  ║
echo ╚══════════════════════════════════════════════════╝
echo.
echo Presiona cualquier tecla para abrir el sistema...
pause >nul

:: Abrir sistema en navegador
start http://fgj-ocr.local

exit
