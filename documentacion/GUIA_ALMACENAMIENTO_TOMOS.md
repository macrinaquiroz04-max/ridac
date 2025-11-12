# 📂 Guía de Almacenamiento de Tomos en Docker

## 🎯 ¿Dónde se guardan los tomos en Docker?

### 📊 **Resumen Rápido:**

Los tomos se almacenan en **2 ubicaciones** según tu configuración:

1. **`/app/uploads/tomos/`** → Volumen Docker persistente (`fj1_documentos_data`)
2. **`/FGJCDMX/documentos/`** → Volumen Docker persistente (`fj1_fgjcdmx_data`)

---

## 🐳 **Configuración de Volúmenes en Docker**

### **En `docker-compose.yml` (líneas 55-57):**

```yaml
volumes:
  - ./backend:/app                    # Código del backend
  - documentos_data:/app/uploads      # 📄 TOMOS Y DOCUMENTOS
  - fgjcdmx_data:/FGJCDMX             # 🏛️ ARCHIVOS FISCALÍA
```

### **Volúmenes Definidos (líneas 112-119):**

```yaml
volumes:
  postgres_data:      # Base de datos PostgreSQL
    driver: local
  pgadmin_data:       # Datos de PgAdmin
    driver: local
  documentos_data:    # 📄 TOMOS, PDFs, IMÁGENES
    driver: local
  fgjcdmx_data:       # 🏛️ LOGS, EXPORTACIONES, TEMP
    driver: local
```

---

## 📍 **Ubicaciones Físicas en el Sistema**

### **1. Dentro del Contenedor Docker:**

```bash
# Directorio principal de tomos
/app/uploads/tomos/
├── <carpeta_id>/
│   ├── <tomo_id>/
│   │   └── archivo.pdf

# Directorio alternativo FGJCDMX
/FGJCDMX/
├── documentos/      # Documentos adicionales
├── exportaciones/   # Exportaciones de análisis
├── logs/           # Logs del sistema
└── temp/           # Archivos temporales
```

### **2. En el Host (Windows con Docker Desktop):**

```
# Volumen documentos_data (Tomos)
\\wsl$\docker-desktop-data\data\docker\volumes\fj1_documentos_data\_data\tomos\

# Volumen fgjcdmx_data
\\wsl$\docker-desktop-data\data\docker\volumes\fj1_fgjcdmx_data\_data\
```

**Nota:** En Windows, Docker Desktop usa WSL2, por eso la ruta empieza con `\\wsl$\`

---

## 📤 **¿Cómo se suben los tomos?**

### **Proceso de Upload:**

1. **Frontend** → Usuario selecciona PDF en `tomos.html`
2. **API Request** → `POST /api/carpetas/{carpeta_id}/tomos`
3. **Backend recibe archivo** → FastAPI guarda en `/app/uploads/tomos/`
4. **Estructura creada:**
   ```
   /app/uploads/tomos/
   └── carpeta_5/
       └── tomo_12/
           └── tomo_12_completo.pdf
   ```
5. **Base de datos** → Se registra la ruta en PostgreSQL
6. **Procesamiento OCR** → Se extrae el texto del PDF

---

## 🔍 **Comandos Útiles para Verificar Tomos**

### **Ver contenido del volumen de tomos:**

```bash
# Listar todos los tomos
docker exec sistema_ocr_backend ls -R /app/uploads/tomos/

# Ver tamaño de tomos almacenados
docker exec sistema_ocr_backend du -sh /app/uploads/tomos/

# Contar cuántos PDFs hay
docker exec sistema_ocr_backend find /app/uploads/tomos/ -name "*.pdf" | wc -l
```

### **Acceder directamente al contenedor:**

```bash
# Entrar al contenedor
docker exec -it sistema_ocr_backend bash

# Una vez dentro:
cd /app/uploads/tomos/
ls -lah
```

### **Ver información de los volúmenes:**

```powershell
# Listar todos los volúmenes
docker volume ls

# Ver detalles de un volumen específico
docker volume inspect fj1_documentos_data

# Ver tamaño de los volúmenes
docker system df -v
```

---

## 💾 **Backup de Tomos**

### **Opción 1: Copiar desde el contenedor a tu PC**

```bash
# Copiar todos los tomos al disco local
docker cp sistema_ocr_backend:/app/uploads/tomos/ C:\Backups\tomos_backup\
```

### **Opción 2: Backup del volumen completo**

```bash
# Crear backup del volumen documentos_data
docker run --rm -v fj1_documentos_data:/data -v C:\Backups:/backup alpine tar czf /backup/tomos_backup_$(date +%Y%m%d).tar.gz -C /data .
```

### **Opción 3: Script automático de backup**

Crea un archivo `backup-tomos.bat`:

```batch
@echo off
echo Creando backup de tomos...
set FECHA=%date:~-4%%date:~3,2%%date:~0,2%
docker cp sistema_ocr_backend:/app/uploads/tomos/ C:\Backups\tomos_%FECHA%\
echo ✅ Backup completado en: C:\Backups\tomos_%FECHA%\
pause
```

---

## 📊 **Estado Actual de tus Tomos**

### **Según el sistema actual:**

```
📂 /app/uploads/tomos/
   Tamaño: 120 MB
   Ubicación: Volumen Docker persistente (fj1_documentos_data)
   
📂 /FGJCDMX/
   Tamaño: 20 KB
   Ubicación: Volumen Docker persistente (fj1_fgjcdmx_data)
```

---

## 🔄 **Restaurar Tomos desde Backup**

### **Si perdiste los datos:**

```bash
# 1. Detener el sistema
docker-compose down

# 2. Restaurar desde backup
docker cp C:\Backups\tomos_backup\ sistema_ocr_backend:/app/uploads/tomos/

