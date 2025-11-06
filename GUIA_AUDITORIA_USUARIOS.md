# 🔍 SISTEMA DE AUDITORÍA - Monitoreo de Usuarios

**Sistema OCR FGJCDMX - Control Total de Actividades**

---

## 📊 ¿QUÉ REGISTRA EL SISTEMA?

La tabla `auditoria` registra **TODAS** las acciones de los usuarios:

### ✅ Acciones Registradas Automáticamente:

| Acción | Descripción | Cuándo se registra |
|--------|-------------|-------------------|
| **LOGIN** | Usuario inició sesión | Al hacer login exitoso |
| **LOGOUT** | Usuario cerró sesión | Al hacer logout |
| **CREAR_USUARIO** | Nuevo usuario creado | Cuando admin crea usuario |
| **EDITAR_USUARIO** | Usuario modificado | Cuando se edita perfil/permisos |
| **ELIMINAR_USUARIO** | Usuario eliminado | Cuando admin elimina usuario |
| **CREAR_CARPETA** | Nueva carpeta creada | Al crear expediente |
| **EDITAR_CARPETA** | Carpeta modificada | Al editar expediente |
| **ELIMINAR_CARPETA** | Carpeta eliminada | Al eliminar expediente |
| **SUBIR_TOMO** | PDF subido | Al subir documento |
| **PROCESAR_OCR** | OCR ejecutado | Al procesar documento |
| **BUSCAR** | Búsqueda realizada | Al buscar en sistema |
| **EXPORTAR** | Datos exportados | Al exportar información |
| **CAMBIAR_PASSWORD** | Contraseña cambiada | Al cambiar password |
| **ASIGNAR_PERMISO** | Permiso otorgado | Al dar acceso a carpeta |
| **REVOCAR_PERMISO** | Permiso revocado | Al quitar acceso |

---

## 🗃️ ESTRUCTURA DE LA TABLA AUDITORIA

```sql
CREATE TABLE auditoria (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),  -- Quién hizo la acción
    accion VARCHAR(100),                          -- Qué acción realizó
    entidad VARCHAR(100),                         -- Sobre qué (usuario, carpeta, tomo)
    entidad_id INTEGER,                           -- ID del elemento afectado
    descripcion TEXT,                             -- Descripción detallada
    ip_address VARCHAR(45),                       -- IP desde donde se conectó
    user_agent TEXT,                              -- Navegador usado
    metadata JSONB,                               -- Datos adicionales
    created_at TIMESTAMP DEFAULT NOW()            -- Cuándo sucedió
);
```

---

## 📋 EJEMPLO DE REGISTROS

```json
{
  "id": 1,
  "usuario_id": 2,
  "accion": "LOGIN",
  "entidad": "usuario",
  "entidad_id": 2,
  "descripcion": "Eduardo inició sesión",
  "ip_address": "192.168.1.105",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
  "metadata": {
    "success": true,
    "rol": "admin"
  },
  "created_at": "2025-10-20 14:30:45"
}

{
  "id": 2,
  "usuario_id": 2,
  "accion": "CREAR_CARPETA",
  "entidad": "carpeta",
  "entidad_id": 15,
  "descripcion": "Carpeta CI-FDS/12345 creada",
  "ip_address": "192.168.1.105",
  "user_agent": "Mozilla/5.0...",
  "metadata": {
    "numero_carpeta": "CI-FDS/12345",
    "tipo": "investigacion"
  },
  "created_at": "2025-10-20 14:35:20"
}

{
  "id": 3,
  "usuario_id": 3,
  "accion": "BUSCAR",
  "entidad": "sistema",
  "entidad_id": null,
  "descripcion": "Búsqueda: 'robo con violencia'",
  "ip_address": "192.168.1.110",
  "user_agent": "Mozilla/5.0...",
  "metadata": {
    "termino_busqueda": "robo con violencia",
    "resultados": 45,
    "tiempo_ms": 234
  },
  "created_at": "2025-10-20 15:10:15"
}
```

---

## 🔍 CONSULTAS ÚTILES PARA MONITOREO

