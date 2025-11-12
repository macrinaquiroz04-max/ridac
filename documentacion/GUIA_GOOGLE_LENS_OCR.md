# 🔍 Funcionalidad Google Lens - Visor PDF OCR

**Sistema OCR FGJCDMX**  
**Desarrollado por:** Eduardo Lozada Quiroz, ISC  
**Fecha:** 27 de Octubre, 2025

---

## 📋 Descripción

Se ha implementado una funcionalidad similar a **Google Lens** en el visor de PDFs del sistema. Esta característica permite a los usuarios seleccionar cualquier área de un documento PDF escaneado y extraer el texto mediante OCR en tiempo real.

---

## ✨ Características Implementadas

### 1. **Selección de Área con el Mouse**
- Los usuarios pueden hacer **clic derecho** en el visor PDF
- Seleccionar la opción **"Seleccionar y copiar texto (Lens)"**
- Dibujar un rectángulo sobre el área deseada del documento
- El sistema resalta visualmente el área seleccionada

### 2. **Panel de Acciones Flotante**
Después de seleccionar un área, aparece un panel con 5 botones de acción:

| Botón | Icono | Función |
|-------|-------|---------|
| **Copiar** | 📋 | Copia el texto extraído al portapapeles |
| **Buscar** | 🔍 | Abre Google con búsqueda del texto extraído |
| **Traducir** | 🌐 | Abre Google Translate con el texto |
| **Escuchar** | 🔊 | Lee el texto en voz alta (español de México) |
| **Cancelar** | ✕ | Cierra el modo de selección |

### 3. **Extracción de Texto con OCR**
- Utiliza **Tesseract OCR** en el backend
- Configurado para español (`lang='spa'`)
- Alta resolución (300 DPI) para mejor precisión
- Procesamiento en tiempo real

---

## 🛠️ Implementación Técnica

### Backend - Nuevo Endpoint

**Ruta:** `POST /api/ocr/extract-area`

**Parámetros:**
```python
- file: UploadFile           # Archivo PDF
- page_number: int           # Número de página (1-indexed)
- x: float                   # Coordenada X del área
- y: float                   # Coordenada Y del área
- width: float               # Ancho del área
- height: float              # Alto del área
```

**Respuesta:**
```json
{
  "success": true,
  "texto": "Texto extraído del área seleccionada"
}
```

**Archivo:** `/backend/app/routes/ocr_area.py`

### Frontend - Modificaciones al Visor

**Archivo:** `/frontend/visor-pdf.html`

**Funciones principales:**
- `activarModoLens()` - Activa el modo de selección
- `extraerTextoDeArea()` - Llama al backend para OCR
- `copiarTextoLens()` - Copia texto al portapapeles
- `buscarTextoLens()` - Busca en Google
- `traducirTextoLens()` - Abre traductor
- `escucharTextoLens()` - Síntesis de voz
- `cerrarLens()` - Desactiva modo de selección

---

## 🎯 Cómo Usar

### Paso 1: Abrir un PDF
1. Ingresa al sistema OCR FGJCDMX
2. Abre cualquier tomo/documento PDF en el visor

### Paso 2: Activar Modo Lens
1. Haz **clic derecho** en cualquier parte del documento
2. Selecciona **"Seleccionar y copiar texto (Lens)"**
3. El cursor cambiará a una cruz (crosshair)

### Paso 3: Seleccionar Área
1. Haz clic y arrastra el mouse para crear un rectángulo
2. Suelta el mouse cuando hayas seleccionado el área deseada
3. Aparecerá un panel flotante con las opciones

### Paso 4: Elegir Acción
- **📋 Copiar:** Extrae y copia el texto al portapapeles
- **🔍 Buscar:** Busca el texto en Google (nueva pestaña)
- **🌐 Traducir:** Traduce el texto (Google Translate)
- **🔊 Escuchar:** Reproduce el texto en voz alta
- **✕ Cancelar:** Cierra sin hacer nada

---

## 📊 Ventajas vs OCR Tradicional

| Característica | OCR Tradicional | Google Lens OCR |
|----------------|-----------------|-----------------|
| Procesa todo el documento | ✅ | ❌ |
| Selección precisa de área | ❌ | ✅ |
| Procesamiento rápido | ❌ (lento) | ✅ (solo área) |
| Extracción on-demand | ❌ | ✅ |
| No requiere pre-procesamiento | ❌ | ✅ |
| Copiar texto específico | ❌ | ✅ |

---

## 🔧 Requisitos Técnicos

### Backend
```python
# Librerías utilizadas
pytesseract      # OCR engine
pdf2image        # Conversión PDF a imagen
Pillow (PIL)     # Procesamiento de imágenes
FastAPI          # Framework web
```

### Frontend
```javascript
// APIs utilizadas
Canvas API              // Renderizado de PDF
Web Speech API          // Síntesis de voz
Clipboard API           // Copiar al portapapeles
Fetch API              // Llamadas al backend
```

---

## 🐛 Solución de Problemas

### Problema: "No se detectó texto"
**Causa:** El área seleccionada no contiene texto legible o es muy pequeña  
**Solución:** 
- Selecciona un área más grande
- Asegúrate de que el texto sea claro en el PDF
- Verifica que no sea una imagen de muy baja calidad

### Problema: "Error al extraer texto"
**Causa:** Problema de conexión con el backend  
**Solución:**
- Verifica que el backend esté ejecutándose
- Revisa los logs: `docker logs sistema_ocr_backend`
- Reinicia el servicio: `docker compose restart backend`

### Problema: El texto extraído es incorrecto
**Causa:** Calidad baja del documento original  
**Solución:**
- El OCR depende de la calidad del documento
- Considera mejorar la resolución del escaneo original
- Selecciona áreas con texto más claro

---

## 🎨 Personalización

### Cambiar Idioma de OCR
En `/backend/app/routes/ocr_area.py`:
```python
texto_extraido = pytesseract.image_to_string(
    cropped_image,
    lang='spa',  # Cambiar a 'eng' para inglés
    config='--psm 6'
)
```

### Cambiar Voz de Síntesis
En `/frontend/visor-pdf.html`:
```javascript
utterance.lang = 'es-MX';  // Cambiar a 'en-US' para inglés
utterance.rate = 0.9;      // Velocidad: 0.5 a 2.0
```

---

## 📝 Notas de Desarrollo

- **DPI:** Se usa 300 DPI para mejor calidad OCR (línea 92 de `ocr_area.py`)
- **PSM Mode:** Configurado con `--psm 6` (bloque uniforme de texto)
- **Coordenadas:** Se escalan automáticamente según el zoom del visor
- **Seguridad:** Requiere autenticación Bearer token
- **Límite de texto:** Búsqueda en Google limitada a 500 caracteres

---

## 🚀 Mejoras Futuras Sugeridas

1. **Caché de OCR:** Guardar resultados de áreas frecuentemente consultadas
2. **Corrección automática:** Aplicar corrección ortográfica al texto extraído
3. **Múltiples selecciones:** Permitir seleccionar varias áreas simultáneamente
4. **Exportar a formatos:** PDF, Word, Excel con el texto extraído
5. **OCR multiidioma:** Detección automática del idioma del texto
6. **Historial:** Guardar áreas seleccionadas previamente

---

## 📞 Soporte

Para problemas técnicos o sugerencias, contactar a:
- **Desarrollador:** Eduardo Lozada Quiroz, ISC
- **Sistema:** OCR FGJCDMX - Unidad de Análisis y Contexto

---

## 📜 Licencia

Sistema OCR FGJCDMX - Propiedad Intelectual Registrada  
© 2025 - Todos los derechos reservados
