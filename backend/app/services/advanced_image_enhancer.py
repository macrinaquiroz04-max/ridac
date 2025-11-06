"""
🎯 ADVANCED IMAGE ENHANCER - ESTILO GOOGLE LENS
=====================================================
Preprocesamiento avanzado de imágenes escaneadas para OCR de máxima calidad.
Implementa técnicas usadas por Google Lens para obtener texto perfecto.

Autor: Sistema OCR FGJ-CDMX
Fecha: Octubre 2025
"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class AdvancedImageEnhancer:
    """
    Mejorador avanzado de imágenes para OCR de alta calidad.
    
    Aplica múltiples técnicas de procesamiento de imagen:
    - Super-resolución con interpolación bicúbica y Lanczos
    - Reducción de ruido con filtros bilaterales y Non-Local Means
    - Corrección automática de perspectiva y rotación
    - Eliminación de sombras y corrección de iluminación no uniforme
    - Mejora de bordes y nitidez adaptativa
    - Binarización inteligente con múltiples métodos
    """
    
    def __init__(self, 
                 target_dpi: int = 300,
                 aggressive_enhancement: bool = True,
                 preserve_color: bool = False):
        """
        Inicializar el mejorador de imágenes.
        
        Args:
            target_dpi: DPI objetivo para super-resolución (300-600 recomendado)
            aggressive_enhancement: Aplicar mejoras agresivas para imágenes muy degradadas
            preserve_color: Mantener información de color (útil para algunos documentos)
        """
        self.target_dpi = target_dpi
        self.aggressive = aggressive_enhancement
        self.preserve_color = preserve_color
        
        logger.info(f"🎯 AdvancedImageEnhancer inicializado (DPI={target_dpi}, aggressive={aggressive_enhancement})")
    
    def enhance_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """
        Pipeline completo de mejora de imagen para OCR.
        
        Args:
            image: Imagen de entrada (formato OpenCV BGR o escala de grises)
            
        Returns:
            Imagen mejorada optimizada para OCR
        """
        logger.debug("🔍 Iniciando pipeline de mejora de imagen")
        
        # 1. Corrección de orientación y perspectiva
        image = self._auto_correct_orientation(image)
        image = self._correct_perspective(image)
        
        # 2. Super-resolución (aumentar calidad)
        image = self._upscale_image(image)
        
        # 3. Reducción de ruido avanzada
        image = self._advanced_denoise(image)
        
        # 4. Corrección de iluminación
        image = self._fix_illumination(image)
        
        # 5. Mejora de contraste adaptativo
        image = self._enhance_contrast_adaptive(image)
        
        # 6. Mejora de bordes y nitidez
        image = self._sharpen_image(image)
        
        # 7. Binarización inteligente
        image = self._smart_binarization(image)
        
        logger.debug("✅ Pipeline de mejora completado")
        return image
    
    def _auto_correct_orientation(self, image: np.ndarray) -> np.ndarray:
        """
        Detecta y corrige la rotación automáticamente usando líneas de texto.
        Similar a la detección de orientación de Google Lens.
        """
        try:
            # Convertir a escala de grises si es necesario
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Detectar bordes
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Detectar líneas con transformada de Hough
            lines = cv2.HoughLines(edges, 1, np.pi/180, 200)
            
            if lines is not None:
                # Calcular ángulos de las líneas
                angles = []
                for rho, theta in lines[:, 0]:
                    angle = np.degrees(theta) - 90
                    angles.append(angle)
                
                # Tomar la mediana de los ángulos
                median_angle = np.median(angles)
                
                # Corregir solo si el ángulo es significativo
                if abs(median_angle) > 0.5:
                    logger.debug(f"🔄 Corrigiendo rotación: {median_angle:.2f}°")
                    (h, w) = image.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                    image = cv2.warpAffine(image, M, (w, h), 
                                          flags=cv2.INTER_CUBIC,
                                          borderMode=cv2.BORDER_REPLICATE)
            
            return image
        except Exception as e:
            logger.warning(f"⚠️ Error en corrección de orientación: {e}")
            return image
    
    def _correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """
        Corrige la perspectiva de documentos escaneados en ángulo.
        Detecta las esquinas del documento y aplica transformación perspectiva.
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Detectar bordes
            edges = cv2.Canny(gray, 50, 150)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Buscar el contorno más grande (probablemente el documento)
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Aproximar el contorno a un polígono
                epsilon = 0.02 * cv2.arcLength(largest_contour, True)
                approx = cv2.approxPolyDP(largest_contour, epsilon, True)
                
                # Si es un cuadrilátero, aplicar transformación de perspectiva
                if len(approx) == 4:
                    logger.debug("📐 Aplicando corrección de perspectiva")
                    pts = approx.reshape(4, 2)
                    rect = self._order_points(pts)
                    (tl, tr, br, bl) = rect
                    
                    # Calcular dimensiones del documento corregido
                    widthA = np.linalg.norm(br - bl)
                    widthB = np.linalg.norm(tr - tl)
                    maxWidth = max(int(widthA), int(widthB))
                    
                    heightA = np.linalg.norm(tr - br)
                    heightB = np.linalg.norm(tl - bl)
                    maxHeight = max(int(heightA), int(heightB))
                    
                    # Puntos de destino
                    dst = np.array([
                        [0, 0],
                        [maxWidth - 1, 0],
                        [maxWidth - 1, maxHeight - 1],
                        [0, maxHeight - 1]
                    ], dtype="float32")
                    
                    # Calcular matriz de transformación
                    M = cv2.getPerspectiveTransform(rect, dst)
                    image = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
            
            return image
        except Exception as e:
            logger.warning(f"⚠️ Error en corrección de perspectiva: {e}")
            return image
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Ordena puntos en orden: top-left, top-right, bottom-right, bottom-left"""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Top-left tendrá la suma más pequeña, bottom-right la más grande
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # Top-right tendrá la diferencia más pequeña, bottom-left la más grande
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def _upscale_image(self, image: np.ndarray, scale_factor: float = 2.0) -> np.ndarray:
        """
        Super-resolución usando interpolación Lanczos (mejor que bicúbica).
        Aumenta la resolución para mejorar la detección de caracteres pequeños.
        """
        try:
            # Calcular nuevas dimensiones
            height, width = image.shape[:2]
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            # Usar INTER_LANCZOS4 para máxima calidad
            upscaled = cv2.resize(image, (new_width, new_height), 
                                 interpolation=cv2.INTER_LANCZOS4)
            
            logger.debug(f"📈 Imagen escalada: {width}x{height} → {new_width}x{new_height}")
            return upscaled
        except Exception as e:
            logger.warning(f"⚠️ Error en upscaling: {e}")
            return image
    
    def _advanced_denoise(self, image: np.ndarray) -> np.ndarray:
        """
        Reducción de ruido agresiva combinando múltiples técnicas.
        Usa Non-Local Means Denoising + filtro bilateral.
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Non-Local Means Denoising (muy efectivo para ruido de escaneo)
            if self.aggressive:
                denoised = cv2.fastNlMeansDenoising(gray, None, h=10, 
                                                   templateWindowSize=7,
                                                   searchWindowSize=21)
            else:
                denoised = cv2.fastNlMeansDenoising(gray, None, h=7,
                                                   templateWindowSize=7,
                                                   searchWindowSize=21)
            
            # Filtro bilateral para suavizar preservando bordes
            denoised = cv2.bilateralFilter(denoised, 9, 75, 75)
            
            logger.debug("🧹 Reducción de ruido aplicada")
            return denoised
        except Exception as e:
            logger.warning(f"⚠️ Error en denoising: {e}")
            return image
    
    def _fix_illumination(self, image: np.ndarray) -> np.ndarray:
        """
        Corrige iluminación no uniforme y elimina sombras.
        Muy útil para documentos escaneados con iluminación irregular.
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Estimar el fondo con un desenfoque grande
            background = cv2.GaussianBlur(gray, (0, 0), sigmaX=20, sigmaY=20)
            
            # Restar el fondo para normalizar la iluminación
            # Añadir 128 para evitar valores negativos
            normalized = cv2.divide(gray, background, scale=255)
            
            logger.debug("💡 Corrección de iluminación aplicada")
            return normalized
        except Exception as e:
            logger.warning(f"⚠️ Error en corrección de iluminación: {e}")
            return image
    
    def _enhance_contrast_adaptive(self, image: np.ndarray) -> np.ndarray:
        """
        CLAHE (Contrast Limited Adaptive Histogram Equalization).
        Mejora el contraste local sin sobre-amplificar el ruido.
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # CLAHE con parámetros optimizados para documentos
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            logger.debug("🎨 Mejora de contraste adaptativo aplicada")
            return enhanced
        except Exception as e:
            logger.warning(f"⚠️ Error en mejora de contraste: {e}")
            return image
    
    def _sharpen_image(self, image: np.ndarray) -> np.ndarray:
        """
        Mejora la nitidez usando unsharp masking.
        Hace los bordes de las letras más definidos.
        """
        try:
            # Kernel de nitidez
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            
            sharpened = cv2.filter2D(image, -1, kernel)
            
            # Combinar con la imagen original para evitar sobre-nitidez
            if self.aggressive:
                result = cv2.addWeighted(image, 0.3, sharpened, 0.7, 0)
            else:
                result = cv2.addWeighted(image, 0.5, sharpened, 0.5, 0)
            
            logger.debug("✨ Mejora de nitidez aplicada")
            return result
        except Exception as e:
            logger.warning(f"⚠️ Error en sharpening: {e}")
            return image
    
    def _smart_binarization(self, image: np.ndarray) -> np.ndarray:
        """
        Binarización inteligente combinando múltiples métodos.
        Prueba Otsu y adaptativo, selecciona el mejor resultado.
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Método 1: Otsu (bueno para imágenes uniformes)
            _, binary_otsu = cv2.threshold(gray, 0, 255, 
                                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Método 2: Adaptativo Gaussiano (mejor para iluminación variable)
            binary_adaptive = cv2.adaptiveThreshold(gray, 255,
                                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                   cv2.THRESH_BINARY, 11, 2)
            
            # Método 3: Sauvola (excelente para documentos degradados)
            binary_sauvola = self._sauvola_threshold(gray)
            
            # Seleccionar el mejor resultado basado en análisis de contenido
            # Por ahora, usar adaptativo que es más robusto
            if self.aggressive:
                result = binary_sauvola
            else:
                result = binary_adaptive
            
            # Morfología para limpiar ruido residual
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)
            
            logger.debug("⚫⚪ Binarización inteligente aplicada")
            return result
        except Exception as e:
            logger.warning(f"⚠️ Error en binarización: {e}")
            return image
    
    def _sauvola_threshold(self, image: np.ndarray, window_size: int = 25, 
                          k: float = 0.2) -> np.ndarray:
        """
        Implementación del método de Sauvola para binarización.
        Excelente para documentos con variaciones de iluminación.
        """
        try:
            # Calcular media local
            mean = cv2.boxFilter(image, cv2.CV_32F, (window_size, window_size))
            
            # Calcular desviación estándar local
            mean_sq = cv2.boxFilter(image.astype(np.float32) ** 2, cv2.CV_32F, 
                                   (window_size, window_size))
            std = np.sqrt(mean_sq - mean ** 2)
            
            # Calcular umbral de Sauvola
            R = 128  # Rango dinámico
            threshold = mean * (1 + k * ((std / R) - 1))
            
            # Aplicar umbral
            binary = np.where(image > threshold, 255, 0).astype(np.uint8)
            
            return binary
        except Exception as e:
            logger.warning(f"⚠️ Error en Sauvola: {e}")
            # Fallback a binarización simple
            _, binary = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
            return binary
    
    def enhance_pil_image(self, pil_image: Image.Image) -> Image.Image:
        """
        Variante para procesar imágenes PIL directamente.
        Útil para integración con algunos motores OCR.
        """
        # Convertir PIL a OpenCV
        image_np = np.array(pil_image)
        if len(image_np.shape) == 2:
            image_cv = image_np
        else:
            image_cv = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        # Aplicar mejoras
        enhanced_cv = self.enhance_for_ocr(image_cv)
        
        # Convertir de vuelta a PIL
        if len(enhanced_cv.shape) == 2:
            enhanced_pil = Image.fromarray(enhanced_cv)
        else:
            enhanced_rgb = cv2.cvtColor(enhanced_cv, cv2.COLOR_BGR2RGB)
            enhanced_pil = Image.fromarray(enhanced_rgb)
        
        return enhanced_pil


# Factory function para fácil uso
def create_enhancer(quality: str = 'high') -> AdvancedImageEnhancer:
    """
    Crea un enhancer con configuración predefinida.
    
    Args:
        quality: 'low', 'medium', 'high', 'ultra'
        
    Returns:
        AdvancedImageEnhancer configurado
    """
    configs = {
        'low': {'target_dpi': 150, 'aggressive_enhancement': False},
        'medium': {'target_dpi': 200, 'aggressive_enhancement': False},
        'high': {'target_dpi': 300, 'aggressive_enhancement': True},
        'ultra': {'target_dpi': 600, 'aggressive_enhancement': True}
    }
    
    config = configs.get(quality, configs['high'])
    return AdvancedImageEnhancer(**config)
