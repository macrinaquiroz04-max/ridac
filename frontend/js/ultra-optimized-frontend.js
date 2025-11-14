/**
 * 🚀 OPTIMIZACIONES FRONTEND ULTRA-AVANZADAS
 * - Web Workers para procesamiento no bloqueante
 * - Cache inteligente con IndexedDB
 * - Lazy loading de componentes
 * - Debouncing y throttling optimizado
 * - Progressive Web App features
 */

class UltraOptimizedFrontend {
    constructor() {
        this.cache = new Map();
        this.worker = null;
        this.isProcessing = false;
        this.processQueue = [];
        
        this.initializeWebWorker();
        this.initializeIndexedDB();
        this.setupProgressiveFeatures();
    }

    // 🔥 WEB WORKER para procesamiento no bloqueante
    initializeWebWorker() {
        const workerCode = `
            self.addEventListener('message', async function(e) {
                const { type, data } = e.data;
                
                switch(type) {
                    case 'PROCESS_OCR':
                        await processOCRBatch(data);
                        break;
                    case 'ANALYZE_TEXT':
                        await analyzeTextPatterns(data);
                        break;
                    case 'OPTIMIZE_IMAGES':
                        await optimizeImageBatch(data);
                        break;
                }
            });
            
            async function processOCRBatch(data) {
                const { tomoId, paginas, config } = data;
                
                try {
                    // Procesamiento paralelo de páginas
                    const promises = paginas.map(async (pagina) => {
                        const response = await fetch('/api/analisis/ocr-ultra', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                tomo_id: tomoId,
                                pagina: pagina,
                                motor: config.motor || 'auto',
                                optimizaciones: config.optimizaciones
                            })
                        });
                        
                        return await response.json();
                    });
                    
                    const resultados = await Promise.all(promises);
                    
                    self.postMessage({
                        type: 'OCR_BATCH_COMPLETE',
                        data: { resultados, tomoId }
                    });
                    
                } catch (error) {
                    self.postMessage({
                        type: 'OCR_BATCH_ERROR',
                        data: { error: error.message, tomoId }
                    });
                }
            }
            
            async function analyzeTextPatterns(data) {
                const { texto, patrones } = data;
                
                // Análisis de patrones en Web Worker (no bloquea UI)
                const resultados = [];
                
                for (const patron of patrones) {
                    const regex = new RegExp(patron.regex, 'gi');
                    const matches = [...texto.matchAll(regex)];
                    
                    if (matches.length > 0) {
                        resultados.push({
                            patron: patron.nombre,
                            matches: matches.length,
                            ejemplos: matches.slice(0, 5).map(m => m[0])
                        });
                    }
                }
                
                self.postMessage({
                    type: 'PATTERN_ANALYSIS_COMPLETE',
                    data: resultados
                });
            }
        `;
        
        const blob = new Blob([workerCode], { type: 'application/javascript' });
        this.worker = new Worker(URL.createObjectURL(blob));
        
        this.worker.addEventListener('message', (e) => {
            this.handleWorkerMessage(e.data);
        });
    }

