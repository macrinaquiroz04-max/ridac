"""
📄 SERVICIO OCR ESTILO PDF24 - ULTRA PROFESIONAL
Implementa todas las características avanzadas de PDF24:
- Auto-rotación inteligente
- Alineación automática de páginas
- Eliminación de texto existente (re-OCR)
- Modelos de velocidad configurables
- DPI optimizado automáticamente
- Procesamiento por lotes masivo
"""

import os
import io
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import fitz  # PyMuPDF
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile

logger = logging.getLogger("ridac_ocr")

class OCRSpeed(Enum):
    """Modelos de velocidad como PDF24"""
    FAST = "fast"           # Rápido - menos precisión
    BALANCED = "balanced"   # Balanceado - equilibrio
    ACCURATE = "accurate"   # Preciso - máxima calidad

class OCRLanguage(Enum):
    """Idiomas soportados"""
    SPANISH = "spa"
    ENGLISH = "eng"
    SPANISH_ENGLISH = "spa+eng"

@dataclass
class PDF24OCRConfig:
    """Configuración estilo PDF24"""
    speed_model: OCRSpeed = OCRSpeed.FAST
    language: OCRLanguage = OCRLanguage.SPANISH
    dpi: int = 300
    auto_rotate: bool = True
    auto_align: bool = True
    remove_existing_text: bool = True
    skip_blank_pages: bool = True
    workers: int = 2
    output_format: str = "searchable_pdf"  # text, searchable_pdf, both

@dataclass
class PDF24PageResult:
    """Resultado de procesamiento de página estilo PDF24"""
    page_number: int
    text_content: str
    confidence: float
    processing_time_ms: int
    rotation_applied: float
    alignment_applied: bool
    dpi_used: int
    model_used: str
    word_count: int
    character_count: int
    blank_page: bool
    errors: List[str]

