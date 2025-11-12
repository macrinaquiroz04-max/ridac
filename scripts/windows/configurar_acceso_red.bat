@echo off
REM ============================================
REM Configuracion automatica - Sistema OCR FGJCDMX
REM ============================================

echo.
echo ================================================
echo   CONFIGURACION SISTEMA OCR - FGJCDMX
echo ================================================
echo.
echo Este script configurara el acceso al sistema
echo usando el nombre: fgjcdmxocr.local
echo.

REM Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Este script requiere permisos de Administrador
    echo.
    echo Por favor:
    echo 1. Click derecho en este archivo
    echo 2. Seleccionar "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo [OK] Permisos de administrador verificados
echo.

REM Hacer backup del archivo hosts
echo Creando backup del archivo hosts...
copy /Y C:\Windows\System32\drivers\etc\hosts C:\Windows\System32\drivers\etc\hosts.backup.%date:~-4,4%%date:~-10,2%%date:~-7,2% >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] Backup creado exitosamente
) else (
    echo [!] No se pudo crear backup, pero continuaremos...
)
echo.

REM Verificar si ya existe la entrada
findstr /C:"fgjcdmxocr.local" C:\Windows\System32\drivers\etc\hosts >nul 2>&1
if %errorLevel% equ 0 (
    echo [!] La entrada ya existe en el archivo hosts
    echo.
    choice /C SN /M "¿Desea actualizarla de todas formas?"
    if errorlevel 2 (
        echo Configuracion cancelada por el usuario
        pause
        exit /b 0
    )
    
    REM Remover entrada anterior
    echo Removiendo entrada anterior...
    findstr /V /C:"fgjcdmxocr.local" C:\Windows\System32\drivers\etc\hosts > C:\Windows\System32\drivers\etc\hosts.tmp
    move /Y C:\Windows\System32\drivers\etc\hosts.tmp C:\Windows\System32\drivers\etc\hosts >nul 2>&1
)

REM Agregar nuevas entradas (Ethernet y WiFi)
echo Agregando configuracion al archivo hosts...
echo # Sistema OCR FGJCDMX - Acceso por Ethernet y WiFi >> C:\Windows\System32\drivers\etc\hosts
echo 192.168.1.132    fgjcdmxocr.local >> C:\Windows\System32\drivers\etc\hosts
echo 192.168.1.85     fgjcdmxocr.local >> C:\Windows\System32\drivers\etc\hosts
if %errorLevel% equ 0 (
    echo [OK] Configuracion agregada exitosamente (Ethernet + WiFi)
) else (
    echo [ERROR] No se pudo agregar la configuracion
    pause
    exit /b 1
)

REM Limpiar cache DNS
echo.
echo Limpiando cache DNS...
ipconfig /flushdns >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] Cache DNS limpiado
) else (
    echo [!] No se pudo limpiar cache DNS
)

echo.
echo ================================================
echo   CONFIGURACION COMPLETADA EXITOSAMENTE
echo ================================================
echo.
echo Ya puedes acceder al sistema usando:
echo.
echo     http://fgjcdmxocr.local:8000
echo.
echo O directamente al login:
echo     http://fgjcdmxocr.local:8000/login
echo.
echo ================================================
echo.

REM Abrir navegador automáticamente
choice /C SN /M "¿Desea abrir el sistema ahora en su navegador?"
if errorlevel 1 if not errorlevel 2 (
    echo Abriendo navegador...
    start http://fgjcdmxocr.local:8000
)

echo.
echo Presiona cualquier tecla para salir...
pause >nul
