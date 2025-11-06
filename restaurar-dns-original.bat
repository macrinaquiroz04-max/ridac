@echo off
echo ============================================
echo  RESTAURAR CONFIGURACIÓN DNS ORIGINAL
echo ============================================
echo.
echo Este script restaurará la configuración
echo DNS original de tu computadora.
echo.
pause

echo Restaurando DNS automático...
netsh interface ip set dns "Ethernet" dhcp

echo.
echo Limpiando cache DNS...
ipconfig /flushdns

echo.
echo ============================================
echo ✅ CONFIGURACIÓN ORIGINAL RESTAURADA
echo ============================================
echo.
echo Tu computadora ya usa DNS automático.
echo.
pause