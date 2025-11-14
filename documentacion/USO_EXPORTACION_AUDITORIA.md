# 🎉 Funcionalidad de Exportación de Auditoría - Lista para Usar

## ✅ Estado: IMPLEMENTADO Y FUNCIONAL

La funcionalidad de exportación de auditoría ha sido completamente implementada y está lista para usar.

---

## 🚀 Cómo Usar

### Opción 1: Desde la Interfaz Web (Recomendado)

1. **Acceder al Sistema**
   ```
   http://sistema-ocr.local/auditoria
   o
   http://localhost/auditoria
   ```

2. **Login con Credenciales**
   - Usuario con permiso `ver_auditoria = true`
   - Ejemplo: usuario administrador

3. **Aplicar Filtros (Opcional)**
   - **Período**: Seleccionar rango de tiempo
     - Hoy
     - Última semana
     - Último mes
     - Último año
     - Todo
   
   - **Usuario**: Filtrar por username específico
   - **Acción**: Filtrar por tipo de acción
   - **IP**: Filtrar por dirección IP

4. **Exportar**
   - Click en el botón **📊 Exportar**
   - El archivo CSV se descargará automáticamente
   - Nombre: `auditoria_export_YYYYMMDD_HHMMSS.csv`

5. **Abrir el Archivo**
   - Excel: Doble click
   - LibreOffice Calc: Doble click
   - Editor de texto: Ver datos crudos

---

### Opción 2: Desde la API

#### Paso 1: Obtener Token de Autenticación

```bash
# Login y guardar token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"TU_USUARIO","password":"TU_PASSWORD"}' \
  | jq -r '.access_token')

# Verificar token
echo $TOKEN
```

#### Paso 2: Exportar Auditoría

```bash
# Exportar todos los registros
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=all" \
  -H "Authorization: Bearer $TOKEN" \
  -o auditoria_completa.csv

# Exportar última semana
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=week" \
  -H "Authorization: Bearer $TOKEN" \
  -o auditoria_semana.csv

# Exportar eventos de hoy
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=today" \
  -H "Authorization: Bearer $TOKEN" \
  -o auditoria_hoy.csv

# Exportar filtrado por usuario
curl -X GET "http://localhost:8000/auditoria/exportar?usuario=eduardo&periodo=month" \
  -H "Authorization: Bearer $TOKEN" \
  -o auditoria_eduardo.csv

# Exportar filtrado por acción
curl -X GET "http://localhost:8000/auditoria/exportar?accion=LOGIN_EXITOSO&periodo=week" \
  -H "Authorization: Bearer $TOKEN" \
  -o logins_semana.csv
```

#### Paso 3: Ver el Contenido

```bash
# Ver primeras líneas
head -n 10 auditoria_completa.csv

# Contar registros
wc -l auditoria_completa.csv

# Buscar eventos específicos
grep "LOGIN_EXITOSO" auditoria_completa.csv
```

---

### Opción 3: Script Automatizado de Prueba

```bash
# Ejecutar script de pruebas completo
cd /home/eduardo/Descargas/sistemaocr
./scripts/test-exportacion-auditoria.sh

# El script te pedirá:
# - Usuario
# - Password
# Y ejecutará 9 pruebas diferentes
```

---

## 📋 Formato del Archivo CSV

### Columnas

| Columna | Descripción |
|---------|-------------|
| ID | Identificador único del evento |
| Fecha/Hora | Timestamp (YYYY-MM-DD HH:MM:SS) |
| Usuario | Username |
| Nombre Completo | Nombre del usuario |
| Acción | Tipo de acción realizada |
| Tabla Afectada | Tabla de la BD afectada |
| Registro ID | ID del registro afectado |
| Descripción | Descripción legible |
| Dirección IP | IP de origen |
| User Agent | Navegador/cliente |
| Valores Anteriores | Estado previo (JSON) |
| Valores Nuevos | Estado nuevo (JSON) |

### Ejemplo de Datos

