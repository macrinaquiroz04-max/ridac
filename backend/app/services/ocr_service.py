# backend/app/services/ocr_service.py
# Sistema OCR con Análisis Jurídico - OPTIMIZADO CON PROCESAMIENTO PARALELO
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Año: 2025

from pathlib import Path
from typing import Optional, List, Dict, Tuple
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from app.models.tomo import Tomo, ContenidoOCR
from app.config import settings
from app.utils.logger import logger
from app.services.image_preprocessing_service import ImagePreprocessingService
from app.services.text_correction_service import TextCorrectionService
from app.services.legal_corrector_service import legal_corrector
from app.services.legal_entity_extractor import entity_extractor
from app.services.cache_service import cache_service

class OCRService:
    """Servicio de OCR multi-motor mejorado con preprocesamiento inteligente"""

    def __init__(self):
        self.tesseract_available = False
        self.easyocr_reader = None
        self.paddleocr_reader = None
        self.trocr_processor = None
        self.trocr_model = None
        
        # Configuraciones de OCR optimizadas
        self.tesseract_configs = {
            'default': '--oem 3 --psm 6',
            'single_column': '--oem 3 --psm 4',
            'single_word': '--oem 3 --psm 8',
            'sparse_text': '--oem 3 --psm 11',
            'vertical_text': '--oem 3 --psm 5'
        }
        
        self.preprocessing_service = ImagePreprocessingService()
        self.correction_service = TextCorrectionService()
        self._init_engines()

    def _init_engines(self):
        """Inicializar motores OCR disponibles con configuraciones optimizadas"""

        # Tesseract con configuraciones mejoradas
        if settings.OCR_ENABLE_TESSERACT:
            try:
                import pytesseract
                # Verificar que Tesseract esté instalado
                version = pytesseract.get_tesseract_version()
                self.tesseract_available = True
                logger.info(f"✓ Tesseract {version} inicializado")
                
                # Configurar idiomas disponibles
                self.tesseract_langs = ['spa', 'eng', 'spa+eng']
                
            except Exception as e:
                logger.warning(f"⚠ Tesseract no disponible: {e}")

        # EasyOCR con configuración mejorada
        if settings.OCR_ENABLE_EASYOCR:
            try:
                import easyocr
                # Configurar con múltiples idiomas y opciones optimizadas
                self.easyocr_reader = easyocr.Reader(
                    ['es', 'en'], 
                    gpu=False,
                    model_storage_directory='./models/easyocr',
                    download_enabled=True
                )
                logger.info("✓ EasyOCR inicializado con configuración mejorada")
            except Exception as e:
                logger.warning(f"⚠ EasyOCR no disponible: {e}")

        # PaddleOCR con configuración optimizada
        if settings.OCR_ENABLE_PADDLEOCR:
            try:
                from paddleocr import PaddleOCR
                self.paddleocr_reader = PaddleOCR(
                    lang='es', 
                    use_angle_cls=True
                )
                logger.info("✓ PaddleOCR inicializado con configuración optimizada")
            except Exception as e:
                logger.warning(f"⚠ PaddleOCR no disponible: {e}")

        # TrOCR (Transformer-based OCR) para casos complejos
        if settings.OCR_ENABLE_TROCR:
            try:
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel
                self.trocr_processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten')
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-handwritten')
                logger.info("✓ TrOCR inicializado para texto manuscrito")
            except Exception as e:
                logger.warning(f"⚠ TrOCR no disponible: {e}")

    def procesar_pdf(self, tomo: Tomo, pdf_path: Path, db: Session):
        """
        Procesar PDF completo con OCR paralelo optimizado
        
        OPTIMIZACIONES:
        - Procesamiento paralelo con ThreadPoolExecutor (4-8x más rápido)
        - Cache de resultados OCR por hash MD5 del PDF
        - Corrección ortográfica legal automática
        - Extracción de entidades jurídicas
        - Deduplicación inteligente
        """
        try:
            if not pdf_path.exists():
                raise Exception(f"Archivo no encontrado: {pdf_path}")

            logger.info(f"🚀 Procesando PDF con OCR PARALELO mejorado: {pdf_path}")

            # OPTIMIZACIÓN 1: Verificar cache de OCR por hash del archivo
            pdf_hash = self._get_file_hash(pdf_path)
            cache_key = f"ocr:pdf:{pdf_hash}"
            
            cached_result = cache_service.get(cache_key)
            if cached_result:
                logger.info(f"✓ Resultados OCR encontrados en caché para {pdf_path.name}")
                self._save_cached_results(tomo, cached_result, db)
                return

            # Abrir PDF
            doc = fitz.open(str(pdf_path))
            total_paginas = len(doc)

            logger.info(f"📄 Total de páginas: {total_paginas}")

            # Actualizar total de páginas
            tomo.total_paginas = total_paginas
            tomo.estado_ocr = 'procesando'
            db.commit()

            # Estadísticas de procesamiento
            stats = {
                'paginas_texto_directo': 0,
                'paginas_ocr': 0,
                'confianza_promedio': 0,
                'tiempo_total': 0,
                'correcciones_totales': 0,
                'entidades_extraidas': {}
            }
            
            inicio_procesamiento = time.time()

            # OPTIMIZACIÓN 2: Procesamiento PARALELO de páginas
            # Usar ThreadPoolExecutor para procesar múltiples páginas simultáneamente
            max_workers = min(8, total_paginas)  # Máximo 8 threads paralelos
            logger.info(f"🔄 Procesando {total_paginas} páginas con {max_workers} workers paralelos")
            
            resultados_paginas = []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Enviar todas las páginas a procesar en paralelo
                futures = {
                    executor.submit(
                        self._procesar_pagina_paralela, 
                        doc, 
                        pagina_num,
                        total_paginas
                    ): pagina_num 
                    for pagina_num in range(total_paginas)
                }
                
                # Recolectar resultados conforme se completan
                for future in as_completed(futures):
                    pagina_num = futures[future]
                    try:
                        resultado = future.result(timeout=90)  # máx 90s por página
                        resultados_paginas.append(resultado)
                        
                        # Actualizar progreso
                        progreso = int((len(resultados_paginas) / total_paginas) * 100)
                        tomo.progreso_ocr = progreso
                        db.commit()
                        
                        logger.info(f"  ✓ Página {pagina_num + 1}/{total_paginas} completada ({progreso}%)")
                        
                    except TimeoutError:
                        logger.warning(f"  ⏱ Página {pagina_num + 1} superó 90s — omitida")
                        resultados_paginas.append({
                            'numero_pagina': pagina_num + 1,
                            'texto_extraido': '[TIEMPO EXCEDIDO — página omitida automáticamente]',
                            'confianza': 0.0,
                            'motor_usado': 'timeout',
                            'error': 'timeout'
                        })
                    except Exception as e:
                        logger.error(f"  ✗ Error en página {pagina_num + 1}: {e}")
                        resultados_paginas.append({
                            'numero_pagina': pagina_num + 1,
                            'texto_extraido': f"[ERROR: {str(e)}]",
                            'confianza': 0.0,
                            'motor_usado': 'error',
                            'error': str(e)
                        })

            doc.close()

            # Ordenar resultados por número de página
            resultados_paginas.sort(key=lambda x: x['numero_pagina'])

            # OPTIMIZACIÓN 3: Corrección ortográfica legal en batch
            logger.info("📝 Aplicando correcciones legales...")
            texto_completo = "\n\n".join([r['texto_extraido'] for r in resultados_paginas])
            texto_corregido = legal_corrector.correct_text(texto_completo)
            
            # Dividir texto corregido de vuelta en páginas (aproximado)
            textos_corregidos = texto_corregido.split("\n\n")
            
            # OPTIMIZACIÓN 4: Extracción de entidades jurídicas
            logger.info("🔍 Extrayendo entidades jurídicas...")
            entidades = entity_extractor.extract_all(texto_corregido)
            entidades = entity_extractor.deduplicate_entities(entidades)
            entidades_summary = entity_extractor.get_summary(entidades)
            
            stats['entidades_extraidas'] = entidades
            logger.info(f"  ✓ Entidades: {entidades_summary}")

            # Guardar resultados en BD
            for i, resultado in enumerate(resultados_paginas):
                # Usar texto corregido si está disponible
                texto_final = textos_corregidos[i] if i < len(textos_corregidos) else resultado['texto_extraido']
                
                # Aplicar corrección adicional de entidades si es necesario
                if entidades:
                    entidades_corregidas = legal_corrector.correct_entities(entidades)
                else:
                    entidades_corregidas = {}
                
                # Guardar contenido OCR
                contenido = ContenidoOCR(
                    tomo_id=tomo.id,
                    numero_pagina=resultado['numero_pagina'],
                    texto_extraido=texto_final,
                    confianza=resultado['confianza'],
                    embeddings=None,  # Se generan después en batch
                    datos_adicionales={
                        "motor_usado": resultado.get('motor_usado'),
                        "correcciones_aplicadas": True,
                        "entidades": entidades_corregidas if resultado['numero_pagina'] == 1 else {}
                    }
                )
                db.add(contenido)
                
                # Actualizar estadísticas
                if resultado.get('es_texto_directo'):
                    stats['paginas_texto_directo'] += 1
                else:
                    stats['paginas_ocr'] += 1
                
                stats['confianza_promedio'] += resultado['confianza']
            
            db.commit()

            # NUEVA OPTIMIZACIÓN: Extraer y guardar diligencias automáticamente
            logger.info("📋 Extrayendo y guardando diligencias automáticamente...")
            self._extraer_y_guardar_diligencias(tomo, texto_corregido, entidades, db)

            # Calcular estadísticas finales
            stats['tiempo_total'] = time.time() - inicio_procesamiento
            stats['confianza_promedio'] = stats['confianza_promedio'] / total_paginas if total_paginas > 0 else 0
            stats['velocidad'] = total_paginas / stats['tiempo_total'] if stats['tiempo_total'] > 0 else 0

            # OPTIMIZACIÓN 5: Guardar en cache para futuras consultas (TTL 7 días)
            cache_data = {
                'resultados': resultados_paginas,
                'entidades': entidades,
                'stats': stats
            }
            cache_service.set(cache_key, cache_data, ttl=604800)  # 7 días

            # Actualizar estado final del tomo
            tomo.progreso_ocr = 100
            tomo.estado_ocr = 'completado'
            tomo.datos_adicionales = {
                'stats_ocr': stats,
                'entidades': entidades
            }
            db.commit()

            logger.info(f"✅ Procesamiento completado en {stats['tiempo_total']:.2f}s")
            logger.info(f"  📄 Páginas con texto directo: {stats['paginas_texto_directo']}")
            logger.info(f"  🔍 Páginas con OCR: {stats['paginas_ocr']}")
            logger.info(f"  📊 Confianza promedio: {stats['confianza_promedio']:.1f}%")
            logger.info(f"  ⚡ Velocidad: {stats['velocidad']:.2f} páginas/segundo")
            logger.info(f"  📑 Entidades: {entidades_summary}")

        except Exception as e:
            logger.error(f"Error procesando PDF: {e}", exc_info=True)
            tomo.estado_ocr = 'error'
            tomo.error_ocr = str(e)
            db.commit()
            raise

    def _get_file_hash(self, file_path: Path) -> str:
        """Calcular hash MD5 del archivo para cache"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _save_cached_results(self, tomo: Tomo, cached_data: Dict, db: Session):
        """Guardar resultados desde cache"""
        resultados = cached_data.get('resultados', [])
        entidades = cached_data.get('entidades', {})
        stats = cached_data.get('stats', {})
        
        for resultado in resultados:
            contenido = ContenidoOCR(
                tomo_id=tomo.id,
                numero_pagina=resultado['numero_pagina'],
                texto_extraido=resultado['texto_extraido'],
                confianza=resultado['confianza'],
                datos_adicionales=resultado.get('datos_adicionales', {})
            )
            db.add(contenido)
        
        tomo.progreso_ocr = 100
        tomo.estado_ocr = 'completado'
        tomo.total_paginas = len(resultados)
        tomo.datos_adicionales = {
            'stats_ocr': stats,
            'entidades': entidades,
            'from_cache': True
        }
        db.commit()

    def _es_pagina_en_blanco(self, page) -> bool:
        """Detección rápida de páginas en blanco a baja resolución (72 DPI)."""
        try:
            import numpy as np
            import cv2
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))  # 72 DPI – rápido
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            arr = np.array(img.convert('L'))
            media = float(arr.mean())
            desv = float(arr.std())
            return media > 245 and desv < 8
        except Exception:
            return False

    def _procesar_pagina_paralela(self, doc, pagina_num: int, total_paginas: int) -> Dict:
        """
        Procesar una página individual (ejecutado en thread paralelo)
        
        Returns:
            Diccionario con resultado del procesamiento
        """
        try:
            # Extraer página
            page = doc[pagina_num]

            # ── Detección rápida de página en blanco ──────────────────────────
            if self._es_pagina_en_blanco(page):
                return {
                    'numero_pagina': pagina_num + 1,
                    'texto_extraido': '[PÁGINA EN BLANCO]',
                    'confianza': 100.0,
                    'motor_usado': 'blank_detection',
                    'es_texto_directo': True,
                    'es_pagina_en_blanco': True,
                    'datos_adicionales': {'motor_usado': 'blank_detection', 'correcciones_aplicadas': False}
                }

            # Intentar extraer texto directamente (si es PDF con texto)
            texto_directo = page.get_text()

            if self._is_text_extractable(texto_directo):
                # PDF con texto extraíble
                texto_final = self._clean_extracted_text(texto_directo)
                motor_usado = 'pdf_text'
                confianza = 99.0
                es_texto_directo = True
                
            else:
                # PDF escaneado, usar OCR
                resultado_ocr = self._extraer_con_multiple_ocr(page)
                texto_final = resultado_ocr['texto']
                motor_usado = resultado_ocr['motor']
                confianza = resultado_ocr['confianza']
                es_texto_directo = False

            return {
                'numero_pagina': pagina_num + 1,
                'texto_extraido': texto_final,
                'confianza': confianza,
                'motor_usado': motor_usado,
                'es_texto_directo': es_texto_directo,
                'datos_adicionales': {
                    'motor_usado': motor_usado,
                    'correcciones_aplicadas': True
                }
            }

        except Exception as e:
            logger.error(f"Error procesando página {pagina_num + 1}: {e}")
            return {
                'numero_pagina': pagina_num + 1,
                'texto_extraido': f"[ERROR: {str(e)}]",
                'confianza': 0.0,
                'motor_usado': 'error',
                'es_texto_directo': False,
                'error': str(e)
            }

    def _is_text_extractable(self, texto: str) -> bool:
        """Determina si el texto extraído directamente es suficientemente bueno"""
        if not texto or len(texto.strip()) < 50:
            return False
        
        # Verificar que no sea solo espacios, saltos de línea o caracteres especiales
        palabras = texto.strip().split()
        if len(palabras) < 10:
            return False
        
        # Verificar que contenga caracteres alfabéticos
        texto_limpio = ''.join(c for c in texto if c.isalpha())
        if len(texto_limpio) < len(texto) * 0.3:  # Al menos 30% debe ser texto
            return False
        
        return True

    def _clean_extracted_text(self, texto: str) -> str:
        """Limpia y mejora el texto extraído directamente"""
        import re
        
        # Eliminar múltiples espacios
        texto = re.sub(r'\s+', ' ', texto)
        
        # Eliminar múltiples saltos de línea
        texto = re.sub(r'\n\s*\n', '\n\n', texto)
        
        # Limpiar caracteres extraños comunes en PDFs
        texto = texto.replace('\x0c', '\n')  # Form feed
        texto = texto.replace('\xa0', ' ')   # Non-breaking space
        
        return texto.strip()

    def _extraer_con_multiple_ocr(self, page) -> Dict[str, any]:
        """
        Extrae texto usando Tesseract con preprocesamiento optimizado para documentos escaneados.
        300 DPI + deskew + CLAHE + Otsu + múltiples PSM = máxima precisión en nombres/fechas/lugares.
        """
        import numpy as np
        import cv2

        # ── 1. Renderizar a ~300 DPI (72 * 4.17 ≈ 300) ───────────────────────
        matrix = fitz.Matrix(4.17, 4.17)
        pix = page.get_pixmap(matrix=matrix)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # ── 2. Deskew — corregir inclinación del escáner ──────────────────────
        try:
            img = self.preprocessing_service.correct_skew(img)
        except Exception:
            pass

        # ── 3. Preprocesamiento adaptado a escaneos ───────────────────────────
        arr = np.array(img.convert('RGB'))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # CLAHE: mejora contraste local (no destruye zonas claras ni oscuras)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Reducción de ruido rápida — medianBlur es ~100x más rápido que
        # fastNlMeansDenoising y suficientemente buena para documentos escaneados
        gray = cv2.medianBlur(gray, 3)

        # Umbral Otsu — se adapta al nivel del papel
        _, binarized = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Invertir si el fondo salió negro
        if np.mean(binarized) < 127:
            binarized = cv2.bitwise_not(binarized)

        # Cierre morfológico mínimo para letras rotas por el escáner
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        binarized = cv2.morphologyEx(binarized, cv2.MORPH_CLOSE, kernel)

        img_processed = Image.fromarray(binarized)

        # ── 4. Tesseract con múltiples PSM (elige el de mayor confianza) ──────
        if self.tesseract_available:
            import pytesseract, statistics as _stats

            mejor = {'texto': '', 'confianza': 0, 'motor': 'tesseract_scan'}
            # Solo PSM 6 (bloque uniforme) y PSM 3 (auto) — suficiente para la
            # mayoría de documentos y 2x más rápido que probar 4 modos.
            for psm in (6, 3):
                try:
                    cfg = f'--psm {psm} --oem 3'
                    data = pytesseract.image_to_data(
                        img_processed, lang='spa', config=cfg,
                        output_type=pytesseract.Output.DICT
                    )
                    confs = [int(c) for c in data['conf']
                             if str(c).lstrip('-').isdigit() and int(c) >= 0]
                    texto = pytesseract.image_to_string(img_processed, lang='spa', config=cfg)
                    conf = int(_stats.mean(confs)) if confs else 0
                    if conf > mejor['confianza'] or (not mejor['texto'] and texto.strip()):
                        mejor = {
                            'texto': self._post_process_text(texto),
                            'confianza': min(99.0, conf * 1.1),
                            'motor': f'tesseract_scan_psm{psm}'
                        }
                    if conf >= 65:  # umbral bajado: 1 intento suele ser suficiente
                        break
                except Exception:
                    continue

            if mejor['texto']:
                return mejor

        # Fallback
        return self._fallback_ocr(img)

    def _tesseract_ocr(self, img: Image.Image, config: str, motor_name: str) -> Dict[str, any]:
        """Ejecuta OCR con Tesseract usando configuración específica"""
        try:
            import pytesseract
            
            # Probar con diferentes idiomas
            for lang in ['spa', 'eng', 'spa+eng']:
                try:
                    # Obtener texto y datos de confianza
                    data = pytesseract.image_to_data(img, lang=lang, config=config, output_type=pytesseract.Output.DICT)
                    texto = pytesseract.image_to_string(img, lang=lang, config=config)
                    
                    # Calcular confianza promedio ponderada
                    confidencias = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    confianza = sum(confidencias) / len(confidencias) if confidencias else 0
                    
                    # Aplicar bonificación por idioma español
                    if 'spa' in lang:
                        confianza *= 1.1
                    
                    return {
                        'texto': self._post_process_text(texto),
                        'confianza': min(99.0, confianza),
                        'motor': f"{motor_name}_{lang}",
                        'raw_data': data
                    }
                    
                except Exception as e:
                    logger.warning(f"Error Tesseract {lang}: {e}")
                    continue
            
            # Si fallan todos los idiomas
            return {'texto': '', 'confianza': 0, 'motor': motor_name}
            
        except Exception as e:
            logger.warning(f"Error en Tesseract: {e}")
            return {'texto': '', 'confianza': 0, 'motor': motor_name}

    def _easyocr_ocr(self, img: Image.Image, motor_name: str) -> Dict[str, any]:
        """Ejecuta OCR con EasyOCR"""
        try:
            import numpy as np
            img_array = np.array(img)
            
            # Configurar parámetros para mejor precisión
            result = self.easyocr_reader.readtext(
                img_array, 
                detail=1,
                paragraph=True,
                width_ths=0.7,
                height_ths=0.7,
                decoder='beamsearch'
            )
            
            if not result:
                return {'texto': '', 'confianza': 0, 'motor': motor_name}
            
            # Extraer texto y calcular confianza
            textos = []
            confidencias = []
            
            for detection in result:
                bbox, texto, conf = detection
                if conf > 0.3:  # Filtrar detecciones de baja confianza
                    textos.append(texto)
                    confidencias.append(conf)
            
            texto_final = ' '.join(textos)
            confianza_promedio = sum(confidencias) / len(confidencias) * 100 if confidencias else 0
            
            return {
                'texto': self._post_process_text(texto_final),
                'confianza': confianza_promedio,
                'motor': motor_name
            }
            
        except Exception as e:
            logger.warning(f"Error en EasyOCR: {e}")
            return {'texto': '', 'confianza': 0, 'motor': motor_name}

    def _paddleocr_ocr(self, img: Image.Image, motor_name: str) -> Dict[str, any]:
        """Ejecuta OCR con PaddleOCR"""
        try:
            import numpy as np
            img_array = np.array(img)
            
            result = self.paddleocr_reader.ocr(img_array, cls=True)
            
            if not result or not result[0]:
                return {'texto': '', 'confianza': 0, 'motor': motor_name}
            
            # Extraer texto y confianzas
            textos = []
            confidencias = []
            
            for line in result[0]:
                if len(line) >= 2:
                    bbox, (texto, conf) = line[0], line[1]
                    if conf > 0.3:  # Filtrar detecciones de baja confianza
                        textos.append(texto)
                        confidencias.append(conf)
            
            texto_final = ' '.join(textos)
            confianza_promedio = sum(confidencias) / len(confidencias) * 100 if confidencias else 0
            
            return {
                'texto': self._post_process_text(texto_final),
                'confianza': confianza_promedio,
                'motor': motor_name
            }
            
        except Exception as e:
            logger.warning(f"Error en PaddleOCR: {e}")
            return {'texto': '', 'confianza': 0, 'motor': motor_name}

    def _trocr_ocr(self, img: Image.Image) -> Dict[str, any]:
        """Ejecuta OCR con TrOCR (para texto manuscrito)"""
        try:
            # Preprocesar para TrOCR
            img_rgb = img.convert('RGB')
            
            # Generar texto
            pixel_values = self.trocr_processor(img_rgb, return_tensors="pt").pixel_values
            generated_ids = self.trocr_model.generate(pixel_values)
            texto = self.trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # TrOCR no proporciona confianza directa, estimarla
            confianza = 70.0 if len(texto.strip()) > 10 else 30.0
            
            return {
                'texto': self._post_process_text(texto),
                'confianza': confianza,
                'motor': 'trocr'
            }
            
        except Exception as e:
            logger.warning(f"Error en TrOCR: {e}")
            return {'texto': '', 'confianza': 0, 'motor': 'trocr'}

    def _fallback_ocr(self, img: Image.Image) -> Dict[str, any]:
        """Método de respaldo cuando todos los motores fallan"""
        if self.tesseract_available:
            try:
                import pytesseract
                texto = pytesseract.image_to_string(img, lang='spa', config='--oem 3 --psm 6')
                return {
                    'texto': self._post_process_text(texto),
                    'confianza': 20.0,  # Baja confianza por ser fallback
                    'motor': 'tesseract_fallback'
                }
            except:
                pass
        
        return {'texto': '', 'confianza': 0, 'motor': 'none'}

    def _post_process_text(self, texto: str) -> str:
        """Postprocesa el texto extraído para mejorar calidad y maximizar extracción de
        fechas, nombres y lugares."""
        import re

        if not texto:
            return ""

        # ── 1. Normalizar espacios y saltos de línea ──────────────────────────
        texto = re.sub(r'\r\n|\r', '\n', texto)
        texto = re.sub(r'[ \t]+', ' ', texto)         # espacios múltiples → uno
        texto = re.sub(r'\n{3,}', '\n\n', texto)       # más de 2 saltos → 2

        # ── 2. Correcciones comunes de OCR en documentos escaneados ──────────
        # l/1/I confundidos en contexto de dígitos
        texto = re.sub(r'(?<=\d)l(?=\d)', '1', texto)    # 3l5 → 315
        texto = re.sub(r'(?<=\d)I(?=\d)', '1', texto)    # 3I5 → 315
        texto = re.sub(r'(?<=\d)O(?=\d)', '0', texto)    # 3O5 → 305
        texto = re.sub(r'(?<=\d)o(?=\d)', '0', texto)    # 3o5 → 305
        # Letras partidas con espacio (error típico de escaneos inclinados)
        # P.E.P → PEP   M. A. → MA — conservador: solo elimina punto+espacio entre mayúsculas
        texto = re.sub(r'\b([A-ZÁÉÍÓÚÑ])\.\s+(?=[A-ZÁÉÍÓÚÑ])', r'\1', texto)

        # ── 3. Reconstruir palabras rotas por guion al final de línea ─────────
        texto = re.sub(r'(\w)-\n(\w)', r'\1\2', texto)

        # ── 4. Limpiar caracteres extraños pero conservar los legales ─────────
        # Conserva: alfanuméricos, tildes, ñ, signos de puntuación, /, \, °, @, #, $, %
        texto = re.sub(r'[^\w\s\.,;:!?\-\(\)\"\'\/\\°ª²³ñÑáéíóúÁÉÍÓÚü@#$%&\n]', '', texto)

        return texto.strip()

    def _calculate_result_score(self, resultado: Dict[str, any]) -> float:
        """Calcula un score para comparar resultados"""
        confianza = resultado['confianza']
        texto = resultado['texto']
        
        # Score base por confianza
        score = confianza
        
        # Bonificaciones
        if len(texto.strip()) > 100:  # Texto sustancial
            score += 10
        
        if 'spa' in resultado['motor']:  # Preferir español
            score += 5
        
        # Detectar si contiene palabras españolas comunes
        palabras_esp = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las']
        texto_lower = texto.lower()
        palabras_encontradas = sum(1 for p in palabras_esp if f' {p} ' in texto_lower)
        score += palabras_encontradas * 2
        
        return score

    def _ensemble_results(self, resultados: List[Dict[str, any]]) -> Dict[str, any]:
        """Combina múltiples resultados buenos para obtener el mejor"""
        # Filtrar solo resultados de alta confianza
        buenos_resultados = [r for r in resultados if r['confianza'] > 80]
        
        if not buenos_resultados:
            return max(resultados, key=lambda x: x['confianza'])
        
        # Si solo hay uno bueno, usarlo
        if len(buenos_resultados) == 1:
            return buenos_resultados[0]
        
        # Para múltiples buenos resultados, usar el de mayor score
        mejor = max(buenos_resultados, key=lambda x: self._calculate_result_score(x))
        
        # Marcar como ensemble
        mejor['motor'] = f"ensemble_{mejor['motor']}"
        
        return mejor
    
    def _extraer_y_guardar_diligencias(self, tomo, texto_completo: str, entidades: dict, db: Session):
        """
        Extrae diligencias del texto OCR y las guarda automáticamente en la BD
        Usa patrones para identificar: Tipo, Responsable, Fecha, Oficio, Página
        """
        from app.models.analisis_juridico import Diligencia
        import re
        from datetime import datetime
        
        try:
            # Buscar todas las diligencias en el texto
            # Patrón para capturar bloques de diligencias
            # Formato típico:
            # TIPO DE DILIGENCIA
            # Responsable: NOMBRE
            # Fecha: DD/MM/YYYY
            # Oficio: XXX-XXX
            # Página: N
            
            diligencias_encontradas = []
            
            # Dividir texto en párrafos
            paragrafos = texto_completo.split('\n\n')
            
            for i, parrafo in enumerate(paragrafos):
                if len(parrafo.strip()) < 20:  # Muy corto, skip
                    continue
                
                # Buscar indicadores de diligencias
                lineas = parrafo.split('\n')
                
                # Intentar extraer información estructurada
                diligencia_info = {
                    'tipo_diligencia': None,
                    'responsable': None,
                    'fecha_diligencia_texto': None,
                    'numero_oficio': None,
                    'numero_pagina': None,
                    'texto_contexto': parrafo[:500]  # Primeros 500 caracteres
                }
                
                for linea in lineas:
                    linea_limpia = linea.strip()
                    
                    # Detectar tipo de diligencia (primera línea con palabras clave)
                    if not diligencia_info['tipo_diligencia']:
                        if any(palabra in linea_limpia.lower() for palabra in 
                               ['actuación', 'diligencia', 'acta', 'oficio', 'comunicado', 'solicitud']):
                            # Aplicar corrección agresiva al tipo
                            tipo_corregido = legal_corrector.correct_field_aggressive(linea_limpia, 'tipo')
                            diligencia_info['tipo_diligencia'] = tipo_corregido[:200]
                    
                    # Detectar responsable
                    # Buscar patrones como: "Responsable:", "Por:", nombres propios
                    if re.search(r'(responsable|por|elaboró|realizó|firmó)[:.]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)', linea_limpia, re.IGNORECASE):
                        match = re.search(r'(responsable|por|elaboró|realizó|firmó)[:.]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)', linea_limpia, re.IGNORECASE)
                        if match:
                            responsable = match.group(2).strip()
                            # Aplicar corrección agresiva
                            responsable_corregido = legal_corrector.correct_field_aggressive(responsable, 'persona')
                            diligencia_info['responsable'] = responsable_corregido[:300]
                    
                    # Detectar fecha
                    if re.search(r'\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?(\d{4})\b', linea_limpia, re.IGNORECASE):
                        match = re.search(r'\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?(\d{4})\b', linea_limpia, re.IGNORECASE)
                        if match:
                            diligencia_info['fecha_diligencia_texto'] = match.group(0)
                    
                    # Detectar número de oficio
                    if re.search(r'(oficio|circular|memorándum)\s*(?:núm\.?|número|no\.?|N°)?\s*:?\s*([A-Z0-9/-]+)', linea_limpia, re.IGNORECASE):
                        match = re.search(r'(oficio|circular|memorándum)\s*(?:núm\.?|número|no\.?|N°)?\s*:?\s*([A-Z0-9/-]+)', linea_limpia, re.IGNORECASE)
                        if match:
                            diligencia_info['numero_oficio'] = match.group(2).strip()[:100]
                    
                    # Detectar número de página
                    if re.search(r'página\s*:?\s*(\d+)', linea_limpia, re.IGNORECASE):
                        match = re.search(r'página\s*:?\s*(\d+)', linea_limpia, re.IGNORECASE)
                        if match:
                            diligencia_info['numero_pagina'] = int(match.group(1))
                
                # Si encontramos al menos tipo de diligencia, guardar
                if diligencia_info['tipo_diligencia']:
                    diligencias_encontradas.append(diligencia_info)
            
            # Guardar diligencias en BD
            contador = 0
            for idx, dil_info in enumerate(diligencias_encontradas):
                try:
                    diligencia = Diligencia(
                        tomo_id=tomo.id,
                        carpeta_id=tomo.carpeta_id,
                        tipo_diligencia=dil_info['tipo_diligencia'],
                        fecha_diligencia_texto=dil_info['fecha_diligencia_texto'],
                        responsable=dil_info['responsable'],
                        numero_oficio=dil_info['numero_oficio'],
                        descripcion=f"Extraída automáticamente del OCR",
                        texto_contexto=dil_info['texto_contexto'],
                        numero_pagina=dil_info['numero_pagina'],
                        confianza=0.75,  # Confianza media para extracción automática
                        verificado=False,
                        orden_cronologico=idx + 1
                    )
                    db.add(diligencia)
                    contador += 1
                except Exception as e:
                    logger.warning(f"Error guardando diligencia {idx}: {e}")
                    continue
            
            if contador > 0:
                db.commit()
                logger.info(f"  ✓ {contador} diligencias extraídas y guardadas automáticamente")
            else:
                logger.info("  ℹ️  No se encontraron diligencias con el patrón estándar")
                
        except Exception as e:
            logger.error(f"Error en extracción automática de diligencias: {e}")
            db.rollback()

    def get_status(self) -> dict:
        """Obtener estado de los motores OCR"""
        return {
            "tesseract": self.tesseract_available,
            "easyocr": self.easyocr_reader is not None,
            "paddleocr": self.paddleocr_reader is not None
        }
