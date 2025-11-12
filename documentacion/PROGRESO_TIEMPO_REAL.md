# 📊 Barra de Progreso en Tiempo Real - Guía de Uso

## 🎯 Descripción

Sistema de monitoreo en tiempo real del procesamiento OCR y análisis jurídico mediante Server-Sent Events (SSE).

## ✨ Características

- **Progreso visual**: Barra animada que muestra el porcentaje de avance
- **Estadísticas en tiempo real**:
  - Página actual / Total de páginas
  - Tiempo transcurrido
  - Tiempo estimado restante
  - Velocidad de procesamiento (páginas/minuto)
  - Personas identificadas
- **Log de eventos**: Registro detallado de cada fase del proceso
- **Estado del proceso**: Indicador visual (Procesando, Completado, Error)

## 🚀 Cómo Usar

### 1. Acceder al Monitor de Progreso

Desde el dashboard, haz clic en el botón **"Monitor de Progreso"** o navega directamente a:

```
http://localhost/progress-monitor.html
```

### 2. Seleccionar Tomo y Tipo de Proceso

1. **Selecciona el Tomo** que deseas monitorear
2. **Elige el tipo de proceso**:
   - **OCR**: Para procesos de extracción de texto con Tesseract
   - **Análisis Jurídico**: Para análisis NLP de documentos ya procesados

### 3. Iniciar Monitoreo

1. Haz clic en el botón **"Iniciar Monitoreo"**
2. La conexión SSE se establecerá automáticamente
3. La interfaz comenzará a mostrar actualizaciones en tiempo real

### 4. Interpretar las Estadísticas

#### Barra de Progreso
- **Verde**: Proceso en curso
- **100%**: Proceso completado exitosamente

#### Estadísticas Principales
- **Página Actual**: Número de la página que se está procesando
- **Total Páginas**: Número total de páginas del documento
- **Tiempo Transcurrido**: Tiempo desde que inició el proceso
- **Tiempo Estimado**: Estimación del tiempo restante (basado en velocidad actual)

#### Estadísticas Adicionales
- **Páginas/Minuto**: Velocidad promedio de procesamiento
- **Personas Identificadas**: Cantidad de personas válidas extraídas (después de filtrado)

#### Registro de Eventos
Muestra mensajes detallados como:
- `✅ Conexión establecida con el servidor`
- `🚀 Iniciando monitoreo del proceso...`
- `📊 Procesando página 25 de 401`
- `✅ Proceso completado exitosamente!`
- `❌ Error en el proceso: [mensaje de error]`

## 🔧 Arquitectura Técnica

### Backend (FastAPI)

#### Endpoint SSE
```python
GET /api/progress/ocr/{tomo_id}?token={jwt_token}
GET /api/progress/analisis/{tomo_id}?token={jwt_token}
```

#### Estado Global
El backend mantiene un diccionario `procesamiento_estado` que almacena:

```python
procesamiento_estado[tomo_id] = {
    "estado": "procesando",           # iniciando|procesando|completado|error
    "progreso": 45.2,                 # Porcentaje (0-100)
    "pagina_actual": 181,             # Página en proceso
    "total_paginas": 401,             # Total de páginas
    "tiempo_transcurrido": 3245,      # Segundos desde inicio
    "tiempo_estimado": 3780,          # Segundos estimados restantes
    "velocidad": 3.35,                # Páginas por minuto
    "personas_encontradas": 15,       # Personas válidas encontradas
    "mensaje": "Procesando página...", # Mensaje descriptivo
    "errores": []                     # Lista de errores
}
```

### Frontend (JavaScript)

#### Conexión SSE
```javascript
const token = localStorage.getItem('token');
const url = `http://localhost:8000/api/progress/ocr/${tomoId}?token=${encodeURIComponent(token)}`;