```csv
ID,Fecha/Hora,Usuario,Nombre Completo,Acción,Tabla Afectada,Registro ID,Descripción,Dirección IP,User Agent,Valores Anteriores,Valores Nuevos
42,2025-11-14 07:42:10,eduardo,Eduardo Lozada,ACCEDER_AUDITORIA,auditoria,,El usuario accedió a la página de auditoría,172.22.134.61,Mozilla/5.0...,,{'evento': 'acceso_pagina_auditoria'}
41,2025-11-14 07:30:15,eduardo,Eduardo Lozada,LOGIN_EXITOSO,usuarios,5,Login exitoso,172.22.134.61,Mozilla/5.0...,,{'username': 'eduardo'}
```

---

## 🔍 Casos de Uso Prácticos

### 1. Reporte Mensual de Actividad

```bash
# Exportar todo el mes actual
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=month" \
  -H "Authorization: Bearer $TOKEN" \
  -o reporte_mensual_$(date +%Y%m).csv
```

**Uso**: Abrir en Excel, crear tabla dinámica, analizar patrones.

---

### 2. Investigación de Seguridad

```bash
# Buscar actividad sospechosa de una IP
curl -X GET "http://localhost:8000/auditoria/exportar?ip=192.168.1.100&periodo=all" \
  -H "Authorization: Bearer $TOKEN" \
  -o investigacion_ip_192_168_1_100.csv
```

**Uso**: Revisar todas las acciones desde esa IP, identificar anomalías.

---

### 3. Auditoría de Usuario

```bash
# Ver todas las acciones de un usuario
curl -X GET "http://localhost:8000/auditoria/exportar?usuario=maria&periodo=year" \
  -H "Authorization: Bearer $TOKEN" \
  -o auditoria_usuario_maria_2025.csv
```

**Uso**: Evaluación de desempeño, compliance, investigaciones.

---

### 4. Monitoreo de Logins

```bash
# Solo logins exitosos de la última semana
curl -X GET "http://localhost:8000/auditoria/exportar?accion=LOGIN_EXITOSO&periodo=week" \
  -H "Authorization: Bearer $TOKEN" \
  -o logins_semana.csv

# Solo logins fallidos (intentos sospechosos)
curl -X GET "http://localhost:8000/auditoria/exportar?accion=LOGIN_FALLIDO&periodo=month" \
  -H "Authorization: Bearer $TOKEN" \
  -o logins_fallidos_mes.csv
```

**Uso**: Detectar patrones de acceso, intentos de intrusión.

---

### 5. Backup Semanal Automatizado

**Crear script**: `/scripts/backup-auditoria-semanal.sh`

```bash
#!/bin/bash
# Backup automático semanal de auditoría

TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"'$ADMIN_PASSWORD'"}' \
  | jq -r '.access_token')

FECHA=$(date +%Y%m%d)
BACKUP_DIR="/backups/auditoria"

mkdir -p $BACKUP_DIR

curl -X GET "http://localhost:8000/auditoria/exportar?periodo=week" \
  -H "Authorization: Bearer $TOKEN" \
  -o "$BACKUP_DIR/auditoria_backup_$FECHA.csv"

echo "✅ Backup completado: $BACKUP_DIR/auditoria_backup_$FECHA.csv"
```

**Cron job** (ejecutar cada domingo):
```cron
0 23 * * 0 /scripts/backup-auditoria-semanal.sh
```

---

## 📊 Análisis con Herramientas

### Excel

1. Abrir el CSV
2. Crear tabla dinámica:
   - Filas: Acción
   - Valores: Contar ID
   - Resultado: Resumen de acciones más frecuentes

3. Gráficos:
   - Línea de tiempo de eventos
   - Top usuarios más activos
   - Distribución de acciones

---

### Python (pandas)

