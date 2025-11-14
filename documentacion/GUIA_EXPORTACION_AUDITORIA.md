# 📊 Guía de Exportación de Auditoría

## 🎯 Descripción

Sistema de exportación de registros de auditoría a formato CSV para análisis offline y generación de reportes.

---

## ✨ Características

- **Exportación a CSV**: Descarga todos los registros filtrados en formato CSV
- **Filtros aplicados**: La exportación respeta los filtros activos (período, usuario, acción, IP)
- **Registro de auditoría**: Cada exportación queda registrada en el sistema
- **Descarga automática**: El archivo se descarga automáticamente al navegador
- **Nombre timestamped**: Archivos con nombre único por fecha y hora

---

## 🚀 Uso

### Desde la Interfaz Web

1. **Acceder a Auditoría**
   - Ir a `http://sistema-ocr.local/auditoria`
   - Solo usuarios con permiso `ver_auditoria` pueden acceder

2. **Aplicar Filtros (Opcional)**
   - **Período**: Hoy, Última semana, Último mes, Último año, Todo
   - **Usuario**: Filtrar por username específico
   - **Acción**: Filtrar por tipo de acción
   - **IP**: Filtrar por dirección IP

3. **Exportar Datos**
   - Click en botón **📊 Exportar**
   - El archivo CSV se descargará automáticamente
   - Nombre del archivo: `auditoria_export_YYYYMMDD_HHMMSS.csv`

### Desde la API (Programático)

```bash
# Exportar toda la auditoría
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=all" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o auditoria.csv

# Exportar última semana
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=week" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o auditoria_semana.csv

# Exportar filtrado por usuario
curl -X GET "http://localhost:8000/auditoria/exportar?usuario=eduardo&periodo=month" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o auditoria_eduardo.csv

# Exportar filtrado por acción
curl -X GET "http://localhost:8000/auditoria/exportar?accion=LOGIN_EXITOSO&periodo=today" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o logins_hoy.csv
```

---

## 📄 Formato del Archivo CSV

### Columnas Incluidas

| Columna | Descripción |
|---------|-------------|
| **ID** | Identificador único del evento |
| **Fecha/Hora** | Timestamp del evento (YYYY-MM-DD HH:MM:SS) |
| **Usuario** | Username del usuario que realizó la acción |
| **Nombre Completo** | Nombre completo del usuario |
| **Acción** | Tipo de acción realizada |
| **Tabla Afectada** | Tabla de la base de datos afectada |
| **Registro ID** | ID del registro afectado |
| **Descripción** | Descripción legible de la acción |
| **Dirección IP** | IP desde donde se realizó la acción |
| **User Agent** | Navegador/cliente utilizado |
| **Valores Anteriores** | Estado previo (formato JSON) |
| **Valores Nuevos** | Estado nuevo (formato JSON) |

### Ejemplo de Contenido

```csv
ID,Fecha/Hora,Usuario,Nombre Completo,Acción,Tabla Afectada,Registro ID,Descripción,Dirección IP,User Agent,Valores Anteriores,Valores Nuevos
1,2025-11-14 07:42:10,eduardo,Eduardo Lozada,ACCEDER_AUDITORIA,auditoria,,El usuario accedió a la página de auditoría,172.22.134.61,Mozilla/5.0...,,{'evento': 'acceso_pagina_auditoria'}
2,2025-11-14 07:30:15,eduardo,Eduardo Lozada,LOGIN_EXITOSO,usuarios,5,Login exitoso,172.22.134.61,Mozilla/5.0...,,{'username': 'eduardo'}
```

---

## 🔒 Seguridad

### Permisos Requeridos

- **ver_auditoria**: Obligatorio para acceder a la exportación
- Solo usuarios con `rol_id = 1` (Administrador) o permisos específicos

### Registro de Exportaciones

Cada exportación se registra en la auditoría con:
- Acción: `EXPORTAR_DATOS`
- Tabla afectada: `auditoria`
- Valores nuevos: Incluye tipo, total de registros y filtros aplicados
- IP y User Agent del solicitante

---

## 📊 Casos de Uso

### 1. Análisis de Actividad Mensual

```bash
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=month" \
  -H "Authorization: Bearer $TOKEN" \
  -o reporte_mensual.csv
```

Abrir en Excel/LibreOffice y crear tablas dinámicas.

### 2. Investigación de Incidentes

```bash
# Buscar actividad de una IP específica
curl -X GET "http://localhost:8000/auditoria/exportar?ip=192.168.1.100&periodo=all" \
  -H "Authorization: Bearer $TOKEN" \
  -o investigacion_ip.csv
```

### 3. Auditoría de Usuario Específico

```bash
# Ver todas las acciones de un usuario
curl -X GET "http://localhost:8000/auditoria/exportar?usuario=maria&periodo=year" \
  -H "Authorization: Bearer $TOKEN" \
  -o auditoria_maria.csv
```

