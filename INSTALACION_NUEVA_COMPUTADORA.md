# 🖥️ Instalación en Nueva Computadora

Guía paso a paso para instalar y configurar el Sistema OCR en una computadora nueva desde el repositorio de GitHub.

---

## 📋 Prerrequisitos

Antes de comenzar, asegúrate de tener instalado:

1. **Git** - Para clonar el repositorio
   - Windows: https://git-scm.com/download/win
   - Linux: `sudo apt install git` o `sudo yum install git`

2. **Docker Desktop** - Para ejecutar los contenedores
   - Windows/Mac: https://www.docker.com/products/docker-desktop
   - Linux: https://docs.docker.com/engine/install/

---

## 🚀 Instalación Paso a Paso

### **Paso 1: Clonar el Repositorio**

```bash
# Clonar desde GitHub
git clone https://github.com/absolut98/sistemaocr.git

# Entrar al directorio
cd sistemaocr
```

---

### **Paso 2: Configurar Variables de Entorno**

El archivo `.env` **NO está en Git por seguridad** (contiene passwords). Debes crearlo:

#### **2.1 Copiar el archivo de ejemplo:**

**En Windows (PowerShell):**
```powershell
copy .env.example .env
copy backend\.env.example backend\.env
```

**En Linux/Mac:**
```bash
cp .env.example .env
cp backend/.env.example backend/.env
```

#### **2.2 Editar el archivo `.env` principal:**

Abre `.env` con un editor de texto y configura:

```env
# Base de Datos PostgreSQL
POSTGRES_USER=sistema_ocr
POSTGRES_PASSWORD=TU_PASSWORD_SEGURO_AQUI    # ⚠️ CAMBIAR
POSTGRES_DB=sistema_ocr
DATABASE_URL=postgresql://sistema_ocr:TU_PASSWORD_SEGURO_AQUI@db:5432/sistema_ocr

# Seguridad
SECRET_KEY=tu_clave_secreta_jwt_muy_larga_y_segura_aqui    # ⚠️ CAMBIAR
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# API
API_HOST=0.0.0.0
API_PORT=8000

# PgAdmin (opcional)
PGADMIN_DEFAULT_EMAIL=admin@sistemaocr.local
PGADMIN_DEFAULT_PASSWORD=admin123    # ⚠️ CAMBIAR
```

**🔐 Importante:**
- Cambia `TU_PASSWORD_SEGURO_AQUI` por una contraseña fuerte
- Genera `SECRET_KEY` único (puedes usar: `openssl rand -hex 32`)
- Usa el mismo password en `POSTGRES_PASSWORD` y `DATABASE_URL`

#### **2.3 Editar el archivo `backend/.env`:**

```env
DATABASE_URL=postgresql://sistema_ocr:TU_PASSWORD_SEGURO_AQUI@db:5432/sistema_ocr
SECRET_KEY=tu_clave_secreta_jwt_muy_larga_y_segura_aqui    # Usar la misma que arriba
```

---

### **Paso 3: Crear Directorios Necesarios**

Estos directorios NO están en Git porque contienen datos de usuario:

**En Windows (PowerShell):**
```powershell
mkdir -p C:\FGJCDMX\uploads
mkdir -p C:\FGJCDMX\logs
mkdir -p C:\FGJCDMX\temp
mkdir backups
```

**En Linux/Mac:**
```bash
mkdir -p /home/$USER/FGJCDMX/uploads
mkdir -p /home/$USER/FGJCDMX/logs
mkdir -p /home/$USER/FGJCDMX/temp
mkdir -p backups
```

**⚠️ Nota para Linux:** Edita `docker-compose.yml` y cambia las rutas de Windows por Linux:
```yaml
volumes:
  - /home/$USER/FGJCDMX:/FGJCDMX  # En lugar de C:/FGJCDMX
```

---

### **Paso 4: Iniciar Docker**

#### **4.1 Primera vez - Construir imágenes:**

**En Windows:**
```powershell
.\start-docker.bat
```

**En Linux/Mac:**
```bash
chmod +x demo-completo.sh
sudo docker-compose up -d --build
```

Esto descargará e instalará:
- PostgreSQL 15
- Backend FastAPI con Python
- Frontend Nginx
- PgAdmin (opcional)

⏱️ **Tiempo estimado:** 5-10 minutos la primera vez.

#### **4.2 Verificar que todo esté corriendo:**

```bash
sudo docker-compose ps
```

Deberías ver:
```
NAME                    STATUS
sistemaocr-backend-1    Up
sistemaocr-db-1         Up
sistemaocr-frontend-1   Up
```

---

### **Paso 5: Inicializar Base de Datos**

El sistema crea las tablas automáticamente al iniciar, pero necesitas crear el **primer usuario administrador**:

#### **5.1 Entrar al contenedor del backend:**

**En Windows (PowerShell):**
```powershell
docker exec -it sistemaocr-backend-1 bash
```

**En Linux/Mac:**
```bash
sudo docker exec -it sistemaocr-backend-1 bash
```

#### **5.2 Crear usuario administrador:**

Dentro del contenedor, ejecuta:

