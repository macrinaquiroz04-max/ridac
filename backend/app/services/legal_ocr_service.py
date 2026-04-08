"""
Servicio de OCR especializado para documentos legales mexicanos
Incluye corrección de abreviaturas y términos jurídicos
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

# OCR
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# PyPDF2 para PDFs con texto
try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# Mejora de imagen (AdvancedImageEnhancer)
try:
    from app.services.advanced_image_enhancer import create_enhancer
    IMAGE_ENHANCER_AVAILABLE = True
except ImportError:
    IMAGE_ENHANCER_AVAILABLE = False

# EasyOCR — motor alternativo de OCR (requiere torch, ~1 GB adicional)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

# Corrección ortográfica específica para OCR
try:
    from app.services.text_correction_service import TextCorrectionService as _TextCorrectionServiceCls
    _ocr_text_corrector = _TextCorrectionServiceCls()
    TEXT_CORRECTOR_AVAILABLE = True
except Exception:
    TEXT_CORRECTOR_AVAILABLE = False
    _ocr_text_corrector = None

logger = logging.getLogger(__name__)


class LegalOCRService:
    """Servicio de OCR para documentos legales con corrección de abreviaturas"""

    # Singleton para EasyOCR (carga modelos de ~300 MB una sola vez)
    _easyocr_reader = None

    # Diccionario de abreviaturas jurídicas mexicanas
    ABREVIATURAS_JURIDICAS = {
        # Instituciones
        r'\bMP\b': 'Ministerio Público',
        r'\bFGE\b': 'Fiscalía General del Estado',
        r'\bFGR\b': 'Fiscalía General de la República',
        r'\bPGJ\b': 'Procuraduría General de Justicia',
        r'\bPGR\b': 'Procuraduría General de la República',
        r'\bSSP\b': 'Secretaría de Seguridad Pública',
        r'\bAEI\b': 'Agente de la Policía de Investigación',
        r'\bAPI\b': 'Agente de la Policía de Investigación',
        r'\bPJE\b': 'Policía Judicial del Estado',
        r'\bSEMEFO\b': 'Servicio Médico Forense',
        r'\bINACIPE\b': 'Instituto Nacional de Ciencias Penales',
        
        # Títulos y cargos
        r'\bLic\.': 'Licenciado',
        r'\bLicdo\.': 'Licenciado',
        r'\bLicda\.': 'Licenciada',
        r'\bDr\.': 'Doctor',
        r'\bDra\.': 'Doctora',
        r'\bIng\.': 'Ingeniero',
        r'\bC\.': 'Ciudadano',
        r'\bProf\.': 'Profesor',
        r'\bMtro\.': 'Maestro',
        r'\bMtra\.': 'Maestra',
        
        # Vías y lugares
        r'\bAv\.': 'Avenida',
        r'\bAvda\.': 'Avenida',
        r'\bCalle\s+C\.': 'Calle',
        r'\bCol\.': 'Colonia',
        r'\bFracc\.': 'Fraccionamiento',
        r'\bMpio\.': 'Municipio',
        r'\bDeleg\.': 'Delegación',
        r'\bEdo\.': 'Estado',
        r'\bC\.P\.': 'Código Postal',
        r'\bNo\.': 'Número',
        r'\bNúm\.': 'Número',
        r'\bInt\.': 'Interior',
        r'\bExt\.': 'Exterior',
        r'\bMz\.': 'Manzana',
        r'\bLt\.': 'Lote',
        r'\bKm\.': 'Kilómetro',
        
        # Términos legales
        r'\bC\.I\.': 'Carpeta de Investigación',
        r'\bCI\b': 'Carpeta de Investigación',
        r'\bAP\b': 'Averiguación Previa',
        r'\bA\.P\.': 'Averiguación Previa',
        r'\bExp\.': 'Expediente',
        r'\bLeg\.': 'Legajo',
        r'\bTomo\s+T\.': 'Tomo',
        r'\bFoja\s+F\.': 'Foja',
        r'\bFojas\s+Fjs\.': 'Fojas',
        r'\bArt\.': 'Artículo',
        r'\bFracc\.': 'Fracción',
        r'\bInc\.': 'Inciso',
        r'\bPárr\.': 'Párrafo',
        r'\bCPF\b': 'Código Penal Federal',
        r'\bCPP\b': 'Código Procesal Penal',
        r'\bCNPP\b': 'Código Nacional de Procedimientos Penales',
        
        # Fechas y tiempos
        r'\bEne\.': 'Enero',
        r'\bFeb\.': 'Febrero',
        r'\bMar\.': 'Marzo',
        r'\bAbr\.': 'Abril',
        r'\bMay\.': 'Mayo',
        r'\bJun\.': 'Junio',
        r'\bJul\.': 'Julio',
        r'\bAgo\.': 'Agosto',
        r'\bSep\.': 'Septiembre',
        r'\bSept\.': 'Septiembre',
        r'\bOct\.': 'Octubre',
        r'\bNov\.': 'Noviembre',
        r'\bDic\.': 'Diciembre',
        r'\bHrs\.': 'Horas',
        r'\bMin\.': 'Minutos',
        
        # Otros
        r'\bS\.S\.': 'Servidor Servidor',
        r'\bAtto\.': 'Atentamente',
        r'\bAtte\.': 'Atentamente',
        r'\bOfc\.': 'Oficio',
        r'\bRef\.': 'Referencia',
        r'\bAsunto:': 'Asunto:',
        r'\bC\.c\.p\.': 'Con copia para',
    }
    
    # Patrones de corrección comunes en OCR
    CORRECCIONES_OCR = {
        # Errores comunes de reconocimiento
        r'([0O])\s+de\s+([A-Z])': r'0 de \2',  # "O de Enero" -> "0 de Enero"
        r'\bl\s+de\s+': r'1 de ',  # "l de enero" -> "1 de enero"
        r'\bO\s+de\s+': r'0 de ',  # "O de enero" -> "0 de enero"
        r'\b([0-9]{1,2})\s*[|l]\s*([0-9]{2})': r'\1/\2',  # "10 l 23" -> "10/23"
        r'\b([0-9]{1,2})\s*\|\s*([0-9]{2})': r'\1/\2',  # "10|23" -> "10/23"
        r'([A-ZÁÉÍÓÚÑ]{2,})\s*-\s*([A-ZÁÉÍÓÚÑ]{2,})': r'\1-\2',  # Unir palabras separadas
        
        # Caracteres especiales mal reconocidos
        r'[òóôõö]': 'o',
        r'[àáâãä]': 'a',
        r'[èéêë]': 'e',
        r'[ìíîï]': 'i',
        r'[ùúûü]': 'u',
        r'[ÒÓÔÕÖ]': 'O',
        r'[ÀÁÂÃÄ]': 'A',
        r'[ÈÉÊË]': 'E',
        r'[ÌÍÎÏ]': 'I',
        r'[ÙÚÛÜ]': 'U',
        
        # Espacios múltiples
        r'\s{2,}': ' ',
        r'\n{3,}': '\n\n',
    }
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Inicializar servicio de OCR
        
        Args:
            tesseract_path: Ruta al ejecutable de Tesseract (opcional)
        """
        if tesseract_path and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def expandir_abreviaturas(self, texto: str, marcar: bool = False) -> str:
        """
        Expandir abreviaturas jurídicas en el texto
        
        Args:
            texto: Texto con abreviaturas
            marcar: Si True, marca las expansiones con [...]
            
        Returns:
            Texto con abreviaturas expandidas
        """
        texto_expandido = texto
        
        for patron, expansion in self.ABREVIATURAS_JURIDICAS.items():
            if marcar:
                texto_expandido = re.sub(
                    patron, 
                    f"[{expansion}]", 
                    texto_expandido, 
                    flags=re.IGNORECASE
                )
            else:
                texto_expandido = re.sub(
                    patron, 
                    expansion, 
                    texto_expandido, 
                    flags=re.IGNORECASE
                )
        
        return texto_expandido
    
    def corregir_errores_ocr(self, texto: str) -> str:
        """
        Corregir errores comunes de OCR
        
        Args:
            texto: Texto con posibles errores de OCR
            
        Returns:
            Texto corregido
        """
        texto_corregido = texto
        
        for patron, reemplazo in self.CORRECCIONES_OCR.items():
            texto_corregido = re.sub(patron, reemplazo, texto_corregido)
        
        # Limpiar espacios al inicio y fin de líneas
        lineas = texto_corregido.split('\n')
        lineas = [linea.strip() for linea in lineas]
        texto_corregido = '\n'.join(lineas)
        
        return texto_corregido
    
    def procesar_texto_completo(self, texto: str, expandir_abrev: bool = True) -> str:
        """
        Procesar texto: corregir errores y expandir abreviaturas
        
        Args:
            texto: Texto original
            expandir_abrev: Si True, expande abreviaturas
            
        Returns:
            Texto procesado
        """
        # Primero corregir errores de OCR
        texto = self.corregir_errores_ocr(texto)
        
        # Luego expandir abreviaturas si se solicita
        if expandir_abrev:
            texto = self.expandir_abreviaturas(texto)
        
        return texto
    
    async def extraer_texto_pdf(
        self, 
        ruta_pdf: str, 
        pagina_inicio: int = 1,
        pagina_fin: Optional[int] = None,
        callback_progreso: Optional[callable] = None
    ) -> Dict[str, any]:
        """
        Extraer texto de PDF (texto nativo o OCR)
        
        Args:
            ruta_pdf: Ruta al archivo PDF
            pagina_inicio: Página inicial (1-indexed)
            pagina_fin: Página final (None = todas)
            callback_progreso: Función para reportar progreso
            
        Returns:
            Dict con texto extraído por página y metadatos
        """
        if not os.path.exists(ruta_pdf):
            raise FileNotFoundError(f"PDF no encontrado: {ruta_pdf}")
        
        resultado = {
            "success": False,
            "paginas": {},
            "total_paginas": 0,
            "metodo": None,
            "errores": []
        }
        
        try:
            # Primero intentar extraer texto nativo del PDF
            if PYPDF2_AVAILABLE:
                resultado_nativo = await self._extraer_texto_nativo(
                    ruta_pdf, pagina_inicio, pagina_fin, callback_progreso
                )
                
                # Verificar si se extrajo texto significativo y de calidad
                total_caracteres = sum(len(texto) for texto in resultado_nativo["paginas"].values())
                num_paginas = len(resultado_nativo["paginas"])
                
                # Calcular promedio de caracteres por página
                promedio_chars_pagina = total_caracteres / num_paginas if num_paginas > 0 else 0
                
                # Verificar calidad del texto (no solo marcadores de página)
                texto_muestra = " ".join(list(resultado_nativo["paginas"].values())[:5])  # Primeras 5 páginas
                tiene_contenido_real = (
                    promedio_chars_pagina > 100 and  # Más de 100 chars por página en promedio
                    not ("=== Página" in texto_muestra and len(texto_muestra) < 200) and  # No solo marcadores
                    len(texto_muestra.split()) > 50  # Al menos 50 palabras en muestra
                )
                
                if tiene_contenido_real:
                    resultado = resultado_nativo
                    resultado["metodo"] = "texto_nativo"
                    resultado["success"] = True
                    logger.info(f"Texto extraído nativamente: {total_caracteres} caracteres, {promedio_chars_pagina:.0f} por página")
                    return resultado
                else:
                    logger.info(f"Texto nativo insuficiente o de baja calidad (promedio: {promedio_chars_pagina:.0f} chars/página). Usando OCR...")
            
            # Si no hay texto nativo o es insuficiente, usar OCR
            if TESSERACT_AVAILABLE:
                logger.info("Usando OCR para extraer texto del PDF escaneado")
                resultado_ocr = await self._extraer_con_ocr(
                    ruta_pdf, pagina_inicio, pagina_fin, callback_progreso
                )
                resultado = resultado_ocr
                resultado["metodo"] = "ocr"
                resultado["success"] = True
            else:
                resultado["errores"].append("Tesseract no disponible para OCR")
        
        except Exception as e:
            logger.error(f"Error extrayendo texto del PDF: {str(e)}")
            resultado["errores"].append(str(e))
        
        return resultado
    
    async def _extraer_texto_nativo(
        self,
        ruta_pdf: str,
        pagina_inicio: int,
        pagina_fin: Optional[int],
        callback_progreso: Optional[callable]
    ) -> Dict[str, any]:
        """Extraer texto nativo del PDF"""
        resultado = {
            "paginas": {},
            "total_paginas": 0,
            "errores": []
        }
        
        try:
            reader = PdfReader(ruta_pdf)
            total_paginas = len(reader.pages)
            resultado["total_paginas"] = total_paginas
            
            if pagina_fin is None or pagina_fin > total_paginas:
                pagina_fin = total_paginas
            
            for i in range(pagina_inicio - 1, pagina_fin):
                try:
                    page = reader.pages[i]
                    texto = page.extract_text()
                    
                    # Procesar texto
                    texto = self.procesar_texto_completo(texto)
                    
                    resultado["paginas"][i + 1] = texto
                    
                    if callback_progreso:
                        progreso = ((i - pagina_inicio + 2) / (pagina_fin - pagina_inicio + 1)) * 100
                        # Detectar si callback es async o sync
                        import inspect
                        if inspect.iscoroutinefunction(callback_progreso):
                            await callback_progreso(i + 1, total_paginas, progreso)
                        else:
                            callback_progreso(i + 1, total_paginas, progreso)
                
                except Exception as e:
                    logger.error(f"Error en página {i + 1}: {str(e)}")
                    resultado["errores"].append(f"Página {i + 1}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error leyendo PDF: {str(e)}")
            resultado["errores"].append(str(e))
        
        return resultado
    
    @classmethod
    def _get_easyocr_reader(cls):
        """Lector EasyOCR con patrón singleton (carga modelos una sola vez)"""
        if cls._easyocr_reader is None and EASYOCR_AVAILABLE:
            try:
                logger.info("Inicializando EasyOCR reader (español + inglés)...")
                cls._easyocr_reader = easyocr.Reader(['es', 'en'], gpu=False, verbose=False)
                logger.info("EasyOCR reader listo")
            except Exception as e_init:
                logger.warning(f"No se pudo inicializar EasyOCR: {e_init}")
        return cls._easyocr_reader

    async def _extraer_con_ocr(
        self,
        ruta_pdf: str,
        pagina_inicio: int,
        pagina_fin: Optional[int],
        callback_progreso: Optional[callable]
    ) -> Dict[str, any]:
        """Extraer texto usando OCR con mejora de imagen, multi-PSM, fallback EasyOCR y corrección ortográfica"""
        resultado = {
            "paginas": {},
            "total_paginas": 0,
            "errores": []
        }
        
        try:
            # ── Configuraciones PSM para votación multi-modo ───────────────────────────
            psm_configs = [
                r'--oem 3 --psm 6 -l spa',   # Bloque de texto uniforme (más común)
                r'--oem 3 --psm 4 -l spa',   # Columna única de tamaño variable
                r'--oem 3 --psm 11 -l spa',  # Texto disperso sin orientación
            ]

            # ── Inicializar AdvancedImageEnhancer ────────────────────────────────
            _enhancer = None
            if IMAGE_ENHANCER_AVAILABLE:
                try:
                    _enhancer = create_enhancer('high')
                    logger.info("AdvancedImageEnhancer activado para OCR")
                except Exception as e_enh_init:
                    logger.warning(f"No se pudo inicializar AdvancedImageEnhancer: {e_enh_init}")

            # Convertir PDF a imágenes (por lotes para no saturar memoria)
            batch_size = 10

            # Primero obtener total de páginas
            try:
                reader = PdfReader(ruta_pdf)
                total_paginas = len(reader.pages)
                resultado["total_paginas"] = total_paginas
            except:
                # Si no se puede leer, asumir que se procesarán todas
                total_paginas = pagina_fin if pagina_fin else 1000

            if pagina_fin is None or pagina_fin > total_paginas:
                pagina_fin = total_paginas

            # Procesar por lotes
            for batch_start in range(pagina_inicio, pagina_fin + 1, batch_size):
                batch_end = min(batch_start + batch_size - 1, pagina_fin)

                logger.info(f"Procesando páginas {batch_start} a {batch_end}")

                try:
                    # Convertir páginas a imágenes
                    imagenes = convert_from_path(
                        ruta_pdf,
                        first_page=batch_start,
                        last_page=batch_end,
                        dpi=300,
                        grayscale=True
                    )

                    # Procesar cada imagen
                    for idx, imagen in enumerate(imagenes):
                        num_pagina = batch_start + idx

                        try:
                            # ── 1. Mejorar imagen con AdvancedImageEnhancer ─────────
                            imagen_ocr = imagen
                            if _enhancer:
                                try:
                                    imagen_ocr = _enhancer.enhance_pil_image(imagen)
                                except Exception as e_enh:
                                    logger.warning(f"Mejora de imagen p{num_pagina} falló: {e_enh}")

                            # ── 2. Multi-PSM voting — elegir el resultado con más texto ─
                            mejor_texto = ""
                            mejor_score = -1
                            for config in psm_configs:
                                try:
                                    texto_cand = pytesseract.image_to_string(
                                        imagen_ocr, config=config
                                    )
                                    score = sum(1 for c in texto_cand if c.isalnum())
                                    if score > mejor_score:
                                        mejor_score = score
                                        mejor_texto = texto_cand
                                except Exception:
                                    continue
                            texto = mejor_texto

                            # ── 3. EasyOCR como fallback para páginas con poco texto ─
                            if EASYOCR_AVAILABLE and mejor_score < 80:
                                try:
                                    reader_easy = self._get_easyocr_reader()
                                    if reader_easy:
                                        import numpy as np
                                        img_np = np.array(imagen_ocr.convert("RGB"))
                                        res_easy = reader_easy.readtext(
                                            img_np, detail=0, paragraph=True
                                        )
                                        texto_easy = "\n".join(res_easy) if res_easy else ""
                                        easy_score = sum(1 for c in texto_easy if c.isalnum())
                                        if easy_score > mejor_score:
                                            texto = texto_easy
                                            logger.info(
                                                f"EasyOCR activado en p{num_pagina} "
                                                f"(score {easy_score} vs {mejor_score} Tesseract)"
                                            )
                                except Exception as e_easy:
                                    logger.warning(f"EasyOCR falló en p{num_pagina}: {e_easy}")

                            # ── 4. Corrección ortográfica de errores OCR ──────────────
                            if TEXT_CORRECTOR_AVAILABLE and _ocr_text_corrector:
                                try:
                                    texto = _ocr_text_corrector.corregir_texto(
                                        texto, contexto="legal"
                                    )
                                except Exception:
                                    pass

                            # ── 5. Procesar texto (abreviaturas jurídicas) ────────────
                            texto = self.procesar_texto_completo(texto)

                            resultado["paginas"][num_pagina] = texto

                            if callback_progreso:
                                progreso = (
                                    (num_pagina - pagina_inicio + 1)
                                    / (pagina_fin - pagina_inicio + 1)
                                    * 100
                                )
                                import inspect
                                if inspect.iscoroutinefunction(callback_progreso):
                                    await callback_progreso(num_pagina, total_paginas, progreso)
                                else:
                                    callback_progreso(num_pagina, total_paginas, progreso)

                        except Exception as e:
                            logger.error(f"Error OCR en página {num_pagina}: {str(e)}")
                            resultado["errores"].append(f"Página {num_pagina}: {str(e)}")

                except Exception as e:
                    logger.error(f"Error procesando lote {batch_start}-{batch_end}: {str(e)}")
                    resultado["errores"].append(f"Lote {batch_start}-{batch_end}: {str(e)}")

        except Exception as e:
            logger.error(f"Error en OCR: {str(e)}")
            resultado["errores"].append(str(e))

        return resultado
    
    def generar_reporte_correcciones(self, texto_original: str, texto_corregido: str) -> List[Dict]:
        """
        Generar reporte de correcciones realizadas
        
        Args:
            texto_original: Texto antes de correcciones
            texto_corregido: Texto después de correcciones
            
        Returns:
            Lista de correcciones realizadas
        """
        correcciones = []
        
        # Buscar diferencias significativas
        lineas_orig = texto_original.split('\n')
        lineas_corr = texto_corregido.split('\n')
        
        for patron, expansion in self.ABREVIATURAS_JURIDICAS.items():
            matches_orig = re.finditer(patron, texto_original, re.IGNORECASE)
            for match in matches_orig:
                correcciones.append({
                    "tipo": "abreviatura",
                    "original": match.group(0),
                    "corregido": expansion,
                    "posicion": match.start()
                })
        
        return correcciones
    
    def __del__(self):
        """Limpiar recursos"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


# Instancia global del servicio
legal_ocr_service = LegalOCRService()