### 1️⃣ Ver últimas 50 acciones
```sql
SELECT 
    u.usuario,
    u.nombre_completo,
    a.accion,
    a.descripcion,
    a.ip_address,
    a.created_at
FROM auditoria a
JOIN usuarios u ON a.usuario_id = u.id
ORDER BY a.created_at DESC
LIMIT 50;
```

### 2️⃣ Ver actividad de un usuario específico
```sql
SELECT 
    accion,
    descripcion,
    ip_address,
    created_at
FROM auditoria
WHERE usuario_id = 2  -- ID de eduardo
ORDER BY created_at DESC;
```

### 3️⃣ Ver quién eliminó algo
```sql
SELECT 
    u.usuario,
    a.descripcion,
    a.entidad,
    a.entidad_id,
    a.created_at
FROM auditoria a
JOIN usuarios u ON a.usuario_id = u.id
WHERE a.accion LIKE '%ELIMINAR%'
ORDER BY a.created_at DESC;
```

### 4️⃣ Ver accesos por IP
```sql
SELECT 
    ip_address,
    COUNT(*) as total_accesos,
    MIN(created_at) as primer_acceso,
    MAX(created_at) as ultimo_acceso
FROM auditoria
WHERE accion = 'LOGIN'
GROUP BY ip_address
ORDER BY total_accesos DESC;
```

### 5️⃣ Ver actividad por día
```sql
SELECT 
    DATE(created_at) as fecha,
    COUNT(*) as total_acciones,
    COUNT(DISTINCT usuario_id) as usuarios_activos
FROM auditoria
GROUP BY DATE(created_at)
ORDER BY fecha DESC;
```

### 6️⃣ Ver quién modificó un expediente
```sql
SELECT 
    u.usuario,
    a.accion,
    a.descripcion,
    a.created_at
FROM auditoria a
JOIN usuarios u ON a.usuario_id = u.id
WHERE a.entidad = 'carpeta' 
  AND a.entidad_id = 15  -- ID de la carpeta
ORDER BY a.created_at DESC;
```

---

## 🚨 ALERTAS Y SEGURIDAD

### Detectar actividad sospechosa:

```sql
-- Muchos intentos de login fallidos
SELECT 
    usuario_id,
    ip_address,
    COUNT(*) as intentos_fallidos
FROM auditoria
WHERE accion = 'LOGIN_FALLIDO'
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY usuario_id, ip_address
HAVING COUNT(*) > 5;

-- Eliminaciones masivas
SELECT 
    u.usuario,
    COUNT(*) as eliminaciones
FROM auditoria a
JOIN usuarios u ON a.usuario_id = u.id
WHERE a.accion LIKE '%ELIMINAR%'
  AND a.created_at > NOW() - INTERVAL '1 hour'
GROUP BY u.usuario
HAVING COUNT(*) > 10;

-- Accesos fuera de horario
SELECT 
    u.usuario,
    a.accion,
    a.created_at
FROM auditoria a
JOIN usuarios u ON a.usuario_id = u.id
WHERE EXTRACT(HOUR FROM a.created_at) NOT BETWEEN 7 AND 20  -- Horario laboral
ORDER BY a.created_at DESC;
```

---

## 🖥️ ACCEDER A LA AUDITORÍA EN LA OFICINA

### Opción 1: PgAdmin (Interfaz Gráfica)

1. Abrir navegador: **http://localhost:5050**
2. Login: **admin@fiscalia.gob.mx** / **admin123**
3. Conectar a servidor:
   - Host: `sistema_ocr_db`
   - Port: `5432`
   - Database: `sistema_ocr`
   - User: `postgres`
   - Password: `1234`
4. Ir a: **sistema_ocr → Schemas → public → Tables → auditoria**
5. Click derecho → **View/Edit Data → All Rows**

### Opción 2: Línea de comandos

```powershell
# Ver últimas 20 acciones
docker exec -it sistema_ocr_db psql -U postgres -d sistema_ocr -c "SELECT u.usuario, a.accion, a.descripcion, a.created_at FROM auditoria a JOIN usuarios u ON a.usuario_id = u.id ORDER BY a.created_at DESC LIMIT 20;"

# Exportar auditoría a CSV
docker exec -it sistema_ocr_db psql -U postgres -d sistema_ocr -c "\COPY (SELECT * FROM auditoria ORDER BY created_at DESC) TO '/tmp/auditoria.csv' WITH CSV HEADER;"
docker cp sistema_ocr_db:/tmp/auditoria.csv C:\auditoria_backup.csv
```

