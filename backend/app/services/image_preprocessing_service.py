# backend/app/services/image_preprocessing_service.py

import warnings
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import io
from typing import Tuple, Optional
from app.utils.logger import logger

# Suprimir advertencias de OpenCV y PIL
warnings.filterwarnings("ignore", category=FutureWarning, module="cv2")
warnings.filterwarnings("ignore", category=UserWarning, module="PIL")

class ImagePreprocessingService:
    """Servicio de preprocesamiento de imágenes para mejorar precisión OCR"""

    @staticmethod
    def preprocess_for_ocr(image: Image.Image, method: str = "auto") -> Image.Image:
        """
        Preprocesa imagen para optimizar OCR
        
        Args:
            image: Imagen PIL a procesar
            method: Método de preprocesamiento ('auto', 'scan', 'photo', 'document')
        
        Returns:
            Imagen preprocessada optimizada para OCR
        """
        try:
            # Convertir a array numpy para OpenCV
            img_array = np.array(image)
            
            # Detectar automáticamente el mejor método si es 'auto'
            if method == "auto":
                method = ImagePreprocessingService._detect_best_method(img_array)
            
            # Aplicar método específico
            if method == "document":
                processed = ImagePreprocessingService._preprocess_document(img_array)
            elif method == "scan":
                processed = ImagePreprocessingService._preprocess_scan(img_array)
            elif method == "photo":
                processed = ImagePreprocessingService._preprocess_photo(img_array)
            else:
                processed = ImagePreprocessingService._preprocess_generic(img_array)
            
            # Convertir de vuelta a PIL
            return Image.fromarray(processed)
            
        except Exception as e:
            logger.warning(f"Error en preprocesamiento, usando imagen original: {e}")
            return image

    @staticmethod
    def _detect_best_method(img_array: np.ndarray) -> str:
        """Detecta automáticamente el mejor método de preprocesamiento"""
        # Convertir a escala de grises si es necesario
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        # Calcular estadísticas de la imagen
        mean_intensity = np.mean(gray)
        std_intensity = np.std(gray)
        
        # Detectar edges para determinar nitidez
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
        
        # Decidir método basado en características
        if edge_density > 0.1 and std_intensity > 50:
            return "photo"  # Imagen con mucho detalle, probablemente foto
        elif mean_intensity > 200:
            return "scan"   # Imagen muy clara, probablemente escaneo
        else:
            return "document"  # Documento estándar

    @staticmethod
    def _preprocess_document(img_array: np.ndarray) -> np.ndarray:
        """Preprocesamiento optimizado para documentos estándar"""
        # Convertir a escala de grises
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        # Normalizar iluminación
        gray = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)
        
        # Reducir ruido
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Binarización adaptativa
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Morfología para limpiar
        kernel = np.ones((1, 1), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return binary

    @staticmethod
    def _preprocess_scan(img_array: np.ndarray) -> np.ndarray:
        """Preprocesamiento para escaneos de alta calidad"""
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        # Mejorar contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Binarización simple por umbral
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary

    @staticmethod
    def _preprocess_photo(img_array: np.ndarray) -> np.ndarray:
        """Preprocesamiento para fotos de documentos"""
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        # Corrección de iluminación más agresiva
        # Usar blur para estimar fondo
        blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=33, sigmaY=33)
        divide = cv2.divide(gray, blur, scale=255)
        
        # Mejorar contraste
        enhanced = cv2.convertScaleAbs(divide, alpha=1.5, beta=0)
        
        # Reducir ruido
        denoised = cv2.medianBlur(enhanced, 3)
        
        # Binarización adaptativa
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        return binary

    @staticmethod
    def _preprocess_generic(img_array: np.ndarray) -> np.ndarray:
        """Preprocesamiento genérico para casos no específicos"""
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array.copy()
        
        # Mejorar contraste ligeramente
        enhanced = cv2.convertScaleAbs(gray, alpha=1.1, beta=5)
        
        # Reducir ruido suave
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        return denoised

    @staticmethod
    def enhance_image_quality(image: Image.Image, 
                            sharpness: float = 1.2,
                            contrast: float = 1.1,
                            brightness: float = 1.0) -> Image.Image:
        """Mejora la calidad general de la imagen"""
        try:
            # Aplicar mejoras PIL
            if sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(sharpness)
            
            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(contrast)
            
            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(brightness)
            
            return image
            
        except Exception as e:
            logger.warning(f"Error mejorando calidad de imagen: {e}")
            return image

    @staticmethod
    def correct_skew(image: Image.Image) -> Image.Image:
        """Corrige la inclinación del documento"""
        try:
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array.copy()
            
            # Detectar líneas usando transformada de Hough
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                # Calcular ángulo promedio de las líneas horizontales
                angles = []
                for rho, theta in lines[:, 0]:
                    angle = theta * 180 / np.pi
                    # Filtrar líneas cercanas a horizontal
                    if 85 <= angle <= 95 or -5 <= angle <= 5:
                        angles.append(angle if angle <= 45 else angle - 90)
                
                if angles:
                    # Usar ángulo mediano para robustez
                    skew_angle = np.median(angles)
                    
                    # Corregir solo si el ángulo es significativo
                    if abs(skew_angle) > 0.5:
                        height, width = gray.shape
                        center = (width // 2, height // 2)
                        
                        # Crear matriz de rotación
                        rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
                        
                        # Aplicar rotación
                        if len(img_array.shape) == 3:
                            corrected = cv2.warpAffine(img_array, rotation_matrix, (width, height),
                                                     flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                        else:
                            corrected = cv2.warpAffine(gray, rotation_matrix, (width, height),
                                                     flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                        
                        return Image.fromarray(corrected)
            
            return image
            
        except Exception as e:
            logger.warning(f"Error corrigiendo inclinación: {e}")
            return image

    @staticmethod
    def remove_noise(image: Image.Image, method: str = "bilateral") -> Image.Image:
        """Elimina ruido de la imagen"""
        try:
            img_array = np.array(image)
            
            if method == "bilateral":
                # Filtro bilateral preserva edges
                if len(img_array.shape) == 3:
                    denoised = cv2.bilateralFilter(img_array, 9, 75, 75)
                else:
                    denoised = cv2.bilateralFilter(img_array, 9, 75, 75)
            elif method == "gaussian":
                denoised = cv2.GaussianBlur(img_array, (5, 5), 0)
            elif method == "median":
                denoised = cv2.medianBlur(img_array, 5)
            else:  # non_local_means
                if len(img_array.shape) == 3:
                    denoised = cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)
                else:
                    denoised = cv2.fastNlMeansDenoising(img_array, None, 10, 7, 21)
            
            return Image.fromarray(denoised)
            
        except Exception as e:
            logger.warning(f"Error eliminando ruido: {e}")
            return image