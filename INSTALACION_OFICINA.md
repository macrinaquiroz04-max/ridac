# 🚀 INSTALACIÓN EN OFICINA - Sistema OCR FGJCDMX

**Fecha:** 20 de octubre de 2025  
**Sistema completo y funcional** ✅

---

## 📋 REQUISITOS PREVIOS

1. **Docker Desktop instalado** (versión 28.4.0 o superior)
2. **WSL2 activado** (Windows Subsystem for Linux)
3. **Git instalado**
4. **8 GB RAM mínimo** (recomendado 16 GB)
5. **50 GB espacio en disco**

---

## 🔧 PASOS DE INSTALACIÓN

### 1️⃣ Clonar el repositorio

```powershell
cd C:\
git clone https://github.com/aduardolozada1958-star/sistemaocr.git
cd sistemaocr
```

### 2️⃣ Iniciar Docker Desktop

- Abrir Docker Desktop
- Esperar a que esté completamente iniciado (icono verde)
- Verificar que WSL2 esté activo

### 3️⃣ Configurar archivo .env (opcional)

Si necesitas cambiar puertos o contraseñas, crear archivo `.env`:

```env
POSTGRES_PASSWORD=1234
POSTGRES_DB=sistema_ocr
POSTGRES_USER=postgres
```

### 4️⃣ Construir e iniciar el sistema

**Opción A: Con internet disponible**
```powershell
docker-compose up -d --build
```

**Opción B: Sin internet (si ya tienes las imágenes)**
```powershell
.\start-docker-inteligente.bat
```

### 5️⃣ Esperar a que inicie (2-3 minutos)

Verificar estado:
```powershell
docker-compose ps
```

Deberías ver 4 contenedores **healthy** o **up**:
- ✅ sistema_ocr_backend
- ✅ sistema_ocr_db
- ✅ sistema_ocr_nginx
- ✅ sistema_ocr_pgadmin

### 6️⃣ Verificar que funciona

Abrir navegador en: **http://localhost**

---

## 👥 USUARIOS CREADOS

| Usuario  | Password      | Rol          | Descripción                    |
|----------|---------------|--------------|--------------------------------|
| eduardo  | loqe1998c33   | admin        | Administrador principal        |
| admin    | admin123      | trabajador   | Usuario de prueba (trabajador) |
| diana    | diana123      | subdirector  | Usuario de prueba (subdirector)|

---

## 📂 ESTRUCTURA DEL SISTEMA

```
Sistema OCR FGJCDMX
├── Frontend (Nginx)
│   ├── http://localhost - Login
│   ├── http://localhost/dashboard - Dashboard Admin
│   ├── http://localhost/carpetas - Gestión de Expedientes
│   ├── http://localhost/usuarios - Gestión de Usuarios
│   └── http://localhost/analisis-ia - Análisis Jurídico
│
├── Backend (FastAPI)
│   ├── http://localhost/api - API REST
│   ├── http://localhost/docs - Documentación Swagger
│   └── http://localhost/health - Health Check
│
├── Base de Datos (PostgreSQL)
│   ├── Puerto: 5432
│   └── Usuario/Pass: postgres/1234
│
└── PgAdmin (Gestión BD)
    ├── http://localhost:5050
    └── admin@fiscalia.gob.mx / admin123
```

---

## 🔍 VERIFICACIONES POST-INSTALACIÓN

### ✅ 1. Verificar Backend
```powershell
Invoke-WebRequest http://localhost/health
```
Debe responder: `{"status":"healthy","database":"connected"}`

### ✅ 2. Verificar Base de Datos
```powershell
docker exec -it sistema_ocr_db psql -U postgres -d sistema_ocr -c "\dt"
```
Debe mostrar lista de tablas.

### ✅ 3. Verificar Login
- Ir a: http://localhost
- Usuario: **eduardo**
- Password: **loqe1998c33**
- Debe entrar al dashboard

### ✅ 4. Verificar Carpetas
- Ir a: http://localhost/carpetas
- Debe aparecer carpeta: **CI-FDS_FDS-6-02_19270_09-2019**
- Con 1 tomo de 821 páginas

---

## 🛠️ COMANDOS ÚTILES

### Ver logs del sistema
```powershell
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f nginx
```

### Reiniciar un contenedor
```powershell
docker-compose restart backend
docker-compose restart nginx
```

### Detener el sistema
```powershell
docker-compose down
```

### Detener y eliminar volúmenes (⚠️ BORRA DATOS)
```powershell
docker-compose down -v
```

### Ver uso de espacio
```powershell
docker system df
```

---

## 🔄 ACTUALIZAR EL SISTEMA

Si hay cambios en el código:

```powershell
git pull origin main
docker-compose up -d --build backend
```

---

## 📊 VOLÚMENES DE DATOS

Los datos persisten en volúmenes de Docker:

| Volumen                | Contenido                      | Tamaño Aprox |
|------------------------|--------------------------------|--------------|
| fj1_postgres_data      | Base de datos PostgreSQL       | ~200 MB      |
| fj1_documentos_data    | PDFs de tomos subidos          | ~500 MB      |
| fj1_fgjcdmx_data       | Logs y archivos temporales     | ~50 MB       |
| fj1_pgadmin_data       | Configuración de PgAdmin       | ~10 MB       |

---

## ⚠️ SOLUCIÓN DE PROBLEMAS

### Error: Puerto 80 ocupado
```powershell
# Detener IIS o Xampp
Stop-Service -Name "W3SVC" -Force
```

### Error: Docker no inicia
```powershell
# Reiniciar WSL2
wsl --shutdown
# Reiniciar Docker Desktop
```

### Error: Base de datos vacía
```powershell
# Ejecutar scripts de inicialización
Get-Content backend/scripts/schema.sql | docker exec -i sistema_ocr_db psql -U postgres -d sistema_ocr
Get-Content backend/scripts/create_analisis_juridico_tables.sql | docker exec -i sistema_ocr_db psql -U postgres -d sistema_ocr
```

### Error: Imágenes no se descargan
```powershell
# Usar modo offline si ya tienes las imágenes
.\start-docker-offline.bat
```

---

## 📞 SOPORTE

**Repositorio:** https://github.com/aduardolozada1958-star/sistemaocr  
**Documentación completa:** Ver carpeta `/docs`

---

## ✅ CHECKLIST DE INSTALACIÓN

- [ ] Docker Desktop instalado y funcionando
- [ ] WSL2 activado
- [ ] Repositorio clonado
- [ ] Contenedores iniciados (`docker-compose ps`)
- [ ] Health check OK (`http://localhost/health`)
- [ ] Login exitoso (eduardo/loqe1998c33)
- [ ] Dashboard cargando
- [ ] Carpetas visibles
- [ ] PgAdmin accesible (opcional)

---

**🎉 ¡Sistema listo para producción!**

Última actualización: 20 de octubre de 2025
