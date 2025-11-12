# 🔍 SISTEMA DE AUDITORÍA COMPLETO - OCR FGJCDMX

## 📋 **Resumen del Sistema**

El Sistema de Auditoría permite monitorear **TODAS** las actividades de los usuarios en el sistema OCR FGJCDMX, proporcionando trazabilidad completa y detección de eventos críticos.

### ✅ **Funcionalidades Implementadas:**
- 📊 **Monitoreo en Tiempo Real** de todas las acciones
- 🔍 **Consultas Avanzadas** por usuario, fecha, IP y tipo de acción
- 🚨 **Detección de Eventos Críticos** (eliminaciones, cambios de permisos)
- 📈 **Estadísticas Detalladas** de actividad del sistema
- 🌐 **Interfaz Web** para consulta visual
- 💻 **Herramientas de Línea de Comandos** para administradores

---

## 🛠️ **Herramientas Disponibles**

### 1. **🖥️ Interfaz Web de Auditoría**
**Acceso**: `http://fgj-ocr.local/auditoria.html`

**Características:**
- ✅ Dashboard con estadísticas en tiempo real
- ✅ Filtros por usuario, acción, fecha e IP
- ✅ Actualización automática cada 30 segundos
- ✅ Visualización de eventos críticos destacados
- ✅ Exportación de datos

### 2. **💻 Script de Administración**
**Comando**: `./scripts/auditoria-admin.sh`

**Funciones disponibles:**
```bash
# Ver auditoría de usuario específico
./scripts/auditoria-admin.sh usuario eduardo 7

# Estadísticas generales
./scripts/auditoria-admin.sh estadisticas 30

# Eventos críticos
./scripts/auditoria-admin.sh criticos 7

# Eventos desde IP específica
./scripts/auditoria-admin.sh ip 192.168.1.100 30

# Resumen de actividad por días
./scripts/auditoria-admin.sh resumen 14

# Usuarios más activos
./scripts/auditoria-admin.sh activos 7

# Acciones más comunes
./scripts/auditoria-admin.sh acciones 30

# Distribución por horas
./scripts/auditoria-admin.sh horas 1

# Consulta SQL personalizada
./scripts/auditoria-admin.sh consulta "SELECT * FROM auditoria WHERE accion='LOGIN_FALLIDO';"
```

### 3. **🐍 Script Python de Consultas**
**Archivo**: `backend/auditoria_query.py`

**Uso desde contenedor:**
```bash
docker exec -it sistema_ocr_backend python auditoria_query.py usuario eduardo 7
docker exec -it sistema_ocr_backend python auditoria_query.py estadisticas 30
docker exec -it sistema_ocr_backend python auditoria_query.py criticos 7
```

---

## 📊 **Tipos de Eventos Monitoreados**

### 🔐 **Eventos de Autenticación**
- `LOGIN_EXITOSO` - Login correcto de usuario
- `LOGIN_FALLIDO` - Intento de login fallido
- `LOGOUT` - Cierre de sesión de usuario
- `CAMBIAR_PASSWORD` - Cambio de contraseña

### 👥 **Gestión de Usuarios**
- `CREAR_USUARIO` - Creación de nuevo usuario
- `MODIFICAR_USUARIO` - Modificación de datos de usuario
- `ELIMINAR_USUARIO` - Eliminación de usuario del sistema
- `MODIFICAR_PERMISOS` - Cambios en permisos de usuario

### 📁 **Gestión de Contenido**
- `CREAR_CARPETA` - Creación de nueva carpeta
- `ELIMINAR_CARPETA` - Eliminación de carpeta
- `PROCESAR_OCR` - Procesamiento de documentos OCR
- `REALIZAR_BUSQUEDA` - Búsquedas realizadas por usuarios

### ⚙️ **Eventos del Sistema**
- `CONFIGURAR_SISTEMA` - Cambios en configuración
- `BACKUP_AUTOMATICO` - Ejecución de backups
- `RESTORE_DATABASE` - Restauración de base de datos

---

## 🚨 **Eventos Críticos Monitoreados**

Los siguientes eventos se consideran **críticos** y requieren atención especial:

1. **`ELIMINAR_USUARIO`** - Eliminación de usuarios del sistema
2. **`LOGIN_FALLIDO`** - Intentos de acceso no autorizados
3. **`MODIFICAR_PERMISOS`** - Cambios en permisos de seguridad
4. **`ELIMINAR_CARPETA`** - Eliminación de contenido importante
5. **`CONFIGURAR_SISTEMA`** - Cambios en configuración crítica

---

## 📈 **Ejemplos de Uso Práctico**

### **🔍 Investigar Actividad Sospechosa**
```bash
# Ver todos los eventos de una IP específica
./scripts/auditoria-admin.sh ip 192.168.1.100 30

# Ver intentos de login fallidos
./scripts/auditoria-admin.sh consulta "
SELECT created_at, ip_address, valores_nuevos 
FROM auditoria 
WHERE accion='LOGIN_FALLIDO' 
ORDER BY created_at DESC;"
```

### **👥 Monitorear Usuario Específico**
```bash
# Ver toda la actividad de un usuario
./scripts/auditoria-admin.sh usuario eduardo 30

# Ver solo cambios críticos de un usuario
./scripts/auditoria-admin.sh consulta "
SELECT * FROM auditoria 
WHERE usuario_id=(SELECT id FROM usuarios WHERE username='eduardo')
AND accion IN ('ELIMINAR_USUARIO', 'MODIFICAR_PERMISOS', 'CONFIGURAR_SISTEMA');"
```

### **📊 Análisis de Patrones**
```bash
# Usuarios más activos del mes
./scripts/auditoria-admin.sh activos 30

# Distribución de actividad por horas
./scripts/auditoria-admin.sh horas 7

# Acciones más comunes
./scripts/auditoria-admin.sh acciones 30
```

### **🚨 Alertas de Seguridad**
```bash
# Eventos críticos recientes
./scripts/auditoria-admin.sh criticos 7

# IPs con múltiples intentos fallidos
./scripts/auditoria-admin.sh consulta "
SELECT ip_address, COUNT(*) as intentos_fallidos
FROM auditoria 
WHERE accion='LOGIN_FALLIDO' 
AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY ip_address 
HAVING COUNT(*) > 3
ORDER BY intentos_fallidos DESC;"
```

---

## 🔧 **Configuración y Mantenimiento**

### **📊 Consultas SQL Útiles**

#### **Resumen Diario de Actividad:**
```sql
SELECT 
    DATE(created_at) as fecha,
    COUNT(*) as total_eventos,
    COUNT(DISTINCT usuario_id) as usuarios_activos
FROM auditoria 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY fecha DESC;
```

#### **Usuarios con Más Actividad:**
```sql
SELECT 
    u.username,
    u.nombre_completo,
    COUNT(a.id) as total_eventos,
    MAX(a.created_at) as ultima_actividad
FROM usuarios u
JOIN auditoria a ON u.id = a.usuario_id
WHERE a.created_at >= NOW() - INTERVAL '7 days'
GROUP BY u.id, u.username, u.nombre_completo
ORDER BY total_eventos DESC;
```

#### **Eventos por Tipo de Acción:**
```sql
SELECT 
    accion,
    COUNT(*) as total,
    COUNT(DISTINCT usuario_id) as usuarios_distintos
FROM auditoria 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY accion
ORDER BY total DESC;
```

### **🔄 Mantenimiento de la Tabla de Auditoría**

#### **Limpieza Automática (ejecutar mensualmente):**
```sql
-- Eliminar eventos de auditoría más antiguos de 1 año
DELETE FROM auditoria 
WHERE created_at < NOW() - INTERVAL '1 year';

-- Reindexar para optimizar rendimiento
REINDEX TABLE auditoria;
```

#### **Verificar Tamaño de la Tabla:**
```sql
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    most_common_vals
FROM pg_stats 
WHERE tablename = 'auditoria';
```

---

## 🎯 **Casos de Uso Específicos**

### **🕵️ Investigación Forense**
Cuando necesites investigar un incidente específico:

1. **Identificar el período del incidente**
2. **Buscar todos los eventos relacionados**
3. **Analizar patrones de IP y usuarios**
4. **Documentar la cadena de eventos**