```bash
python -c "
from app.database import get_db, Base, engine
from app.models import Usuario
from app.utils.password import get_password_hash
from sqlalchemy.orm import Session

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Crear usuario admin
db = next(get_db())
admin = Usuario(
    username='admin',
    email='admin@fgjcdmx.gob.mx',
    password_hash=get_password_hash('admin123'),  # ⚠️ Cambiar después
    nombre_completo='Administrador del Sistema',
    rol='admin',
    activo=True
)
db.add(admin)
db.commit()
print('✅ Usuario admin creado')
"

exit
```

**🔐 Importante:** Cambia la contraseña `admin123` después del primer login.

---

### **Paso 6: Acceder al Sistema**

Abre tu navegador en:

- 🌐 **Frontend (Sistema):** http://localhost
- 📚 **API Docs:** http://localhost/api/docs
- 🗄️ **PgAdmin:** http://localhost:5050

**Credenciales iniciales:**
- Usuario: `admin`
- Contraseña: `admin123` (cambiar inmediatamente)

---

## 🔧 Configuración Adicional (Opcional)

### **Configurar DNS Local (Windows)**

Para usar `sistema-ocr.local` en lugar de `localhost`:

1. Abre el archivo hosts como administrador:
   ```
   C:\Windows\System32\drivers\etc\hosts
   ```

2. Agrega la línea:
   ```
   127.0.0.1    sistema-ocr.local
   ```

3. Guarda y cierra

4. Accede en: http://sistema-ocr.local

### **Configurar DNS Local (Linux/Mac)**

```bash
sudo nano /etc/hosts
```

Agrega:
```
127.0.0.1    sistema-ocr.local
```

---

## 🛠️ Comandos Útiles

### **Ver logs del sistema:**

```bash
# Ver logs del backend
sudo docker-compose logs -f backend

# Ver logs de todos los servicios
sudo docker-compose logs -f
```

### **Reiniciar servicios:**

```bash
# Reiniciar todo
sudo docker-compose restart

# Reiniciar solo backend
sudo docker-compose restart backend
```

### **Detener el sistema:**

```bash
sudo docker-compose down
```

### **Actualizar desde Git:**

```bash
# Obtener últimos cambios
git pull origin main

# Reconstruir y reiniciar
sudo docker-compose up -d --build
```

---

## 📦 Restaurar un Respaldo (Opcional)

Si tienes un respaldo de la base de datos:

```bash
# Copiar el archivo .sql al proyecto
cp /ruta/backup.sql backups/

# Restaurar en el contenedor de PostgreSQL
cat backups/backup.sql | sudo docker exec -i sistemaocr-db-1 psql -U sistema_ocr -d sistema_ocr
```

---

## ❓ Problemas Comunes

### **Error: "Cannot connect to Docker daemon"**

**Solución:**
- Asegúrate de que Docker Desktop está corriendo
- En Linux: `sudo systemctl start docker`

### **Error: "Port 80 is already allocated"**

**Solución:**
- Otro servicio está usando el puerto 80
- Cambia el puerto en `docker-compose.yml`:
  ```yaml
  ports:
    - "8080:80"  # Usar puerto 8080 en lugar de 80
  ```

### **Error: "Database connection failed"**

**Solución:**
- Verifica que el password en `.env` y `backend/.env` sea el mismo
- Reinicia los contenedores: `sudo docker-compose restart`

### **Error: "No module named 'app'"**

**Solución:**
- Reconstruye el backend: `sudo docker-compose build backend`

---

## 🔒 Seguridad - Lista de Verificación

Antes de usar en producción:

- [ ] Cambiar password de `admin`
- [ ] Cambiar `SECRET_KEY` en `.env`
- [ ] Cambiar `POSTGRES_PASSWORD`
- [ ] Cambiar password de PgAdmin
- [ ] Configurar firewall (solo puertos necesarios)
- [ ] Habilitar HTTPS con certificados SSL
- [ ] Configurar backups automáticos

---

## 📞 Soporte

Si tienes problemas:

1. Revisa los logs: `sudo docker-compose logs -f backend`
2. Consulta `SOLUCION_PROBLEMAS.md`
3. Verifica que todos los archivos `.env` estén configurados
4. Asegúrate de que Docker Desktop está corriendo

---

## 📄 Archivos que NO están en Git

Estos archivos debes crearlos/configurarlos manualmente:

```
❌ .env                          # Variables de entorno (copiar de .env.example)
❌ backend/.env                  # Variables del backend
❌ C:/FGJCDMX/                   # Directorio de datos
❌ logs/*.log                    # Archivos de log
❌ backups/*.sql                 # Respaldos de BD
```

**Razón:** Contienen información sensible (passwords, datos de usuario) que no debe estar en un repositorio público.

---

## ✅ Verificación Final

Para verificar que todo está bien:

```bash
# 1. Verificar contenedores corriendo
sudo docker-compose ps

# 2. Verificar logs sin errores
sudo docker-compose logs backend | tail -20

# 3. Probar API
curl http://localhost/api/health

# 4. Abrir navegador
# http://localhost
```

Si todo muestra `✅` o `STATUS: Up`, ¡el sistema está listo! 🎉

---

**Desarrollado por:** Eduardo Lozada Quiroz, ISC  
**Cliente:** Fiscalía General de Justicia CDMX - Unidad de Análisis y Contexto
