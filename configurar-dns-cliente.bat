@echo off
REM Script para configurar DNS en clientes Windows
REM Sistema OCR FGJCDMX - Configuración automática
REM Desarrollador: Eduardo Lozada Quiroz

echo ========================================
echo   SISTEMA OCR - CONFIGURACION DNS
echo   FGJCDMX - Unidad de Analisis y Contexto
echo ========================================
echo.
echo Este script configurara tu PC para acceder a:
echo http://fgj-ocr.local
echo.

REM Solicitar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script necesita permisos de administrador
    echo Por favor, haz clic derecho y selecciona "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo Configurando DNS...
echo.

REM Agregar entrada en el archivo hosts como respaldo
echo 172.22.134.61 fgj-ocr.local >> C:\Windows\System32\drivers\etc\hosts
echo 172.22.134.61 www.fgj-ocr.local >> C:\Windows\System32\drivers\etc\hosts

REM Limpiar cache DNS
ipconfig /flushdns >nul 2>&1

echo.
echo ========================================
echo   CONFIGURACION COMPLETADA
echo ========================================
echo.
echo Ya puedes acceder al sistema en:
echo http://fgj-ocr.local
echo.
echo Presiona cualquier tecla para abrir el sistema en tu navegador...
pause >nul

REM Abrir el navegador
start http://fgj-ocr.local

exit /b 0
