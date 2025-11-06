# 🏛️ Guía de Despliegue para Fiscalía - Sistema OCR

## 📋 Requisitos del Servidor

### Hardware Mínimo
- **CPU**: Intel Core i5 (4 núcleos) o superior
- **RAM**: 16 GB (recomendado 32 GB)
- **Disco**: 500 GB SSD
- **Red**: Gigabit Ethernet

### Software
- **Sistema Operativo**: Windows 10 Pro/Enterprise o Windows Server 2019/2022
- **Docker Desktop**: Versión 4.x o superior
- **Navegador**: Chrome, Edge o Firefox actualizado

---

## 🔧 Instalación en Servidor de Fiscalía

### Paso 1: Preparar el Servidor

1. **Actualizar Windows**
```powershell
# Ejecutar Windows Update
# Reiniciar si es necesario
```

2. **Habilitar Virtualización**
- Verificar en BIOS que Intel VT-x o AMD-V esté habilitado
- Verificar en Windows:
```powershell
systeminfo | findstr /i "Hyper-V"
```

3. **Instalar Docker Desktop**
- Descargar: https://www.docker.com/products/docker-desktop
- Ejecutar instalador
- Reiniciar servidor
- Verificar instalación:
```powershell
docker --version
docker-compose --version
```

### Paso 2: Copiar el Proyecto

1. **Crear carpeta en servidor**
```powershell
# Ejemplo: D:\Sistemas\SistemaOCR
mkdir D:\Sistemas\SistemaOCR
cd D:\Sistemas\SistemaOCR
```

2. **Copiar todos los archivos del proyecto**
- Copiar carpeta completa `FJ1` al servidor
- Asegurar que se incluyan subcarpetas y archivos ocultos

### Paso 3: Configurar Variables de Entorno

1. **Copiar archivo de configuración**
```powershell
copy .env.example .env
```

2. **Editar .env con contraseñas seguras**
```powershell
notepad .env
```

**IMPORTANTE**: Cambiar estas variables:
```env
# Base de datos
DB_PASSWORD=ContraseñaSeguraPostgres2024!

# Seguridad JWT
JWT_SECRET_KEY=ClaveSecretaMuyLargaYAleatoria123456789ABC

# PgAdmin
PGADMIN_DEFAULT_EMAIL=admin@fiscalia.cdmx.gob.mx
PGADMIN_DEFAULT_PASSWORD=AdminPgAdmin2024!
```

### Paso 4: Configurar Firewall de Windows

```powershell
# Ejecutar PowerShell como Administrador

# Permitir puerto 80 (HTTP)
New-NetFirewallRule -DisplayName "Sistema OCR - HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow

# Permitir puerto 443 (HTTPS) - Opcional
New-NetFirewallRule -DisplayName "Sistema OCR - HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow

# Permitir puerto 5050 (PgAdmin) - Solo desde red local
New-NetFirewallRule -DisplayName "Sistema OCR - PgAdmin" -Direction Inbound -LocalPort 5050 -Protocol TCP -Action Allow -RemoteAddress LocalSubnet
```

### Paso 5: Iniciar el Sistema

```powershell
# Ejecutar el script de inicio
start-docker.bat
```

Esperar a que muestre:
```
✅ Contenedores iniciados correctamente
```

### Paso 6: Verificar Instalación

```powershell
# Ver estado del sistema
ver-estado.bat
```

Todos los servicios deben mostrar "running" (corriendo).

### Paso 7: Configurar Usuario Administrador

1. **Acceder a http://localhost**
2. **Iniciar sesión con usuario por defecto**:
   - Usuario: `admin`
   - Contraseña: `admin123`

3. **Cambiar contraseña del administrador**:
   - Ir a Configuración → Cambiar Contraseña
   - Establecer contraseña segura

4. **Crear usuarios adicionales**:
   - Ir a Panel de Administración → Usuarios
   - Crear usuarios para cada persona autorizada