eventSource = new EventSource(url);

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    // Actualizar interfaz con data.progreso, data.pagina_actual, etc.
};
```

#### Formato de Eventos
Cada evento SSE contiene un objeto JSON:

```json
{
    "estado": "procesando",
    "progreso": 45.2,
    "pagina_actual": 181,
    "total_paginas": 401,
    "tiempo_transcurrido": 3245,
    "tiempo_estimado": 3780,
    "velocidad": 3.35,
    "personas_encontradas": 15,
    "mensaje": "Procesando página 181 de 401",
    "errores": 0,
    "timestamp": "2025-06-15T14:30:25.123456"
}
```

## 📝 Ejemplos de Uso

### Ejemplo 1: Monitorear OCR de Tomo 12 (401 páginas)

1. Selecciona "Tomo 12" del dropdown
2. Mantén "OCR" como tipo de proceso
3. Haz clic en "Iniciar Monitoreo"
4. Observa:
   - Barra de progreso avanzando gradualmente
   - Velocidad estabilizándose alrededor de 3-4 pág/min
   - Tiempo estimado disminuyendo progresivamente
   - Personas encontradas incrementándose

**Tiempo estimado**: ~2 horas para 401 páginas

### Ejemplo 2: Monitorear Re-análisis

Si ya procesaste el OCR y solo quieres re-analizar:

1. Selecciona el tomo
2. Cambia a "Análisis Jurídico"
3. Inicia monitoreo
4. El análisis será mucho más rápido (solo NLP, sin OCR)

## ⚠️ Consideraciones Importantes

### Autenticación
- El monitor requiere autenticación válida
- El token JWT se pasa como query parameter (EventSource no soporta headers)
- Si el token expira, verás un error de conexión

### Rendimiento
- La actualización es cada 1 segundo
- No afecta el rendimiento del procesamiento OCR
- El stream se cierra automáticamente al completar o en error

### Múltiples Usuarios
- Varios usuarios pueden monitorear el mismo tomo simultáneamente
- Cada uno tiene su propia conexión SSE independiente
- Todos ven el mismo progreso (estado compartido)

### Reconexión
- Si pierdes conexión, haz clic en "Iniciar Monitoreo" nuevamente
- El estado se mantiene en el servidor
- Verás el progreso actual inmediatamente

## 🐛 Solución de Problemas

### "Error al cargar tomos"
- Verifica que el token sea válido
- Revisa que el backend esté ejecutándose
- Comprueba la consola del navegador para detalles

### "Conexión perdida con el servidor"
- El backend pudo haberse reiniciado
- Verificar estado del servicio Docker
- Revisar logs del backend: `docker logs backend`

### "No hay proceso activo"
- El proceso no ha iniciado aún
- Verifica que hayas iniciado el OCR/Análisis desde el dashboard
- El estado puede haberse limpiado si el backend se reinició

### Progreso estancado
- Página pesada (imagen de alta resolución)
- Tesseract procesando texto denso
- Revisa logs del backend para ver actividad

## 📊 Integración con Otros Componentes

### Dashboard Principal
Agrega un enlace al monitor:

```html
<a href="progress-monitor.html" class="btn btn-info">
    <i class="bi bi-activity"></i> Monitor de Progreso
</a>
```

### Iniciar OCR con Monitoreo Automático
Desde el dashboard, después de iniciar OCR:

```javascript
// Después de iniciar OCR exitosamente
if (response.success) {
    // Redirigir al monitor con el tomo preseleccionado
    window.location.href = `progress-monitor.html?tomo=${tomoId}&tipo=ocr&autostart=true`;
}
```

### API Endpoints Relacionados

- **Iniciar OCR**: `POST /api/iniciar-ocr-completo`
- **Iniciar Análisis**: `POST /api/analizar-contenido-ocr`
- **Estado del Tomo**: `GET /api/tomos/{tomo_id}/estado`
- **Monitor SSE**: `GET /api/progress/ocr/{tomo_id}`

## 🎨 Personalización

### Cambiar Colores de la Barra
Edita `progress-monitor.html`, busca `.progress-bar`:

```css
.progress-bar {
    background: linear-gradient(90deg, #4CAF50, #81C784); /* Verde personalizado */
}
```

### Modificar Frecuencia de Actualización
En `progress_controller.py`, cambia el sleep:

```python
await asyncio.sleep(2)  # Actualizar cada 2 segundos en lugar de 1
```

### Agregar Sonido al Completar
En `progress-monitor.html`, función `updateProgress`:

```javascript
if (data.estado === 'completado') {
    const audio = new Audio('completion-sound.mp3');
    audio.play();
}
```

## 📈 Casos de Uso Avanzados

### Monitorear Procesamiento por Lotes
Si procesas múltiples tomos:

1. Abre múltiples pestañas del monitor
2. Cada pestaña monitorea un tomo diferente
3. Observa el progreso de todos simultáneamente

### Exportar Log de Eventos
Agrega un botón para descargar el log:

```javascript
function exportarLog() {
    const logText = document.getElementById('logContainer').innerText;
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `log_tomo_${tomoId}_${Date.now()}.txt`;
    a.click();
}
```

## 🔒 Seguridad

- ✅ Requiere autenticación JWT válida
- ✅ Validación de permisos del usuario
- ✅ CORS configurado para origen específico
- ✅ No expone información sensible en eventos
- ✅ Conexión cerrada automáticamente al completar

## 🚀 Mejoras Futuras

- [ ] Notificaciones push al completar proceso
- [ ] Gráficos históricos de velocidad de procesamiento
- [ ] Estimación más precisa basada en ML
- [ ] Pausa/Reanudación de procesamiento
- [ ] Vista de múltiples tomos en una sola pantalla
- [ ] Exportación de estadísticas a CSV/Excel

## 📞 Soporte

Si encuentras problemas o tienes sugerencias, revisa:

1. **Logs del backend**: `docker logs -f backend`
2. **Consola del navegador**: F12 → Console
3. **Estado del sistema**: `docker ps -a`
4. **Documentación adicional**: `docs/`

---

**Última actualización**: Junio 2025  
**Versión**: 2.0  
**Compatibilidad**: Chrome 90+, Firefox 88+, Edge 90+
