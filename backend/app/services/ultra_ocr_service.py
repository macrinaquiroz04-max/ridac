"""
🚀 SERVICIO OCR ULTRA OPTIMIZADO V6
- Multi-motor paralelo (Tesseract + PaddleOCR + EasyOCR + IA)
- Cache inteligente con Redis
- Procesamiento por GPU
- Pool de conexiones optimizado
- Batch processing masivo
- 🧠 NLP con modelo spaCy GRANDE (es_core_news_lg)
- ⚡ Compilación acelerada con ccache
"""

import warnings
import asyncio
import aioredis
import aiofiles
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Optional
import hashlib
import json
import time
from dataclasses import dataclass
import numpy as np
import cv2
from PIL import Image
import io
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Suprimir advertencias de componentes relacionados con OCR
warnings.filterwarnings("ignore", category=FutureWarning, module="torch")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", category=FutureWarning, module="cv2")
warnings.filterwarnings("ignore", category=UserWarning, message=".*ccache.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*recompiling.*")

# 🔧 Configurar ccache para PaddleOCR si está disponible
import os
import shutil
ccache_path = shutil.which('ccache')
if not ccache_path:
    ccache_path = r"C:\tools\ccache.exe" if os.path.exists(r"C:\tools\ccache.exe") else None

if ccache_path:
    os.environ['CC'] = f'"{ccache_path}" gcc'
    os.environ['CXX'] = f'"{ccache_path}" g++'
    os.environ['CCACHE_PATH'] = ccache_path
    os.environ['CCACHE_DISABLE'] = '0'
    os.environ['CCACHE_NOHASHDIR'] = '1'

# Imports para múltiples motores OCR
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    # 🔇 PARCHE AGRESIVO PARA SUPRIMIR WARNINGS DE CCACHE
    import warnings
    import sys
    import io
    from contextlib import redirect_stderr
    
    # Suprimir todos los UserWarnings antes de importar
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", message=".*ccache.*")
    warnings.filterwarnings("ignore", message=".*No ccache found.*")
    warnings.filterwarnings("ignore", message=".*recompiling.*")
    
    # Interceptar stderr durante la importación de PaddleOCR
    stderr_buffer = io.StringIO()
    
    with redirect_stderr(stderr_buffer):
        # Configurar variables críticas antes de importar
        os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'
        import paddleocr
    
    # El warning fue capturado y suprimido en stderr_buffer
    PADDLE_AVAILABLE = True
    logger.info("⚡ PaddleOCR cargado - warnings de ccache interceptados y suprimidos")
    
except ImportError:
    PADDLE_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# 🧠 SERVICIO NLP AVANZADO
try:
    from app.services.legal_nlp_service import LegalNLPService
    NLP_SERVICE_AVAILABLE = True
except ImportError:
    NLP_SERVICE_AVAILABLE = False

logger = logging.getLogger("ridac_ocr")

@dataclass
class OCRResult:
    texto: str
    confianza: float
    motor: str
    tiempo_ms: int
    hash_imagen: str