---

## 🔒 Configuración de Seguridad

### 1. Contraseñas Fuertes

Todas las contraseñas deben cumplir:
- Mínimo 12 caracteres
- Mayúsculas y minúsculas
- Números
- Caracteres especiales
- No usar palabras del diccionario

### 2. Respaldos Automáticos

Crear tarea programada para backups diarios:

```powershell
# Crear script de backup automático
# Guardar como: C:\Scripts\backup-diario.bat
```

Contenido del script:
```batch
@echo off
cd D:\Sistemas\SistemaOCR
call backup-database.bat
```

**Programar en Programador de Tareas de Windows**:
1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Nombre: "Backup Sistema OCR"
4. Desencadenador: Diario a las 2:00 AM
5. Acción: Iniciar programa → `C:\Scripts\backup-diario.bat`

### 3. Monitoreo

Crear script de monitoreo:
```powershell
# Ejecutar cada hora para verificar salud
D:\Sistemas\SistemaOCR\ver-estado.bat > D:\Logs\estado-sistema.log
```

### 4. Logs de Auditoría

Los logs se guardan automáticamente en:
- PostgreSQL: Auditoría de accesos y cambios
- Backend: `logs/` dentro del volumen Docker
- Nginx: Logs de acceso HTTP

Para ver logs:
```powershell
ver-logs.bat
```

---

## 🌐 Acceso desde Red Local

### Configurar IP Estática

1. **Obtener IP del servidor**
```powershell
ipconfig
# Anotar IPv4 Address, ej: 192.168.1.100
```

2. **Configurar IP estática en Windows**
- Panel de Control → Redes → Adaptador de red
- Propiedades → IPv4 → Configurar IP manual
- Establecer IP fija, máscara de subred, gateway y DNS

3. **Actualizar hosts en clientes** (opcional)
```
# En cada PC cliente, editar: C:\Windows\System32\drivers\etc\hosts
# Agregar línea:
192.168.1.100    sistema-ocr.fiscalia.local
```

### Acceso desde Clientes

Los usuarios accederán mediante:
- **URL**: http://192.168.1.100 (IP del servidor)
- **URL amigable**: http://sistema-ocr.fiscalia.local (si se configuró hosts)

---

## 📊 Mantenimiento

### Diario
- [ ] Verificar que el sistema esté corriendo: `ver-estado.bat`
- [ ] Revisar logs en busca de errores: `ver-logs.bat`
- [ ] Verificar espacio en disco

### Semanal
- [ ] Crear backup manual: `backup-database.bat`
- [ ] Revisar backups automáticos
- [ ] Verificar actualizaciones de Docker Desktop

### Mensual
- [ ] Actualizar sistema operativo Windows
- [ ] Revisar usuarios activos e inactivos
- [ ] Limpiar archivos temporales
- [ ] Verificar logs de auditoría

---

## 🆘 Procedimientos de Emergencia

### Sistema No Responde

```powershell
# 1. Verificar estado
ver-estado.bat

# 2. Ver logs para identificar problema
ver-logs.bat

# 3. Reiniciar servicios
stop-docker.bat
start-docker.bat
```

### Error de Base de Datos

```powershell
# 1. Detener sistema
stop-docker.bat

# 2. Verificar backups disponibles
dir backups

# 3. Restaurar último backup
restaurar-backup.bat

# 4. Reiniciar sistema
start-docker.bat
```

### Pérdida de Datos

```powershell
# 1. Detener sistema inmediatamente
stop-docker.bat

# 2. NO reiniciar hasta analizar
# 3. Contactar soporte técnico
# 4. Preparar último backup conocido
```

### Servidor Reiniciado Inesperadamente

```powershell
# El sistema NO se inicia automáticamente
# Ejecutar manualmente después de reinicio:
cd D:\Sistemas\SistemaOCR
start-docker.bat
```

