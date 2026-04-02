"""
📸 SERVICIO DE PREPROCESAMIENTO AVANZADO DE IMÁGENES
OpenCV + técnicas avanzadas para documentos legales escaneados
"""

import warnings
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import logging
from typing import Tuple, Optional, List, Dict
import math
from dataclasses import dataclass

# Suprimir advertencias de OpenCV sobre GFPGAN
warnings.filterwarnings("ignore", category=FutureWarning, module="cv2")
warnings.filterwarnings("ignore", message=".*GFPGAN.*")

logger = logging.getLogger("ridac_ocr")

@dataclass
class ImageProcessingResult:
    """Resultado del procesamiento de imagen"""
    processed_image: np.ndarray
    original_size: Tuple[int, int]
    processed_size: Tuple[int, int]
    rotation_angle: float
    quality_score: float
    preprocessing_steps: List[str]

class AdvancedImageProcessor:
    """Procesador avanzado de imágenes para OCR optimizado"""
    
    def __init__(self):
        self.debug_mode = False
    
    def process_document_image(self, image: Image.Image, 
                             target_dpi: int = 300) -> ImageProcessingResult:
        """
        Procesamiento completo de imagen de documento legal
        """
        processing_steps = []
        
        try:
            # Convertir PIL a OpenCV
            cv_image = self._pil_to_cv2(image)
            original_size = cv_image.shape[:2]
            
            # 1. Detección y corrección de rotación
            cv_image, rotation_angle = self._auto_rotate_document(cv_image)
            if abs(rotation_angle) > 0.5:
                processing_steps.append(f"Rotación: {rotation_angle:.1f}°")
            
            # 2. Corrección de perspectiva (documentos fotografiados)
            cv_image = self._correct_perspective(cv_image)
            processing_steps.append("Corrección de perspectiva")
            
            # 3. Mejora de contraste y brillo
            cv_image = self._enhance_contrast_brightness(cv_image)
            processing_steps.append("Mejora de contraste")
            
            # 4. Reducción de ruido
            cv_image = self._denoise_document(cv_image)
            processing_steps.append("Reducción de ruido")
            
            # 5. Afilado de texto
            cv_image = self._sharpen_text(cv_image)
            processing_steps.append("Afilado de texto")
            
            # 6. Binarización adaptativa
            cv_image = self._adaptive_binarization(cv_image)
            processing_steps.append("Binarización adaptativa")
            
            # 7. Mejora de DPI si es necesario
            if target_dpi > 150:
                cv_image = self._enhance_resolution(cv_image, target_dpi)
                processing_steps.append(f"Mejora DPI a {target_dpi}")
            
            # Calcular calidad final
            quality_score = self._calculate_image_quality(cv_image)
            
            processed_size = cv_image.shape[:2]
            
            return ImageProcessingResult(
                processed_image=cv_image,
                original_size=original_size,
                processed_size=processed_size,
                rotation_angle=rotation_angle,
                quality_score=quality_score,
                preprocessing_steps=processing_steps
            )
            
        except Exception as e:
            logger.error(f"Error en procesamiento de imagen: {e}")
            # Fallback: procesamiento básico
            cv_image = self._pil_to_cv2(image)
            return ImageProcessingResult(
                processed_image=cv_image,
                original_size=cv_image.shape[:2],
                processed_size=cv_image.shape[:2],
                rotation_angle=0.0,
                quality_score=0.5,
                preprocessing_steps=["Procesamiento básico (error)"]
            )
    
    def _pil_to_cv2(self, pil_image: Image.Image) -> np.ndarray:
        """Convertir imagen PIL a OpenCV"""
        if pil_image.mode == 'RGB':
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        elif pil_image.mode == 'L':
            return np.array(pil_image)
        else:
            # Convertir a RGB primero
            rgb_image = pil_image.convert('RGB')
            return cv2.cvtColor(np.array(rgb_image), cv2.COLOR_RGB2BGR)
    
    def _cv2_to_pil(self, cv_image: np.ndarray) -> Image.Image:
        """Convertir imagen OpenCV a PIL"""
        if len(cv_image.shape) == 3:
            return Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        else:
            return Image.fromarray(cv_image)
    
    def _auto_rotate_document(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detectar y corregir automáticamente la rotación del documento
        """
        try:
            # Convertir a escala de grises si es necesario
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Detección de bordes
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Transformada de Hough para detectar líneas
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for line in lines[:20]:  # Solo primeras 20 líneas
                    rho, theta = line[0]  # Desempaquetar correctamente
                    angle = np.degrees(theta) - 90
                    angles.append(angle)
                
                # Calcular ángulo promedio
                if angles:
                    # Filtrar ángulos extremos
                    angles = [a for a in angles if -45 <= a <= 45]
                    if angles:
                        rotation_angle = np.median(angles)
                        
                        # Solo rotar si el ángulo es significativo
                        if abs(rotation_angle) > 0.5:
                            # Rotar imagen
                            (h, w) = image.shape[:2]
                            center = (w // 2, h // 2)
                            M = cv2.getRotationMatrix2D(center, rotation_angle, 1.0)
                            rotated = cv2.warpAffine(image, M, (w, h), 
                                                   flags=cv2.INTER_CUBIC, 
                                                   borderMode=cv2.BORDER_REPLICATE)
                            return rotated, rotation_angle
            
            return image, 0.0
            
        except Exception as e:
            logger.warning(f"Error en auto-rotación: {e}")
            return image, 0.0
    
    def _correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """
        Corregir perspectiva de documentos fotografiados
        """
        try:
            # Convertir a escala de grises
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Detectar bordes
            edges = cv2.Canny(gray, 50, 150)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Buscar el contorno rectangular más grande (probablemente el documento)
            for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
                # Aproximar contorno
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Si es un cuadrilátero y es suficientemente grande
                if len(approx) == 4 and cv2.contourArea(contour) > 10000:
                    # Ordenar puntos
                    rect = self._order_points(approx.reshape(4, 2))
                    
                    # Calcular dimensiones del documento rectificado
                    (tl, tr, br, bl) = rect
                    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
                    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
                    maxWidth = max(int(widthA), int(widthB))
                    
                    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
                    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
                    maxHeight = max(int(heightA), int(heightB))
                    
                    # Puntos destino
                    dst = np.array([
                        [0, 0],
                        [maxWidth - 1, 0],
                        [maxWidth - 1, maxHeight - 1],
                        [0, maxHeight - 1]
                    ], dtype="float32")
                    
                    # Transformación de perspectiva
                    M = cv2.getPerspectiveTransform(rect, dst)
                    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
                    
                    return warped
            
            return image
            
        except Exception as e:
            logger.warning(f"Error en corrección de perspectiva: {e}")
            return image
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Ordenar puntos en orden: top-left, top-right, bottom-right, bottom-left"""
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
    
    def _enhance_contrast_brightness(self, image: np.ndarray) -> np.ndarray:
        """
        Mejorar contraste y brillo usando CLAHE
        """
        try:
            if len(image.shape) == 3:
                # Convertir a LAB para mejor procesamiento
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                
                # Aplicar CLAHE al canal L
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                cl = clahe.apply(l)
                
                # Recombinar canales
                enhanced = cv2.merge((cl, a, b))
                enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
                
                return enhanced
            else:
                # Escala de grises
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                return clahe.apply(image)
                
        except Exception as e:
            logger.warning(f"Error en mejora de contraste: {e}")
            return image
    
    def _denoise_document(self, image: np.ndarray) -> np.ndarray:
        """
        Reducir ruido preservando el texto
        """
        try:
            if len(image.shape) == 3:
                # Filtro bilateral para color
                return cv2.bilateralFilter(image, 9, 75, 75)
            else:
                # Filtro bilateral para escala de grises
                return cv2.bilateralFilter(image, 9, 75, 75)
                
        except Exception as e:
            logger.warning(f"Error en reducción de ruido: {e}")
            return image
    
    def _sharpen_text(self, image: np.ndarray) -> np.ndarray:
        """
        Afilar texto para mejor OCR
        """
        try:
            # Kernel de afilado
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]])
            
            sharpened = cv2.filter2D(image, -1, kernel)
            
            # Combinar con imagen original para efecto más sutil
            return cv2.addWeighted(image, 0.6, sharpened, 0.4, 0)
            
        except Exception as e:
            logger.warning(f"Error en afilado: {e}")
            return image
    
    def _adaptive_binarization(self, image: np.ndarray) -> np.ndarray:
        """
        Binarización adaptativa para mejor OCR
        """
        try:
            # Convertir a escala de grises si es necesario
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Binarización adaptativa gaussiana
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            return binary
            
        except Exception as e:
            logger.warning(f"Error en binarización: {e}")
            return image
    
    def _enhance_resolution(self, image: np.ndarray, target_dpi: int) -> np.ndarray:
        """
        Mejorar resolución usando interpolación
        """
        try:
            # Calcular factor de escala basado en DPI objetivo
            current_dpi = 150  # Asumimos DPI base
            scale_factor = target_dpi / current_dpi
            
            if scale_factor > 1.0:
                # Redimensionar con interpolación cúbica
                height, width = image.shape[:2]
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                
                return cv2.resize(image, (new_width, new_height), 
                                interpolation=cv2.INTER_CUBIC)
            
            return image
            
        except Exception as e:
            logger.warning(f"Error en mejora de resolución: {e}")
            return image
    
    def _calculate_image_quality(self, image: np.ndarray) -> float:
        """
        Calcular puntuación de calidad de la imagen
        """
        try:
            # Convertir a escala de grises si es necesario
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Calcular varianza del Laplaciano (medida de nitidez)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Normalizar a escala 0-1
            quality_score = min(1.0, laplacian_var / 1000.0)
            
            return quality_score
            
        except Exception as e:
            logger.warning(f"Error calculando calidad: {e}")
            return 0.5

# Instancia global del procesador
advanced_image_processor = AdvancedImageProcessor()

def process_image_for_ocr(pil_image: Image.Image) -> Tuple[Image.Image, Dict]:
    """
    Función de integración para procesar imagen antes del OCR
    """
    result = advanced_image_processor.process_document_image(pil_image)
    
    # Convertir resultado a PIL
    processed_pil = advanced_image_processor._cv2_to_pil(result.processed_image)
    
    # Información de procesamiento
    processing_info = {
        'rotation_angle': result.rotation_angle,
        'quality_score': result.quality_score,
        'processing_steps': result.preprocessing_steps,
        'size_change': f"{result.original_size} → {result.processed_size}"
    }
    
    return processed_pil, processing_info