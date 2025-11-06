# backend/app/routes/ocr_area.py
"""
Endpoint para extraer texto de áreas específicas de PDFs usando OCR
Funcionalidad tipo Google Lens
Desarrollado por: Eduardo Lozada Quiroz, ISC
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Optional
import io
import os
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pdf2image import convert_from_path
import tempfile

from app.database import get_db
from app.models.usuario import Usuario
from app.middlewares.auth_middleware import get_current_user
from app.utils.logger import logger
from app.utils.auditoria_utils import AuditoriaLogger

router = APIRouter(
    prefix="/api/ocr",
    tags=["OCR Area Selection"]
)

@router.post("/extract-area")
async def extract_text_from_area(
    request: Request,
    file: UploadFile = File(...),
    page_number: int = Form(...),
    x: float = Form(...),
    y: float = Form(...),
    width: float = Form(...),
    height: float = Form(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Extrae texto de un área específica de una página PDF usando OCR
    
    Parámetros:
    - file: Archivo PDF
    - page_number: Número de página (1-indexed)
    - x, y: Coordenadas de la esquina superior izquierda del área
    - width, height: Dimensiones del área a extraer
    
    Retorna el texto extraído
    """
    
    temp_pdf_path = None
    
    try:
        # Validar formato
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos PDF"
            )
        
        # Validar coordenadas
        if x < 0 or y < 0 or width <= 0 or height <= 0:
            raise HTTPException(
                status_code=400,
                detail="Coordenadas inválidas"
            )
        
        logger.info(f"Extrayendo texto del área: página={page_number}, x={x}, y={y}, w={width}, h={height}")
        
        # Guardar PDF temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            content = await file.read()
            temp_pdf.write(content)
            temp_pdf_path = temp_pdf.name
        
        # Convertir página específica a imagen con MÁXIMA RESOLUCIÓN
        # pdf2image usa 1-indexed, así que no necesitamos ajustar
        images = convert_from_path(
            temp_pdf_path,
            first_page=page_number,
            last_page=page_number,
            dpi=600  # DUPLICAR resolución para mejor OCR
        )
        
        if not images:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo convertir la página {page_number}"
            )
        
        page_image = images[0]
        
        # Recortar el área seleccionada
        # PIL usa coordenadas (left, top, right, bottom)
        left = int(x)
        top = int(y)
        right = int(x + width)
        bottom = int(y + height)
        
        # Validar que el área está dentro de la imagen
        img_width, img_height = page_image.size
        if right > img_width or bottom > img_height:
            # Ajustar coordenadas si exceden
            right = min(right, img_width)
            bottom = min(bottom, img_height)
            logger.warning(f"Coordenadas ajustadas: right={right}, bottom={bottom}")
        
        cropped_image = page_image.crop((left, top, right, bottom))
        
        # MEJORAR LA IMAGEN PARA MEJOR OCR (como Google Lens) - SOLO CON PIL
        logger.info("Aplicando mejoras de imagen para OCR...")
        
        # Convertir a escala de grises
        if cropped_image.mode != 'L':
            cropped_image = cropped_image.convert('L')
        
        # Aumentar contraste significativamente
        enhancer = ImageEnhance.Contrast(cropped_image)
        cropped_image = enhancer.enhance(2.5)
        
        # Aumentar brillo ligeramente
        enhancer = ImageEnhance.Brightness(cropped_image)
        cropped_image = enhancer.enhance(1.2)
        
        # Aumentar nitidez
        cropped_image = cropped_image.filter(ImageFilter.SHARPEN)
        cropped_image = cropped_image.filter(ImageFilter.SHARPEN)  # Aplicar dos veces
        
        # Binarización (convertir a blanco y negro puro)
        # Esto ayuda enormemente al OCR
        threshold = 128
        cropped_image = cropped_image.point(lambda x: 255 if x > threshold else 0, mode='1')
        
        # Aplicar OCR con configuración optimizada
        texto_extraido = pytesseract.image_to_string(
            cropped_image,
            lang='spa',
            config='--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNÑOPQRSTUVWXYZabcdefghijklmnñopqrstuvwxyzáéíóúÁÉÍÓÚ0123456789.,;:()/-_ '
        )
        
        # Si no se extrajo nada, intentar con diferentes configuraciones
        if not texto_extraido.strip():
            logger.warning("Reintentando OCR con PSM 11...")
            texto_extraido = pytesseract.image_to_string(
                cropped_image,
                lang='spa',
                config='--psm 11 --oem 3'
            )
        
        # Último intento con la imagen original
        if not texto_extraido.strip():
            logger.warning("Último intento con imagen sin procesar...")
            texto_extraido = pytesseract.image_to_string(
                page_image.crop((left, top, right, bottom)),
                lang='spa',
                config='--psm 3'
            )
        
        # Limpiar texto
        texto_extraido = texto_extraido.strip()
        
        if not texto_extraido:
            logger.warning("No se extrajo texto del área seleccionada")
            return {
                "success": True,
                "texto": "",
                "mensaje": "No se detectó texto en el área seleccionada"
            }
        
        logger.info(f"Texto extraído exitosamente: {len(texto_extraido)} caracteres")
        
        # Registrar en auditoría
        try:
            ip_address, user_agent = AuditoriaLogger.extraer_info_request(request)
            AuditoriaLogger.registrar(
                db=db,
                usuario_id=current_user.id,
                accion="OCR_AREA_EXTRAIDO",
                tabla_afectada="contenido_ocr",
                valores_nuevos={
                    "archivo": file.filename,
                    "pagina": page_number,
                    "coordenadas": {"x": x, "y": y, "width": width, "height": height},
                    "caracteres_extraidos": len(texto_extraido),
                    "usuario": current_user.username
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            logger.warning(f"No se pudo registrar auditoría: {e}")
        
        return {
            "success": True,
            "texto": texto_extraido
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extrayendo texto del área: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al extraer texto: {str(e)}"
        )
    finally:
        # Limpiar archivo temporal
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.unlink(temp_pdf_path)
            except Exception as e:
                logger.error(f"Error eliminando archivo temporal: {e}")
