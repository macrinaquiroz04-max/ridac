@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════════════════════════════╗
echo ║     Verificación de Separación: Entornos Local vs Docker      ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 🔍 Verificando montajes de Docker...
echo.
docker inspect sistema_ocr_backend -f "{{range .Mounts}}{{.Type}}: {{.Source}} =^> {{.Destination}}{{println}}{{end}}"
echo.

echo ═══════════════════════════════════════════════════════════════
echo ✅ VERIFICACIÓN DE NO-CONFLICTO
echo ═══════════════════════════════════════════════════════════════
echo.

echo 📊 Debe mostrar SOLO estos 3 montajes:
echo    1. bind: B:\FJ1\backend =^> /app (código)
echo    2. volume: fj1_documentos_data =^> /app/uploads
echo    3. volume: fj1_fgjcdmx_data =^> /FGJCDMX
echo.

echo ❌ NO debe aparecer:
echo    - backend\uploads montado directamente
echo    - backend\C montado directamente
echo    - C:\FGJCDMX montado directamente
echo.

echo ═══════════════════════════════════════════════════════════════
echo 📁 ARCHIVOS LOCALES (no afectan Docker)
echo ═══════════════════════════════════════════════════════════════
echo.

if exist "backend\uploads\" (
    echo ✅ backend\uploads\ existe (SOLO LOCAL)
    for /f %%A in ('dir /s /b backend\uploads\*.pdf 2^>nul ^| find /c /v ""') do echo    Archivos: %%A PDFs
) else (
    echo ⚪ backend\uploads\ no existe
)

echo.

if exist "backend\C\" (
    echo ✅ backend\C\ existe (SOLO LOCAL)
    dir backend\C\ /s /b 2>nul | find /c /v ""
) else (
    echo ⚪ backend\C\ no existe
)

echo.

if exist "C:\FGJCDMX\" (
    echo ✅ C:\FGJCDMX\ existe (SOLO LOCAL)
) else (
    echo ⚪ C:\FGJCDMX\ no existe
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo 📦 ARCHIVOS DOCKER (no afectan Local)
echo ═══════════════════════════════════════════════════════════════
echo.

echo 📂 Tomos en Docker:
docker exec sistema_ocr_backend du -sh /app/uploads/tomos/ 2>nul

echo.
echo 📂 Archivos FGJCDMX en Docker:
docker exec sistema_ocr_backend ls -lh /FGJCDMX/ 2>nul

echo.
echo ═══════════════════════════════════════════════════════════════
echo 🛡️ PROTECCIÓN EN .gitignore
echo ═══════════════════════════════════════════════════════════════
echo.

findstr /C:"backend/C/" .gitignore >nul 2>&1
if %errorlevel%==0 (
    echo ✅ backend/C/ está en .gitignore
) else (
    echo ❌ backend/C/ NO está en .gitignore
)

findstr /C:"backend/uploads/" .gitignore >nul 2>&1
if %errorlevel%==0 (
    echo ✅ backend/uploads/ está protegido en .gitignore
) else (
    echo ⚠️  backend/uploads/ no está completamente en .gitignore
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo 🎯 RESUMEN
echo ═══════════════════════════════════════════════════════════════
echo.

echo Si todo está bien, debes ver:
echo    ✅ 3 montajes en Docker (bind + 2 volumes)
echo    ✅ Archivos locales separados
echo    ✅ Archivos Docker separados
echo    ✅ .gitignore protegiendo rutas sensibles
echo.
echo ❌ NO debes ver:
echo    - Rutas locales montadas directamente en Docker
echo    - Archivos compartidos entre local y Docker
echo.

pause
