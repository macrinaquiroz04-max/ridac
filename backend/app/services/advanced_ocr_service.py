# backend/app/services/advanced_ocr_service.py

import os
import re
import time
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from datetime import datetime

from app.models.tomo import Tomo, ContenidoOCR
from app.utils.logger import logger

# 🚀 SERVICIOS AVANZADOS INTEGRADOS
try:
    from app.services.legal_nlp_service import analyze_legal_document_nlp
    from app.services.advanced_image_processor import process_image_for_ocr
    from app.services.legal_table_extractor import extract_tables_from_legal_document
    ADVANCED_SERVICES_AVAILABLE = True
    logger.info("✅ Servicios avanzados (NLP, OpenCV, Camelot) cargados")
except ImportError as e:
    logger.warning(f"⚠️ Servicios avanzados no disponibles: {e}")
    ADVANCED_SERVICES_AVAILABLE = False

class AdvancedOCRService:
    """Servicio OCR avanzado con IA para procesamiento completo de documentos legales"""
    
    def __init__(self):
        self.max_workers = min(4, multiprocessing.cpu_count())  # Limitamos para no sobrecargar
        self.protected_patterns = {
            'menores': r'\b[A-Z]\.[A-Z]\.[A-Z]\b',  # Patrón B.C.A
            'expedientes': r'\b\d{2,4}[-/]\d{2,4}[-/]\d{2,4}\b',  # Números de expediente
            'identificacion': r'\b[A-Z]{4}\d{6}[A-Z0-9]{3}\b'  # CURP pattern
        }
    
    def setup_tesseract_config(self) -> str:
        """🚀 CONFIGURACIÓN ULTRA-RÁPIDA de Tesseract para documentos legales"""
        # Configuración optimizada para máxima velocidad
        return '--oem 3 --psm 6 -c tessedit_create_hocr=0 -c tessedit_create_pdf=0 -c preserve_interword_spaces=1'
    
    def enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Mejora la imagen para mejor reconocimiento OCR"""
        try:
            # Convertir a escala de grises si no lo está
            if image.mode != 'L':
                image = image.convert('L')
            
            # Aumentar contraste
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Aumentar nitidez
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Aplicar filtro para reducir ruido
            image = image.filter(ImageFilter.MedianFilter())
            
            return image
        except Exception as e:
            logger.warning(f"Error mejorando imagen: {e}")
            return image
    
    def extract_text_with_multiple_engines(self, image: Image.Image) -> Dict[str, Any]:
        """🚀 EXTRACCIÓN ULTRA-AVANZADA con OpenCV + múltiples motores OCR"""
        results = []
        
        # 📸 PREPROCESAMIENTO AVANZADO DE IMAGEN
        if ADVANCED_SERVICES_AVAILABLE:
            try:
                processed_image, processing_info = process_image_for_ocr(image)
                logger.debug(f"📸 Imagen procesada: calidad {processing_info['quality_score']:.2f}")
                image = processed_image  # Usar imagen mejorada
            except Exception as e:
                logger.warning(f"⚠️ Error en preprocesamiento avanzado: {e}")
                # Continuar con imagen original
        
        # Motor 1: Tesseract básico
        try:
            config_basic = r'--oem 3 --psm 6'
            text_basic = pytesseract.image_to_string(image, lang='spa+eng', config=config_basic)
            if text_basic.strip():
                confidence_basic = len([c for c in text_basic if c.isalnum()]) / max(len(text_basic), 1) * 100
                results.append({
                    'texto': text_basic,
                    'motor': 'tesseract_basic',
                    'confianza': min(confidence_basic, 85)
                })
        except Exception as e:
            logger.warning(f"Tesseract básico falló: {e}")
        
        # Motor 2: Tesseract optimizado para documentos
        try:
            config_doc = self.setup_tesseract_config()
            text_doc = pytesseract.image_to_string(image, lang='spa+eng', config=config_doc)
            if text_doc.strip():
                confidence_doc = len([c for c in text_doc if c.isalnum()]) / max(len(text_doc), 1) * 100
                results.append({
                    'texto': text_doc,
                    'motor': 'tesseract_optimized',
                    'confianza': min(confidence_doc + 10, 95)  # Bonus por optimización
                })
        except Exception as e:
            logger.warning(f"Tesseract optimizado falló: {e}")
        
        # Motor 3: Tesseract con imagen mejorada
        try:
            enhanced_image = self.enhance_image_for_ocr(image)
            config_enhanced = self.setup_tesseract_config()
            text_enhanced = pytesseract.image_to_string(enhanced_image, lang='spa+eng', config=config_enhanced)
            if text_enhanced.strip():
                confidence_enhanced = len([c for c in text_enhanced if c.isalnum()]) / max(len(text_enhanced), 1) * 100
                results.append({
                    'texto': text_enhanced,
                    'motor': 'tesseract_enhanced',
                    'confianza': min(confidence_enhanced + 15, 98)  # Bonus por mejora de imagen
                })
        except Exception as e:
            logger.warning(f"Tesseract con imagen mejorada falló: {e}")
        
        # Seleccionar el mejor resultado
        if not results:
            return {'texto': '', 'motor': 'error', 'confianza': 0}
        
        # Ordenar por confianza y longitud de texto
        results.sort(key=lambda x: (x['confianza'], len(x['texto'])), reverse=True)
        best_result = results[0]
        
        # Aplicar limpieza final
        best_result['texto'] = self.clean_extracted_text(best_result['texto'])
        
        return best_result
    
    def clean_extracted_text(self, text: str) -> str:
        """Limpia y normaliza el texto extraído"""
        if not text:
            return ""
        
        # Eliminar caracteres de control
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Normalizar espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        
        # Normalizar saltos de línea múltiples
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Eliminar líneas que solo contienen espacios o caracteres especiales
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if len(line) >= 2 and re.search(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]', line):
                lines.append(line)
        
        return '\n'.join(lines).strip()
    
    def protect_sensitive_data(self, text: str) -> str:
        """Protege datos sensibles como nombres de menores"""
        protected_text = text
        
        for category, pattern in self.protected_patterns.items():
            if category == 'menores':
                protected_text = re.sub(pattern, '[MENOR PROTEGIDO]', protected_text)
            elif category == 'expedientes':
                # Los números de expediente pueden mantenerse parcialmente
                protected_text = re.sub(pattern, lambda m: m.group()[:8] + '***', protected_text)
        
        return protected_text
    
    def process_single_page(self, page_data: Tuple[int, fitz.Page, int]) -> Dict[str, Any]:
        """Procesa una sola página del PDF"""
        page_num, page, tomo_id = page_data
        
        try:
            # Convertir página a imagen de alta resolución
            mat = fitz.Matrix(3, 3)  # 3x resolución para mejor calidad
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Extraer texto con múltiples motores
            result = self.extract_text_with_multiple_engines(image)
            
            # Proteger datos sensibles
            if result['texto']:
                result['texto'] = self.protect_sensitive_data(result['texto'])
            
            # Verificar que el texto sea útil
            if len(result['texto'].strip()) < 10:
                result['confianza'] = 0
                result['motor'] = 'insufficient_text'
            
            result['pagina'] = page_num + 1
            result['tomo_id'] = tomo_id
            
            return result
            
        except Exception as e:
            logger.error(f"Error procesando página {page_num + 1}: {e}")
            return {
                'pagina': page_num + 1,
                'tomo_id': tomo_id,
                'texto': f'[ERROR: {str(e)}]',
                'motor': 'error',
                'confianza': 0
            }
    
    def process_pdf_complete(self, db: Session, tomo: Tomo) -> Dict[str, Any]:
        """Procesa un PDF completo sin limitaciones"""
        try:
            pdf_path = Path(tomo.ruta_archivo)
            
            if not pdf_path.exists():
                raise Exception(f"Archivo no encontrado: {pdf_path}")
            
            logger.info(f"🚀 Iniciando procesamiento OCR COMPLETO: {pdf_path}")
            
            # Abrir PDF
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            
            logger.info(f"📄 Total de páginas: {total_pages}")
            
            # Actualizar estado del tomo
            tomo.numero_paginas = total_pages
            tomo.estado_ocr = 'procesando'
            tomo.progreso_ocr = 0
            db.commit()
            
            # Verificar páginas ya procesadas
            existing_pages = db.query(ContenidoOCR.numero_pagina).filter(
                ContenidoOCR.tomo_id == tomo.id
            ).all()
            existing_page_numbers = {page[0] for page in existing_pages}
            
            # Preparar páginas para procesamiento paralelo
            pages_to_process = []
            for page_num in range(total_pages):
                if page_num + 1 not in existing_page_numbers:
                    pages_to_process.append((page_num, doc[page_num], tomo.id))
            
            logger.info(f"🔄 Páginas nuevas a procesar: {len(pages_to_process)}")
            logger.info(f"⏩ Páginas ya procesadas: {len(existing_page_numbers)}")
            
            # Procesamiento paralelo por lotes
            batch_size = 50  # 🚀 ULTRA-OPTIMIZADO: Lotes grandes para máxima velocidad
            total_processed = len(existing_page_numbers)
            total_errors = 0
            
            start_time = time.time()
            
            for batch_start in range(0, len(pages_to_process), batch_size):
                batch_end = min(batch_start + batch_size, len(pages_to_process))
                batch_pages = pages_to_process[batch_start:batch_end]
                
                # 🚀 LOGGING OPTIMIZADO: Solo lotes importantes para mayor velocidad
                if (batch_start // batch_size + 1) % 5 == 1:  # Solo cada 5 lotes
                    logger.info(f"🔄 Procesando lote {batch_start // batch_size + 1}: páginas {batch_pages[0][0] + 1}-{batch_pages[-1][0] + 1}")
                
                # Procesar lote en paralelo
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = [executor.submit(self.process_single_page, page_data) for page_data in batch_pages]
                    
                    batch_results = []
                    for future in as_completed(futures):
                        try:
                            result = future.result(timeout=60)  # 60 segundos por página máximo
                            batch_results.append(result)
                        except Exception as e:
                            logger.error(f"Error en procesamiento paralelo: {e}")
                            total_errors += 1
                
                # Guardar resultados del lote
                for result in batch_results:
                    try:
                        # Limpiar y validar texto
                        texto_limpio = result['texto'].strip() if result['texto'] else ""
                        
                        # 🔍 DETECTAR AUTOMÁTICAMENTE SI ES CARÁTULA
                        es_caratula = False
                        razon_caratula = None
                        
                        if texto_limpio:
                            try:
                                from app.services.caratula_detector_service import caratula_detector
                                es_caratula, razon_caratula = caratula_detector.es_caratula(
                                    texto_limpio, 
                                    result['pagina']
                                )
                                if es_caratula:
                                    logger.info(f"📄 Página {result['pagina']} detectada como carátula: {razon_caratula}")
                            except Exception as e:
                                logger.warning(f"Error detectando carátula en página {result['pagina']}: {e}")
                        
                        # Determinar si el texto es útil
                        es_texto_util = len(texto_limpio) > 10 and result['confianza'] > 0 and not es_caratula
                        
                        # Generar embedding solo si hay texto útil (no carátulas)
                        embedding = None
                        if es_texto_util:
                            try:
                                from app.controllers.busqueda_controller import busqueda_controller
                                embedding_vector = busqueda_controller.generar_embedding(texto_limpio)
                                if embedding_vector:
                                    embedding = {
                                        "vector": embedding_vector,
                                        "modelo": "paraphrase-multilingual-MiniLM-L12-v2"
                                    }
                            except Exception as embed_error:
                                logger.warning(f"No se pudo generar embedding para página {result['pagina']}: {embed_error}")

                        # Determinar texto a guardar
                        if es_caratula:
                            texto_final = f"[CARÁTULA - {razon_caratula}]"
                        elif es_texto_util:
                            texto_final = texto_limpio
                        elif result['confianza'] == 0:
                            texto_final = "[PÁGINA EN BLANCO]"
                        else:
                            texto_final = "[NO PROCESABLE - SIN TEXTO LEGIBLE]"
                        
                        # Preparar datos adicionales
                        datos_adicionales = {
                            'motor': result['motor'],
                            'ignorada': es_caratula,  # 🗑️ Marcar como ignorada automáticamente
                            'es_caratula': es_caratula,
                            'razon': razon_caratula if es_caratula else None,
                            'auto_detectada': es_caratula
                        }
                        
                        # Guardar TODAS las páginas para evitar reprocesamiento infinito
                        contenido = ContenidoOCR(
                            tomo_id=result['tomo_id'],
                            numero_pagina=result['pagina'],
                            texto_extraido=texto_final,
                            confianza=result['confianza'],
                            embeddings=embedding,
                            datos_adicionales=datos_adicionales
                        )
                        db.add(contenido)
                        total_processed += 1
                    except Exception as e:
                        logger.error(f"Error guardando página {result['pagina']}: {e}")
                        total_errors += 1
                
                # Commit del lote
                db.commit()
                
                # Actualizar progreso
                progress = int((total_processed / total_pages) * 100)
                tomo.progreso_ocr = progress
                db.commit()
                
                elapsed_time = time.time() - start_time
                avg_time_per_page = elapsed_time / max(total_processed - len(existing_page_numbers), 1)
                estimated_remaining = (total_pages - total_processed) * avg_time_per_page
                
                logger.info(f"📊 Progreso: {total_processed}/{total_pages} ({progress}%) | Errores: {total_errors}")
                logger.info(f"⏱️ Tiempo estimado restante: {estimated_remaining/60:.1f} minutos")
            
            doc.close()
            
            # Finalizar procesamiento OCR
            final_count = db.query(ContenidoOCR).filter(ContenidoOCR.tomo_id == tomo.id).count()
            tomo.estado_ocr = 'completado'
            tomo.progreso_ocr = 100
            db.commit()
            
            processing_time = time.time() - start_time
            
            logger.info(f"✅ PROCESAMIENTO OCR COMPLETADO")
            logger.info(f"📄 Total páginas procesadas: {final_count}/{total_pages}")
            logger.info(f"⏱️ Tiempo total: {processing_time/60:.1f} minutos")
            logger.info(f"🚫 Total errores: {total_errors}")
            logger.info(f"📈 Promedio: {processing_time/final_count:.2f} segundos por página")
            
            # 🔍 AHORA ANALIZAR ENTIDADES (personas, lugares, fechas, diligencias)
            logger.info(f"🔍 Iniciando análisis NLP del tomo completo...")
            analisis_start = time.time()
            
            try:
                # Unir todo el texto del tomo
                texto_completo = ""
                contenidos_ocr = db.query(ContenidoOCR).filter(
                    ContenidoOCR.tomo_id == tomo.id,
                    ContenidoOCR.texto_extraido.isnot(None)
                ).all()
                
                for contenido in contenidos_ocr:
                    if contenido.texto_extraido and not contenido.texto_extraido.startswith("["):
                        texto_completo += contenido.texto_extraido + "\n\n"
                
                if texto_completo.strip():
                    # Analizar con NLP
                    resultado_analisis = analyze_legal_document_nlp(texto_completo)
                    
                    # Guardar personas con validación inteligente
                    from app.services.legal_entity_filter_service import LegalEntityFilterService
                    legal_entity_filter = LegalEntityFilterService()
                    
                    personas_guardadas = 0
                    personas_rechazadas = 0
                    
                    if resultado_analisis and "personas" in resultado_analisis:
                        from app.models.analisis_juridico import PersonaIdentificada
                        
                        for per in resultado_analisis["personas"]:
                            nombre = per.get("nombre", "").strip()
                            
                            # 🔍 VALIDACIÓN INTELIGENTE
                            es_valido, razon_invalido = legal_entity_filter.es_nombre_valido(nombre)
                            if not es_valido:
                                logger.debug(f"Persona rechazada: '{nombre}' - Razón: {razon_invalido}")
                                personas_rechazadas += 1
                                continue
                            
                            # Guardar persona válida
                            try:
                                persona = PersonaIdentificada(
                                    tomo_id=tomo.id,
                                    carpeta_id=tomo.carpeta_id,
                                    nombre_completo=nombre,
                                    rol=per.get("rol"),
                                    direccion=per.get("direccion"),
                                    telefono=per.get("telefono"),
                                    confianza=per.get("confianza", 0.5)
                                )
                                db.add(persona)
                                personas_guardadas += 1
                            except Exception as e:
                                logger.error(f"Error guardando persona '{nombre}': {e}")
                        
                        db.commit()
                        logger.info(f"✅ Personas guardadas: {personas_guardadas} de {len(resultado_analisis['personas'])} (rechazadas: {personas_rechazadas})")
                    
                    # Guardar otras entidades (lugares, fechas, etc.)
                    # ... (código existente para otras entidades)
                    
                    analisis_time = time.time() - analisis_start
                    logger.info(f"✅ Análisis NLP completado en {analisis_time:.1f} segundos")
                else:
                    logger.warning("No hay texto útil para analizar")
                    
            except Exception as e:
                logger.error(f"Error en análisis NLP: {e}")
                # No fallar todo el proceso si falla el análisis
            
            # Actualizar estado final del tomo
            tomo.estado = 'completado'
            tomo.fecha_procesamiento = datetime.now()
            db.commit()
            
            return {
                'success': True,
                'total_pages': total_pages,
                'processed_pages': final_count,
                'errors': total_errors,
                'processing_time': processing_time,
                'pages_per_second': final_count / processing_time if processing_time > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error en procesamiento OCR completo: {e}")
            tomo.estado_ocr = 'error'
            tomo.error_ocr = str(e)
            db.commit()
            raise
    
    def get_processing_stats(self, db: Session, tomo_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas detalladas del procesamiento OCR"""
        try:
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
            if not tomo:
                return {'error': 'Tomo no encontrado'}
            
            contenidos = db.query(ContenidoOCR).filter(ContenidoOCR.tomo_id == tomo_id).all()
            
            if not contenidos:
                return {
                    'tomo_id': tomo_id,
                    'estado': 'sin_procesar',
                    'total_pages': tomo.numero_paginas or 0,
                    'processed_pages': 0,
                    'completion_percentage': 0
                }
            
            # Análisis de motores utilizados
            motors = {}
            total_confidence = 0
            error_pages = 0
            
            for contenido in contenidos:
                # Obtener motor desde datos_adicionales si existe
                motor = 'tesseract'
                if contenido.datos_adicionales and isinstance(contenido.datos_adicionales, dict):
                    motor = contenido.datos_adicionales.get('motor', 'tesseract')
                
                motors[motor] = motors.get(motor, 0) + 1
                
                if contenido.confianza:
                    total_confidence += contenido.confianza
                
                if motor == 'error':
                    error_pages += 1
            
            avg_confidence = total_confidence / len(contenidos) if contenidos else 0
            completion_percentage = (len(contenidos) / max(tomo.numero_paginas, 1)) * 100
            
            return {
                'tomo_id': tomo_id,
                'estado': tomo.estado_ocr,
                'total_pages': tomo.numero_paginas,
                'processed_pages': len(contenidos),
                'completion_percentage': round(completion_percentage, 1),
                'avg_confidence': round(avg_confidence, 1),
                'error_pages': error_pages,
                'motors_used': motors,
                'progreso_ocr': tomo.progreso_ocr
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas OCR: {e}")
            return {'error': str(e)}