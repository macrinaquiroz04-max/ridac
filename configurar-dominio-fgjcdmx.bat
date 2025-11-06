@echo off
echo ========================================
echo CONFIGURAR DOMINIO: fgjcdmx
echo ========================================
echo.
echo Este script requiere permisos de ADMINISTRADOR
echo.
pause

REM Agregar entrada al archivo hosts
echo 127.0.0.1 fgjcdmx >> C:\Windows\System32\drivers\etc\hosts

echo.
echo ✓ Entrada agregada al archivo hosts
echo.
echo Ahora podras acceder con: http://fgjcdmx
echo.
pause