```python
import pandas as pd
import matplotlib.pyplot as plt

# Cargar datos
df = pd.read_csv('auditoria_export_20251114.csv')

# Convertir fechas
df['Fecha/Hora'] = pd.to_datetime(df['Fecha/Hora'])

# Top 10 acciones más comunes
top_acciones = df['Acción'].value_counts().head(10)
print(top_acciones)

# Top usuarios más activos
top_usuarios = df['Usuario'].value_counts().head(10)
print(top_usuarios)

# Gráfico de acciones por día
df['Fecha'] = df['Fecha/Hora'].dt.date
eventos_por_dia = df.groupby('Fecha').size()
eventos_por_dia.plot(kind='line', title='Eventos por Día')
plt.show()

# Exportar resumen
resumen = df.groupby('Acción').agg({
    'ID': 'count',
    'Usuario': 'nunique'
}).rename(columns={'ID': 'Total Eventos', 'Usuario': 'Usuarios Únicos'})
resumen.to_excel('resumen_auditoria.xlsx')
```

---

### LibreOffice Calc

1. Abrir archivo CSV
2. Datos > Tabla Dinámica
3. Arrastrar campos:
   - Filtros: Período
   - Filas: Usuario
   - Columnas: Acción
   - Datos: Contar ID
4. Insertar gráfico

---

## 🔒 Seguridad y Permisos

### Verificar Permisos

```sql
-- Conectarse a la base de datos
psql -U postgres -d sistema_ocr

-- Ver permisos de un usuario
SELECT u.username, ps.ver_auditoria 
FROM usuarios u
LEFT JOIN permisos_sistema ps ON u.id = ps.usuario_id
WHERE u.username = 'TU_USUARIO';

-- Otorgar permiso (si es necesario)
UPDATE permisos_sistema 
SET ver_auditoria = true 
WHERE usuario_id = (SELECT id FROM usuarios WHERE username = 'TU_USUARIO');
```

### Auditoría de Exportaciones

Cada exportación queda registrada:

```bash
# Ver tus propias exportaciones
curl -X GET "http://localhost:8000/auditoria/eventos?accion=EXPORTAR_DATOS&usuario=TU_USUARIO" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## ❓ Solución de Problemas

### Problema: "No tienes permisos"

**Solución**:
```bash
# Como admin, otorgar permisos
docker exec -it sistema_ocr_db psql -U postgres -d sistema_ocr -c \
  "UPDATE permisos_sistema SET ver_auditoria = true WHERE usuario_id = X;"
```

---

### Problema: El archivo está vacío

**Causas posibles**:
1. Los filtros son muy restrictivos (no hay eventos que coincidan)
2. No hay eventos en ese período

**Solución**:
```bash
# Probar sin filtros
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=all" \
  -H "Authorization: Bearer $TOKEN" \
  -o test.csv
```

---

### Problema: CSV no se abre bien en Excel

**Solución**:
1. Excel > Datos > Obtener datos externos > Desde texto
2. Seleccionar archivo CSV
3. Delimitador: Coma
4. Codificación: UTF-8

---

## 📚 Documentación Completa

Para más detalles, ver:
- `documentacion/GUIA_EXPORTACION_AUDITORIA.md` - Guía completa
- `documentacion/RESUMEN_IMPLEMENTACION_EXPORTACION.md` - Detalles técnicos
- `documentacion/GUIA_AUDITORIA_COMPLETA.md` - Sistema de auditoría

---

## ✅ Verificación Rápida

```bash
# 1. Sistema corriendo
docker ps | grep sistema_ocr_backend

# 2. Obtener token
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r '.access_token')

# 3. Probar exportación
curl -X GET "http://localhost:8000/auditoria/exportar?periodo=today" \
  -H "Authorization: Bearer $TOKEN" \
  -o test_export.csv

# 4. Verificar
ls -lh test_export.csv
head -n 3 test_export.csv
```

---

## 🎉 ¡Listo para Usar!

La funcionalidad está **completamente implementada y funcional**. Puedes comenzar a exportar tus datos de auditoría inmediatamente.

**Desarrollado por**: Eduardo Lozada Quiroz, ISC  
**Organización**: Unidad de Análisis y Contexto (UAyC)  
**Fecha**: 14 de noviembre de 2025