class UltraOptimizedOCRService:
    """Servicio OCR ultra optimizado con múltiples motores y cache"""
    
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.redis_client = None
        
        # Pool de workers optimizado
        self.thread_pool = ThreadPoolExecutor(max_workers=8)
        self.process_pool = ProcessPoolExecutor(max_workers=4)
        
        # 🧠 Servicio NLP con modelo GRANDE
        self.nlp_service = None
        if NLP_SERVICE_AVAILABLE:
            try:
                self.nlp_service = LegalNLPService()
                logger.info("✅ Servicio NLP con modelo GRANDE inicializado")
            except Exception as e:
                logger.warning(f"⚠️ Error inicializando NLP: {e}")
                self.nlp_service = None
        
        # Inicializar motores OCR
        self.motores_disponibles = []
        self._init_ocr_engines()
        
        # Cache de configuraciones optimizadas
        self.tesseract_configs = {
            'fast': '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789áéíóúÁÉÍÓÚñÑüÜ.,;:()?!-" "',
            'accurate': '--oem 3 --psm 6',
            'digits': '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789'
        }
    
    async def init_cache(self):
        """Inicializar cache Redis para ultra velocidad"""
        try:
            self.redis_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)
            logger.info("🚀 Cache Redis iniciado para OCR ultra-rápido")
        except Exception as e:
            logger.warning(f"⚠️ Redis no disponible: {e}. Usando cache en memoria")
            self.redis_client = {}  # Fallback a dict en memoria
    
    def _init_ocr_engines(self):
        """Inicializar todos los motores OCR disponibles"""
        
        if TESSERACT_AVAILABLE:
            self.motores_disponibles.append('tesseract')
            logger.info("✅ Tesseract OCR disponible")
        
        if PADDLE_AVAILABLE:
            try:
                # PaddleOCR con parámetros compatibles (removidos use_gpu y show_log)
                self.paddle_ocr = paddleocr.PaddleOCR(
                    use_angle_cls=True, 
                    lang='es'
                )
                self.motores_disponibles.append('paddle')
                logger.info("✅ PaddleOCR disponible")
            except Exception as e:
                logger.warning(f"⚠️ PaddleOCR error: {e}")
        
        if EASYOCR_AVAILABLE:
            try:
                self.easy_reader = easyocr.Reader(['es', 'en'], gpu=True)
                self.motores_disponibles.append('easyocr')
                logger.info("✅ EasyOCR disponible con GPU")
            except Exception as e:
                logger.warning(f"⚠️ EasyOCR error: {e}")
        
        if OPENAI_AVAILABLE:
            self.motores_disponibles.append('openai_vision')
            logger.info("✅ OpenAI Vision API disponible")
        
        logger.info(f"🔥 Motores OCR activos: {self.motores_disponibles}")
    
    async def process_batch_ultra_fast(self, tomo_id: int, paginas: List[int], 
                                      motor_preferido: str = 'auto') -> List[OCRResult]:
        """Procesamiento ultra-rápido por lotes con múltiples motores"""
        
        start_time = time.time()
        
        # 1. Verificar cache primero
        resultados_cache = await self._check_cache_batch(tomo_id, paginas)
        paginas_pendientes = [p for p in paginas if p not in resultados_cache]
        
        logger.info(f"📊 Cache: {len(resultados_cache)} hits, {len(paginas_pendientes)} pendientes")
        
        if not paginas_pendientes:
            return list(resultados_cache.values())
        
        # 2. Preparar imágenes en paralelo
        imagenes_tasks = [self._load_and_preprocess_image(tomo_id, p) for p in paginas_pendientes]
        imagenes = await asyncio.gather(*imagenes_tasks)
        
        # 3. Procesamiento multi-motor en paralelo
        if motor_preferido == 'auto':
            # Selección inteligente de motor basada en contenido
            resultados = await self._process_multi_engine_parallel(imagenes, paginas_pendientes)
        else:
            # Motor específico
            resultados = await self._process_single_engine_batch(imagenes, paginas_pendientes, motor_preferido)
        
        # 4. Guardar en cache para futuro
        await self._save_to_cache_batch(tomo_id, resultados)
        
        # 5. Combinar resultados
        todos_resultados = list(resultados_cache.values()) + resultados
        
        elapsed_time = time.time() - start_time
        logger.info(f"⚡ Batch completado: {len(todos_resultados)} páginas en {elapsed_time:.2f}s")
        
        return todos_resultados
    
    async def _process_multi_engine_parallel(self, imagenes: List[np.ndarray], 
                                           paginas: List[int]) -> List[OCRResult]:
        """Procesamiento con múltiples motores en paralelo para máxima confianza"""
        
        tasks = []
        
        for i, (imagen, pagina) in enumerate(zip(imagenes, paginas)):
            # Crear hash de imagen para cache
            img_hash = hashlib.md5(imagen.tobytes()).hexdigest()
            
            # Procesar con todos los motores disponibles
            motor_tasks = []
            for motor in self.motores_disponibles:
                task = self._extract_text_with_motor(imagen, motor, img_hash)
                motor_tasks.append(task)
            
            # Ejecutar todos los motores y tomar el mejor resultado
            combined_task = self._select_best_result(motor_tasks, pagina)
            tasks.append(combined_task)
        
        resultados = await asyncio.gather(*tasks)
        return resultados
    
    async def _extract_text_with_motor(self, imagen: np.ndarray, motor: str, 
                                     img_hash: str) -> OCRResult:
        """Extraer texto con motor específico"""
        
        start_time = time.time()
        
        try:
            if motor == 'tesseract':
                resultado = await self._tesseract_extract(imagen)
            elif motor == 'paddle':
                resultado = await self._paddle_extract(imagen)
            elif motor == 'easyocr':
                resultado = await self._easyocr_extract(imagen)
            elif motor == 'openai_vision':
                resultado = await self._openai_vision_extract(imagen)
            else:
                raise ValueError(f"Motor desconocido: {motor}")
            
            tiempo_ms = int((time.time() - start_time) * 1000)
            
            return OCRResult(
                texto=resultado['texto'],
                confianza=resultado['confianza'],
                motor=motor,
                tiempo_ms=tiempo_ms,
                hash_imagen=img_hash
            )
            
        except Exception as e:
            logger.error(f"❌ Error en motor {motor}: {e}")
            return OCRResult(
                texto="",
                confianza=0.0,
                motor=f"{motor}_error",
                tiempo_ms=int((time.time() - start_time) * 1000),
                hash_imagen=img_hash
            )
    
    async def _tesseract_extract(self, imagen: np.ndarray) -> Dict:
        """Extracción optimizada con Tesseract"""
        
        # Preprocesamiento de imagen optimizado
        imagen_proc = self._optimize_image_for_ocr(imagen)
        
        # Configuración dinámica basada en contenido
        config = self.tesseract_configs['accurate']
        
        # Ejecutar en thread pool para no bloquear
        loop = asyncio.get_event_loop()
        texto = await loop.run_in_executor(
            self.thread_pool,
            lambda: pytesseract.image_to_string(imagen_proc, config=config, lang='spa')
        )
        
        # Obtener confianza
        data = await loop.run_in_executor(
            self.thread_pool,
            lambda: pytesseract.image_to_data(imagen_proc, config=config, lang='spa', output_type=pytesseract.Output.DICT)
        )
        
        confianzas = [int(conf) for conf in data['conf'] if int(conf) > 0]
        confianza_promedio = sum(confianzas) / len(confianzas) if confianzas else 0
        
        return {
            'texto': texto.strip(),
            'confianza': confianza_promedio
        }
    
    async def _paddle_extract(self, imagen: np.ndarray) -> Dict:
        """Extracción con PaddleOCR (muy preciso para textos complejos)"""
        
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
            self.thread_pool,
            lambda: self.paddle_ocr.ocr(imagen, cls=True)
        )
        
        texto_completo = []
        confianzas = []
        
        if resultado and resultado[0]:
            for linea in resultado[0]:
                if len(linea) >= 2:
                    texto_completo.append(linea[1][0])
                    confianzas.append(linea[1][1] * 100)  # Convertir a porcentaje
        
        confianza_promedio = sum(confianzas) / len(confianzas) if confianzas else 0
        
        return {
            'texto': '\n'.join(texto_completo),
            'confianza': confianza_promedio
        }
    
    async def _easyocr_extract(self, imagen: np.ndarray) -> Dict:
        """Extracción con EasyOCR (bueno para textos multiidioma)"""
        
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
            self.thread_pool,
            lambda: self.easy_reader.readtext(imagen)
        )
        
        texto_completo = []
        confianzas = []
        
        for detection in resultado:
            texto_completo.append(detection[1])
            confianzas.append(detection[2] * 100)  # Convertir a porcentaje
        
        confianza_promedio = sum(confianzas) / len(confianzas) if confianzas else 0
        
        return {
            'texto': '\n'.join(texto_completo),
            'confianza': confianza_promedio
        }
    
    async def _openai_vision_extract(self, imagen: np.ndarray) -> Dict:
        """Extracción con OpenAI Vision (para casos complejos y documentos legales)"""
        
        # Convertir imagen a base64
        pil_image = Image.fromarray(imagen)
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        prompt = """
        Eres un experto en OCR de documentos legales mexicanos. 
        Extrae TODO el texto de esta imagen manteniendo:
        - Estructura original
        - Nombres y apellidos exactos
        - Fechas y números
        - Formato de párrafos
        
        Si detectas nombres de menores (iniciales como B.C.A), protégelos como [MENOR PROTEGIDO].
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-vision-preview",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                    ]
                }],
                max_tokens=2000
            )
            
            texto = response.choices[0].message.content.strip()
            
            return {
                'texto': texto,
                'confianza': 85.0  # OpenAI suele ser muy confiable
            }
            
        except Exception as e:
            logger.error(f"❌ Error OpenAI Vision: {e}")
            return {'texto': '', 'confianza': 0.0}
    
    def _optimize_image_for_ocr(self, imagen: np.ndarray) -> np.ndarray:
        """
        Optimización avanzada de imagen para OCR usando Google Lens-style enhancement.
        Aplica preprocesamiento profesional para máxima calidad.
        """
        try:
            # Importar el enhancer avanzado
            from app.services.advanced_image_enhancer import create_enhancer
            
            # Crear enhancer con calidad ULTRA para documentos de fiscalía
            enhancer = create_enhancer(quality='ultra')
            
            # Aplicar pipeline completo de mejora
            enhanced = enhancer.enhance_for_ocr(imagen)
            
            logger.debug("✨ Imagen mejorada con pipeline avanzado (Google Lens-style)")
            return enhanced
            
        except Exception as e:
            logger.warning(f"⚠️ Error en enhancer avanzado, usando fallback: {e}")
            
            # FALLBACK: Método básico original
            if len(imagen.shape) == 3:
                gray = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
            else:
                gray = imagen
            
            # Mejora de contraste adaptativo
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Reducción de ruido
            denoised = cv2.medianBlur(enhanced, 3)
            
            # Binarización adaptativa
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            return binary
    
    async def _select_best_result(self, motor_tasks: List, pagina: int) -> OCRResult:
        """Seleccionar el mejor resultado entre todos los motores"""
        
        resultados = await asyncio.gather(*motor_tasks, return_exceptions=True)
        
        # Filtrar errores
        resultados_validos = [r for r in resultados if isinstance(r, OCRResult) and r.confianza > 0]
        
        if not resultados_validos:
            return OCRResult("", 0.0, "error", 0, "")
        
        # Estrategia de selección inteligente
        if len(resultados_validos) == 1:
            return resultados_validos[0]
        
        # Si hay múltiples resultados, combinar o seleccionar el mejor
        mejor_confianza = max(resultados_validos, key=lambda x: x.confianza)
        texto_mas_largo = max(resultados_validos, key=lambda x: len(x.texto))
        
        # Si la diferencia de confianza es pequeña, preferir el texto más largo
        if abs(mejor_confianza.confianza - texto_mas_largo.confianza) < 10:
            resultado_final = texto_mas_largo
            resultado_final.motor = f"hybrid_{resultado_final.motor}"
        else:
            resultado_final = mejor_confianza
        
        logger.debug(f"📄 Página {pagina}: Mejor motor = {resultado_final.motor} ({resultado_final.confianza:.1f}%)")
        return resultado_final
    
    async def _check_cache_batch(self, tomo_id: int, paginas: List[int]) -> Dict[int, OCRResult]:
        """Verificar cache para múltiples páginas"""
        
        if not self.redis_client:
            return {}
        
        resultados = {}
        
        try:
            for pagina in paginas:
                cache_key = f"ocr:{tomo_id}:{pagina}"
                cached_data = await self.redis_client.get(cache_key)
                
                if cached_data:
                    data = json.loads(cached_data)
                    resultados[pagina] = OCRResult(**data)
        except Exception as e:
            logger.warning(f"⚠️ Error leyendo cache: {e}")
        
        return resultados
    
    async def save_results_to_db_optimized(self, tomo_id: int, resultados: List[OCRResult]):
        """Guardar resultados con inserción masiva optimizada"""
        
        if not resultados:
            return
        
        # Preparar datos para inserción masiva
        datos_insercion = []
        for resultado in resultados:
            datos_insercion.append({
                'tomo_id': tomo_id,
                'numero_pagina': resultado.hash_imagen.split('_')[-1] if '_' in resultado.hash_imagen else 1,
                'texto_extraido': resultado.texto,
                'confianza': resultado.confianza,
                'datos_adicionales': {
                    'motor': resultado.motor,
                    'tiempo_ms': resultado.tiempo_ms,
                    'hash_imagen': resultado.hash_imagen
                }
            })
        
        # Inserción masiva con UPSERT
        async with self.db_session_factory() as db:
            try:
                # PostgreSQL UPSERT optimizado
                stmt = text("""
                    INSERT INTO contenido_ocr (tomo_id, numero_pagina, texto_extraido, confianza, datos_adicionales)
                    VALUES (:tomo_id, :numero_pagina, :texto_extraido, :confianza, :datos_adicionales)
                    ON CONFLICT (tomo_id, numero_pagina) 
                    DO UPDATE SET 
                        texto_extraido = EXCLUDED.texto_extraido,
                        confianza = EXCLUDED.confianza,
                        datos_adicionales = EXCLUDED.datos_adicionales,
                        updated_at = NOW()
                """)
                
                await db.execute(stmt, datos_insercion)
                await db.commit()
                
                logger.info(f"💾 Guardados {len(resultados)} resultados en DB (batch optimizado)")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"❌ Error guardando batch en DB: {e}")
                raise

# Singleton para el servicio
_ocr_service_instance = None

def get_ultra_ocr_service(db_session_factory):
    """Obtener instancia singleton del servicio OCR ultra optimizado"""
    global _ocr_service_instance
    
    if _ocr_service_instance is None:
        _ocr_service_instance = UltraOptimizedOCRService(db_session_factory)
    
    return _ocr_service_instance