**Para inicio automático** (opcional):
1. Crear acceso directo a `start-docker.bat`
2. Copiar a: `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp`

---

## 📞 Contactos de Soporte

### Soporte Técnico Interno
- **Responsable**: [Nombre del responsable técnico]
- **Teléfono**: [Número de contacto]
- **Email**: [Email de soporte]

### Escalamiento
- **Director de TI**: [Nombre]
- **Teléfono**: [Número]

### Documentación de Ayuda
1. `README.md` - Información general
2. `DOCKER_GUIA_INSTALACION.md` - Guía completa de Docker
3. `INSTALACION_DOCKER.md` - Instalación de Docker Desktop
4. `LEEME_PRIMERO.md` - Funcionalidades del sistema

---

## 📋 Checklist de Entrega

### Instalación Completada
- [ ] Docker Desktop instalado y funcionando
- [ ] Proyecto copiado en servidor
- [ ] Variables de entorno configuradas (`.env`)
- [ ] Contraseñas cambiadas a valores seguros
- [ ] Firewall configurado correctamente
- [ ] Sistema iniciado exitosamente
- [ ] Todos los contenedores corriendo (4/4)

### Configuración
- [ ] IP estática configurada
- [ ] Acceso desde red local verificado
- [ ] Usuario administrador con contraseña segura
- [ ] Al menos 2 usuarios de prueba creados
- [ ] Permisos asignados correctamente

### Seguridad
- [ ] Todas las contraseñas por defecto cambiadas
- [ ] Backup manual creado y probado
- [ ] Backup automático programado
- [ ] Logs de auditoría verificados
- [ ] Acceso restringido a personal autorizado

### Capacitación
- [ ] Personal técnico capacitado en mantenimiento
- [ ] Usuarios finales capacitados en uso del sistema
- [ ] Documentación entregada
- [ ] Procedimientos de emergencia explicados
- [ ] Contactos de soporte registrados

### Pruebas
- [ ] Login de usuarios funcional
- [ ] Carga de documentos PDF funcional
- [ ] Procesamiento OCR funcional
- [ ] Búsqueda de texto funcional
- [ ] Análisis jurídico funcional
- [ ] Exportación de datos funcional
- [ ] Backup y restauración probados

---

## 🎓 Capacitación Recomendada

### Para Administradores del Sistema (4 horas)

**Módulo 1: Operación Básica (1 hora)**
- Iniciar y detener sistema
- Verificar estado
- Ver logs
- Crear backups

**Módulo 2: Mantenimiento (1 hora)**
- Gestión de usuarios
- Permisos y roles
- Monitoreo de recursos
- Limpieza de archivos

**Módulo 3: Troubleshooting (1 hora)**
- Problemas comunes y soluciones
- Lectura de logs
- Reinicio de servicios
- Restauración de backups

**Módulo 4: Seguridad (1 hora)**
- Mejores prácticas
- Auditoría de accesos
- Configuración de firewall
- Procedimientos de emergencia

### Para Usuarios Finales (2 horas)

**Módulo 1: Introducción (30 min)**
- Login y navegación
- Dashboard principal
- Conceptos básicos

**Módulo 2: Uso del Sistema (1 hora)**
- Crear carpetas de investigación
- Subir documentos PDF
- Procesar OCR
- Búsqueda de información

**Módulo 3: Funciones Avanzadas (30 min)**
- Análisis jurídico automatizado
- Búsqueda semántica
- Exportación de datos
- Generación de reportes

---

## ✅ Firma de Aceptación

Al finalizar la instalación y capacitación:

**Sistema instalado y aceptado por:**

Nombre: ______________________________
Cargo: ______________________________
Fecha: ______________________________
Firma: ______________________________

**Sistema entregado por:**

Nombre: ______________________________
Cargo: ______________________________
Fecha: ______________________________
Firma: ______________________________

---

**¡Sistema listo para operar en la Fiscalía!** 🎉
