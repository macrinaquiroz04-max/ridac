# 📊 Sistema de Análisis Jurídico Integrado
## Guía Completa de Uso

---

## ✅ **INTEGRACIÓN COMPLETADA**

El sistema de análisis jurídico ha sido **completamente integrado** en el dashboard de usuario. Todos los componentes están listos para usar.

---

## 📁 **ARCHIVOS CREADOS/MODIFICADOS**

### **Backend (Ya implementado previamente)**
✅ `backend/app/models/analisis_juridico.py` - 7 modelos de base de datos
✅ `backend/app/services/legal_ocr_service.py` - Extracción OCR con corrección de abreviaturas
✅ `backend/app/services/legal_nlp_analysis_service.py` - Análisis NLP de documentos legales
✅ `backend/app/controllers/analisis_admin_controller.py` - API endpoints para administradores
✅ `backend/app/controllers/analisis_usuario_controller.py` - API endpoints para usuarios
✅ `backend/app/routes/analisis_admin.py` - Rutas de administración
✅ `backend/app/routes/analisis_usuario.py` - Rutas de usuario
✅ `backend/scripts/create_analisis_juridico_tables.sql` - Script SQL de migración

### **Frontend (Recién implementado)**
🆕 `frontend/js/analisis-juridico.js` - Módulo JavaScript completo (~500 líneas)
🆕 `frontend/css/analisis-juridico.css` - Estilos personalizados para análisis jurídico
✏️ `frontend/dashboard-usuario.html` - **MODIFICADO** con nueva sección de análisis

---

## 🚀 **CÓMO USAR EL SISTEMA**

### **PASO 1: Preparar la Base de Datos**

Si aún no has creado las tablas, ejecuta:

```bash
cd backend/scripts
psql -U postgres -d tu_base_datos -f create_analisis_juridico_tables.sql
```

### **PASO 2: Iniciar el Servidor Backend**

```bash
cd backend
python main.py
```

El servidor debe estar corriendo en `http://localhost:8000`

### **PASO 3: Usar el Sistema**

#### **A) Desde el Admin (Extracción OCR)**

1. Ve a la interfaz de administrador existente (ej: `ocr-pdf24.html` o `ocr-extraction.html`)
2. Sube un tomo PDF escaneado (800-900 páginas)
3. El sistema automáticamente:
   - Extrae texto con Tesseract OCR
   - Corrige 50+ abreviaturas legales mexicanas
   - Guarda el resultado en la base de datos

#### **B) Iniciar Análisis NLP (Admin)**

**Endpoint:** `POST /admin/tomos/{tomo_id}/analyze`

```javascript
// Ejemplo desde consola del navegador en admin
fetch('http://localhost:8000/admin/tomos/1/analyze', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('token'),
        'Content-Type': 'application/json'
    }
})
.then(r => r.json())
.then(data => console.log('Análisis iniciado:', data));
```

El sistema extraerá automáticamente:
- ✅ **Diligencias** (tipo, fecha, responsable, número de oficio)
- ✅ **Personas** (nombre, rol, dirección, teléfonos)
- ✅ **Lugares** (direcciones completas, colonias, municipios)
- ✅ **Fechas importantes**
- ✅ **Alertas de inactividad MP** (>6 meses)

#### **C) Visualizar Resultados (Usuario)**

1. Abre `dashboard-usuario.html`
2. Inicia sesión con credenciales de usuario
3. En la lista de carpetas, haz clic en el botón **"Ver Análisis"** (verde)
4. Se desplegará la sección de análisis con 5 tabs:

   **📋 Tab 1: Diligencias**
   - Tabla con todas las diligencias
   - Filtros: tipo, fecha inicio/fin, ordenamiento
   - Columnas: #, Tipo, Fecha, Responsable, Oficio, Acciones

   **👥 Tab 2: Personas**
   - Tabla de personas identificadas
   - Filtros: nombre, rol
   - Columnas: Nombre, Rol, Dirección, Teléfono, # Declaraciones
   - Click en "Ver Declaraciones" para ver detalles en modal

   **📍 Tab 3: Lugares**
   - Tarjetas con ubicaciones extraídas
   - Filtros: buscar texto, tipo (avenida/calle/colonia)
   - Muestra: dirección, colonia, municipio, CP

   **🚨 Tab 4: Alertas**
   - Alertas de inactividad del Ministerio Público
   - Filtros: Todas / Críticas (>365 días) / Altas (>270 días) / Medias (>180 días)
   - Tarjetas con colores por prioridad

   **🕐 Tab 5: Línea de Tiempo**
   - Visualización cronológica de todos los eventos
   - Integra diligencias, personas, lugares y fechas importantes
   - Timeline visual con marcadores de colores