class PDF24OCRService:
    """Servicio OCR profesional estilo PDF24"""
    
    def __init__(self):
        self.config = PDF24OCRConfig()
        self.temp_dir = tempfile.gettempdir()
        
        # Configuraciones de Tesseract por modelo de velocidad
        self.tesseract_configs = {
            OCRSpeed.FAST: {
                'config': '--oem 3 --psm 6 -c tessedit_create_hocr=0 -c tessedit_create_pdf=0',
                'timeout': 30,
                'description': 'Modelo rápido - optimizado para velocidad'
            },
            OCRSpeed.BALANCED: {
                'config': '--oem 3 --psm 6 -c preserve_interword_spaces=1',
                'timeout': 60,
                'description': 'Modelo balanceado - equilibrio velocidad/precisión'
            },
            OCRSpeed.ACCURATE: {
                'config': '--oem 3 --psm 6 -c preserve_interword_spaces=1 -c textord_heavy_nr=1',
                'timeout': 120,
                'description': 'Modelo preciso - máxima calidad'
            }
        }
        
        logger.info("🚀 PDF24OCRService inicializado")
    
    def process_document_pdf24_style(self, pdf_path: str, 
                                   config: Optional[PDF24OCRConfig] = None) -> Dict[str, Any]:
        """
        Procesar documento completo estilo PDF24
        """
        if config:
            self.config = config
        
        start_time = time.time()
        
        try:
            # Abrir documento PDF
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            logger.info(f"📄 Procesando documento PDF24: {total_pages} páginas")
            logger.info(f"⚙️ Configuración: {self.config.speed_model.value}, DPI: {self.config.dpi}")
            
            # Procesar páginas en paralelo
            results = self._process_pages_parallel(doc, total_pages)
            
            # Generar estadísticas finales
            stats = self._generate_statistics(results, time.time() - start_time)
            
            # Crear archivo de salida si se requiere
            output_files = self._create_output_files(results, pdf_path) if self.config.output_format != "text" else {}
            
            doc.close()
            
            return {
                'success': True,
                'total_pages': total_pages,
                'processed_pages': len([r for r in results if not r.blank_page]),
                'blank_pages': len([r for r in results if r.blank_page]),
                'results': results,
                'statistics': stats,
                'output_files': output_files,
                'config_used': {
                    'speed_model': self.config.speed_model.value,
                    'language': self.config.language.value,
                    'dpi': self.config.dpi,
                    'auto_rotate': self.config.auto_rotate,
                    'auto_align': self.config.auto_align
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando documento PDF24: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    def _process_pages_parallel(self, doc: fitz.Document, total_pages: int) -> List[PDF24PageResult]:
        """Procesar páginas en paralelo como PDF24"""
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
            # Crear tareas para cada página
            futures = {}
            
            for page_num in range(total_pages):
                future = executor.submit(self._process_single_page, doc, page_num)
                futures[future] = page_num
            
            # Recopilar resultados
            completed = 0
            for future in as_completed(futures):
                page_num = futures[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    completed += 1
                    
                    # Log de progreso cada 10 páginas o al final
                    if completed % 10 == 0 or completed == total_pages:
                        progress = (completed / total_pages) * 100
                        logger.info(f"📊 Progreso PDF24: {completed}/{total_pages} ({progress:.1f}%)")
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando página {page_num + 1}: {e}")
                    # Crear resultado de error
                    error_result = PDF24PageResult(
                        page_number=page_num + 1,
                        text_content="",
                        confidence=0.0,
                        processing_time_ms=0,
                        rotation_applied=0.0,
                        alignment_applied=False,
                        dpi_used=self.config.dpi,
                        model_used=self.config.speed_model.value,
                        word_count=0,
                        character_count=0,
                        blank_page=True,
                        errors=[str(e)]
                    )
                    results.append(error_result)
        
        # Ordenar resultados por número de página
        results.sort(key=lambda x: x.page_number)
        
        return results
    
    def _process_single_page(self, doc: fitz.Document, page_num: int) -> PDF24PageResult:
        """Procesar una página individual estilo PDF24"""
        
        start_time = time.time()
        errors = []
        
        try:
            # Obtener página
            page = doc.load_page(page_num)
            
            # Renderizar página a imagen con DPI configurado
            mat = fitz.Matrix(self.config.dpi / 72.0, self.config.dpi / 72.0)
            pix = page.get_pixmap(matrix=mat)
            
            # Convertir a PIL Image
            img_data = pix.tobytes("ppm")
            image = Image.open(io.BytesIO(img_data))
            
            # 🔄 AUTO-ROTACIÓN (como PDF24)
            rotation_applied = 0.0
            if self.config.auto_rotate:
                image, rotation_applied = self._auto_rotate_page(image)
                if abs(rotation_applied) > 0.5:
                    logger.debug(f"📄 Página {page_num + 1}: Rotada {rotation_applied:.1f}°")
            
            # 📐 AUTO-ALINEACIÓN (como PDF24)
            alignment_applied = False
            if self.config.auto_align:
                image, alignment_applied = self._auto_align_page(image)
                if alignment_applied:
                    logger.debug(f"📄 Página {page_num + 1}: Alineación aplicada")
            
            # 🗑️ ELIMINAR TEXTO EXISTENTE (como PDF24)
            if self.config.remove_existing_text:
                image = self._remove_existing_text(image)
            
            # ❓ DETECTAR PÁGINA EN BLANCO
            is_blank = self._is_blank_page(image)
            
            if is_blank and self.config.skip_blank_pages:
                return PDF24PageResult(
                    page_number=page_num + 1,
                    text_content="",
                    confidence=0.0,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    rotation_applied=rotation_applied,
                    alignment_applied=alignment_applied,
                    dpi_used=self.config.dpi,
                    model_used=self.config.speed_model.value,
                    word_count=0,
                    character_count=0,
                    blank_page=True,
                    errors=[]
                )
            
            # 🔤 EXTRACCIÓN OCR CON MODELO CONFIGURADO
            text_content, confidence = self._extract_text_with_model(image)
            
            # 📊 ESTADÍSTICAS
            word_count = len(text_content.split()) if text_content else 0
            character_count = len(text_content) if text_content else 0
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return PDF24PageResult(
                page_number=page_num + 1,
                text_content=text_content,
                confidence=confidence,
                processing_time_ms=processing_time_ms,
                rotation_applied=rotation_applied,
                alignment_applied=alignment_applied,
                dpi_used=self.config.dpi,
                model_used=self.config.speed_model.value,
                word_count=word_count,
                character_count=character_count,
                blank_page=is_blank,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"❌ Error procesando página {page_num + 1}: {e}")
            return PDF24PageResult(
                page_number=page_num + 1,
                text_content="",
                confidence=0.0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                rotation_applied=0.0,
                alignment_applied=False,
                dpi_used=self.config.dpi,
                model_used=self.config.speed_model.value,
                word_count=0,
                character_count=0,
                blank_page=True,
                errors=[str(e)]
            )
    
    def _auto_rotate_page(self, image: Image.Image) -> Tuple[Image.Image, float]:
        """Auto-rotación inteligente como PDF24"""
        
        try:
            # Convertir a OpenCV
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Detectar líneas de texto usando transformada de Hough
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for line in lines[:20]:  # Solo primeras 20 líneas
                    rho, theta = line[0]  # Desempaquetar correctamente
                    angle = np.degrees(theta) - 90
                    if -45 <= angle <= 45:  # Filtrar ángulos razonables
                        angles.append(angle)
                
                if angles:
                    # Usar mediana para evitar outliers
                    rotation_angle = np.median(angles)
                    
                    # Solo rotar si el ángulo es significativo
                    if abs(rotation_angle) > 0.5:
                        rotated = image.rotate(-rotation_angle, expand=True, fillcolor='white')
                        return rotated, rotation_angle
            
            return image, 0.0
            
        except Exception as e:
            logger.warning(f"⚠️ Error en auto-rotación: {e}")
            return image, 0.0
    
    def _auto_align_page(self, image: Image.Image) -> Tuple[Image.Image, bool]:
        """Auto-alineación como PDF24"""
        
        try:
            # Convertir a OpenCV
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Detectar bordes del documento
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Buscar el contorno rectangular más grande (el documento)
            for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Si es un cuadrilátero y es suficientemente grande
                if len(approx) == 4 and cv2.contourArea(contour) > (image.width * image.height * 0.1):
                    # Aplicar corrección de perspectiva
                    corrected = self._correct_perspective(cv_image, approx.reshape(4, 2))
                    if corrected is not None:
                        corrected_pil = Image.fromarray(cv2.cvtColor(corrected, cv2.COLOR_BGR2RGB))
                        return corrected_pil, True
            
            return image, False
            
        except Exception as e:
            logger.warning(f"⚠️ Error en auto-alineación: {e}")
            return image, False
    
    def _correct_perspective(self, image: np.ndarray, corners: np.ndarray) -> Optional[np.ndarray]:
        """Corregir perspectiva del documento"""
        
        try:
            # Ordenar esquinas: top-left, top-right, bottom-right, bottom-left
            rect = self._order_corners(corners)
            
            # Calcular dimensiones del rectángulo corregido
            (tl, tr, br, bl) = rect
            widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
            widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
            maxWidth = max(int(widthA), int(widthB))
            
            heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
            heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
            maxHeight = max(int(heightA), int(heightB))
            
            # Puntos de destino
            dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")
            
            # Aplicar transformación de perspectiva
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
            
            return warped
            
        except Exception as e:
            logger.warning(f"⚠️ Error corrigiendo perspectiva: {e}")
            return None
    
    def _order_corners(self, pts: np.ndarray) -> np.ndarray:
        """Ordenar esquinas en orden correcto"""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Top-left: suma mínima, bottom-right: suma máxima
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # Top-right: diferencia mínima, bottom-left: diferencia máxima
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def _remove_existing_text(self, image: Image.Image) -> Image.Image:
        """Eliminar texto existente como PDF24"""
        
        try:
            # Convertir a OpenCV
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Detectar áreas de texto usando morfología
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            
            # Binarización
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Operaciones morfológicas para limpiar
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
            
            # Convertir de vuelta a PIL
            cleaned_pil = Image.fromarray(cleaned)
            
            return cleaned_pil
            
        except Exception as e:
            logger.warning(f"⚠️ Error eliminando texto existente: {e}")
            return image
    
    def _is_blank_page(self, image: Image.Image) -> bool:
        """Detectar si la página está en blanco"""
        
        try:
            # Convertir a escala de grises
            gray = image.convert('L')
            
            # Calcular histograma
            histogram = gray.histogram()
            
            # Si más del 95% de los píxeles son blancos/claros, es página en blanco
            total_pixels = sum(histogram)
            white_pixels = sum(histogram[200:])  # Píxeles claros
            
            white_percentage = (white_pixels / total_pixels) * 100
            
            return white_percentage > 95
            
        except Exception as e:
            logger.warning(f"⚠️ Error detectando página en blanco: {e}")
            return False
    
    def _extract_text_with_model(self, image: Image.Image) -> Tuple[str, float]:
        """
        Extraer texto usando el modelo configurado con mejoras Google Lens-style.
        Aplica preprocesamiento avanzado ANTES de OCR para máxima calidad.
        """
        
        model_config = self.tesseract_configs[self.config.speed_model]
        
        try:
            # 🎯 APLICAR MEJORAS AVANZADAS GOOGLE LENS-STYLE
            try:
                from app.services.advanced_image_enhancer import create_enhancer
                
                # Crear enhancer con calidad ULTRA para fiscalía
                enhancer = create_enhancer(quality='ultra')
                
                # Aplicar pipeline completo de mejoras
                enhanced_image = enhancer.enhance_pil_image(image)
                
                logger.debug("✨ Imagen mejorada con Google Lens-style enhancement")
                
            except Exception as e:
                logger.warning(f"⚠️ Error en enhancer, usando imagen original: {e}")
                enhanced_image = image
            
            # Configurar idioma
            lang = self.config.language.value
            
            # Extraer texto con imagen mejorada
            text = pytesseract.image_to_string(
                enhanced_image, 
                lang=lang, 
                config=model_config['config'],
                timeout=model_config['timeout']
            )
            
            # Calcular confianza aproximada
            if text.strip():
                # Obtener datos de confianza de Tesseract
                try:
                    data = pytesseract.image_to_data(enhanced_image, lang=lang, config=model_config['config'], output_type=pytesseract.Output.DICT)
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    confidence = sum(confidences) / len(confidences) if confidences else 0
                except:
                    # Confianza aproximada basada en caracteres alfanuméricos
                    confidence = len([c for c in text if c.isalnum()]) / max(len(text), 1) * 100
            else:
                confidence = 0.0
            
            return text.strip(), confidence
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo texto: {e}")
            return "", 0.0
    
    def _generate_statistics(self, results: List[PDF24PageResult], total_time: float) -> Dict[str, Any]:
        """Generar estadísticas finales como PDF24"""
        
        processed_pages = [r for r in results if not r.blank_page]
        blank_pages = [r for r in results if r.blank_page]
        
        # Estadísticas de tiempo
        total_processing_time = sum(r.processing_time_ms for r in results) / 1000  # en segundos
        avg_time_per_page = total_processing_time / len(results) if results else 0
        
        # Estadísticas de contenido
        total_words = sum(r.word_count for r in processed_pages)
        total_characters = sum(r.character_count for r in processed_pages)
        avg_confidence = sum(r.confidence for r in processed_pages) / len(processed_pages) if processed_pages else 0
        
        # Estadísticas de transformaciones
        rotated_pages = len([r for r in results if abs(r.rotation_applied) > 0.5])
        aligned_pages = len([r for r in results if r.alignment_applied])
        
        return {
            'total_pages': len(results),
            'processed_pages': len(processed_pages),
            'blank_pages': len(blank_pages),
            'total_time_seconds': total_time,
            'processing_time_seconds': total_processing_time,
            'avg_time_per_page': avg_time_per_page,
            'pages_per_minute': (len(results) / total_time) * 60 if total_time > 0 else 0,
            'total_words': total_words,
            'total_characters': total_characters,
            'avg_confidence': avg_confidence,
            'rotated_pages': rotated_pages,
            'aligned_pages': aligned_pages,
            'model_used': self.config.speed_model.value,
            'dpi_used': self.config.dpi,
            'language_used': self.config.language.value
        }
    
    def _create_output_files(self, results: List[PDF24PageResult], original_pdf: str) -> Dict[str, str]:
        """Crear archivos de salida como PDF24"""
        
        output_files = {}
        
        try:
            base_name = os.path.splitext(os.path.basename(original_pdf))[0]
            
            # Archivo de texto
            if self.config.output_format in ["text", "both"]:
                text_file = os.path.join(self.temp_dir, f"{base_name}_ocr.txt")
                with open(text_file, 'w', encoding='utf-8') as f:
                    for result in results:
                        if not result.blank_page and result.text_content:
                            f.write(f"--- PÁGINA {result.page_number} ---\n")
                            f.write(result.text_content)
                            f.write("\n\n")
                
                output_files['text_file'] = text_file
            
            # TODO: Implementar PDF con texto buscable
            # if self.config.output_format in ["searchable_pdf", "both"]:
            #     searchable_pdf = self._create_searchable_pdf(results, original_pdf)
            #     output_files['searchable_pdf'] = searchable_pdf
            
        except Exception as e:
            logger.error(f"❌ Error creando archivos de salida: {e}")
        
        return output_files

# Instancia global del servicio PDF24
pdf24_ocr_service = PDF24OCRService()

def process_document_pdf24_style(pdf_path: str, speed: str = "fast", 
                                dpi: int = 300, auto_rotate: bool = True) -> Dict[str, Any]:
    """
    Función de integración para procesar documento estilo PDF24
    """
    
    # Configurar según parámetros
    config = PDF24OCRConfig(
        speed_model=OCRSpeed(speed),
        dpi=dpi,
        auto_rotate=auto_rotate,
        auto_align=True,
        remove_existing_text=True,
        skip_blank_pages=True,
        workers=2
    )
    
    return pdf24_ocr_service.process_document_pdf24_style(pdf_path, config)