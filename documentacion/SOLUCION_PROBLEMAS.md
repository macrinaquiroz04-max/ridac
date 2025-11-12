# 🔧 Solución de Problemas - Sistema OCR Fiscalía

## 🚨 Error: Docker Hub no disponible (503 Service Unavailable)

### Síntoma:
```
ERROR [internal] load metadata for docker.io/library/python:3.11-slim
failed to fetch oauth token: unexpected status from POST request to 
https://auth.docker.io/token: 503 Service Unavailable
```

### ✅ Soluciones:

#### **Opción 1: Esperar y reintentar** (Recomendado)
Docker Hub puede estar temporalmente caído. Espera 5-10 minutos y ejecuta:
```bash
.\start-docker.bat
```

#### **Opción 2: Usar modo OFFLINE** (Si las imágenes ya están descargadas)
```bash
.\start-docker-offline.bat
```

#### **Opción 3: Verificar imágenes locales**
```bash
.\diagnostico-docker.bat
```

#### **Opción 4: Descargar imágenes manualmente** (Cuando Docker Hub vuelva)
```bash
docker pull postgres:15-alpine
docker pull python:3.11-slim
docker pull nginx:alpine
docker pull dpage/pgadmin4:latest
```

---

## 🐳 Problemas Comunes de Docker

### 1. **Docker Desktop no está corriendo**

**Síntoma:** Error "Docker daemon is not running"

**Solución:**
1. Abre Docker Desktop desde el menú Inicio
2. Espera a que el ícono de Docker sea verde
3. Ejecuta de nuevo `.\start-docker.bat`

---

### 2. **Puerto 80 o 5432 ya está en uso**

**Síntoma:** Error "port is already allocated"

**Solución:**
```bash
# Ver qué proceso usa el puerto
netstat -ano | findstr :80
netstat -ano | findstr :5432

# Detener todos los contenedores
docker-compose down

# Reiniciar
.\start-docker.bat
```

---

### 3. **Contenedores no inician correctamente**

**Síntoma:** Contenedor en estado "Restarting" o "Exited"

**Solución:**
```bash
# Ver logs del contenedor problemático
docker-compose logs backend
docker-compose logs postgres
docker-compose logs nginx

# Reiniciar contenedor específico
docker-compose restart backend

# Reconstruir desde cero
docker-compose down -v
.\start-docker.bat
```

---

### 4. **Base de datos no se conecta**

**Síntoma:** Backend muestra "Connection refused" o "could not connect to server"

**Solución:**
```bash
# Verificar que PostgreSQL esté corriendo
docker-compose ps

# Ver logs de PostgreSQL
docker-compose logs postgres

# Reiniciar PostgreSQL
docker-compose restart postgres

# Esperar 30 segundos y reiniciar backend
timeout /t 30
docker-compose restart backend
```

---

### 5. **Frontend muestra página en blanco o error 502**

**Síntoma:** http://localhost no carga o muestra "Bad Gateway"

**Solución:**
```bash
# Verificar estado de nginx y backend
docker-compose ps

# Ver logs
docker-compose logs nginx
docker-compose logs backend

# Reiniciar servicios
docker-compose restart nginx backend
```

---

### 6. **Error "version is obsolete"** (Warning - no crítico)

**Síntoma:**
```
level=warning msg="docker-compose.yml: the attribute `version` is obsolete"
```

**Solución:** Ya está corregido en la última versión del docker-compose.yml. Si ves este warning, ignóralo (no afecta funcionalidad).

---

### 7. **Disco lleno / Sin espacio**

**Síntoma:** Error "no space left on device"

**Solución:**
```bash
# Ver espacio usado por Docker
docker system df

# Limpiar contenedores e imágenes no usadas
docker system prune -a

# Limpiar volúmenes (¡CUIDADO! Borra datos)
docker volume prune
```

---

## 📊 Comandos de Diagnóstico

### Ver estado del sistema:
```bash
.\diagnostico-docker.bat
```

### Ver estado de contenedores:
```bash
docker-compose ps
```

### Ver logs en tiempo real:
```bash
docker-compose logs -f
```

### Ver logs de un servicio específico:
```bash
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f nginx
```

### Ver recursos usados:
```bash
docker stats
```

### Ejecutar comando dentro de un contenedor:
```bash
# Abrir consola en backend
docker exec -it sistema_ocr_backend bash

# Abrir consola SQL en PostgreSQL
docker exec -it sistema_ocr_db psql -U postgres -d sistema_ocr
```

---

## 🔄 Comandos de Reinicio

### Reinicio suave (mantiene datos):
```bash
docker-compose restart
```

### Reinicio completo (mantiene datos):
```bash
docker-compose down
.\start-docker.bat
```

### Reinicio desde cero (BORRA TODOS LOS DATOS):
```bash
docker-compose down -v
.\start-docker.bat
```

---

## 🆘 Último Recurso: Reset Completo

Si nada funciona, haz un reset completo:

```bash
# 1. Detener todo
docker-compose down -v

# 2. Limpiar Docker completamente
docker system prune -a --volumes

# 3. Reiniciar Docker Desktop

# 4. Iniciar desde cero
.\start-docker.bat
```

**⚠️ ADVERTENCIA:** Esto eliminará TODOS los datos, incluida la base de datos.

---

## 📞 Verificar que Todo Funciona

Después de solucionar el problema:

1. **Verificar contenedores:**
   ```bash
   .\ver-estado.bat
   ```
   Debe mostrar todos los servicios "Up" o "Healthy"

2. **Probar el frontend:**
   - Abre: http://localhost
   - Debe cargar la página de login

3. **Probar el backend:**
   - Abre: http://localhost/api/docs
   - Debe mostrar la documentación de Swagger

4. **Probar PgAdmin:**
   - Abre: http://localhost:5050
   - Login: admin@fiscalia.gob.mx / admin123

---

## 🌐 Problemas de Conectividad

### No puedo acceder desde otra computadora en la red

**Solución:**
```bash
# 1. Ejecuta esto para configurar el dominio
.\configurar-dominio-fgjcdmx.bat

# 2. Agrega regla de firewall
netsh advfirewall firewall add rule name="Sistema OCR HTTP" dir=in action=allow protocol=TCP localport=80

# 3. Accede desde otra PC usando:
http://IP_DEL_SERVIDOR
http://fgjcdmx (si configuraste DNS)
```

---

## 📝 Crear un Reporte de Error

Si necesitas ayuda, recopila esta información:

```bash
# 1. Información del sistema
docker --version
docker-compose --version

# 2. Estado de contenedores
docker-compose ps > error-report.txt

# 3. Logs
docker-compose logs >> error-report.txt

# 4. Información del sistema
docker info >> error-report.txt

# 5. Enviar error-report.txt para análisis
```

---

**Última actualización:** 20 de octubre de 2025