### 4. Reporte de Logins

```bash
# Solo logins exitosos
curl -X GET "http://localhost:8000/auditoria/exportar?accion=LOGIN_EXITOSO&periodo=week" \
  -H "Authorization: Bearer $TOKEN" \
  -o logins_semana.csv
```

---

## 🛠️ Integración con Herramientas

### Excel / LibreOffice Calc

1. Abrir el archivo CSV exportado
2. Los datos se organizan automáticamente en columnas
3. Crear tablas dinámicas para análisis
4. Aplicar filtros y ordenamientos

### Python (pandas)

```python
import pandas as pd

# Leer el CSV
df = pd.read_csv('auditoria_export_20251114_074210.csv')

# Análisis básico
print(df['Acción'].value_counts())
print(df['Usuario'].value_counts())

# Filtrar por fecha
df['Fecha/Hora'] = pd.to_datetime(df['Fecha/Hora'])
df_hoy = df[df['Fecha/Hora'].dt.date == pd.Timestamp.today().date()]

# Exportar a Excel con formato
df.to_excel('auditoria_analisis.xlsx', index=False)
```

### R

```r
library(readr)
library(dplyr)

# Leer CSV
auditoria <- read_csv('auditoria_export_20251114_074210.csv')

# Resumen por acción
summary_acciones <- auditoria %>%
  group_by(Acción) %>%
  summarise(
    total = n(),
    usuarios_unicos = n_distinct(Usuario)
  )

print(summary_acciones)
```

---

## ⚡ Optimización

### Límites y Rendimiento

- **Sin límite de registros**: La exportación incluye todos los registros filtrados
- **Memoria eficiente**: Usa streaming para archivos grandes
- **Codificación UTF-8**: Soporta caracteres especiales

### Recomendaciones

1. **Filtrar antes de exportar**: Usa filtros para reducir el tamaño
2. **Exportaciones periódicas**: Programa exportaciones automáticas
3. **Almacenamiento**: Guarda los CSV como respaldo histórico

---

## 🐛 Solución de Problemas

### Error 403 - Sin Permisos

**Problema**: No tienes permiso para exportar auditoría

**Solución**: 
```sql
-- Verificar permisos
SELECT * FROM permisos_sistema WHERE usuario_id = YOUR_USER_ID;

-- Otorgar permiso (como admin)
UPDATE permisos_sistema 
SET ver_auditoria = true 
WHERE usuario_id = YOUR_USER_ID;
```

### El archivo no se descarga

**Problema**: El botón muestra "Exportando..." pero no descarga

**Solución**:
1. Verificar token de autenticación en localStorage
2. Revisar consola del navegador (F12)
3. Verificar que el backend esté corriendo
4. Comprobar permisos CORS

### CSV mal formateado

**Problema**: Los datos no se ven bien en Excel

**Solución**:
1. Abrir Excel
2. Datos > Obtener datos externos > Desde texto
3. Seleccionar el archivo CSV
4. Elegir delimitador: Coma
5. Codificación: UTF-8

---

## 📚 Archivos Relacionados

### Backend
- `backend/app/routes/auditoria.py` - Endpoint de exportación

### Frontend
- `frontend/auditoria.html` - Interfaz de usuario

### Documentación
- `GUIA_AUDITORIA_COMPLETA.md` - Sistema completo de auditoría
- `GUIA_AUDITORIA_USUARIOS.md` - Auditoría por usuario

---

## 🎓 Ejemplos Avanzados

### Script Bash - Exportación Automática Diaria

```bash
#!/bin/bash
# Exportar auditoría diaria

TOKEN="your_jwt_token_here"
FECHA=$(date +%Y%m%d)
OUTPUT_DIR="/backups/auditoria"

mkdir -p $OUTPUT_DIR

# Exportar eventos de hoy
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=today" \
  -H "Authorization: Bearer $TOKEN" \
  -o "$OUTPUT_DIR/auditoria_$FECHA.csv"

echo "Exportación completada: $OUTPUT_DIR/auditoria_$FECHA.csv"
```

### Cron Job - Exportación Semanal

```cron
# Exportar auditoría cada domingo a las 23:00
0 23 * * 0 /scripts/exportar_auditoria_semanal.sh
```

---

## ✅ Verificación

### Probar la Exportación

```bash
# 1. Obtener token
TOKEN=$(curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' | jq -r '.access_token')

# 2. Exportar auditoría
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=week" \
  -H "Authorization: Bearer $TOKEN" \
  -o test_export.csv

# 3. Verificar contenido
head -n 5 test_export.csv
wc -l test_export.csv
```

---

## 📞 Soporte

**Desarrollador**: Eduardo Lozada Quiroz, ISC  
**Organización**: Unidad de Análisis y Contexto (UAyC)  
**Año**: 2025

Para reportar problemas o sugerencias, consultar la documentación completa del sistema.
