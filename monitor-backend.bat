@echo off
:: Script para monitorear el estado del backend en tiempo real
:: Útil para detectar si se "apendeja" durante procesamiento OCR

title Monitor Backend - Sistema OCR
color 0A

echo.
echo ========================================
echo   MONITOR DE ESTADO DEL BACKEND
echo ========================================
echo.
echo Iniciando monitor PowerShell mejorado...
echo.

:: Verificar si existe el script PowerShell
if exist "%~dp0monitor-backend.ps1" (
    echo Ejecutando monitor avanzado...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0monitor-backend.ps1"
    goto :eof
)

:: Si no existe el .ps1, usar versión básica
echo Usando monitor basico...
echo Presiona Ctrl+C para detener
echo.

:loop
cls
echo ========================================
echo   ESTADO DEL BACKEND - %date% %time%
echo ========================================
echo.

:: Verificar estado de Docker
echo [1] Estado del Contenedor:
docker ps --filter "name=sistema_ocr_backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

:: Verificar health check
echo [2] Health Check:
powershell -Command "try { $response = Invoke-RestMethod -Uri 'http://localhost:8000/health' -TimeoutSec 5; Write-Host '[OK] Backend respondiendo:' -ForegroundColor Green; $response | ConvertTo-Json -Compress } catch { Write-Host '[ERROR] Backend NO responde' -ForegroundColor Red }"
echo.

:: Verificar procesos OCR activos
echo [3] Procesos OCR Activos:
powershell -Command "try { $token = Get-Content -Path '%USERPROFILE%\.sistemaocr_token' -ErrorAction SilentlyContinue; if ($token) { $headers = @{'Authorization'='Bearer '+$token}; $response = Invoke-RestMethod -Uri 'http://localhost:8000/api/admin/estado-procesamiento' -Headers $headers -TimeoutSec 5; $response | ConvertTo-Json -Compress } else { Write-Host '[INFO] No hay token guardado. Usa el browser para autenticarte.' -ForegroundColor Yellow } } catch { Write-Host '[ERROR] No se pudo obtener estado' -ForegroundColor Red; Write-Host $_.Exception.Message }"
echo.

:: Verificar uso de recursos
echo [4] Uso de Recursos:
docker stats sistema_ocr_backend --no-stream --format "CPU: {{.CPUPerc}}\tRAM: {{.MemUsage}}\tRED: {{.NetIO}}"
echo.

:: Últimas líneas del log
echo [5] Últimas Líneas del Log:
docker logs --tail 5 sistema_ocr_backend 2>nul
echo.

echo ========================================
echo Actualizando en 10 segundos...
echo ========================================

timeout /t 10 /nobreak >nul 2>nul
goto loop