# 3. Reiniciar el sistema
docker-compose up -d
```

---

## 🗺️ **Mapeo Completo de Rutas**

| Contexto | Ruta | Descripción |
|----------|------|-------------|
| **Dentro del contenedor** | `/app/uploads/tomos/` | Donde el backend guarda los PDFs |
| **Volumen Docker** | `fj1_documentos_data` | Nombre del volumen persistente |
| **Host Windows** | `\\wsl$\docker-desktop-data\...` | Ubicación física en WSL2 |
| **Base de datos** | Tabla `tomos`, campo `ruta_pdf` | Registro en PostgreSQL |
| **Frontend URL** | `http://localhost/api/tomos/{id}/pdf` | URL para acceder al PDF |

---

## 📁 **Estructura Completa de Directorios**

```
Docker Container (sistema_ocr_backend)
│
├── /app/                           # Backend FastAPI
│   ├── main.py
│   ├── uploads/                    # 📂 VOLUMEN: documentos_data
│   │   ├── tomos/                  # ⭐ TOMOS PDFs (120 MB)
│   │   │   ├── carpeta_1/
│   │   │   │   └── tomo_1/
│   │   │   │       └── tomo_1.pdf
│   │   │   ├── carpeta_2/
│   │   │   └── ...
│   │   └── profiles/               # Fotos de perfil
│   │       └── user_1.jpg
│
└── /FGJCDMX/                       # 📂 VOLUMEN: fgjcdmx_data
    ├── documentos/                 # Docs adicionales
    ├── exportaciones/              # Exportaciones JSON/Excel
    ├── logs/                       # Logs del sistema
    │   └── sistema_20251020.log
    └── temp/                       # Archivos temporales OCR
```

---

## ⚙️ **Configuración en el Código Backend**

### **En `app/config.py`:**

```python
UPLOAD_DIR = Path("/app/uploads")
TOMOS_DIR = UPLOAD_DIR / "tomos"
PROFILES_DIR = UPLOAD_DIR / "profiles"

FGJCDMX_DIR = Path("/FGJCDMX")
LOGS_DIR = FGJCDMX_DIR / "logs"
TEMP_DIR = FGJCDMX_DIR / "temp"
```

### **Al subir un tomo (controller):**

```python
# Crear estructura de directorios
carpeta_dir = TOMOS_DIR / f"carpeta_{carpeta_id}"
tomo_dir = carpeta_dir / f"tomo_{tomo_id}"
tomo_dir.mkdir(parents=True, exist_ok=True)

# Guardar PDF
pdf_path = tomo_dir / f"tomo_{tomo_id}.pdf"
with open(pdf_path, "wb") as f:
    f.write(await file.read())
```

---

## 🚨 **Problemas Comunes y Soluciones**

### **1. "No se pueden subir tomos"**

**Causa:** Permisos del volumen Docker

**Solución:**
```bash
# Dar permisos al directorio uploads
docker exec sistema_ocr_backend chown -R appuser:appuser /app/uploads
docker exec sistema_ocr_backend chmod -R 755 /app/uploads
```

### **2. "Los tomos desaparecen al reiniciar Docker"**

**Causa:** Volumen no está configurado como persistente

**Verificación:**
```bash
docker volume ls | findstr fj1_documentos_data
```

Si no aparece, el volumen se está creando como temporal.

**Solución:** Ya está correcto en tu `docker-compose.yml`

### **3. "No hay espacio para más tomos"**

**Verificar espacio:**
```bash
# Ver espacio en volúmenes Docker
docker system df -v

# Ver espacio en el disco de WSL2
wsl df -h
```

**Solución:**
```bash
# Limpiar imágenes y contenedores no usados
docker system prune -a

# Aumentar espacio de WSL2 (editar .wslconfig)
```

---

## 📝 **Script de Diagnóstico de Tomos**

Crea `verificar-tomos.bat`:

```batch
@echo off
echo ╔════════════════════════════════════════════════════════════════╗
echo ║            Diagnóstico de Almacenamiento de Tomos             ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

echo 📂 Ubicación de tomos en el contenedor:
docker exec sistema_ocr_backend pwd
echo.

echo 📊 Tamaño de tomos almacenados:
docker exec sistema_ocr_backend du -sh /app/uploads/tomos/
echo.

echo 📁 Estructura de directorios:
docker exec sistema_ocr_backend ls -lah /app/uploads/tomos/
echo.

echo 📄 Total de PDFs:
docker exec sistema_ocr_backend find /app/uploads/tomos/ -name "*.pdf" -type f 2>nul | find /c /v ""
echo.

echo 💾 Información del volumen Docker:
docker volume inspect fj1_documentos_data
echo.

echo ✅ Diagnóstico completado
pause
```

---

## 🎯 **Resumen - Lo Más Importante**

### **Para subir tomos:**
1. Ve a la interfaz web: http://localhost
2. Navega a "Carpetas" → Selecciona carpeta → "Agregar Tomo"
3. Sube el PDF
4. El sistema lo guarda automáticamente en `/app/uploads/tomos/`

### **Para hacer backup:**
```bash
docker cp sistema_ocr_backend:/app/uploads/tomos/ C:\Backups\tomos\
```

### **Para ver los tomos:**
```bash
docker exec sistema_ocr_backend ls -R /app/uploads/tomos/
```

### **Los tomos están en:**
- **Contenedor:** `/app/uploads/tomos/` (120 MB actualmente)
- **Volumen:** `fj1_documentos_data` (persistente)
- **Windows:** `\\wsl$\docker-desktop-data\data\docker\volumes\fj1_documentos_data\_data\`

---

**¡Los tomos están seguros en volúmenes Docker persistentes!** 🔒

Última actualización: 20 de octubre de 2025