---

## 🎨 **CARACTERÍSTICAS VISUALES**

### **Estadísticas Rápidas**
Al abrir el análisis verás 4 tarjetas de estadísticas:
- 🔨 **Diligencias** (morado)
- 👥 **Personas Identificadas** (azul)
- 📍 **Lugares** (verde)
- ⚠️ **Alertas Activas** (rojo)

### **Colores de Alerta**
- 🔴 **Crítica** (>365 días): Borde rojo, fondo rosa claro
- 🟠 **Alta** (>270 días): Borde naranja, fondo amarillo claro
- 🔵 **Media** (>180 días): Borde azul, fondo azul claro

### **Animaciones**
- ✨ Hover effects en todas las tarjetas
- 🎞️ Transiciones suaves al cambiar de tab
- 📜 Scroll automático al abrir análisis

---

## 🔌 **ESTRUCTURA DE LA API**

### **Endpoints de Usuario** (Base: `/usuario`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/carpetas/{id}/estadisticas` | Estadísticas generales |
| GET | `/carpetas/{id}/diligencias` | Listado de diligencias (con filtros) |
| GET | `/carpetas/{id}/personas` | Personas identificadas |
| GET | `/personas/{id}/declaraciones` | Declaraciones de una persona |
| GET | `/carpetas/{id}/lugares` | Lugares identificados |
| GET | `/carpetas/{id}/fechas` | Fechas importantes |
| GET | `/carpetas/{id}/alertas` | Alertas de inactividad MP |
| GET | `/carpetas/{id}/linea-tiempo` | Timeline completo |

### **Parámetros de Filtro**

**Diligencias:**
- `tipo` (str): Filtrar por tipo de diligencia
- `fecha_inicio` (date): Desde esta fecha
- `fecha_fin` (date): Hasta esta fecha
- `orden` (str): "cronologico" / "fecha_desc" / "fecha_asc"

**Personas:**
- `buscar` (str): Buscar en nombre
- `rol` (str): Filtrar por rol

**Lugares:**
- `buscar` (str): Buscar en dirección/colonia/municipio
- `tipo` (str): "avenida" / "calle" / "colonia"

**Alertas:**
- `estado` (str): "activa" / "resuelta"
- `prioridad` (str): "crítica" / "alta" / "media"

---

## 🛠️ **FUNCIONES JAVASCRIPT DISPONIBLES**

### **Globales (frontend/js/analisis-juridico.js)**

```javascript
// Módulo principal
AnalisisJuridico.inicializar(carpetaId)
AnalisisJuridico.cargarEstadisticas()
AnalisisJuridico.cargarDiligencias(filtros)
AnalisisJuridico.cargarPersonas(filtros)
AnalisisJuridico.cargarLugares(filtros)
AnalisisJuridico.cargarAlertas(estado, prioridad)
AnalisisJuridico.cargarLineaTiempo()
AnalisisJuridico.verDetallePersona(personaId)

// Funciones del dashboard
abrirAnalisisJuridico(carpetaId, nombreCarpeta)
cerrarAnalisisJuridico()
filtrarDiligencias()
limpiarFiltrosDiligencias()
filtrarPersonas()
limpiarFiltrosPersonas()
filtrarLugares()
filtrarAlertasPrioridad(prioridad)
```

---

## 📦 **TECNOLOGÍAS UTILIZADAS**

### **Backend**
- **FastAPI** - Framework web
- **SQLAlchemy** - ORM
- **PostgreSQL** - Base de datos
- **Tesseract OCR** - Extracción de texto
- **PyPDF2** - Manipulación de PDFs
- **python-dateutil** - Parsing de fechas

