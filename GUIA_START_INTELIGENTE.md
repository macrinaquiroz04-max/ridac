# 🧠 Script Inteligente de Inicio Docker

## 🎯 ¿Qué hace `start-docker-inteligente.bat`?

Este script **detecta automáticamente** si necesita descargar imágenes de internet o puede iniciar el sistema en modo offline.

---

## 🚀 Uso

```bash
.\start-docker-inteligente.bat
```

**El script decide por ti:**
- ✅ Si todas las imágenes están locales → Inicia **SIN internet** (modo offline)
- 🌐 Si faltan imágenes → Descarga solo las que faltan y luego inicia

---

## 🔍 ¿Cómo funciona?

### **Paso 1: Verificación de imágenes**

El script verifica si existen localmente:
- `postgres:15-alpine`
- `nginx:alpine`
- `dpage/pgadmin4:latest`
- `python:3.11-slim`

### **Paso 2: Decisión automática**

#### **Escenario A: Todas las imágenes existen ✅**
```
═══════════════════════════════════════════════════════════════
🎯 TODAS LAS IMÁGENES DISPONIBLES LOCALMENTE
═══════════════════════════════════════════════════════════════

✅ Iniciando en MODO OFFLINE (sin descargar nada)
```

**Acciones:**
1. NO intenta descargar nada de internet
2. Inicia contenedores con `docker-compose up -d --no-build`
3. Sistema listo en segundos

#### **Escenario B: Faltan imágenes ⚠️**
```
═══════════════════════════════════════════════════════════════
⚠️  FALTAN 2 IMAGEN(ES)
═══════════════════════════════════════════════════════════════

🌐 Se necesita INTERNET para descargar imágenes faltantes
```

**Acciones:**
1. Verifica si hay conexión a Docker Hub
2. Si hay conexión:
   - Descarga SOLO las imágenes que faltan
   - Construye el backend si es necesario
   - Inicia el sistema
3. Si NO hay conexión:
   - Muestra opciones alternativas
   - No falla, te explica qué hacer

---

## 📊 Comparación de Scripts

| Script | Cuándo usar | Necesita Internet |
|--------|-------------|-------------------|
| **start-docker-inteligente.bat** | ⭐ Siempre (detecta automáticamente) | Solo si falta algo |
| **start-docker.bat** | Cuando todo está listo | Puede intentar rebuild |
| **start-docker-offline.bat** | Forzar modo offline | ❌ No |

---

## 🎯 Casos de Uso

### **Caso 1: Primera vez (PC nueva)**
```bash
.\start-docker-inteligente.bat
```
**Resultado:**
- Detecta que faltan imágenes
- Descarga todo lo necesario
- Construye el backend
- Inicia el sistema

### **Caso 2: PC con imágenes ya descargadas**
```bash
.\start-docker-inteligente.bat
```
**Resultado:**
- Detecta que todo está local
- NO descarga nada
- Inicia en modo offline
- Rápido (5-10 segundos)

### **Caso 3: Sin conexión a internet**
```bash
.\start-docker-inteligente.bat
```
**Resultado:**
- Detecta que faltan imágenes
- Detecta que NO hay internet
- Te explica cómo copiar imágenes desde otra PC
- No falla abruptamente

---

## 🛠️ Flujo de Decisión (Diagrama)

```
Inicio
  │
  ├─> Verificar Docker instalado
  │   ├─ ❌ No → Error y salir
  │   └─ ✅ Sí → Continuar
  │
  ├─> Verificar Docker corriendo
  │   ├─ ❌ No → Pedir iniciar Docker Desktop
  │   └─ ✅ Sí → Continuar
  │
  ├─> Detectar imágenes locales
  │   │
  │   ├─> ✅ TODAS presentes
  │   │   └─> MODO OFFLINE
  │   │       ├─ docker-compose up -d --no-build
  │   │       └─ Sistema listo (SIN internet)
  │   │
  │   └─> ⚠️ Faltan algunas
  │       │
  │       ├─> Verificar internet
  │       │   │
  │       │   ├─> ✅ Hay internet
  │       │   │   ├─ docker pull <imagen_faltante>
  │       │   │   ├─ docker-compose build backend
  │       │   │   └─ docker-compose up -d
  │       │   │
  │       │   └─> ❌ No hay internet
  │       │       ├─ Mostrar mensaje de error
  │       │       ├─ Sugerir alternativas
  │       │       └─ Salir sin fallar
  │       │
  │       └─> Sistema listo
  │
  └─> Fin
```

---

## 💡 Ventajas

### ✅ **Inteligente:**
- Detecta automáticamente qué necesita
- No descarga cosas innecesarias
- Ahorra tiempo y ancho de banda

### ✅ **Robusto:**
- Funciona con o sin internet
- Maneja errores elegantemente
- No falla si ya está corriendo

### ✅ **Informativo:**
- Muestra exactamente qué está haciendo
- Indica qué modo usó (online/offline)
- Explica por qué necesita internet (si aplica)