```bash
# Ejemplo: Investigar eliminación no autorizada
./scripts/auditoria-admin.sh consulta "
SELECT 
    a.created_at,
    u.username,
    a.accion,
    a.ip_address,
    a.valores_anteriores
FROM auditoria a
LEFT JOIN usuarios u ON a.usuario_id = u.id
WHERE a.accion = 'ELIMINAR_USUARIO'
AND a.created_at >= '2025-10-24 00:00:00'
ORDER BY a.created_at;"
```

### **📈 Reportes de Compliance**
Para generar reportes de cumplimiento y actividad:

```bash
# Reporte mensual de actividad
./scripts/auditoria-admin.sh resumen 30
./scripts/auditoria-admin.sh activos 30
./scripts/auditoria-admin.sh criticos 30
```

### **🚨 Monitoreo de Seguridad**
Para detectar actividades sospechosas:

```bash
# Revisar eventos críticos diarios
./scripts/auditoria-admin.sh criticos 1

# Monitorear IPs externas
./scripts/auditoria-admin.sh consulta "
SELECT DISTINCT ip_address, COUNT(*) as eventos
FROM auditoria 
WHERE ip_address NOT LIKE '172.22.134.%'
AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY ip_address
ORDER BY eventos DESC;"
```

---

## 📋 **Checklist de Administración Diaria**

### ✅ **Revisión Matutina (5 minutos)**
```bash
# 1. Eventos críticos de ayer
./scripts/auditoria-admin.sh criticos 1

# 2. Actividad general de ayer  
./scripts/auditoria-admin.sh resumen 1

# 3. Intentos de login fallidos
./scripts/auditoria-admin.sh consulta "
SELECT COUNT(*) as login_fallidos_ayer
FROM auditoria 
WHERE accion='LOGIN_FALLIDO' 
AND DATE(created_at) = CURRENT_DATE - 1;"
```

### ✅ **Revisión Semanal (15 minutos)**
```bash
# 1. Usuarios más activos
./scripts/auditoria-admin.sh activos 7

# 2. Nuevos patrones de IP
./scripts/auditoria-admin.sh consulta "
SELECT ip_address, COUNT(DISTINCT usuario_id) as usuarios, COUNT(*) as eventos
FROM auditoria 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY ip_address 
ORDER BY eventos DESC;"

# 3. Eventos por hora (detectar patrones anómalos)
./scripts/auditoria-admin.sh horas 7
```

### ✅ **Revisión Mensual (30 minutos)**
```bash
# 1. Limpieza de datos antiguos (si es necesario)
./scripts/auditoria-admin.sh consulta "
SELECT COUNT(*) as eventos_total, 
       MIN(created_at) as evento_mas_antiguo,
       MAX(created_at) as evento_mas_reciente
FROM auditoria;"

# 2. Estadísticas completas del mes
./scripts/auditoria-admin.sh estadisticas 30

# 3. Reporte de compliance mensual
./scripts/auditoria-admin.sh acciones 30
```

---

## 🎉 **Estado del Sistema de Auditoría**

### ✅ **Completamente Implementado:**
- ✅ Tabla de auditoría con estructura optimizada
- ✅ Scripts de consulta y administración funcionales
- ✅ Interfaz web para visualización
- ✅ Eventos de ejemplo registrados y probados
- ✅ Documentación completa de uso

### 🔗 **Accesos Disponibles:**
- **Web**: `http://fgj-ocr.local/auditoria.html`
- **Scripts**: `./scripts/auditoria-admin.sh`
- **Base de datos**: Tabla `auditoria` con eventos registrados

### 📊 **Estado Actual:**
- **Total de eventos registrados**: 3
- **Usuarios monitoreados**: eduardo (administrador)
- **Eventos críticos detectados**: 1 (eliminación de usuario)
- **Última actividad**: 24/10/2025 13:28:38

---

**🔍 El sistema de auditoría está completamente operativo y listo para monitorear todas las actividades del sistema OCR FGJCDMX.**

**Fecha de Implementación**: 24 de Octubre de 2025  
**Estado**: ✅ PRODUCCIÓN - MONITOREO ACTIVO  
**Acceso Principal**: http://fgj-ocr.local/auditoria.html