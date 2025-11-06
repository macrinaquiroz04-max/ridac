# 🚀 GUÍA RÁPIDA PARA COMPAÑEROS - SISTEMA OCR FGJCDMX

## 📍 **ACCESO AL SISTEMA**

### **URL Principal:**
```
http://fgj-ocr.local/
```

### **URL de Respaldo (si hay problemas):**
```
http://172.22.134.61/
```

---

## 👥 **USUARIOS DISPONIBLES**

| Usuario    | Email                      | Rol              |
|------------|----------------------------|------------------|
| `analista` | analista@fiscalia.gob.mx   | Usuario Analista |
| `testuser` | test@fgj.gob.mx           | Usuario Test     |
| `newuser`  | newuser@fgj.gob.mx        | Usuario Nuevo    |
| `eduardo`  | eduardo@fiscalia.gob.mx   | Eduardo Lozada   |

> **Nota**: Las contraseñas están configuradas por el administrador del sistema.

---

## 🌐 **CONECTIVIDAD DESDE WINDOWS**

### **Opción 1: Automática (Recomendada)**
1. Abrir navegador web
2. Ir a: `http://fgj-ocr.local/`
3. ¡Listo! El sistema debería cargar automáticamente

### **Opción 2: Si no carga (DNS Manual)**
1. **Presionar** `Windows + R`
2. **Escribir**: `notepad C:\Windows\System32\drivers\etc\hosts`
3. **Ejecutar como Administrador** si se solicita
4. **Agregar esta línea** al final del archivo:
   ```
   172.22.134.61    fgj-ocr.local
   ```
5. **Guardar** el archivo
6. **Abrir navegador** y ir a: `http://fgj-ocr.local/`

### **Opción 3: Acceso Directo por IP**
Si hay problemas con el dominio, usar directamente:
```
http://172.22.134.61/
```

---

## ✅ **VERIFICACIÓN DE CONECTIVIDAD**

### **Desde CMD de Windows:**
```cmd
ping fgj-ocr.local
```
**Resultado esperado**: `Reply from 172.22.134.61: bytes=32 time<1ms TTL=64`

### **Desde Navegador:**
1. Ir a: `http://fgj-ocr.local/health`
2. **Debe mostrar**: `{"status":"healthy","service":"Sistema OCR - FGJCDMX"...}`

---

## 🔧 **SOLUCIÓN RÁPIDA DE PROBLEMAS**

### **❌ "No se puede acceder al sitio"**
**Solución**: Usar la IP directa `http://172.22.134.61/`

### **❌ "Error de DNS" o "No se encuentra el sitio"**
**Solución**: Configurar DNS manual (ver Opción 2 arriba)

### **❌ "Failed to fetch" o errores de conexión**
**Solución**: 
1. Verificar que estén en la misma red que el servidor
2. Contactar al administrador del sistema

### **❌ Página carga lenta**
**Solución**: 
1. Limpiar caché del navegador (Ctrl + F5)
2. Cerrar y abrir el navegador

---

## 📱 **ACCESO DESDE MÓVILES**

El sistema también funciona desde dispositivos móviles:
- **Android/iPhone**: Abrir navegador y ir a `http://fgj-ocr.local/`
- **Si no funciona**: Usar `http://172.22.134.61/`

---

## 🎯 **FUNCIONALIDADES PRINCIPALES**

Una vez conectados, podrán acceder a:
- 📄 **OCR de Documentos**: Extracción de texto de PDFs
- 🔍 **Búsqueda Avanzada**: Búsqueda semántica en documentos
- 📊 **Dashboard**: Panel de control y estadísticas
- 👥 **Gestión de Usuarios**: Administración de permisos
- 📁 **Carpetas**: Organización de expedientes
- 🤖 **Análisis IA**: Análisis jurídico automatizado

---

## 📞 **SOPORTE TÉCNICO**

### **Estado del Sistema:**
- ✅ **Sistema Principal**: http://fgj-ocr.local/
- ✅ **Base de Datos**: Conectada y operativa
- ✅ **Servicios**: Todos los contenedores funcionando
- ✅ **DNS**: Configuración automática activa
- ✅ **Backups**: Sistema automático configurado

### **En Caso de Problemas:**
1. **Verificar conectividad**: `ping fgj-ocr.local`
2. **Probar IP directa**: `http://172.22.134.61/`
3. **Contactar administrador** si persisten los problemas

---

## 🏛️ **INFORMACIÓN DEL SISTEMA**

- **Nombre**: Sistema OCR - FGJCDMX
- **Versión**: 2.1.0
- **Dominio Principal**: fgj-ocr.local
- **IP del Servidor**: 172.22.134.61
- **Estado**: ✅ **COMPLETAMENTE OPERATIVO**

---

**📅 Fecha de Configuración**: 24 de Octubre de 2025  
**🔧 Configurado por**: Administrador del Sistema  
**📊 Estado**: ✅ PRODUCCIÓN - LISTO PARA USO COMPLETO