### ✅ **Rápido:**
- Si todo está local: 5-10 segundos
- Solo descarga lo que falta

---

## 🔧 Detalles Técnicos

### **Verificación de imágenes:**
```batch
docker images -q postgres:15-alpine >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Falta: postgres:15-alpine
    set /a MISSING_IMAGES+=1
)
```

### **Verificación de internet:**
```batch
curl -s --max-time 5 https://hub.docker.com >nul 2>&1
if errorlevel 1 (
    echo ❌ NO HAY CONEXIÓN A INTERNET
    REM Mostrar alternativas
)
```

### **Inicio offline:**
```batch
docker-compose up -d --no-build
```
- `--no-build`: No reconstruye imágenes
- `-d`: Modo daemon (segundo plano)

### **Inicio con descarga:**
```batch
docker pull <imagen_faltante>
docker-compose build backend
docker-compose up -d
```

---

## 📝 Logs y Mensajes

### **Modo Offline:**
```
✅ Existe: postgres:15-alpine
✅ Existe: nginx:alpine
✅ Existe: dpage/pgadmin4:latest
✅ Existe: python:3.11-slim

═══════════════════════════════════════════════════════════════
🎯 TODAS LAS IMÁGENES DISPONIBLES LOCALMENTE
═══════════════════════════════════════════════════════════════

✅ Iniciando en MODO OFFLINE (sin descargar nada)

💡 Modo usado: OFFLINE (sin internet)
```

### **Modo Online:**
```
⚠️  Falta: postgres:15-alpine
✅ Existe: nginx:alpine
⚠️  Falta: dpage/pgadmin4:latest
✅ Existe: python:3.11-slim

═══════════════════════════════════════════════════════════════
⚠️  FALTAN 2 IMAGEN(ES)
═══════════════════════════════════════════════════════════════

🌐 Se necesita INTERNET para descargar imágenes faltantes
✅ Conexión a Docker Hub detectada

📥 Descargando imágenes faltantes...
📦 Descargando postgres:15-alpine...
📦 Descargando dpage/pgadmin4:latest...

💡 Modo usado: ONLINE (descargó 2 imagen/es)
```

---

## 🆘 Resolución de Problemas

### **Problema: "Falta imagen pero no hay internet"**

**Solución 1: Copiar imagen desde otra PC**
```bash
# En PC con internet:
docker save postgres:15-alpine -o postgres.tar

# Copiar postgres.tar a USB/red

# En PC sin internet:
docker load -i postgres.tar
```

**Solución 2: Descargar todas las imágenes de antemano**
```bash
# Cuando tengas internet, ejecuta:
docker pull postgres:15-alpine
docker pull nginx:alpine
docker pull dpage/pgadmin4:latest
docker pull python:3.11-slim
docker-compose build backend
```

### **Problema: "Dice offline pero intenta descargar"**

Verifica si el backend necesita reconstruirse:
```bash
docker images | findstr fj1-backend
```

Si no existe `fj1-backend`, necesitas construirlo:
```bash
docker-compose build backend
```

---

## 🎯 Recomendaciones

### **Para Desarrollo (con internet frecuente):**
```bash
.\start-docker-inteligente.bat
```
- Siempre actualizado
- Descarga solo lo nuevo

### **Para Producción (sin internet garantizado):**
```bash
# 1. Pre-descargar todo (con internet):
docker pull postgres:15-alpine
docker pull nginx:alpine
docker pull dpage/pgadmin4:latest
docker pull python:3.11-slim
docker-compose build backend

# 2. Luego usa:
.\start-docker-inteligente.bat
```
- Siempre usará modo offline
- Rápido y confiable

### **Para Servidores Aislados:**
```bash
# 1. Exportar imágenes en PC con internet:
docker save postgres:15-alpine nginx:alpine dpage/pgadmin4:latest -o imagenes.tar
docker save fj1-backend -o backend.tar

# 2. Copiar al servidor

# 3. Cargar en servidor:
docker load -i imagenes.tar
docker load -i backend.tar

# 4. Iniciar:
.\start-docker-inteligente.bat
```

---

## 📊 Estadísticas de Uso

### **Primera ejecución (sin imágenes):**
- Tiempo: ~5-10 minutos (según internet)
- Descarga: ~800 MB
- Builds: 1 (backend)

### **Ejecuciones subsecuentes (imágenes locales):**
- Tiempo: ~5-10 segundos
- Descarga: 0 MB
- Builds: 0

---

## ✅ Checklist de Preparación

- [ ] Docker Desktop instalado y corriendo
- [ ] Ejecutar script al menos una vez con internet
- [ ] Verificar que todas las imágenes se descargaron:
  ```bash
  docker images | findstr "postgres nginx pgadmin fj1-backend"
  ```
- [ ] Probar modo offline:
  - Desconectar internet
  - Ejecutar `.\start-docker-inteligente.bat`
  - Debe iniciar sin errores

---

**¡Script listo para usar en cualquier situación!** 🎉

Última actualización: 20 de octubre de 2025
