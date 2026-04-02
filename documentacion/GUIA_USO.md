# Guía de Uso — Sistema OCR RIDAC

## Acceso al Sistema

Abrir el navegador en `http://localhost:5173` (desarrollo) o en la URL asignada en producción.

Ingresar con las credenciales proporcionadas por el administrador.  
El sistema redirige automáticamente al dashboard correspondiente según el rol.

---

## Rol: Administrador

### Dashboard Principal `/dashboard`

Panorama general del sistema: tomos procesados, pendientes, usuarios activos, alertas recientes.

---

### Gestión de Carpetas `/carpetas`

- Crear, editar y eliminar **carpetas de investigación**
- Cada carpeta agrupa varios **tomos** (expedientes escaneados)
- Subir tomos en PDF — el sistema los encola para procesamiento OCR

---

### Gestión de Usuarios `/usuarios`

- Alta, baja y modificación de usuarios analistas
- Asignación de rol (`admin` / `usuario`)
- Resetear contraseña

---

### Permisos por Analista `/permisos`

- Por cada combinación **usuario + tomo** se pueden activar:
  - **Ver** — el analista puede abrir el tomo
  - **Buscar** — puede buscar texto dentro del tomo
  - **Exportar** — puede descargar resultados
- Sin permiso de `ver`, el tomo no aparece en el dashboard del analista

---

### Monitor OCR `/monitor-ocr`

- Estado en tiempo real de los trabajos de extracción OCR
- Ver progreso por tomo: páginas procesadas / total
- Reencolar tomos con error

---

### Análisis IA `/analisis-ia`

Módulo de análisis jurídico masivo:

1. Seleccionar carpeta
2. Elegir tomos a analizar (checkbox)
3. Iniciar análisis — el sistema extrae automáticamente:
   - Diligencias (tipo, fecha, responsable, folio)
   - Personas mencionadas
   - Fechas clave
   - Lugares
   - Alertas de inactividad del MP
4. Ver resultados agrupados con estadísticas por carpeta

---

### Autocorrector Legal `/autocorrector-legal`

Herramienta para estandarizar términos jurídicos en el texto OCR extraído.  
Corrige abreviaciones, errores tipográficos comunes en expedientes legales.

---

### Corrección de Diligencias `/correccion-diligencias`

Revisión manual y corrección de diligencias detectadas automáticamente.

---

### Auditoría `/auditoria`

Log completo de acciones del sistema:
- Quién accedió a qué documento y cuándo
- Búsquedas realizadas
- Exportaciones generadas
- Cambios de configuración

Exportable en CSV.

---

### Búsqueda Semántica `/busqueda-semantica`

Búsqueda por significado mediante embeddings vectoriales.  
Previamente generar los embeddings desde `/generar-embeddings`.

---

### Revisión de Direcciones `/revision-direcciones`

Validación y normalización de domicilios detectados en los documentos.

---

### Limpieza de Personas `/limpieza-personas`

Deduplicación y normalización de nombres de personas extraídos por OCR.

---

## Rol: Analista (Usuario)

### Dashboard Analista `/dashboard-usuario`

Muestra únicamente los **tomos asignados** al analista con permisos activos.

Acciones disponibles por tomo (según permisos):
- **Ver** — abre el visor PDF
- **Buscar** — accede a la búsqueda de texto
- **Análisis jurídico** — accede al análisis avanzado del tomo
- **Exportar** — descarga resultados

---

### Búsqueda de Texto `/busqueda`

Búsqueda libre dentro de los tomos a los que el analista tiene acceso.

- Resaltado de coincidencias en texto
- Filtros por carpeta / tomo / fecha

---

### Análisis Jurídico Avanzado `/analisis-avanzado`

Vista detallada del análisis de un tomo específico, organizada en pestañas:

| Pestaña | Contenido |
|---------|-----------|
| 📅 Fechas | Todas las fechas detectadas con contexto y número de página |
| 👤 Nombres | Personas mencionadas con frecuencia y rol |
| 🏠 Direcciones | Domicilios detectados |
| 🌍 Lugares | Lugares geográficos referenciados |
| ⚖️ Diligencias | Lista completa: tipo, fecha, responsable, folio, descripción |
| 🚨 Alertas | Alertas de inactividad del MP con texto literal |

El tomo se puede precargar con `?tomo_id=X` en la URL.

---

### Visor PDF `/visor-pdf`

Visualizador de documentos con:
- Navegación de páginas
- Texto OCR extraído superpuesto / seleccionable
- Salto directo a páginas con coincidencias de búsqueda

---

### Cambiar Contraseña `/cambiar-password`

Disponible para todos los usuarios. Requiere contraseña actual.

---

## Flujo de Trabajo Típico

```
Admin sube PDF ──► OCR procesa ──► Admin asigna permisos al analista
                                              │
                                   Analista ve tomo en dashboard
                                              │
                              ┌───────────────┴───────────────┐
                              │                               │
                       Busca texto                    Ve análisis jurídico
                    (términos específicos)         (diligencias, alertas, etc.)
                              │                               │
                         Exporta resultados              Reporta hallazgos
```
