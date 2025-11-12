# 💾 SISTEMA DE BACKUPS - OCR FGJCDMX

## 📋 Resumen del Sistema

El Sistema OCR FGJCDMX incluye un sistema completo de backups automatizado que permite:
- ✅ Backups manuales bajo demanda
- ✅ Backups automáticos programados (diarios, semanales, personalizados)
- ✅ Restauración completa de la base de datos
- ✅ Gestión automática de backups antiguos
- ✅ Logs detallados de todas las operaciones

## 🛠️ Scripts Disponibles

### 1. **Backup Manual** - `scripts/backup-database.sh`
Crea backups de la base de datos PostgreSQL del sistema.

#### **Uso Básico:**
```bash
# Crear backup inmediato
./scripts/backup-database.sh

# Listar backups existentes
./scripts/backup-database.sh --list

# Ver estadísticas
./scripts/backup-database.sh --stats

# Ver ayuda
./scripts/backup-database.sh --help
```

#### **Características:**
- ✅ Verificación automática de prerequisitos
- ✅ Creación de backup con timestamp
- ✅ Verificación de integridad
- ✅ Limpieza automática (mantiene últimos 10)
- ✅ Logs detallados de operaciones

### 2. **Restauración** - `scripts/restore-database.sh`
Restaura backups de la base de datos con seguridad.

#### **Uso Básico:**
```bash
# Restauración interactiva (recomendado)
./scripts/restore-database.sh

# Restaurar backup específico
./scripts/restore-database.sh sistema_ocr_backup_20251024_130628.sql

# Listar backups disponibles
./scripts/restore-database.sh --list

# Ver ayuda
./scripts/restore-database.sh --help
```

#### **Características de Seguridad:**
- ✅ Backup automático antes de restaurar
- ✅ Confirmación explícita requerida
- ✅ Detención temporal de servicios
- ✅ Verificación post-restauración
- ✅ Logs completos del proceso

### 3. **Backups Automáticos** - `scripts/setup-automatic-backups.sh`
Configura backups automáticos programados.

#### **Uso Básico:**
```bash
# Configurar backup diario (2:00 AM)
sudo ./scripts/setup-automatic-backups.sh --daily

# Configurar backup semanal (domingos 1:00 AM)
sudo ./scripts/setup-automatic-backups.sh --weekly

# Configurar horario personalizado
sudo ./scripts/setup-automatic-backups.sh --custom "30 3 * * *"

# Ver estado actual
sudo ./scripts/setup-automatic-backups.sh --status

# Desactivar backups automáticos
sudo ./scripts/setup-automatic-backups.sh --disable

# Ejecutar backup manual
sudo ./scripts/setup-automatic-backups.sh --run
```

## 📂 Ubicaciones Importantes

### **Directorio de Backups:**
```
/home/vboxuser/Downloads/FJ1/backups/
```

### **Logs del Sistema:**
```
/var/log/sistema-ocr-backup.log          # Backups manuales (root)
/var/log/sistema-ocr-restore.log         # Restauraciones (root)
/var/log/sistema-ocr-backup-cron.log     # Backups automáticos
/home/vboxuser/sistema-ocr-backup.log    # Backups como usuario
```

### **Configuración Cron:**
```
/etc/cron.d/sistema-ocr-backup           # Configuración de backups automáticos
```

## 🚀 Guía de Uso Práctica

### **Crear Backup Manual:**
```bash
cd /home/vboxuser/Downloads/FJ1
./scripts/backup-database.sh
```

### **Configurar Backup Diario:**
```bash
cd /home/vboxuser/Downloads/FJ1
sudo ./scripts/setup-automatic-backups.sh --daily
```

### **Restaurar desde Backup:**
```bash
cd /home/vboxuser/Downloads/FJ1
./scripts/restore-database.sh
# Seguir las instrucciones interactivas
```

### **Ver Estado del Sistema:**
```bash
# Estado de backups automáticos
sudo ./scripts/setup-automatic-backups.sh --status

# Lista de backups disponibles
./scripts/backup-database.sh --list

# Estadísticas generales
./scripts/backup-database.sh --stats
```

## ⚠️ Importantes Consideraciones de Seguridad

### **Antes de Restaurar:**
1. **Backup Automático**: El sistema crea un backup de seguridad automáticamente
2. **Confirmación Requerida**: Debe escribir "SI" para confirmar
3. **Servicios**: Se detienen temporalmente durante la restauración
4. **Verificación**: El sistema verifica la conectividad post-restauración

### **Gestión de Espacio:**
- Los backups se limpian automáticamente (se mantienen los últimos 10)
- Backup típico: ~2-3 MB (puede variar según datos)
- Monitorear espacio en disco regularmente

### **Permisos:**
- Backups manuales: Pueden ejecutarse como usuario normal
- Backups automáticos: Requieren permisos root (sudo)
- Restauraciones: Pueden ejecutarse como usuario normal

## 📊 Ejemplos de Horarios Personalizados

```bash
# Todos los días a las 3:30 AM
sudo ./scripts/setup-automatic-backups.sh --custom "30 3 * * *"

# Lunes, miércoles y viernes a las 2:15 AM
sudo ./scripts/setup-automatic-backups.sh --custom "15 2 * * 1,3,5"

# Cada 6 horas
sudo ./scripts/setup-automatic-backups.sh --custom "0 */6 * * *"

# Primer día de cada mes a las 1:00 AM
sudo ./scripts/setup-automatic-backups.sh --custom "0 1 1 * *"
```

## 🔧 Solución de Problemas

### **Error: "Contenedor no está ejecutándose"**
```bash
# Verificar estado de servicios
cd /home/vboxuser/Downloads/FJ1
sudo docker compose ps

# Iniciar servicios si es necesario
sudo docker compose up -d
```

### **Error: "No hay backups disponibles"**
```bash
# Crear un backup inicial
./scripts/backup-database.sh

# Verificar directorio
ls -la backups/
```

### **Error de permisos en logs**
```bash
# Para backups automáticos, usar sudo
sudo ./scripts/setup-automatic-backups.sh --run

# Para backups manuales como usuario normal
./scripts/backup-database.sh
```

### **Restauración fallida**
```bash
# Verificar logs
tail -20 /var/log/sistema-ocr-restore.log

# Verificar servicios
sudo docker compose ps

# Reiniciar servicios si es necesario
sudo docker compose restart
```

## 📈 Monitoreo y Mantenimiento

### **Verificación Semanal:**
```bash
# Estado de backups automáticos
sudo ./scripts/setup-automatic-backups.sh --status

# Lista y estadísticas de backups
./scripts/backup-database.sh --stats

# Verificar logs de errores
sudo tail -50 /var/log/sistema-ocr-backup-cron.log
```

### **Limpieza Manual:**
```bash
# Los backups se limpian automáticamente, pero si necesitas:
# Mantener solo los últimos 5 backups
cd /home/vboxuser/Downloads/FJ1/backups
ls -1t *.sql | tail -n +6 | xargs rm -f
```

### **Prueba de Restauración:**
Se recomienda probar el proceso de restauración mensualmente en un entorno de desarrollo.

---

## ✅ **Estado Actual del Sistema**

- 🌐 **Dominio Principal**: http://fgj-ocr.local/
- 💾 **Backups**: Sistema completo implementado y probado
- 🔒 **Seguridad**: Backups automáticos de seguridad antes de restaurar
- 📊 **Monitoreo**: Logs detallados y estadísticas disponibles
- 🔄 **Automatización**: Configuración flexible de horarios

**El sistema de backups está completamente operativo y listo para uso en producción.**