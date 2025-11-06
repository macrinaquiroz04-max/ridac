@echo off
echo ============================================
echo  CONFIGURACIÓN AUTOMÁTICA SISTEMA OCR
echo ============================================
echo.
echo Este script configurará tu computadora para
echo acceder al sistema usando: http://fgj-ocr
echo.
pause

echo Configurando DNS...
netsh interface ip set dns "Ethernet" static 172.22.134.61 primary
netsh interface ip add dns "Ethernet" 8.8.8.8 index=2

echo.
echo Limpiando cache DNS...
ipconfig /flushdns

echo.
echo ============================================
echo ✅ CONFIGURACIÓN COMPLETADA
echo ============================================
echo.
echo Ahora puedes acceder al sistema con:
echo 👉 http://fgj-ocr
echo.
echo Usuario: eduardo
echo Password: lalo1998c33
echo.
echo Para volver a la configuración original:
echo netsh interface ip set dns "Ethernet" dhcp
echo.
pause