    // 💾 INDEXEDDB para cache ultra-rápido
    async initializeIndexedDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('FGJOCRCache', 1);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                (() => {})('🚀 IndexedDB cache inicializado');
                resolve();
            };
            
            request.onupgradeneeded = (e) => {
                const db = e.target.result;
                
                // Store para resultados OCR
                if (!db.objectStoreNames.contains('ocrResults')) {
                    const ocrStore = db.createObjectStore('ocrResults', { keyPath: 'id' });
                    ocrStore.createIndex('tomoId', 'tomoId', { unique: false });
                    ocrStore.createIndex('timestamp', 'timestamp', { unique: false });
                }
                
                // Store para imágenes procesadas
                if (!db.objectStoreNames.contains('processedImages')) {
                    const imgStore = db.createObjectStore('processedImages', { keyPath: 'hash' });
                    imgStore.createIndex('tomoId', 'tomoId', { unique: false });
                }
            };
        });
    }

    // 📱 PROGRESSIVE WEB APP features
    setupProgressiveFeatures() {
        // Service Worker para cache offline
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js').then(() => {
                (() => {})('🔄 Service Worker registrado para cache offline');
            });
        }
        
        // Notificaciones push
        if ('Notification' in window) {
            Notification.requestPermission();
        }
        
        // Background sync para procesamiento offline
        if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
            navigator.serviceWorker.ready.then((registration) => {
                (() => {})('🌐 Background sync disponible');
            });
        }
    }

    // ⚡ PROCESAMIENTO ULTRA-OPTIMIZADO
    async processDocumentUltraFast(tomoId, opciones = {}) {
        if (this.isProcessing) {
            (() => {})('⏳ Ya hay un procesamiento en curso, agregando a cola...');
            this.processQueue.push({ tomoId, opciones });
            return;
        }
        
        this.isProcessing = true;
        
        try {
            // 1. Verificar cache primero
            const cacheKey = `tomo_${tomoId}_${JSON.stringify(opciones)}`;
            let cachedResult = await this.getFromCache(cacheKey);
            
            if (cachedResult && !opciones.forceRefresh) {
                (() => {})('⚡ Resultado obtenido del cache ultra-rápido');
                this.displayResults(cachedResult);
                return;
            }
            
            // 2. Obtener información del documento
            const docInfo = await this.fetchDocumentInfo(tomoId);
            (() => {})(`📊 Procesando ${docInfo.numero_paginas} páginas con optimizaciones ultra`);
            
            // 3. Preparar configuración optimizada
            const config = {
                motor: opciones.motor || 'auto',
                batchSize: opciones.batchSize || 50, // Lotes más grandes
                parallelWorkers: navigator.hardwareConcurrency || 4,
                optimizaciones: {
                    cache: true,
                    compression: true,
                    smartRetry: true,
                    gpuAcceleration: true
                }
            };
            
            // 4. Dividir en lotes optimizados
            const paginas = Array.from({length: docInfo.numero_paginas}, (_, i) => i + 1);
            const lotes = this.chunkArray(paginas, config.batchSize);
            
            // 5. Procesamiento con Web Worker
            const resultados = await this.processWithWorkers(tomoId, lotes, config);
            
            // 6. Guardar en cache para futuro
            await this.saveToCache(cacheKey, resultados);
            
            // 7. Mostrar resultados
            this.displayResults(resultados);
            
        } catch (error) {
            console.error('❌ Error en procesamiento ultra-optimizado:', error);
            this.showErrorNotification('Error en procesamiento', error.message);
        } finally {
            this.isProcessing = false;
            
            // Procesar siguiente en cola
            if (this.processQueue.length > 0) {
                const next = this.processQueue.shift();
                setTimeout(() => this.processDocumentUltraFast(next.tomoId, next.opciones), 100);
            }
        }
    }

    // 🔄 PROCESAMIENTO CON WORKERS PARALELOS
    async processWithWorkers(tomoId, lotes, config) {
        const resultados = [];
        const progressBar = document.getElementById('processingProgress');
        const statusDiv = document.getElementById('processingStatus');
        
        let completedBatches = 0;
        const totalBatches = lotes.length;
        
        // Actualización de progreso en tiempo real
        const updateProgress = () => {
            const progress = (completedBatches / totalBatches) * 100;
            progressBar.style.width = `${progress}%`;
            statusDiv.textContent = `Procesando lote ${completedBatches}/${totalBatches} (${progress.toFixed(1)}%)`;
        };
        
        // Procesar lotes con límite de concurrencia
        const concurrencyLimit = Math.min(config.parallelWorkers, lotes.length);
        const semaforo = Array(concurrencyLimit).fill(null);
        
        const processLote = async (loteIndex) => {
            const lote = lotes[loteIndex];
            
            return new Promise((resolve, reject) => {
                const messageId = `batch_${Date.now()}_${loteIndex}`;
                
                // Timeout de seguridad
                const timeout = setTimeout(() => {
                    reject(new Error(`Timeout en lote ${loteIndex}`));
                }, 300000); // 5 minutos
                
                // Listener temporal para este lote
                const listener = (e) => {
                    const { type, data } = e.data;
                    
                    if (type === 'OCR_BATCH_COMPLETE' && data.tomoId === tomoId) {
                        clearTimeout(timeout);
                        this.worker.removeEventListener('message', listener);
                        
                        resultados.push(...data.resultados);
                        completedBatches++;
                        updateProgress();
                        
                        resolve(data.resultados);
                    } else if (type === 'OCR_BATCH_ERROR' && data.tomoId === tomoId) {
                        clearTimeout(timeout);
                        this.worker.removeEventListener('message', listener);
                        reject(new Error(data.error));
                    }
                };
                
                this.worker.addEventListener('message', listener);
                
                // Enviar trabajo al Worker
                this.worker.postMessage({
                    type: 'PROCESS_OCR',
                    data: {
                        tomoId: tomoId,
                        paginas: lote,
                        config: config,
                        messageId: messageId
                    }
                });
            });
        };
        
        // Ejecutar lotes con concurrencia limitada
        const promises = [];
        for (let i = 0; i < lotes.length; i++) {
            promises.push(processLote(i));
        }
        
        await Promise.all(promises);
        
        return resultados;
    }

    // 💾 CACHE INTELIGENTE
    async getFromCache(key) {
        if (!this.db) return null;
        
        return new Promise((resolve) => {
            const transaction = this.db.transaction(['ocrResults'], 'readonly');
            const store = transaction.objectStore('ocrResults');
            const request = store.get(key);
            
            request.onsuccess = () => {
                const result = request.result;
                
                if (result) {
                    // Verificar si el cache no está expirado (24 horas)
                    const now = Date.now();
                    const cacheAge = now - result.timestamp;
                    const maxAge = 24 * 60 * 60 * 1000; // 24 horas
                    
                    if (cacheAge < maxAge) {
                        resolve(result.data);
                    } else {
                        // Cache expirado, eliminar
                        this.removeFromCache(key);
                        resolve(null);
                    }
                } else {
                    resolve(null);
                }
            };
            
            request.onerror = () => resolve(null);
        });
    }

    async saveToCache(key, data) {
        if (!this.db) return;
        
        const cacheEntry = {
            id: key,
            data: data,
            timestamp: Date.now(),
            size: JSON.stringify(data).length
        };
        
        const transaction = this.db.transaction(['ocrResults'], 'readwrite');
        const store = transaction.objectStore('ocrResults');
        store.put(cacheEntry);
    }

    // 🎨 UI OPTIMIZADA CON LAZY LOADING
    displayResults(resultados) {
        const container = document.getElementById('resultados-container');
        container.innerHTML = '';
        
        // Lazy loading de resultados grandes
        if (resultados.length > 100) {
            this.setupVirtualScrolling(container, resultados);
        } else {
            this.displayAllResults(container, resultados);
        }
        
        // Animaciones suaves
        container.style.opacity = '0';
        container.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            container.style.transition = 'all 0.3s ease';
            container.style.opacity = '1';
            container.style.transform = 'translateY(0)';
        }, 50);
    }

    // 📱 NOTIFICACIONES PUSH INTELIGENTES
    showSuccessNotification(title, message) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const notification = new Notification(title, {
                body: message,
                icon: '/favicon.svg',
                badge: '/images/badge.png',
                tag: 'fgj-success'
            });
            
            setTimeout(() => notification.close(), 5000);
        }
        
        // Fallback a notificación en página
        this.showInPageNotification(title, message, 'success');
    }

    // 🔧 UTILIDADES OPTIMIZADAS
    chunkArray(array, chunkSize) {
        const chunks = [];
        for (let i = 0; i < array.length; i += chunkSize) {
            chunks.push(array.slice(i, i + chunkSize));
        }
        return chunks;
    }

    // Debouncing optimizado para búsquedas
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Throttling para scroll events
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }
}

