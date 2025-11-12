# 📄 VISOR PDF CON TEXTO SELECCIONABLE - Estilo Google Lens

**Sistema OCR FGJCDMX - Permitir copiar y pegar texto de PDFs**

---

## 🎯 OBJETIVO

Crear un visor de PDF que permita a los usuarios:
- ✅ Ver el PDF procesado en pantalla completa
- ✅ **Seleccionar y copiar texto** directamente del PDF (como Google Lens)
- ✅ Hacer zoom y navegación
- ✅ Buscar texto dentro del documento (Ctrl+F)
- ✅ Funciona con los PDFs que ya tienen OCR embebido

---

## 📋 OPCIONES DE IMPLEMENTACIÓN

### ✅ **OPCIÓN 1: Visor PDF con PDF.js (RECOMENDADA)**

**Ventajas:**
- ✅ Los PDFs ya tienen texto OCR embebido (Tesseract lo hace)
- ✅ No requiere procesamiento adicional
- ✅ Funciona nativamente en navegador
- ✅ Permite selección de texto automáticamente
- ✅ Incluye búsqueda (Ctrl+F)

**Biblioteca:** [PDF.js de Mozilla](https://mozilla.github.io/pdf.js/)

---

### ⚙️ **OPCIÓN 2: PDF a Imágenes + Texto Overlay**

**Ventajas:**
- ✅ Control total sobre la presentación
- ✅ Puedes destacar palabras específicas
- ✅ Estilo más parecido a Google Lens

**Desventajas:**
- ❌ Requiere convertir PDF → imágenes
- ❌ Más procesamiento
- ❌ Más complejo de mantener

---

## 🚀 IMPLEMENTACIÓN RÁPIDA - OPCIÓN 1 (PDF.js)

### 1️⃣ **Crear archivo `frontend/visor-pdf.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visor PDF - Sistema OCR FGJCDMX</title>
    <link rel="stylesheet" href="css/styles.css">
    <style>
        body {
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: #2c3e50;
        }

        .pdf-container {
            width: 100%;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .pdf-toolbar {
            background: #34495e;
            padding: 10px 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            color: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }

        .pdf-toolbar button {
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }

        .pdf-toolbar button:hover {
            background: #2980b9;
        }

        .pdf-toolbar button:disabled {
            background: #7f8c8d;
            cursor: not-allowed;
        }

        .pdf-info {
            flex: 1;
            text-align: center;
            font-size: 14px;
        }

        .pdf-viewer {
            flex: 1;
            overflow: auto;
            background: #34495e;
            display: flex;
            justify-content: center;
            padding: 20px;
        }

        #pdf-canvas {
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            cursor: text;
            background: white;
        }

        .text-layer {
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            bottom: 0;
            overflow: hidden;
            opacity: 0.2;
            line-height: 1.0;
        }

        .text-layer > span {
            color: transparent;
            position: absolute;
            white-space: pre;
            cursor: text;
            transform-origin: 0% 0%;
        }

        .text-layer ::selection {
            background: rgba(52, 152, 219, 0.5);
        }

        .search-box {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .search-box input {
            padding: 8px;
            border: none;
            border-radius: 5px;
            width: 200px;
        }

        .zoom-controls {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .zoom-level {
            min-width: 60px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="pdf-container">
        <div class="pdf-toolbar">
            <button onclick="volverAtras()">← Volver</button>
            
            <button id="prev-page" onclick="prevPage()">◄ Anterior</button>
            <div class="pdf-info">
                Página <span id="page-num">1</span> de <span id="page-count">0</span>
            </div>
            <button id="next-page" onclick="nextPage()">Siguiente ►</button>

            <div class="zoom-controls">
                <button onclick="zoomOut()">🔍-</button>
                <span class="zoom-level" id="zoom-level">100%</span>
                <button onclick="zoomIn()">🔍+</button>
                <button onclick="fitToWidth()">Ajustar ancho</button>
            </div>

            <div class="search-box">
                <input type="text" id="search-input" placeholder="Buscar texto...">
                <button onclick="searchText()">🔍 Buscar</button>
            </div>

            <button onclick="descargarPDF()">📥 Descargar</button>
        </div>

        <div class="pdf-viewer" id="pdf-viewer">
            <div style="position: relative;">
                <canvas id="pdf-canvas"></canvas>
                <div id="text-layer" class="text-layer"></div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script src="js/config.js"></script>
    <script>
        // Configurar PDF.js
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

        let pdfDoc = null;
        let pageNum = 1;
        let pageRendering = false;
        let pageNumPending = null;
        let scale = 1.5;
        let tomoId = null;
        let pdfUrl = null;

        // Obtener ID del tomo desde URL
        const urlParams = new URLSearchParams(window.location.search);
        tomoId = urlParams.get('tomo_id');

        if (!tomoId) {
            alert('❌ No se especificó el tomo a visualizar');
            window.location.href = 'carpetas.html';
        }

        // Cargar información del tomo
        async function cargarTomo() {
            try {
                const response = await fetch(`${API_URL}/tomos/${tomoId}`, {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });

                if (!response.ok) throw new Error('Error al cargar tomo');

                const tomo = await response.json();
                pdfUrl = `${API_URL.replace('/api', '')}/documentos/${tomo.ruta_pdf}`;
                
                // Cargar PDF
                await cargarPDF(pdfUrl);
            } catch (error) {
                console.error('Error:', error);
                alert('❌ Error al cargar el documento');
            }
        }

        // Cargar PDF
        async function cargarPDF(url) {
            const loadingTask = pdfjsLib.getDocument(url);
            
            try {
                pdfDoc = await loadingTask.promise;
                document.getElementById('page-count').textContent = pdfDoc.numPages;
                renderPage(pageNum);
            } catch (error) {
                console.error('Error cargando PDF:', error);
                alert('❌ Error al cargar el PDF');
            }
        }

        // Renderizar página
        async function renderPage(num) {
            pageRendering = true;
            
            const page = await pdfDoc.getPage(num);
            const viewport = page.getViewport({ scale: scale });
            
            const canvas = document.getElementById('pdf-canvas');
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };

            await page.render(renderContext).promise;

            // Renderizar capa de texto (para selección)
            const textLayer = document.getElementById('text-layer');
            textLayer.innerHTML = '';
            textLayer.style.width = canvas.width + 'px';
            textLayer.style.height = canvas.height + 'px';

            const textContent = await page.getTextContent();
            
            textContent.items.forEach(item => {
                const tx = pdfjsLib.Util.transform(
                    pdfjsLib.Util.transform(viewport.transform, item.transform),
                    [1, 0, 0, -1, 0, 0]
                );

                const span = document.createElement('span');
                span.textContent = item.str;
                span.style.left = tx[4] + 'px';
                span.style.top = tx[5] + 'px';
                span.style.fontSize = Math.abs(tx[3]) + 'px';
                span.style.fontFamily = item.fontName;
                textLayer.appendChild(span);
            });

            pageRendering = false;
            
            if (pageNumPending !== null) {
                renderPage(pageNumPending);
                pageNumPending = null;
            }

            document.getElementById('page-num').textContent = num;
            document.getElementById('prev-page').disabled = (num <= 1);
            document.getElementById('next-page').disabled = (num >= pdfDoc.numPages);
        }

        function queueRenderPage(num) {
            if (pageRendering) {
                pageNumPending = num;
            } else {
                renderPage(num);
            }
        }

        function prevPage() {
            if (pageNum <= 1) return;
            pageNum--;
            queueRenderPage(pageNum);
        }

        function nextPage() {
            if (pageNum >= pdfDoc.numPages) return;
            pageNum++;
            queueRenderPage(pageNum);
        }

        function zoomIn() {
            scale += 0.2;
            updateZoomLevel();
            queueRenderPage(pageNum);
        }

        function zoomOut() {
            if (scale <= 0.5) return;
            scale -= 0.2;
            updateZoomLevel();
            queueRenderPage(pageNum);
        }

        function fitToWidth() {
            const viewer = document.getElementById('pdf-viewer');
            scale = (viewer.clientWidth - 40) / (612 * 1.5); // 612 = ancho carta en puntos
            updateZoomLevel();
            queueRenderPage(pageNum);
        }

        function updateZoomLevel() {
            document.getElementById('zoom-level').textContent = Math.round(scale * 100) + '%';
        }

        async function searchText() {
            const searchTerm = document.getElementById('search-input').value.toLowerCase();
            if (!searchTerm) return;

            // Buscar en todas las páginas
            for (let i = 1; i <= pdfDoc.numPages; i++) {
                const page = await pdfDoc.getPage(i);
                const textContent = await page.getTextContent();
                const text = textContent.items.map(item => item.str).join(' ').toLowerCase();
                
                if (text.includes(searchTerm)) {
                    pageNum = i;
                    queueRenderPage(pageNum);
                    alert(`✅ Encontrado en página ${i}`);
                    return;
                }
            }

            alert('❌ No se encontró el texto');
        }

        function descargarPDF() {
            window.open(pdfUrl, '_blank');
        }

        function volverAtras() {
            window.history.back();
        }

        // Atajos de teclado
        document.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowLeft') prevPage();
            if (e.key === 'ArrowRight') nextPage();
            if (e.key === '+' || e.key === '=') zoomIn();
            if (e.key === '-') zoomOut();
        });

        // Iniciar carga
        cargarTomo();
    </script>
</body>
</html>
```

---

### 2️⃣ **Modificar `frontend/carpetas.html`**

Agregar botón "Ver PDF" en la tabla de tomos:

```javascript
// Agregar esta columna en la tabla de tomos
<td>
    <button onclick="verPDF(${tomo.id})" class="btn-view">
        📄 Ver PDF
    </button>
</td>

// Agregar esta función
function verPDF(tomoId) {
    window.open(`visor-pdf.html?tomo_id=${tomoId}`, '_blank');
}
```

---

### 3️⃣ **Endpoint de backend para servir PDFs**

En `backend/app/routes/tomos.py`:

```python
@router.get("/tomos/{tomo_id}")
async def obtener_tomo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    GET /api/tomos/{tomo_id}
    Obtener información de un tomo.
    """
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    
    if not tomo:
        raise HTTPException(status_code=404, detail="Tomo no encontrado")
    
    # Verificar permisos del usuario para ver la carpeta
    # (código de verificación de permisos aquí)
    
    return {
        "id": tomo.id,
        "numero_tomo": tomo.numero_tomo,
        "nombre_archivo": tomo.nombre_archivo,
        "ruta_pdf": tomo.ruta_pdf,
        "total_paginas": tomo.total_paginas,
        "carpeta_id": tomo.carpeta_id
    }
```

---

## 🎯 CARACTERÍSTICAS DEL VISOR

### ✅ **Funcionalidades incluidas:**

1. **Navegación:**
   - ◄ Anterior / Siguiente ►
   - Flechas del teclado (← →)
   - Contador de páginas

2. **Zoom:**
   - 🔍+ Aumentar
   - 🔍- Reducir
   - Ajustar al ancho
   - Atajos: `+` y `-`

3. **Búsqueda:**
   - 🔍 Buscar texto en todo el documento
   - Navega a la primera coincidencia

4. **Selección de texto:**
   - ✂️ Click y arrastrar para seleccionar
   - Ctrl+C para copiar
   - ¡COMO GOOGLE LENS! 🎯

5. **Descargar:**
   - 📥 Descargar PDF completo

---

## 🔧 ALTERNATIVA: PDF a Imágenes (Opción 2)

Si quieres más control visual (como Google Lens), puedes convertir el PDF a imágenes:

### Backend endpoint para convertir PDF → Imágenes:

```python
from pdf2image import convert_from_path

@router.get("/tomos/{tomo_id}/pagina/{numero_pagina}")
async def obtener_pagina_imagen(
    tomo_id: int,
    numero_pagina: int,
    db: Session = Depends(get_db)
):
    """
    Convertir una página del PDF a imagen PNG
    """
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    
    # Convertir página a imagen
    images = convert_from_path(
        tomo.ruta_pdf,
        first_page=numero_pagina,
        last_page=numero_pagina,
        dpi=200
    )
    
    # Retornar imagen
    img_byte_arr = io.BytesIO()
    images[0].save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return StreamingResponse(img_byte_arr, media_type="image/png")
```

---

## 📊 COMPARACIÓN DE OPCIONES

| Característica | PDF.js (Opción 1) | PDF → Imagen (Opción 2) |
|----------------|-------------------|-------------------------|
| **Facilidad** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Velocidad** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Selección texto** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Control visual** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Procesamiento** | Ninguno | Alto |
| **Calidad** | Original | Depende del DPI |

---

## 🚀 INSTALACIÓN MAÑANA

### Pasos:

1. **Copiar `visor-pdf.html`** a `frontend/`
2. **Modificar `carpetas.html`** para agregar botón "Ver PDF"
3. **Agregar endpoint** `/api/tomos/{id}` en backend (si no existe)
4. **Reiniciar Docker:**
   ```powershell
   docker-compose restart nginx backend
   ```
5. **Probar:**
   - Ir a Carpetas
   - Click en "Ver PDF"
   - Seleccionar texto con el mouse
   - Copiar (Ctrl+C) ✅

---

## 📝 MEJORAS FUTURAS

- 🖍️ Resaltado de palabras clave
- 📌 Marcadores/anotaciones
- 🔄 Rotación de páginas
- 📄 Vista de miniaturas
- 💾 Guardar progreso de lectura
- 🎨 Modo nocturno
- 📱 Versión móvil optimizada

---

## ✅ VENTAJAS DE ESTE SISTEMA

1. ✅ **Sin dependencias adicionales** (solo PDF.js del CDN)
2. ✅ **Funciona con PDFs existentes** (ya tienen OCR)
3. ✅ **Selección nativa** (como cualquier PDF)
4. ✅ **Búsqueda integrada** en el navegador
5. ✅ **Rápido y ligero**
6. ✅ **Compatible con todos los navegadores modernos**

---

**¡Mañana lo armamos en la oficina en menos de 30 minutos!** 🚀

Última actualización: 20 de octubre de 2025