### Opción 3: Crear vista en Frontend (PRÓXIMA MEJORA)

Crear página `frontend/auditoria.html` con:
- 📊 Dashboard de actividad en tiempo real
- 🔍 Filtros por usuario, acción, fecha
- 📈 Gráficas de actividad
- 🚨 Alertas de seguridad
- 📥 Exportar reportes

---

## 🔧 CONFIGURAR IP EN LA OFICINA

### Cuando llegues mañana:

1. **Verificar IP del servidor:**
   ```powershell
   ipconfig
   ```
   Buscar: `IPv4 Address` (ejemplo: 192.168.1.100)

2. **Actualizar configuración del frontend:**

   Editar: `frontend/js/config.js`
   ```javascript
   const API_URL = 'http://192.168.1.100/api';  // Cambiar por IP real
   ```

3. **Actualizar Nginx (si usas dominio local):**

   Editar: `nginx.conf`
   ```nginx
   server_name 192.168.1.100;  # Cambiar por IP real
   ```

4. **Reiniciar Nginx:**
   ```powershell
   docker-compose restart nginx
   ```

5. **Acceder desde otras PCs en la red:**
   ```
   http://192.168.1.100
   ```

---

## 📊 REPORTES RECOMENDADOS

### Reporte Diario (CSV)
```sql
COPY (
    SELECT 
        u.usuario,
        u.nombre_completo,
        a.accion,
        a.descripcion,
        a.ip_address,
        a.created_at
    FROM auditoria a
    JOIN usuarios u ON a.usuario_id = u.id
    WHERE DATE(a.created_at) = CURRENT_DATE
    ORDER BY a.created_at DESC
) TO '/tmp/reporte_diario.csv' WITH CSV HEADER;
```

### Reporte Semanal (Resumen)
```sql
SELECT 
    u.usuario,
    COUNT(*) as total_acciones,
    COUNT(DISTINCT a.accion) as tipos_acciones,
    MIN(a.created_at) as primera_actividad,
    MAX(a.created_at) as ultima_actividad
FROM auditoria a
JOIN usuarios u ON a.usuario_id = u.id
WHERE a.created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY u.usuario
ORDER BY total_acciones DESC;
```

---

## ⚙️ MANTENIMIENTO DE AUDITORÍA

### Limpiar registros antiguos (después de 1 año)
```sql
DELETE FROM auditoria 
WHERE created_at < NOW() - INTERVAL '1 year';
```

### Archivar registros antiguos
```sql
-- Crear tabla de archivo
CREATE TABLE auditoria_archivo (LIKE auditoria INCLUDING ALL);

-- Mover registros
INSERT INTO auditoria_archivo 
SELECT * FROM auditoria 
WHERE created_at < NOW() - INTERVAL '6 months';

DELETE FROM auditoria 
WHERE created_at < NOW() - INTERVAL '6 months';
```

---

## ✅ CHECKLIST DE AUDITORÍA

- [x] Tabla `auditoria` creada con columna `metadata`
- [ ] Configurar IP del servidor en la oficina
- [ ] Verificar que se registran los logins
- [ ] Crear reportes automáticos
- [ ] Configurar alertas de seguridad
- [ ] Exportar auditoría semanal
- [ ] Crear página de auditoría en frontend (opcional)

---

## 🎯 RESUMEN

**La auditoría registra:**
- ✅ Quién hizo qué
- ✅ Cuándo lo hizo
- ✅ Desde qué IP
- ✅ Qué navegador usó
- ✅ Datos adicionales (metadata)

**Para monitorear:**
- 🔍 Usar PgAdmin (interfaz gráfica)
- 💻 Usar comandos SQL (línea de comandos)
- 📊 Crear reportes automáticos
- 🚨 Configurar alertas

**Mañana en la oficina:**
1. Instalar Docker
2. Clonar repositorio
3. Iniciar sistema
4. Obtener IP local (`ipconfig`)
5. Actualizar `frontend/js/config.js` con la IP
6. ¡Listo para monitorear! 🎉

---

**Última actualización:** 20 de octubre de 2025