### **Frontend**
- **Bootstrap 5.1.3** - Framework CSS
- **Font Awesome 6.0.0** - Iconos
- **Vanilla JavaScript** - Sin frameworks adicionales
- **CSS Grid/Flexbox** - Layouts responsivos

---

## 🔍 **CORRECCIÓN DE ABREVIATURAS**

El sistema corrige automáticamente **50+ abreviaturas** legales mexicanas:

| Abreviatura | Expansión | Categoría |
|-------------|-----------|-----------|
| `M.P.` | Ministerio Público | Autoridad |
| `Lic.` | Licenciado | Título |
| `Av.` | Avenida | Ubicación |
| `Col.` | Colonia | Ubicación |
| `C.P.` | Código Postal | Ubicación |
| `C.I.` | Carpeta de Investigación | Documento |
| `NUC` | Número Único de Caso | Documento |
| `Gob.` | Gobierno | Institución |

Ver lista completa en `backend/app/services/legal_ocr_service.py`

---

## 🧪 **TESTING**

### **Verificar Backend**
```bash
curl -X GET "http://localhost:8000/usuario/carpetas/1/estadisticas" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Respuesta esperada:
```json
{
  "success": true,
  "data": {
    "total_diligencias": 45,
    "total_personas": 23,
    "total_lugares": 18,
    "total_alertas_activas": 3,
    "ultima_actualizacion": "2024-01-15T10:30:00"
  }
}
```

### **Verificar Frontend**
1. Abre `dashboard-usuario.html` en navegador
2. Abre DevTools (F12) → Console
3. Verifica que no haya errores 404 o JS
4. Click en "Ver Análisis" de una carpeta
5. Verifica que las llamadas API aparezcan en Network tab

---

## ⚙️ **CONFIGURACIÓN**

### **API Base URL**
Edita `frontend/js/config.js`:
```javascript
const API_BASE_URL = 'http://localhost:8000'; // Cambia según tu entorno
```

### **Tokens JWT**
Los tokens se almacenan automáticamente en `localStorage`:
- Key: `token`
- Se incluyen en header `Authorization: Bearer {token}`

---

## 📚 **DOCUMENTACIÓN ADICIONAL**

- **Backend completo:** Ver `SISTEMA_ANALISIS_JURIDICO.md`
- **Instalación rápida:** Ver `INSTALACION_RAPIDA_ANALISIS.md`
- **Modelos de datos:** Ver `backend/app/models/analisis_juridico.py`
- **Endpoints API:** Ver `backend/app/controllers/analisis_usuario_controller.py`

---

## 🐛 **TROUBLESHOOTING**

### **Error: "El módulo AnalisisJuridico no está cargado"**
✅ Verifica que `<script src="js/analisis-juridico.js"></script>` esté en el HTML
✅ Revisa la consola de DevTools por errores de carga

### **Error 401: Unauthorized**
✅ Verifica que el token JWT esté en localStorage
✅ Prueba hacer logout/login nuevamente

### **No se muestran datos**
✅ Verifica que el backend esté corriendo
✅ Revisa que las tablas SQL estén creadas
✅ Confirma que haya datos de análisis en la carpeta seleccionada

### **Los estilos no se aplican**
✅ Verifica que `<link href="css/analisis-juridico.css">` esté en el `<head>`
✅ Limpia caché del navegador (Ctrl+Shift+R)

---

## 📞 **SOPORTE**

Para problemas o consultas:
1. Revisa los logs del backend: `backend/main.py`
2. Revisa la consola del navegador (F12)
3. Verifica que todos los archivos estén en su lugar
4. Confirma que el token JWT sea válido

---

## 🎉 **¡LISTO PARA USAR!**

El sistema está **100% funcional** e integrado. Solo necesitas:

1. ✅ Crear las tablas SQL (si no lo has hecho)
2. ✅ Iniciar el servidor backend
3. ✅ Abrir `dashboard-usuario.html`
4. ✅ Hacer click en "Ver Análisis"

**¡Disfruta del análisis jurídico automatizado!** 🚀⚖️