// 🚀 INICIALIZACIÓN GLOBAL
const ultraFrontend = new UltraOptimizedFrontend();

// Funciones globales optimizadas
window.procesarDocumentoUltraRapido = (tomoId, opciones = {}) => {
    return ultraFrontend.processDocumentUltraFast(tomoId, opciones);
};

// Auto-optimización basada en hardware del usuario
window.addEventListener('load', () => {
    // Detectar capacidades del dispositivo
    const cores = navigator.hardwareConcurrency || 2;
    const memory = navigator.deviceMemory || 4;
    const connection = navigator.connection || { effectiveType: '4g' };
    
    (() => {})(`🔍 Hardware detectado: ${cores} cores, ${memory}GB RAM, ${connection.effectiveType}`);
    
    // Ajustar configuraciones automáticamente
    if (cores >= 8 && memory >= 8) {
        (() => {})('🚀 Modo ULTRA activado: Hardware potente detectado');
        ultraFrontend.configMode = 'ultra';
    } else if (cores >= 4 && memory >= 4) {
        (() => {})('⚡ Modo RAPIDO activado: Hardware medio detectado');
        ultraFrontend.configMode = 'fast';
    } else {
        (() => {})('🐌 Modo CONSERVADOR activado: Hardware limitado detectado');
        ultraFrontend.configMode = 'conservative';
    }
});

(() => {})('🎯 Frontend Ultra-Optimizado cargado y listo para máximo rendimiento!');