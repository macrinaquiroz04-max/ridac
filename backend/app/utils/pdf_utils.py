# backend/app/utils/pdf_utils.py

import fitz  # PyMuPDF
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def extraer_info_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extraer información básica de un archivo PDF.
    
    Args:
        file_path: Ruta al archivo PDF
        
    Returns:
        dict: Información del PDF (número de páginas, metadatos, etc.)
    """
    try:
        # Abrir el documento PDF
        doc = fitz.open(file_path)
        
        # Información básica
        info = {
            "numero_paginas": len(doc),
            "titulo": doc.metadata.get("title", ""),
            "autor": doc.metadata.get("author", ""),
            "creador": doc.metadata.get("creator", ""),
            "productor": doc.metadata.get("producer", ""),
            "fecha_creacion": doc.metadata.get("creationDate", ""),
            "fecha_modificacion": doc.metadata.get("modDate", ""),
            "es_valido": True,
            "encriptado": doc.is_encrypted,
            "necesita_password": doc.needs_pass if hasattr(doc, 'needs_pass') else False
        }
        
        # Validar que el PDF tenga contenido
        if len(doc) == 0:
            info["es_valido"] = False
            info["error"] = "El archivo PDF está vacío"
        
        # Cerrar el documento
        doc.close()
        
        logger.info(f"PDF analizado: {file_path} - {info['numero_paginas']} páginas")
        return info
        
    except Exception as e:
        logger.error(f"Error al analizar PDF {file_path}: {str(e)}")
        return {
            "numero_paginas": 0,
            "es_valido": False,
            "error": str(e),
            "titulo": "",
            "autor": "",
            "creador": "",
            "productor": "",
            "fecha_creacion": "",
            "fecha_modificacion": "",
            "encriptado": False,
            "necesita_password": False
        }


def validar_pdf(file_path: str) -> Dict[str, Any]:
    """
    Validar que un archivo PDF sea válido y legible.
    
    Args:
        file_path: Ruta al archivo PDF
        
    Returns:
        dict: Resultado de la validación
    """
    try:
        info = extraer_info_pdf(file_path)
        
        validacion = {
            "es_valido": info["es_valido"],
            "numero_paginas": info["numero_paginas"],
            "errores": [],
            "advertencias": []
        }
        
        # Validaciones específicas
        if not info["es_valido"]:
            validacion["errores"].append(info.get("error", "PDF inválido"))
        
        if info["encriptado"]:
            validacion["advertencias"].append("El PDF está encriptado")
            
        if info["necesita_password"]:
            validacion["errores"].append("El PDF requiere contraseña")
            validacion["es_valido"] = False
            
        if info["numero_paginas"] == 0:
            validacion["errores"].append("El PDF no tiene páginas")
            validacion["es_valido"] = False
            
        if info["numero_paginas"] > 10000:  # Límite razonable
            validacion["advertencias"].append(f"PDF muy grande: {info['numero_paginas']} páginas")
            
        return validacion
        
    except Exception as e:
        logger.error(f"Error al validar PDF {file_path}: {str(e)}")
        return {
            "es_valido": False,
            "numero_paginas": 0,
            "errores": [f"Error al validar: {str(e)}"],
            "advertencias": []
        }


def obtener_texto_preview_pdf(file_path: str, max_paginas: int = 3) -> str:
    """
    Obtener un preview del texto del PDF (primeras páginas).
    
    Args:
        file_path: Ruta al archivo PDF
        max_paginas: Número máximo de páginas a procesar
        
    Returns:
        str: Texto extraído de las primeras páginas
    """
    try:
        doc = fitz.open(file_path)
        texto_preview = ""
        
        # Extraer texto de las primeras páginas
        for page_num in range(min(max_paginas, len(doc))):
            page = doc[page_num]
            texto_pagina = page.get_text()
            texto_preview += f"\n--- Página {page_num + 1} ---\n{texto_pagina}\n"
            
        doc.close()
        
        # Limitar longitud del preview
        if len(texto_preview) > 5000:
            texto_preview = texto_preview[:5000] + "\n... (texto truncado)"
            
        return texto_preview.strip()
        
    except Exception as e:
        logger.error(f"Error al extraer preview de {file_path}: {str(e)}")
        return f"Error al extraer preview: {str(e)}"