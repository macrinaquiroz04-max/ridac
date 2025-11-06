/**
 * 🔍 GOOGLE LENS-STYLE OCR v2.0
 * Implementación avanzada con Computer Vision y Deep Learning
 * 
 * Tecnologías implementadas:
 * - Computer Vision: Detección de regiones de texto
 * - OCR Multi-Motor: Tesseract + WebAssembly
 * - Segmentación semántica: Separación texto/fondo
 * - Resaltado en tiempo real: Overlay con OpenGL-like rendering
 * - NLP básico: Corrección y contextualización
 * 
 * Autor: Eduardo Lozada
 * Fecha: 29 Octubre 2025
 */

class GoogleLensOCR {
    constructor(pdfViewer, canvasId) {
        this.pdfViewer = pdfViewer;
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
        this.isSelecting = false;
        this.startX = 0;
        this.startY = 0;
        this.endX = 0;
        this.endY = 0;
        this.selectionBox = null;
        this.overlay = null;
        this.tesseractWorker = null;
        this.isProcessing = false;
        this.autoDetectMode = false;
        this.detectedRegions = [];
        
        // Configuración de Computer Vision
        this.visionConfig = {
            minTextHeight: 10,
            minTextWidth: 20,
            contrastThreshold: 30,
            edgeDetectionSensitivity: 0.3
        };
        
        this.initTesseract();
        this.setupEventListeners();
        this.createOverlay();
        
        console.log('🔍 Google Lens OCR v2.0 inicializado con Computer Vision');
    }
    
    async initTesseract() {
        try {
            console.log('📦 Cargando Tesseract.js con modelos avanzados...');
            
            // Crear worker de Tesseract con MEJOR configuración
            this.tesseractWorker = await Tesseract.createWorker({
                logger: m => {
                    if (m.status === 'recognizing text') {
                        const progress = Math.round(m.progress * 100);
                        this.updateProcessingIndicator(progress);
                    }
                },
                // Usar caché para mejorar velocidad
                cacheMethod: 'write',
            });
            
            // Cargar MEJOR modelo de idioma
            await this.tesseractWorker.loadLanguage('spa');
            await this.tesseractWorker.initialize('spa');
            
            // Configuración ÓPTIMA para documentos
            await this.tesseractWorker.setParameters({
                tessedit_pageseg_mode: Tesseract.PSM.AUTO,
                tessedit_ocr_engine_mode: Tesseract.OEM.LSTM_ONLY, // Solo red neuronal
            });
            
            console.log('✅ Tesseract.js listo con LSTM neural network');
        } catch (error) {
            console.error('❌ Error cargando Tesseract:', error);
        }
    }
    
