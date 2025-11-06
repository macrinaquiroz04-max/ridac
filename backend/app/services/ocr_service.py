# backend/app/services/ocr_service.py

from pathlib import Path
from typing import Optional, List, Dict, Tuple
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import time
from sqlalchemy.orm import Session
from app.models.tomo import Tomo, ContenidoOCR
from app.config import settings
from app.utils.logger import logger
from app.services.image_preprocessing_service import ImagePreprocessingService
from app.services.text_correction_service import TextCorrectionService

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

    def procesar_pdf(self, db: Session, tomo: Tomo):
        """Procesar PDF con OCR mejorado y optimizado"""
        try:
            pdf_path = Path(tomo.ruta_archivo)

            if not pdf_path.exists():
                raise Exception(f"Archivo no encontrado: {pdf_path}")

            logger.info(f"Procesando PDF con OCR mejorado: {pdf_path}")

            # Abrir PDF
            doc = fitz.open(str(pdf_path))
            total_paginas = len(doc)

            logger.info(f"Total de páginas: {total_paginas}")

            # Actualizar total de páginas
            tomo.total_paginas = total_paginas
            tomo.estado_ocr = 'procesando'
            db.commit()

            # Estadísticas de procesamiento
            stats = {
                'paginas_texto_directo': 0,
                'paginas_ocr': 0,
                'confianza_promedio': 0,
                'tiempo_total': 0
            }
            
            inicio_procesamiento = time.time()

            # Procesar cada página
            for pagina_num in range(total_paginas):
                try:
                    # Actualizar progreso
                    progreso = int((pagina_num / total_paginas) * 100)
                    tomo.progreso_ocr = progreso
                    db.commit()

                    logger.info(f"Procesando página {pagina_num + 1}/{total_paginas} ({progreso}%)")

                    # Extraer página
                    page = doc[pagina_num]

                    # Intentar extraer texto directamente (si es PDF con texto)
                    texto_directo = page.get_text()

                    if self._is_text_extractable(texto_directo):
                        # PDF con texto extraíble
                        texto_final = self._clean_extracted_text(texto_directo)
                        
                        # MODO RÁPIDO: Solo correcciones básicas + alcaldías
                        # (SEPOMEX y entidades deshabilitadas para velocidad)
                        try:
                            from app.services.autocorrector_integrado_service import autocorrector_integrado
                            resultado_correccion = autocorrector_integrado.corregir_texto_completo(
                                texto_final,
                                aplicar_sepomex=False,  # DESHABILITADO (ahorra ~5 seg/página)
                                detectar_entidades=(pagina_num == 0)  # Solo primera página
                            )
                            texto_final = resultado_correccion['texto_corregido']
                            if pagina_num == 0:
                                logger.info(f"  ✓ Correcciones completas: {resultado_correccion['correcciones_aplicadas']}")
                        except Exception as e:
                            # Fallback a corrección básica
                            texto_final = self.correction_service.corregir_texto(texto_final, "legal")
                            logger.warning(f"  ⚠️ Usando corrección básica: {e}")
                        
                        motor_usado = 'pdf_text'
                        confianza = 99.0
                        stats['paginas_texto_directo'] += 1
                        logger.info(f"  ✓ Texto extraído directamente de PDF")
                    else:
                        # PDF escaneado, usar OCR con múltiples motores
                        resultado = self._extraer_con_multiple_ocr(page)
                        texto_original = resultado['texto']
                        
                        # MODO RÁPIDO: Correcciones básicas + alcaldías
                        try:
                            from app.services.autocorrector_integrado_service import autocorrector_integrado
                            resultado_correccion = autocorrector_integrado.corregir_texto_completo(
                                texto_original,
                                aplicar_sepomex=False,  # DESHABILITADO para velocidad
                                detectar_entidades=(pagina_num == 0)  # Solo primera página
                            )
                            texto_final = resultado_correccion['texto_corregido']
                            correcciones = resultado_correccion['correcciones_aplicadas']
                            if pagina_num == 0:
                                logger.info(f"  ✓ Correcciones completas: {correcciones}")
                        except Exception as e:
                            # Fallback a corrección básica
                            texto_final = self.correction_service.corregir_texto(texto_original, "legal")
                            logger.warning(f"  ⚠️ Usando corrección básica: {e}")
                            correcciones = 1
                        
                        motor_usado = resultado['motor']
                        confianza = resultado['confianza']
                        
                        # Validar calidad de corrección y ajustar confianza
                        validacion = self.correction_service.validar_calidad_correccion(texto_original, texto_final)
                        confianza = min(confianza, validacion['confianza_correccion'])
                        
                        stats['paginas_ocr'] += 1
                        logger.info(f"  ✓ OCR aplicado ({motor_usado}), confianza: {confianza}%, correcciones: {correcciones}")

                    # Actualizar estadísticas
                    stats['confianza_promedio'] += confianza

                    # DESACTIVADO: Generar embeddings después en batch (mucho más rápido)
                    # Los embeddings se pueden generar con un script separado si se necesitan
                    embedding = None
                    # try:
                    #     from app.controllers.busqueda_controller import busqueda_controller
                    #     embedding_vector = busqueda_controller.generar_embedding(texto_final)
                    #     if embedding_vector:
                    #         embedding = {
                    #             "vector": embedding_vector,
                    #             "modelo": "paraphrase-multilingual-MiniLM-L12-v2"
                    #         }
                    # except Exception as embed_error:
                    #     logger.warning(f"No se pudo generar embedding para página {pagina_num + 1}: {embed_error}")

                    # Guardar resultado
                    contenido = ContenidoOCR(
                        tomo_id=tomo.id,
                        numero_pagina=pagina_num + 1,
                        texto_extraido=texto_final,
                        confianza=confianza,
                        embeddings=embedding,
                        datos_adicionales={
                            "motor_usado": motor_usado,
                            "correcciones_aplicadas": True
                        }
                    )
                    db.add(contenido)
                    db.commit()

                except Exception as e:
                    logger.error(f"Error en página {pagina_num + 1}: {e}")
                    # Guardar página con error para seguimiento
                    contenido_error = ContenidoOCR(
                        tomo_id=tomo.id,
                        numero_pagina=pagina_num + 1,
                        texto_extraido=f"[ERROR: {str(e)}]",
                        confianza=0.0,
                        datos_adicionales={"motor_usado": "error", "error": str(e)}
                    )
                    db.add(contenido_error)
                    db.commit()

            doc.close()

            # Calcular estadísticas finales
            stats['tiempo_total'] = time.time() - inicio_procesamiento
            stats['confianza_promedio'] = stats['confianza_promedio'] / total_paginas if total_paginas > 0 else 0

            # Actualizar estado final del tomo
            tomo.progreso_ocr = 100
            tomo.estado_ocr = 'completado'
            db.commit()

            logger.info(f"✓ Procesamiento completado en {stats['tiempo_total']:.2f}s")
            logger.info(f"  📄 Páginas con texto directo: {stats['paginas_texto_directo']}")
            logger.info(f"  🔍 Páginas con OCR: {stats['paginas_ocr']}")
            logger.info(f"  📊 Confianza promedio: {stats['confianza_promedio']:.1f}%")

        except Exception as e:
            logger.error(f"Error procesando PDF: {e}", exc_info=True)
            tomo.estado_ocr = 'error'
            tomo.error_ocr = str(e)
            db.commit()
            raise

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
        Extrae texto usando Tesseract RÁPIDO (sin ensemble)
        OPTIMIZADO: Solo 1 estrategia en lugar de 15+ = 80% más rápido
        """
        # Renderizar página a imagen con alta calidad
        matrix = fitz.Matrix(3, 3)  # 3x zoom para mejor calidad
        pix = page.get_pixmap(matrix=matrix)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # MODO RÁPIDO: Solo Tesseract con preprocesamiento 'document'
        img_processed = self.preprocessing_service.preprocess_for_ocr(img, 'document')
        
        # Tesseract con configuración óptima para documentos legales
        if self.tesseract_available:
            resultado = self._tesseract_ocr(
                img_processed, 
                self.tesseract_configs.get('single_column_spa', '--psm 4'),
                "tesseract_fast"
            )
            if resultado['confianza'] > 30:
                return resultado
        
        # Fallback si Tesseract falla
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
        """Postprocesa el texto extraído para mejorar calidad"""
        import re
        
        if not texto:
            return ""
        
        # Eliminar múltiples espacios
        texto = re.sub(r'\s+', ' ', texto)
        
        # Corregir errores comunes de OCR específicos de este motor
        correcciones_basicas = {
            r'\b0\b': 'O',  # Cero por O
            r'\b1\b': 'I',  # Uno por I en contextos apropiados
            r'\bIOS\b': '105',  # iOS por 105
            r'\bI0\b': '10',   # I0 por 10
            r'\b5\b(?=\w)': 'S',  # 5 por S al inicio de palabra
        }
        
        for patron, reemplazo in correcciones_basicas.items():
            texto = re.sub(patron, reemplazo, texto)
        
        # Limpiar caracteres extraños (preservar más caracteres especiales legales)
        texto = re.sub(r'[^\w\s\.,;:!?\-\(\)\"\'\/\\°ª²³ñÑáéíóúÁÉÍÓÚü@#$%&]', '', texto)
        
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

    def get_status(self) -> dict:
        """Obtener estado de los motores OCR"""
        return {
            "tesseract": self.tesseract_available,
            "easyocr": self.easyocr_reader is not None,
            "paddleocr": self.paddleocr_reader is not None
        }
