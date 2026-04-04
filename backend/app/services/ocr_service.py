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
from app.services.entity_correction_service import entity_correction

# IDs de tomos cuyo OCR ha sido cancelado por el usuario.
# El set se vive en memoria del proceso; el hilo de OCR lo chequea en cada página.
_ocr_cancelados: set[int] = set()

def cancelar_ocr(tomo_id: int) -> None:
    """Marca un tomo para que su OCR se detenga lo antes posible."""
    _ocr_cancelados.add(tomo_id)

def limpiar_cancelacion(tomo_id: int) -> None:
    """Quita la marca de cancelación (se llama al iniciar o al terminar)."""
    _ocr_cancelados.discard(tomo_id)

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

            # Limpiar cancelación previa al iniciar
            limpiar_cancelacion(tomo.id)
            
            cached_result = cache_service.get(cache_key)
            if cached_result:
                logger.info(f"✓ Resultados OCR encontrados en caché para {pdf_path.name}")
                self._save_cached_results(tomo, cached_result, db)
                return

            # Abrir PDF sólo para contar páginas; cada worker abrirá su propia
            # instancia para evitar problemas de thread-safety de PyMuPDF.
            with fitz.open(str(pdf_path)) as _tmp:
                total_paginas = len(_tmp)

            logger.info(f"📄 Total de páginas: {total_paginas}")

            # Actualizar total de páginas
            tomo.total_paginas = total_paginas
            tomo.estado_ocr = 'procesando'
            db.commit()

            pdf_path_str = str(pdf_path)  # se pasa a los workers

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
                # Enviar todas las páginas a procesar en paralelo.
                # IMPORTANTE: se pasa pdf_path_str (string), NO el objeto fitz.Document,
                # porque PyMuPDF no es thread-safe con un documento compartido entre hilos.
                futures = {
                    executor.submit(
                        self._procesar_pagina_paralela, 
                        pdf_path_str, 
                        pagina_num,
                        total_paginas
                    ): pagina_num 
                    for pagina_num in range(total_paginas)
                }
                
                # Recolectar resultados conforme se completan
                for future in as_completed(futures):
                    # —— Cheque de cancelación ——
                    if tomo.id in _ocr_cancelados:
                        logger.info(f"⏹️ OCR cancelado por usuario: tomo {tomo.id}")
                        executor.shutdown(wait=False, cancel_futures=True)
                        tomo.estado_ocr = 'cancelado'
                        tomo.estado = 'pendiente'
                        tomo.progreso_ocr = 0
                        db.commit()
                        limpiar_cancelacion(tomo.id)
                        return

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

    def _es_pagina_mayormente_fotografia(self, page) -> bool:
        """
        Detecta si la página es principalmente una fotografía o imagen oscura
        (documentos forenses, fotos sin texto relevante).
        
        Criterio: si más del 60% de los píxeles son muy oscuros (< 50 de brillo)
        Y el texto extraíble es prácticamente nulo, la página es foto.
        """
        try:
            import numpy as np
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # ~108 DPI — balance calidad/velocidad
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            arr = np.array(img.convert('L'))
            total_pixels = arr.size
            pixeles_muy_oscuros = int(np.sum(arr < 50))
            porcentaje_oscuro = pixeles_muy_oscuros / total_pixels
            # También verificar que no haya texto nativo en el PDF
            texto_nativo = page.get_text().strip()
            return porcentaje_oscuro > 0.60 and len(texto_nativo) < 30
        except Exception:
            return False

    def _enmascarar_bloques_foto(self, gray_arr) -> "np.ndarray":
        """
        Detecta grandes bloques rectangulares muy oscuros dentro de la imagen
        (fotografías incrustadas en documentos legales) y los rellena con blanco
        para que Tesseract no intente leerlos y genere basura.
        
        Un bloque se considera fotografía si:
        - Su área supera el 2% del total de la imagen
        - Su brillo promedio interno es < 80 (zona muy oscura)
        """
        import numpy as np
        import cv2

        result = gray_arr.copy()
        h, w = gray_arr.shape[:2]
        area_total = h * w

        # Umbralizar: píxeles muy oscuros → negro, resto → blanco
        _, dark_mask = cv2.threshold(gray_arr, 80, 255, cv2.THRESH_BINARY_INV)

        # Dilatar para unir píxeles oscuros próximos (fotos tienen bordes difusos)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 40))
        dark_dilated = cv2.dilate(dark_mask, kernel, iterations=2)

        # Encontrar contornos de regiones oscuras continuas
        contours, _ = cv2.findContours(dark_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            area_bloque = bw * bh
            if area_bloque < area_total * 0.02:
                # Demasiado pequeño para ser foto — podría ser letra gruesa o sello
                continue
            # Verificar que la región sea genuinamente oscura en la imagen original
            region = gray_arr[y:y + bh, x:x + bw]
            if region.size == 0:
                continue
            brillo_medio = float(region.mean())
            if brillo_medio < 100:
                # Rellenar con blanco para "eliminar" la foto del OCR
                result[y:y + bh, x:x + bw] = 255
                logger.debug(f"  📷 Bloque foto enmascarado: ({x},{y}) {bw}x{bh}px brillo={brillo_medio:.0f}")

        return result

    def _eliminar_firmas_ruido(self, binarized: "np.ndarray") -> "np.ndarray":
        """
        Elimina firmas y ruido visual sobre la imagen binarizada (texto negro/fondo blanco).

        Lógica:
        - Firma: componente conectado cuyo bounding box es grande PERO su densidad
          de píxeles es baja (trazo fino que recorre mucho espacio = rúbrica).
        - Ruido: componentes de 1-5 píxeles aislados que no pueden ser letras.
        - Los sellos con TEXTO (LFTAIPG, escudo, etc.) se conservan porque sus
          letras individuales son componentes pequeños normales.
        """
        import numpy as np
        import cv2

        result = binarized.copy()
        h, w = binarized.shape[:2]

        # connectedComponents espera texto BLANCO sobre fondo NEGRO
        if np.mean(binarized) > 127:
            working = cv2.bitwise_not(binarized)
        else:
            working = binarized.copy()

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            working, connectivity=8
        )

        # A 400 DPI una letra minúscula mide ≈ 20-60 px de alto.
        # Umbral mínimo de área para considerar "posible letra".
        min_px = max(15, (h // 300) ** 2)

        # Umbral de ancho y alto para considerar "demasiado grande para ser letra"
        max_char_h = h // 10       # más alto que el 10% de la página = no es una letra
        max_char_w = w // 4        # más ancho que el 25% de la página = probable firma

        for i in range(1, num_labels):
            area  = int(stats[i, cv2.CC_STAT_AREA])
            c_w   = int(stats[i, cv2.CC_STAT_WIDTH])
            c_h   = int(stats[i, cv2.CC_STAT_HEIGHT])

            # ── Ruido aislado ────────────────────────────────────────────────
            if area < min_px:
                result[labels == i] = 255
                continue

            bbox_area = c_w * c_h
            fill_ratio = area / bbox_area if bbox_area > 0 else 1.0

            # ── Firma: componente grande + densidad baja ─────────────────────
            # Una rúbrica tiene trazos finos que cubren mucho espacio → fill < 0.18
            # Una letra normal llena ≥ 25-30% de su bounding box.
            es_grande = (c_w > max_char_w) or (c_h > max_char_h)
            es_esparso = fill_ratio < 0.18

            if es_grande and es_esparso:
                result[labels == i] = 255
                logger.debug(
                    f"  ✏️ Firma/garabato eliminado: {c_w}x{c_h}px fill={fill_ratio:.2f}"
                )

        return result

    def _recuperar_palabras_clave(self, texto: str) -> str:
        """
        Corrección fuzzy de palabras críticas que Tesseract deforma en copias
        de baja calidad. Opera a nivel de token individual comparando contra
        vocabularios cerrados (meses, días ordinales, términos legales frecuentes).

        Solo corrige tokens donde Levenshtein-ratio >= 0.80 para evitar
        sustituir palabras válidas pero poco comunes.
        """
        import re
        from difflib import SequenceMatcher

        # ── Vocabularios cerrados de alta prioridad ────────────────────────────
        MESES = [
            'enero','febrero','marzo','abril','mayo','junio',
            'julio','agosto','septiembre','octubre','noviembre','diciembre'
        ]
        ORDINALES = [
            'primero','segundo','tercero','cuarto','quinto',
            'sexto','séptimo','octavo','noveno','décimo',
            'undécimo','duodécimo','decimotercero','decimocuarto',
            'decimoquinto','decimosexto','decimoséptimo','decimoctavo',
            'decimonoveno','vigésimo','trigésimo'
        ]
        TERMINOS = [
            'noviembre','septiembre','averiguación','investigación',
            'ministerio','procuraduría','federación','constitución',
            'folio','oficio','página','artículo','fracción',
            'diligencia','declaración','actuación','resolución',
            'sentencia','expediente','carpeta','dependencia',
            'secretaría','coordinación','dirección','sección',
            'batallón','regimiento','coronel','teniente',
            'general','soldado','comandante','subprocurador',
        ]
        vocabulario = MESES + ORDINALES + TERMINOS

        def _ratio(a: str, b: str) -> float:
            return SequenceMatcher(None, a, b).ratio()

        def _corregir_token(token: str) -> str:
            t_lower = token.lower()
            # No tocar tokens < 4 letras, números o ya correctos
            if len(t_lower) < 4 or not t_lower.isalpha():
                return token
            if t_lower in vocabulario:
                return token
            # Buscar el candidato más parecido
            mejor_ratio = 0.0
            mejor_candidato = None
            for candidato in vocabulario:
                if abs(len(candidato) - len(t_lower)) > 3:
                    continue  # diferencia de longitud muy grande → saltar
                r = _ratio(t_lower, candidato)
                if r > mejor_ratio:
                    mejor_ratio = r
                    mejor_candidato = candidato
            if mejor_ratio >= 0.82 and mejor_candidato:
                # Preservar capitalización original
                if token[0].isupper():
                    return mejor_candidato.capitalize()
                return mejor_candidato
            return token

        # Tokenizar conservando separadores
        partes = re.split(r'(\s+|[,;:\.\-\(\)])', texto)
        resultado = []
        for parte in partes:
            if re.match(r'[A-Za-záéíóúüñÁÉÍÓÚÜÑ]{4,}', parte):
                resultado.append(_corregir_token(parte))
            else:
                resultado.append(parte)
        return ''.join(resultado)

    def _filtrar_lineas_basura(self, texto: str) -> str:
        """
        Filtra las líneas de texto que Tesseract generó al intentar leer
        sellos, manchas o restos de firma — no contienen palabras reales.

        Criterio de basura (se elimina la línea):
        - Menos del 40% de sus caracteres son alfanuméricos/puntuación común
          Y tiene menos de 2 palabras reales (≥2 letras consecutivas).
        - O bien la línea es muy corta (≤ 8 chars) y no contiene ninguna
          palabra real (probable carácter suelto de sello).
        """
        import re

        lineas_validas = []
        for linea in texto.splitlines():
            stripped = linea.strip()
            if not stripped:
                lineas_validas.append(linea)
                continue

            # Caracteres "legibles": letras, dígitos, espacios, puntuación básica
            legibles = sum(
                1 for c in stripped
                if c.isalpha() or c.isdigit() or c in ' .,;:-()/\'"°'
            )
            ratio_legible = legibles / len(stripped)

            # Palabras reales: secuencias de ≥ 2 letras
            palabras_reales = len(re.findall(r'[A-Za-záéíóúüñÁÉÍÓÚÜÑ]{2,}', stripped))

            # Regla 1: Demasiado ruido y pocas palabras
            if ratio_legible < 0.40 and palabras_reales < 2:
                logger.debug(f"  🗑️ Línea basura filtrada: {stripped[:50]!r}")
                continue

            # Regla 2: Cadena muy corta sin palabras (carácter saltado de sello)
            if len(stripped) <= 8 and palabras_reales == 0:
                continue

            lineas_validas.append(linea)

        return '\n'.join(lineas_validas)

    # ══════════════════════════════════════════════════════════════════════════
    # MÉTODOS PARA DOCUMENTOS MUY DETERIORADOS (copias de copias)
    # ══════════════════════════════════════════════════════════════════════════

    def _detectar_nivel_degradacion(self, gray_arr: "np.ndarray") -> float:
        """
        Estima el nivel de degradación de una imagen en escala 0.0–1.0.
        0.0 = imagen excelente, 1.0 = completamente ilegible.

        Indicadores:
        - Rango dinámico reducido (histograma estrecho → copia lavada)
        - Alto nivel de ruido granular (copia-de-copia)
        - Bajo contraste local promedio
        """
        import numpy as np
        import cv2

        # Rango dinámico: percentil 5 al 95
        p5, p95 = float(np.percentile(gray_arr, 5)), float(np.percentile(gray_arr, 95))
        rango = (p95 - p5) / 255.0          # 0 = sin contraste, 1 = máximo

        # Ruido: std de la imagen original vs. imagen suavizada
        suave = cv2.GaussianBlur(gray_arr, (3, 3), 0)
        ruido = float(np.std(
            gray_arr.astype(np.float32) - suave.astype(np.float32)
        )) / 25.0
        ruido = min(1.0, ruido)

        # Bordes débiles → texto borroso
        laplacian = cv2.Laplacian(gray_arr, cv2.CV_64F)
        foco = float(np.var(laplacian))
        foco_norm = min(1.0, foco / 500.0)  # alto = bien enfocado

        degradacion = (1.0 - rango) * 0.50 + ruido * 0.25 + (1.0 - foco_norm) * 0.25
        return min(1.0, max(0.0, degradacion))

    def _pipeline_alta_degradacion(self, gray_arr: "np.ndarray") -> "np.ndarray":
        """
        Pipeline agresivo para recuperar texto de documentos extremadamente degradados
        (copias de copias con texto casi invisible, alto grano, bajo contraste).

        Pasos extras respecto al pipeline normal:
        1. Denoising fuerte (fastNlMeans)
        2. Gamma < 1 para realzar zonas oscuras
        3. CLAHE muy agresivo (clipLimit 7, tile 4×4)
        4. Unsharp mask con radio amplio para bordes de letra muy desdibujados
        5. Top-Hat morfológico para rescatar texto en fondos grises heterogéneos
        """
        import numpy as np
        import cv2

        # 1. Denoising fuerte — h=20 elimina grano severo de fotocopiado
        denoised = cv2.fastNlMeansDenoising(
            gray_arr, h=20, templateWindowSize=7, searchWindowSize=21
        )

        # 2. Top-Hat: elimina fondos grises heterogéneos, resalta texto oscuro
        kernel_tophat = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        tophat = cv2.morphologyEx(denoised, cv2.MORPH_TOPHAT, kernel_tophat)
        # Combinar: realzar el contraste de borde con la imagen original
        denoised = cv2.addWeighted(denoised, 1.0, tophat, 2.0, 0).clip(0, 255).astype(np.uint8)

        # 3. CLAHE agresivo
        clahe = cv2.createCLAHE(clipLimit=7.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(denoised)

        # 4. Gamma correction (γ=0.65 ilumina zonas muy oscuras)
        gamma = 0.65
        lookup = np.array(
            [((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8
        )
        enhanced = cv2.LUT(enhanced, lookup)

        # 5. Unsharp mask con radio mayor (σ=3) para bordes borrosos
        blur = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=3)
        sharpened = cv2.addWeighted(enhanced, 2.2, blur, -1.2, 0).clip(0, 255).astype(np.uint8)

        return sharpened

    def _suprimir_bleedthrough(self, gray_arr: "np.ndarray") -> "np.ndarray":
        """
        Suprime el texto "sangrado" del reverso de la página que aparece en
        copias de copias como texto tenue y espejado en el fondo.

        Estrategia:
        - El bleed-through tiene diferencia de brillo 5–25 respecto al fondo.
        - El texto real supera los 30 unidades de diferencia.
        - Estimamos el fondo "limpio" con un cierre morfológico grande y
          solo conservamos las diferencias fuertes (texto auténtico).
        """
        import numpy as np
        import cv2

        # Fondo estimado: dilatación grande + blur (sin letras, sin bleed-through)
        bg = cv2.dilate(gray_arr, np.ones((51, 51), np.uint8))
        bg = cv2.GaussianBlur(bg, (51, 51), 0)

        diff = bg.astype(np.int16) - gray_arr.astype(np.int16)

        # Preservar solo diferencias >= 22 (texto real obscuro)
        # — zonas con diff < 22 (bleed-through tenue) → restaurar al color de fondo
        mask_real = (diff >= 22).astype(np.uint8)
        result = np.where(mask_real, gray_arr, bg).astype(np.uint8)
        return result

    def _enmascarar_sellos(self, gray_arr: "np.ndarray") -> "np.ndarray":
        """
        Detecta y enmascara sellos/timbres circulares o elípticos que solapan
        el texto del documento.

        Los sellos en documentos legales mexicanos son típicamente:
        - Circulares o elípticos (diámetro real 3–7 cm)
        - A 400 DPI: radio ≈ 240–550 px
        - Densidad de píxeles oscuros dentro del círculo: 10–55%
          (anillo + texto interior, pero no imagen sólida)

        Estrategia:
        1. HoughCircles sobre imagen Gaussian-blur (menos sensible a ruido)
        2. Para cada círculo candidato verificar densidad de oscuros
        3. Si es sello: rellenar con blanco para que Tesseract no lea basura
        """
        import numpy as np
        import cv2

        result = gray_arr.copy()
        h, w = gray_arr.shape[:2]

        # Suavizar para HoughCircles (necesita imagen sin ruido granular)
        blurred = cv2.GaussianBlur(gray_arr, (9, 9), 2)

        # Rangos de radio @400 DPI para sellos de 3–7 cm
        min_r = max(100, min(h, w) // 14)   # ≈ 240 px para una página A4 400 DPI
        max_r = min(600, min(h, w) // 3)    # sin superar 1/3 del lado menor

        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=min(h, w) // 5,   # mínima distancia entre centros (evita duplicados)
            param1=60,                 # umbral Canny
            param2=35,                 # umbral acumulador (más bajo = detecta más)
            minRadius=min_r,
            maxRadius=max_r,
        )

        if circles is not None:
            circles = np.round(circles[0, :]).astype(int)
            for cx, cy, r in circles:
                # Crear máscara circular para calcular densidad
                mask = np.zeros_like(gray_arr, dtype=np.uint8)
                cv2.circle(mask, (cx, cy), r, 255, -1)
                pixels_en_circulo = gray_arr[mask == 255]
                if pixels_en_circulo.size == 0:
                    continue
                dark_ratio = float(np.sum(pixels_en_circulo < 128)) / pixels_en_circulo.size
                # Sello: densidad entre 8% y 58% (ni foto sólida, ni casi blanco)
                if 0.08 <= dark_ratio <= 0.58:
                    cv2.circle(result, (cx, cy), r, 255, -1)
                    logger.debug(
                        f"  🔏 Sello enmascarado: centro=({cx},{cy}) r={r}px "
                        f"densidad_oscura={dark_ratio:.2f}"
                    )

        return result

    def _pipeline_rescate_baja_confianza(
        self, gray_arr: "np.ndarray"
    ) -> "np.ndarray":
        """
        Pipeline alternativo cuando el resultado de OCR tiene confianza < 40.
        Prueba estrategias distintas al pipeline principal:

        Estrategia: inversión de color + umbral muy agresivo.
        Algunos documentos viejos tienen fondo marrón/gris oscuro con texto claro
        (telégrafos, documentos en papel carbón, etc.).
        """
        import numpy as np
        import cv2

        # Invertir la imagen y volver a normalizar
        inverted = cv2.bitwise_not(gray_arr)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(inverted)

        # Unsharp con σ más pequeño (letras delgadas)
        blur = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.5)
        sharpened = cv2.addWeighted(enhanced, 1.8, blur, -0.8, 0).clip(0, 255).astype(np.uint8)

        return sharpened

    # ══════════════════════════════════════════════════════════════════════════
    # SUPER-RESOLUCIÓN POR SOFTWARE (copias tan borrosas que 400 DPI no basta)
    # ══════════════════════════════════════════════════════════════════════════

    def _super_resolution_software(self, gray_arr: "np.ndarray") -> "np.ndarray":
        """
        Super-resolución por software: escala 2× con interpolación cúbica y
        re-afila los bordes.  Es la diferencia entre leer y no leer texto de
        fotocopias de 3ª generación donde las letras miden < 10 px de alto.

        NO usa redes neuronales (ESRGAN/Real-ESRGAN) para mantener la
        compatibilidad sin GPU.  En su lugar:
        1. Upscale 2× bicúbico
        2. Bilateral filter (preserva bordes, elimina artefactos de upscale)
        3. Unsharp mask agresivo para que Tesseract vea letras nítidas
        """
        import numpy as np
        import cv2

        h, w = gray_arr.shape[:2]

        # Upscale 2× — equivale a pasar de 400 a 800 DPI efectivos
        upscaled = cv2.resize(
            gray_arr, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC
        )

        # Bilateral: suaviza artefactos del upscale SIN borrar bordes de letras
        smooth = cv2.bilateralFilter(upscaled, d=7, sigmaColor=40, sigmaSpace=40)

        # Unsharp mask con σ=2.5 para re-afilar
        blur = cv2.GaussianBlur(smooth, (0, 0), sigmaX=2.5)
        sharp = cv2.addWeighted(smooth, 2.0, blur, -1.0, 0).clip(0, 255).astype(np.uint8)

        return sharp

    def _binarizacion_niblack_wolf(
        self, gray_arr: "np.ndarray", k: float = -0.2, window: int = 0
    ) -> "np.ndarray":
        """
        Binarización tipo Niblack/Wolf: el MEJOR método para fondos sucios,
        manchas de café, gris heterogéneo de fotocopiado.

        La fórmula clásica de Niblack es:
            T(x,y) = mean(x,y) + k * std(x,y)
        Con k negativo (-0.2) se obtiene un umbral agresivo que conserva texto
        débil contra fondos grises.

        Se implementa con filtros de caja (boxFilter) para velocidad O(1) por pixel.
        """
        import numpy as np
        import cv2

        h, w = gray_arr.shape[:2]
        if window == 0:
            # Por defecto: window_size proporcional al texto (~25 px @ 400 DPI)
            window = max(15, min(h, w) // 40)
            if window % 2 == 0:
                window += 1  # debe ser impar

        gray_f = gray_arr.astype(np.float64)

        # Media local y desviación estándar local con box filter O(1)
        mean_local = cv2.boxFilter(gray_f, ddepth=-1, ksize=(window, window))
        sq_mean = cv2.boxFilter(gray_f ** 2, ddepth=-1, ksize=(window, window))
        std_local = np.sqrt(np.maximum(sq_mean - mean_local ** 2, 0))

        # Umbral Niblack: T = mean + k * std
        threshold = mean_local + k * std_local

        binary = np.where(gray_f > threshold, 255, 0).astype(np.uint8)

        return binary

    def _reconectar_trazos_agresivo(self, bin_arr: "np.ndarray") -> "np.ndarray":
        """
        Reconecta trazos rotos de texto mecanografiado en documentos muy
        deteriorados.  El kernel (2,1) del flujo normal no basta cuando las
        fotocopias rompen los trazos verticales de letras como l, t, f, d.

        Estrategia: cierre morfológico en 2 orientaciones (horizontal y vertical)
        con kernels delgados para no fusionar líneas de texto adyacentes.
        """
        import numpy as np
        import cv2

        result = bin_arr.copy()

        # Cierre horizontal: reconectar partes izquierda-derecha de letras
        kh = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1))
        result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kh)

        # Cierre vertical: reconectar trazos superiores-inferiores (l, t, f)
        kv = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
        result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kv)

        return result

    def _ocr_con_binarizacion(
        self, bin_img: "np.ndarray", nombre: str, psm_list: tuple = (6, 4, 3)
    ) -> Dict:
        """
        Helper: ejecuta Tesseract sobre una imagen ya binarizada y devuelve
        el mejor resultado entre los PSM dados.
        """
        import statistics as _st

        if not self.tesseract_available:
            return {'texto': '', 'confianza': 0, 'motor': nombre}

        import pytesseract

        mejor = {'texto': '', 'confianza': 0, 'motor': nombre}
        pil_img = Image.fromarray(bin_img)

        for psm in psm_list:
            try:
                cfg = f'--psm {psm} --oem 1'
                data = pytesseract.image_to_data(
                    pil_img, lang='spa', config=cfg,
                    output_type=pytesseract.Output.DICT,
                )
                confs = [
                    int(c) for c in data['conf']
                    if str(c).lstrip('-').isdigit() and int(c) >= 0
                ]
                texto = pytesseract.image_to_string(pil_img, lang='spa', config=cfg)
                conf = int(_st.mean(confs)) if confs else 0
                if conf > mejor['confianza'] or (not mejor['texto'] and texto.strip()):
                    mejor = {
                        'texto': self._post_process_text(texto),
                        'confianza': min(99.0, conf * 1.1),
                        'motor': f'{nombre}_psm{psm}',
                    }
                if conf >= 70:
                    break
            except Exception:
                continue
        return mejor

    def _ocr_multi_resolucion(self, page) -> Dict:
        """
        Ejecuta OCR a 3 resoluciones distintas (300, 400, 600 DPI) y elige el
        resultado con mayor confianza.

        ¿Por qué funciona?
        - A 300 DPI: letras grandes se leen mejor (carátulas, títulos)
        - A 400 DPI: balance general
        - A 600 DPI: texto muy pequeño o desgastado se lee mejor

        En copias de copias, ciertas zonas se recuperan a una resolución y no
        a otra. El voting asegura que siempre ganemos la mejor.
        """
        import numpy as np
        import cv2

        dpis = [
            (300, 300 / 72),   # factor ≈ 4.17
            (400, 400 / 72),   # factor ≈ 5.56
            (600, 600 / 72),   # factor ≈ 8.33
        ]

        mejor_global = {'texto': '', 'confianza': 0, 'motor': 'multi_dpi'}

        for dpi_val, factor in dpis:
            try:
                matrix = fitz.Matrix(factor, factor)
                pix = page.get_pixmap(matrix=matrix)
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                arr = np.array(img.convert('RGB'))
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

                # Sombras + CLAHE + bilateral + unsharp (pipeline estándar)
                bg = cv2.dilate(gray, np.ones((21, 21), np.uint8))
                bg = cv2.GaussianBlur(bg, (21, 21), 0)
                sf = cv2.divide(gray, bg, scale=255.0).astype(np.uint8)
                clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
                sf = clahe.apply(sf)
                sf = cv2.bilateralFilter(sf, d=5, sigmaColor=30, sigmaSpace=30)
                _b = cv2.GaussianBlur(sf, (0, 0), sigmaX=2)
                sf = cv2.addWeighted(sf, 1.6, _b, -0.6, 0).astype(np.uint8)

                # Niblack (la mejor para fondos sucios)
                bin_niblack = self._binarizacion_niblack_wolf(sf)
                bin_niblack = self._reconectar_trazos_agresivo(bin_niblack)
                bin_niblack = self._eliminar_firmas_ruido(bin_niblack)

                resultado = self._ocr_con_binarizacion(
                    bin_niblack, f'niblack_{dpi_val}dpi'
                )

                if resultado['confianza'] > mejor_global['confianza']:
                    mejor_global = resultado

                # Si ya tenemos confianza alta, no seguir probando DPIs
                if mejor_global['confianza'] >= 72:
                    break
            except Exception as e:
                logger.debug(f"  multi-DPI {dpi_val}: error {e}")
                continue

        return mejor_global

    def _procesar_pagina_paralela(self, pdf_path: str, pagina_num: int, total_paginas: int) -> Dict:
        """
        Procesar una página individual (ejecutado en thread paralelo).
        Cada invocación abre su propio fitz.Document para garantizar thread-safety.
        
        Returns:
            Diccionario con resultado del procesamiento
        """
        doc = None
        try:
            # Cada worker abre su propia instancia del documento (thread-safe)
            doc = fitz.open(pdf_path)
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

            # ── Detección de página principalmente fotográfica ─────────────────
            # Documentos como dictámenes periciales de fotografía forense tienen páginas
            # que son casi 100% imágenes oscuras sin texto recuperable.
            if self._es_pagina_mayormente_fotografia(page):
                return {
                    'numero_pagina': pagina_num + 1,
                    'texto_extraido': '[PÁGINA CON FOTOGRAFÍA — sin texto extraíble]',
                    'confianza': 100.0,
                    'motor_usado': 'photo_detection',
                    'es_texto_directo': True,
                    'es_pagina_en_blanco': False,
                    'es_pagina_foto': True,
                    'datos_adicionales': {'motor_usado': 'photo_detection', 'correcciones_aplicadas': False}
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
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass

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
        400 DPI + shadow removal + deskew + CLAHE + Otsu + múltiples PSM = máxima precisión
        en nombres/fechas/lugares para documentos a máquina de escribir y sellos.
        """
        import numpy as np
        import cv2

        # ── 1. Renderizar a ~400 DPI (72 * 5.56 ≈ 400) ───────────────────────
        # 400 DPI mejora significativamente el reconocimiento de texto mecanografiado
        # y caracteres con bordes irregulares típicos de documentos viejos escaneados.
        matrix = fitz.Matrix(5.56, 5.56)
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

        # Eliminación de sombras por iluminación no uniforme (documentos envejecidos).
        # Se estima el fondo con un blur grande y se normaliza contra él.
        bg = cv2.dilate(gray, np.ones((21, 21), np.uint8))
        bg = cv2.GaussianBlur(bg, (21, 21), 0)
        shadow_free = cv2.divide(gray, bg, scale=255.0).astype(np.uint8)

        # CLAHE con clipLimit 3.5 para documentos envejecidos con bajo contraste
        clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
        shadow_free = clahe.apply(shadow_free)

        # Filtro bilateral: suaviza el grano de copia-de-copia PRESERVANDO bordes
        # de letras. Mejor que medianBlur para texto borroso.
        shadow_free = cv2.bilateralFilter(shadow_free, d=5, sigmaColor=30, sigmaSpace=30)

        # Unsharp mask — recupera bordes de letras desdibujadas por generaciones
        # de fotocopia. Fórmula: sharpened = original + alpha*(original - blur)
        _blur = cv2.GaussianBlur(shadow_free, (0, 0), sigmaX=2)
        shadow_free = cv2.addWeighted(shadow_free, 1.6, _blur, -0.6, 0).astype(np.uint8)

        # ── Enmascarar bloques de fotografías incrustadas ─────────────────────
        shadow_free = self._enmascarar_bloques_foto(shadow_free)

        # ── Supresión de bleed-through (texto del reverso en copias de copias) ─
        shadow_free = self._suprimir_bleedthrough(shadow_free)

        # ── Enmascarar sellos/timbres circulares ──────────────────────────────
        shadow_free = self._enmascarar_sellos(shadow_free)

        # ── Pipeline especial para documentos muy degradados ──────────────────
        nivel_degradacion = self._detectar_nivel_degradacion(shadow_free)
        if nivel_degradacion > 0.60:
            logger.debug(
                f"  ⚠️ Documento degradado (nivel={nivel_degradacion:.2f}), "
                "usando pipeline de rescate"
            )
            shadow_free = self._pipeline_alta_degradacion(shadow_free)

        # ── Super-resolución por software para texto ultra-borroso ────────────
        # Si el foco (laplaciano) es muy bajo, las letras miden < 10 px y
        # Tesseract no puede leerlas. Escalamos 2× para darle más píxeles.
        _lap_var = float(cv2.Laplacian(shadow_free, cv2.CV_64F).var())
        usar_superres = _lap_var < 120 or nivel_degradacion > 0.70
        if usar_superres:
            logger.debug(f"  🔎 Aplicando super-resolución (laplacian_var={_lap_var:.0f})")
            shadow_free_hr = self._super_resolution_software(shadow_free)
        else:
            shadow_free_hr = shadow_free

        # ── Candidato A: Otsu (umbral global) ────────────────────────────────
        _, bin_otsu = cv2.threshold(shadow_free_hr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(bin_otsu) < 127:
            bin_otsu = cv2.bitwise_not(bin_otsu)

        # ── Candidato B: Binarización adaptativa local (tipo Sauvola) ─────────
        # Mucho mejor que Otsu en fondos con iluminación dispareja o gris sucio.
        # window_size 51 px @ 400 DPI ≈ 3.2 mm — cubre una letra con contexto.
        bin_local = cv2.adaptiveThreshold(
            shadow_free_hr, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=51, C=15
        )
        if np.mean(bin_local) < 127:
            bin_local = cv2.bitwise_not(bin_local)

        # ── Candidato C: Niblack/Wolf — la mejor para copias de copias ────────
        # La binarización Niblack usa umbral local basado en media+k*std que
        # rescata texto tenue que Otsu y Adaptivo pierden completamente.
        bin_niblack = self._binarizacion_niblack_wolf(shadow_free_hr, k=-0.2)
        if np.mean(bin_niblack) < 127:
            bin_niblack = cv2.bitwise_not(bin_niblack)

        # Cierre morfológico para reconectar trazos rotos en texto mecanografiado
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
        bin_otsu  = cv2.morphologyEx(bin_otsu,  cv2.MORPH_CLOSE, kernel)
        bin_local = cv2.morphologyEx(bin_local, cv2.MORPH_CLOSE, kernel)

        # Reconexión más agresiva para Niblack (documentos muy deteriorados)
        bin_niblack = self._reconectar_trazos_agresivo(bin_niblack)

        # ── Eliminar firmas y ruido visual en todos los candidatos ─────────────
        bin_otsu    = self._eliminar_firmas_ruido(bin_otsu)
        bin_local   = self._eliminar_firmas_ruido(bin_local)
        bin_niblack = self._eliminar_firmas_ruido(bin_niblack)

        # ── 4. Tesseract: probar las 3 binarizaciones y elegir la mejor ───────
        if self.tesseract_available:
            import pytesseract, statistics as _stats

            mejor = {'texto': '', 'confianza': 0, 'motor': 'tesseract_scan'}

            # Cada candidato de imagen × cada PSM → elegir el de mayor confianza
            for img_bin, bin_nombre in (
                (bin_otsu,    'otsu'),
                (bin_local,   'local'),
                (bin_niblack, 'niblack'),
            ):
                img_candidate = Image.fromarray(img_bin)
                for psm in (4, 6, 3):
                    try:
                        cfg = f'--psm {psm} --oem 1'
                        data = pytesseract.image_to_data(
                            img_candidate, lang='spa', config=cfg,
                            output_type=pytesseract.Output.DICT
                        )
                        confs = [int(c) for c in data['conf']
                                 if str(c).lstrip('-').isdigit() and int(c) >= 0]
                        texto = pytesseract.image_to_string(
                            img_candidate, lang='spa', config=cfg
                        )
                        conf = int(_stats.mean(confs)) if confs else 0
                        if conf > mejor['confianza'] or (not mejor['texto'] and texto.strip()):
                            mejor = {
                                'texto': self._post_process_text(texto),
                                'confianza': min(99.0, conf * 1.1),
                                'motor': f'tesseract_{bin_nombre}_psm{psm}'
                            }
                        # Si ya es suficientemente bueno no seguimos probando
                        if conf >= 72:
                            break
                    except Exception:
                        continue
                # Si con otsu ya tenemos confianza alta, no probamos local
                if mejor['confianza'] >= 72:
                    break

            if mejor['texto']:
                return mejor

        # ── 5. Retry con pipeline "rescate invertido" si confianza < 40 ───────
        # Algunos documentos carbón/papel marrón tienen fondo oscuro + texto claro
        if not (self.tesseract_available) or (mejor.get('confianza', 0) < 40):
            try:
                import pytesseract, statistics as _stats_r
                gray_inv = self._pipeline_rescate_baja_confianza(gray)
                _, bin_inv = cv2.threshold(
                    gray_inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
                if np.mean(bin_inv) < 127:
                    bin_inv = cv2.bitwise_not(bin_inv)
                bin_inv = self._eliminar_firmas_ruido(bin_inv)

                for psm_r in (6, 4):
                    cfg_r = f'--psm {psm_r} --oem 1'
                    data_r = pytesseract.image_to_data(
                        Image.fromarray(bin_inv), lang='spa', config=cfg_r,
                        output_type=pytesseract.Output.DICT
                    )
                    confs_r = [int(c) for c in data_r['conf']
                               if str(c).lstrip('-').isdigit() and int(c) >= 0]
                    texto_r = pytesseract.image_to_string(
                        Image.fromarray(bin_inv), lang='spa', config=cfg_r
                    )
                    conf_r = int(_stats_r.mean(confs_r)) if confs_r else 0
                    if conf_r > mejor.get('confianza', 0):
                        mejor = {
                            'texto': self._post_process_text(texto_r),
                            'confianza': min(99.0, conf_r * 1.1),
                            'motor': f'tesseract_rescate_psm{psm_r}',
                        }
                    if conf_r >= 45:
                        break
            except Exception:
                pass

        if mejor.get('texto'):
            return mejor

        # ── 6. Multi-resolución: último recurso antes del fallback ────────────
        # Prueba 300, 400 y 600 DPI con Niblack desde cero — a veces una
        # resolución distinta recupera texto que otra pierde completamente.
        try:
            multi_res = self._ocr_multi_resolucion(page)
            if multi_res.get('confianza', 0) > mejor.get('confianza', 0):
                mejor = multi_res
        except Exception:
            pass

        if mejor.get('texto'):
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

        # ── 5. Filtrar líneas basura generadas por sellos/manchas/firmas ──────
        texto = self._filtrar_lineas_basura(texto)

        # ── 6. Recuperación fuzzy de palabras clave mal reconocidas ──────────
        texto = self._recuperar_palabras_clave(texto)

        # ── 7. Corrección post-OCR de entidades críticas ──────────────────────
        # Fechas, Nombres y Ubicaciones son lo más importante → se corrigen al final
        texto = entity_correction.corregir_todo(texto)

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