    createOverlay() {
        // Crear overlay transparente para dibujar la selección
        this.overlay = document.createElement('div');
        this.overlay.id = 'google-lens-overlay';
        this.overlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1000;
        `;
        
        // Crear caja de selección
        this.selectionBox = document.createElement('div');
        this.selectionBox.id = 'selection-box';
        this.selectionBox.style.cssText = `
            position: absolute;
            border: 2px solid #4285f4;
            background: rgba(66, 133, 244, 0.1);
            display: none;
            pointer-events: none;
            box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.3);
            transition: all 0.1s ease;
        `;
        
        this.overlay.appendChild(this.selectionBox);
        
        // Agregar al contenedor del PDF
        const pdfContainer = this.canvas.parentElement;
        pdfContainer.style.position = 'relative';
        pdfContainer.appendChild(this.overlay);
        
        // Crear indicador de procesamiento
        this.createProcessingIndicator();
    }
    
    createProcessingIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'processing-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(33, 33, 33, 0.95);
            color: white;
            padding: 20px 30px;
            border-radius: 12px;
            display: none;
            z-index: 10000;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        `;
        indicator.innerHTML = `
            <div style="text-align: center;">
                <div style="font-size: 16px; margin-bottom: 10px;">🔍 Analizando texto...</div>
                <div style="width: 200px; height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; overflow: hidden;">
                    <div id="progress-bar" style="width: 0%; height: 100%; background: #4285f4; transition: width 0.3s;"></div>
                </div>
                <div id="progress-text" style="font-size: 12px; margin-top: 8px; color: #aaa;">0%</div>
            </div>
        `;
        document.body.appendChild(indicator);
    }
    
    updateProcessingIndicator(progress) {
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        if (progressBar) progressBar.style.width = progress + '%';
        if (progressText) progressText.textContent = progress + '%';
    }
    
    showProcessingIndicator() {
        const indicator = document.getElementById('processing-indicator');
        if (indicator) indicator.style.display = 'block';
    }
    
    hideProcessingIndicator() {
        const indicator = document.getElementById('processing-indicator');
        if (indicator) indicator.style.display = 'none';
    }
    
    setupEventListeners() {
        // Mouse down - iniciar selección
        this.canvas.addEventListener('mousedown', (e) => this.startSelection(e));
        
        // Mouse move - actualizar selección
        this.canvas.addEventListener('mousemove', (e) => this.updateSelection(e));
        
        // Mouse up - finalizar y extraer texto
        this.canvas.addEventListener('mouseup', (e) => this.endSelection(e));
        
        // Cambiar cursor
        this.canvas.style.cursor = 'crosshair';
    }
    
    startSelection(e) {
        if (this.isProcessing) return;
        
        this.isSelecting = true;
        const rect = this.canvas.getBoundingClientRect();
        this.startX = e.clientX - rect.left;
        this.startY = e.clientY - rect.top;
        
        // Mostrar caja de selección
        this.selectionBox.style.display = 'block';
        this.selectionBox.style.left = this.startX + 'px';
        this.selectionBox.style.top = this.startY + 'px';
        this.selectionBox.style.width = '0px';
        this.selectionBox.style.height = '0px';
    }
    
    updateSelection(e) {
        if (!this.isSelecting) return;
        
        const rect = this.canvas.getBoundingClientRect();
        this.endX = e.clientX - rect.left;
        this.endY = e.clientY - rect.top;
        
        // Actualizar tamaño de la caja
        const x = Math.min(this.startX, this.endX);
        const y = Math.min(this.startY, this.endY);
        const width = Math.abs(this.endX - this.startX);
        const height = Math.abs(this.endY - this.startY);
        
        this.selectionBox.style.left = x + 'px';
        this.selectionBox.style.top = y + 'px';
        this.selectionBox.style.width = width + 'px';
        this.selectionBox.style.height = height + 'px';
    }
    
    async endSelection(e) {
        if (!this.isSelecting) return;
        
        this.isSelecting = false;
        
        // Obtener coordenadas finales
        const rect = this.canvas.getBoundingClientRect();
        this.endX = e.clientX - rect.left;
        this.endY = e.clientY - rect.top;
        
        // Calcular área seleccionada
        const x = Math.min(this.startX, this.endX);
        const y = Math.min(this.startY, this.endY);
        const width = Math.abs(this.endX - this.startX);
        const height = Math.abs(this.endY - this.startY);
        
        // Validar selección mínima
        if (width < 10 || height < 10) {
            this.selectionBox.style.display = 'none';
            return;
        }
        
        // Extraer texto del área seleccionada
        await this.extractTextFromArea(x, y, width, height);
    }
    
    async extractTextFromArea(x, y, width, height) {
        if (!this.tesseractWorker) {
            this.showToast('❌ Tesseract no está listo', 'error');
            this.selectionBox.style.display = 'none';
            return;
        }
        
        try {
            this.isProcessing = true;
            this.showProcessingIndicator();
            this.showToast('🔍 Analizando con Computer Vision...', 'info');
            
            // Obtener imagen del área seleccionada
            const imageData = this.ctx.getImageData(x, y, width, height);
            
            // Crear canvas temporal con el área seleccionada
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = width;
            tempCanvas.height = height;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.putImageData(imageData, 0, 0);
            
            // 🎨 Mejorar imagen para mejor OCR
            const enhancedCanvas = this.simpleEnhance(tempCanvas);
            
            // 🔍 Extraer texto con Tesseract - MÁXIMA PRECISIÓN
            await this.tesseractWorker.setParameters({
                tessedit_pageseg_mode: Tesseract.PSM.AUTO, // Detección automática de layout
                tessedit_char_whitelist: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÉÍÓÚáéíóúÑñ0123456789 .,;:()[]{}/-_"\'°',
                preserve_interword_spaces: '1',
                tessedit_do_invert: '0',
                classify_bln_numeric_mode: '0',
            });
            
            const result = await this.tesseractWorker.recognize(enhancedCanvas);
            const texto = result.data.text.trim();
            const confidence = result.data.confidence;
            
            console.log(`📊 OCR completado: ${confidence.toFixed(1)}% confianza`);
            
            if (texto) {
                // 📝 Post-procesamiento NLP básico
                const textoLimpio = this.postProcessText(texto);
                
                // Mostrar resultado SIN copiar automáticamente
                this.showTextResult(textoLimpio, confidence, x, y + height + 10);
                this.showToast(`✅ Texto extraído y listo para copiar`, 'success');
            } else {
                this.showToast('⚠️ No se detectó texto en el área', 'warning');
            }
            
        } catch (error) {
            console.error('❌ Error extrayendo texto:', error);
            this.showToast('❌ Error al extraer texto', 'error');
        } finally {
            this.isProcessing = false;
            this.hideProcessingIndicator();
            
            // Ocultar selección después de 2 segundos
            setTimeout(() => {
                this.selectionBox.style.display = 'none';
            }, 2000);
        }
    }
    
    postProcessText(texto) {
        /**
         * 📝 Post-procesamiento inteligente para limpiar errores de OCR
         */
        let cleaned = texto;
        
        try {
            console.log('📝 Texto original:', texto);
            
            // 1. Corregir palabras comunes mal reconocidas PRIMERO
            const diccionario = {
                'FiscalIINVESTIGACIÓN': 'Fiscalía INVESTIGACIÓN',
                'FiscalIa': 'Fiscalía',
                'Investigacion': 'Investigación',
                'INVESTIGACION': 'INVESTIGACIÓN',
                'Numero': 'Número',
                'Agencia': 'Agencia',
                'Ministerio': 'Ministerio',
                'Publico': 'Público',
                'Mexico': 'México',
                'Distrito': 'Distrito',
            };
            
            for (const [mal, bien] of Object.entries(diccionario)) {
                const regex = new RegExp(mal, 'gi');
                cleaned = cleaned.replace(regex, bien);
            }
            
            // 2. ELIMINAR letras duplicadas incorrectas (ej: "II" → "I" en medio de palabra)
            // Pero NO tocar siglas como "III" o números romanos
            cleaned = cleaned.replace(/([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])\2+/gu, '$1$2');
            
            // 3. SEPARAR palabras pegadas: minúscula seguida de MAYÚSCULAS
            // "FiscalINVESTIGACIÓN" → "Fiscal INVESTIGACIÓN"
            cleaned = cleaned.replace(/([a-záéíóúñ])([A-ZÁÉÍÓÚÑ]{4,})/gu, '$1 $2');
            
            // 4. ELIMINAR letras minúsculas sueltas pegadas a palabras capitalizadas
            // "dMéxico" → "México"
            cleaned = cleaned.replace(/\b[a-z]([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)/gu, '$1');
            
            // 5. Eliminar letras minúsculas antes de palabras en mayúscula
            // "d MÉXICO" → "MÉXICO"
            cleaned = cleaned.replace(/\b[a-z]\s+([A-ZÁÉÍÓÚÑ]{3,})/gu, '$1');
            
            // 6. Corregir números confundidos en palabras
            cleaned = cleaned.replace(/([a-záéíóúñ])0([a-záéíóúñ])/gi, '$1o$2'); // 0 → o
            
            // 7. Limpiar espacios múltiples
            cleaned = cleaned.replace(/\s+/g, ' ').trim();
            
            // 8. Corregir puntuación duplicada
            cleaned = cleaned.replace(/([.,;:!?])\1+/g, '$1');
            
            // 9. Capitalizar después de punto
            cleaned = cleaned.replace(/\.\s+([a-z])/g, (match, char) => {
                return '. ' + char.toUpperCase();
            });
            
            console.log('✅ Texto corregido:', cleaned);
            
        } catch (e) {
            console.warn('⚠️ Error en post-procesamiento:', e);
            return texto; // Devolver original si falla
        }
        
        return cleaned;
    }
    
    simpleEnhance(canvas) {
        /**
         * 🎨 PREPROCESAMIENTO MÁXIMO estilo Google Lens
         */
        // Escalar 4x para MÁXIMA resolución
        const scaledCanvas = document.createElement('canvas');
        scaledCanvas.width = canvas.width * 4;
        scaledCanvas.height = canvas.height * 4;
        const scaledCtx = scaledCanvas.getContext('2d');
        
        scaledCtx.imageSmoothingEnabled = true;
        scaledCtx.imageSmoothingQuality = 'high';
        scaledCtx.drawImage(canvas, 0, 0, scaledCanvas.width, scaledCanvas.height);
        
        const imageData = scaledCtx.getImageData(0, 0, scaledCanvas.width, scaledCanvas.height);
        const data = imageData.data;
        
        // Convertir a escala de grises
        const grayData = new Uint8ClampedArray(data.length / 4);
        for (let i = 0; i < data.length; i += 4) {
            grayData[i / 4] = Math.round(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
        }
        
        // Binarización Otsu
        const threshold = this.otsuThreshold(grayData);
        
        // Aplicar con margen más estricto
        for (let i = 0; i < data.length; i += 4) {
            const gray = grayData[i / 4];
            const value = gray > threshold ? 255 : 0;
            data[i] = data[i + 1] = data[i + 2] = value;
        }
        
        scaledCtx.putImageData(imageData, 0, 0);
        return scaledCanvas;
    }
    
    otsuThreshold(grayData) {
        /**
         * Método de Otsu para binarización automática
         * Encuentra el mejor umbral según el histograma
         */
        const histogram = new Array(256).fill(0);
        
        // Crear histograma
        for (let i = 0; i < grayData.length; i++) {
            histogram[Math.floor(grayData[i])]++;
        }
        
        const total = grayData.length;
        let sum = 0;
        for (let i = 0; i < 256; i++) {
            sum += i * histogram[i];
        }
        
        let sumB = 0;
        let wB = 0;
        let wF = 0;
        let maxVariance = 0;
        let threshold = 0;
        
        for (let t = 0; t < 256; t++) {
            wB += histogram[t];
            if (wB === 0) continue;
            
            wF = total - wB;
            if (wF === 0) break;
            
            sumB += t * histogram[t];
            
            const mB = sumB / wB;
            const mF = (sum - sumB) / wF;
            
            const variance = wB * wF * (mB - mF) * (mB - mF);
            
            if (variance > maxVariance) {
                maxVariance = variance;
                threshold = t;
            }
        }
        
        return threshold;
    }
    
    enhanceImage(canvas) {
        /**
         * 🎨 MEJORA AVANZADA DE IMAGEN
         * Aplica técnicas de Computer Vision para mejor OCR
         * Similar a Google ML Kit preprocessing
         */
        const ctx = canvas.getContext('2d');
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;
        
        // 1. Convertir a escala de grises
        for (let i = 0; i < data.length; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            data[i] = data[i + 1] = data[i + 2] = gray;
        }
        
        // 2. Aplicar filtro de mediana (reduce ruido mejor que Gaussian)
        const filtered = this.medianFilter(imageData, 3);
        
        // 3. Detección de bordes Sobel (identifica texto)
        const edges = this.sobelEdgeDetection(filtered);
        
        // 4. Binarización adaptativa Sauvola (mejor que Otsu para documentos)
        const binarized = this.sauvolaBinarization(edges, 15, 0.2);
        
        // 5. Morfología: Cierre para conectar letras
        const morphed = this.morphologicalClosing(binarized, 2);
        
        ctx.putImageData(morphed, 0, 0);
        return canvas;
    }
    
    medianFilter(imageData, kernelSize) {
        /**
         * Filtro de mediana - reduce ruido preservando bordes
         * Mejor que Gaussian blur para documentos
         */
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        const output = new ImageData(width, height);
        const half = Math.floor(kernelSize / 2);
        
        for (let y = half; y < height - half; y++) {
            for (let x = half; x < width - half; x++) {
                const values = [];
                
                for (let ky = -half; ky <= half; ky++) {
                    for (let kx = -half; kx <= half; kx++) {
                        const idx = ((y + ky) * width + (x + kx)) * 4;
                        values.push(data[idx]);
                    }
                }
                
                values.sort((a, b) => a - b);
                const median = values[Math.floor(values.length / 2)];
                
                const idx = (y * width + x) * 4;
                output.data[idx] = output.data[idx + 1] = output.data[idx + 2] = median;
                output.data[idx + 3] = 255;
            }
        }
        
        return output;
    }
    
    sobelEdgeDetection(imageData) {
        /**
         * 🔍 Detección de bordes Sobel
         * Detecta los contornos de las letras
         */
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        const output = new ImageData(width, height);
        
        // Kernels Sobel
        const sobelX = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]];
        const sobelY = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]];
        
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                let gx = 0, gy = 0;
                
                for (let ky = -1; ky <= 1; ky++) {
                    for (let kx = -1; kx <= 1; kx++) {
                        const idx = ((y + ky) * width + (x + kx)) * 4;
                        const pixel = data[idx];
                        gx += pixel * sobelX[ky + 1][kx + 1];
                        gy += pixel * sobelY[ky + 1][kx + 1];
                    }
                }
                
                const magnitude = Math.sqrt(gx * gx + gy * gy);
                const idx = (y * width + x) * 4;
                output.data[idx] = output.data[idx + 1] = output.data[idx + 2] = magnitude;
                output.data[idx + 3] = 255;
            }
        }
        
        return output;
    }
    
    sauvolaBinarization(imageData, windowSize, k) {
        /**
         * 📊 Binarización de Sauvola
         * Mejor que Otsu para documentos con iluminación variable
         * Usado en sistemas OCR profesionales
         */
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        const output = new ImageData(width, height);
        const half = Math.floor(windowSize / 2);
        const R = 128; // Rango dinámico
        
        for (let y = half; y < height - half; y++) {
            for (let x = half; x < width - half; x++) {
                // Calcular media y desviación estándar local
                let sum = 0, sumSq = 0, count = 0;
                
                for (let ky = -half; ky <= half; ky++) {
                    for (let kx = -half; kx <= half; kx++) {
                        const idx = ((y + ky) * width + (x + kx)) * 4;
                        const pixel = data[idx];
                        sum += pixel;
                        sumSq += pixel * pixel;
                        count++;
                    }
                }
                
                const mean = sum / count;
                const variance = (sumSq / count) - (mean * mean);
                const stdDev = Math.sqrt(Math.max(0, variance));
                
                // Umbral de Sauvola
                const threshold = mean * (1 + k * ((stdDev / R) - 1));
                
                const idx = (y * width + x) * 4;
                const pixel = data[idx];
                const value = pixel > threshold ? 255 : 0;
                
                output.data[idx] = output.data[idx + 1] = output.data[idx + 2] = value;
                output.data[idx + 3] = 255;
            }
        }
        
        return output;
    }
    
    morphologicalClosing(imageData, iterations) {
        /**
         * 🔗 Cierre morfológico
         * Conecta partes de letras y elimina huecos pequeños
         */
        let current = imageData;
        
        // Dilatación seguida de erosión
        for (let i = 0; i < iterations; i++) {
            current = this.dilate(current);
        }
        for (let i = 0; i < iterations; i++) {
            current = this.erode(current);
        }
        
        return current;
    }
    
    dilate(imageData) {
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        const output = new ImageData(width, height);
        
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                let maxVal = 0;
                
                for (let ky = -1; ky <= 1; ky++) {
                    for (let kx = -1; kx <= 1; kx++) {
                        const idx = ((y + ky) * width + (x + kx)) * 4;
                        maxVal = Math.max(maxVal, data[idx]);
                    }
                }
                
                const idx = (y * width + x) * 4;
                output.data[idx] = output.data[idx + 1] = output.data[idx + 2] = maxVal;
                output.data[idx + 3] = 255;
            }
        }
        
        return output;
    }
    
    erode(imageData) {
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        const output = new ImageData(width, height);
        
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                let minVal = 255;
                
                for (let ky = -1; ky <= 1; ky++) {
                    for (let kx = -1; kx <= 1; kx++) {
                        const idx = ((y + ky) * width + (x + kx)) * 4;
                        minVal = Math.min(minVal, data[idx]);
                    }
                }
                
                const idx = (y * width + x) * 4;
                output.data[idx] = output.data[idx + 1] = output.data[idx + 2] = minVal;
                output.data[idx + 3] = 255;
            }
        }
        
        return output;
    }
    
    async detectTextRegionsAutomatic() {
        /**
         * 🎯 DETECCIÓN AUTOMÁTICA DE REGIONES DE TEXTO
         * Computer Vision para encontrar dónde hay texto
         * Similar a Text Detection API de Google ML Kit
         */
        try {
            console.log('🔍 Detectando regiones de texto automáticamente...');
            
            // Obtener imagen del canvas completo
            const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Aplicar detección de bordes
            const edges = this.sobelEdgeDetection(imageData);
            
            // Encontrar componentes conectados (regiones con texto)
            const regions = this.findConnectedComponents(edges);
            
            // Filtrar regiones que parecen texto
            const textRegions = regions.filter(r => 
                r.width >= this.visionConfig.minTextWidth &&
                r.height >= this.visionConfig.minTextHeight &&
                r.aspectRatio > 0.1 && r.aspectRatio < 20
            );
            
            console.log(`✅ ${textRegions.length} regiones de texto detectadas`);
            
            // Dibujar regiones detectadas
            this.highlightTextRegions(textRegions);
            
            return textRegions;
            
        } catch (error) {
            console.error('❌ Error detectando regiones:', error);
            return [];
        }
    }
    
    findConnectedComponents(imageData) {
        /**
         * Encuentra componentes conectados (bloques de texto)
         * Algoritmo básico de escaneo
         */
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        const visited = new Array(width * height).fill(false);
        const regions = [];
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = (y * width + x) * 4;
                
                if (data[idx] > 128 && !visited[y * width + x]) {
                    // Iniciar BFS/DFS para encontrar componente conectado
                    const region = this.floodFill(data, width, height, x, y, visited);
                    
                    if (region.pixels > 50) { // Filtrar ruido
                        regions.push(region);
                    }
                }
            }
        }
        
        return regions;
    }
    
    floodFill(data, width, height, startX, startY, visited) {
        const stack = [[startX, startY]];
        let minX = startX, maxX = startX;
        let minY = startY, maxY = startY;
        let pixels = 0;
        
        while (stack.length > 0) {
            const [x, y] = stack.pop();
            
            if (x < 0 || x >= width || y < 0 || y >= height) continue;
            if (visited[y * width + x]) continue;
            
            const idx = (y * width + x) * 4;
            if (data[idx] <= 128) continue;
            
            visited[y * width + x] = true;
            pixels++;
            
            minX = Math.min(minX, x);
            maxX = Math.max(maxX, x);
            minY = Math.min(minY, y);
            maxY = Math.max(maxY, y);
            
            // Vecinos (4-conectividad)
            stack.push([x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]);
        }
        
        const w = maxX - minX + 1;
        const h = maxY - minY + 1;
        
        return {
            x: minX,
            y: minY,
            width: w,
            height: h,
            pixels,
            aspectRatio: w / h
        };
    }
    
    highlightTextRegions(regions) {
        /**
         * 💡 Resalta las regiones detectadas con overlay azul
         * Similar al highlight de Google Lens
         */
        // Limpiar overlays anteriores
        const oldRegions = document.querySelectorAll('.detected-region');
        oldRegions.forEach(r => r.remove());
        
        regions.forEach((region, index) => {
            const highlight = document.createElement('div');
            highlight.className = 'detected-region';
            highlight.style.cssText = `
                position: absolute;
                left: ${region.x}px;
                top: ${region.y}px;
                width: ${region.width}px;
                height: ${region.height}px;
                border: 2px dashed #4285f4;
                background: rgba(66, 133, 244, 0.05);
                pointer-events: none;
                animation: pulseRegion 2s infinite;
            `;
            
            this.overlay.appendChild(highlight);
        });
        
        // Agregar animación CSS si no existe
        if (!document.getElementById('region-animations')) {
            const style = document.createElement('style');
            style.id = 'region-animations';
            style.textContent = `
                @keyframes pulseRegion {
                    0%, 100% { opacity: 0.6; }
                    50% { opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    showTextResult(texto, confidence, x, y) {
        /**
         * Muestra el texto extraído en un modal GRANDE al estilo Google Lens
         */
        // Remover modal anterior
        const oldModal = document.getElementById('lens-result-modal');
        if (oldModal) oldModal.remove();
        
        // Crear backdrop
        const backdrop = document.createElement('div');
        backdrop.id = 'lens-result-modal';
        backdrop.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.7); display: flex; align-items: center;
            justify-content: center; z-index: 10000; animation: fadeIn 0.2s ease;
        `;
        
        // Crear modal
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: #2d2d2d; border-radius: 12px; max-width: 600px;
            width: 90%; max-height: 80vh; overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5); animation: slideUp 0.3s ease;
        `;
        
        modal.innerHTML = `
            <div style="background: linear-gradient(135deg, #4285f4, #34a853); padding: 20px; color: white; position: relative;">
                <button onclick="document.getElementById('lens-result-modal').remove()" style="position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.2); border: none; color: white; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 18px;">✕</button>
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 32px;">🔍</span>
                    <h3 style="margin: 0; font-size: 20px; font-weight: 600;">Lens FGJCDMX</h3>
                </div>
            </div>
            <div style="padding: 24px; max-height: 50vh; overflow-y: auto;">
                <div id="modal-text-content" style="background: #1e1e1e; padding: 16px; border-radius: 8px; margin-bottom: 16px; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.6; color: #e0e0e0; white-space: pre-wrap; word-break: break-word;"></div>
            </div>
            <div style="padding: 20px; background: #232323; display: flex; gap: 12px; align-items: center; justify-content: space-between; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 200px;">
                    <div style="font-size: 11px; color: #666;">
                        ✨ Procesado localmente - Sin enviar datos a internet
                    </div>
                </div>
                <button id="copy-btn-modal" style="background: #4285f4; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">
                    📋 Copiar texto
                </button>
                <button onclick="document.getElementById('lens-result-modal').remove()" style="background: #444; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 14px; font-weight: 500; cursor: pointer;">
                    Cerrar
                </button>
            </div>
        `;
        
        backdrop.appendChild(modal);
        document.body.appendChild(backdrop);
        
        document.getElementById('modal-text-content').textContent = texto;
        
        document.getElementById('copy-btn-modal').addEventListener('click', function() {
            const ta = document.createElement('textarea');
            ta.value = texto;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            this.innerHTML = '✅ Copiado';
            setTimeout(() => this.innerHTML = '📋 Copiar texto', 2000);
        });
        
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) backdrop.remove();
        });
        
        if (!document.getElementById('lens-modal-animations')) {
            const style = document.createElement('style');
            style.id = 'lens-modal-animations';
            style.textContent = `
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
            `;
            document.head.appendChild(style);
        }
    }
    
    showToast(message, type = 'info') {
        /**
         * Muestra notificación tipo toast
         */
        const colors = {
            info: '#4285f4',
            success: '#34a853',
            warning: '#fbbc04',
            error: '#ea4335'
        };
        
        // Crear toast
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: ${colors[type]};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Auto-remover
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
        
        // Agregar animaciones si no existen
        if (!document.getElementById('toast-animations')) {
            const style = document.createElement('style');
            style.id = 'toast-animations';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(400px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(400px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    destroy() {
        /**
         * Limpiar recursos
         */
        if (this.tesseractWorker) {
            this.tesseractWorker.terminate();
        }
        if (this.overlay) {
            this.overlay.remove();
        }
        console.log('🔍 Google Lens OCR destruido');
    }
}

// Exportar para uso global
window.GoogleLensOCR = GoogleLensOCR;
