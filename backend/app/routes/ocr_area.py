# backend/app/routes/ocr_area.py
"""
Endpoint para extraer texto de áreas específicas de PDFs usando OCR
Funcionalidad tipo Google Lens
Desarrollado por: Eduardo Lozada Quiroz, ISC
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import io
import os
import statistics
import base64
import json
import numpy as np
import cv2
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
from pdf2image import convert_from_path
import tempfile
import httpx

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


# ── Nuevo endpoint: OCR de área por tomo almacenado ─────────────────────────
class OcrAreaRequest(BaseModel):
    x_pct: float   # 0.0 – 1.0, posición relativa dentro de la página
    y_pct: float
    w_pct: float
    h_pct: float


@router.post("/tomo/{tomo_id}/pagina/{pagina}/area")
async def ocr_area_tomo_almacenado(
    tomo_id: int,
    pagina: int,
    body: OcrAreaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Extrae texto de un área seleccionada de una página de un tomo almacenado.
    Renderiza a 400 DPI, aplica preprocesamiento adaptado al tamaño del recorte,
    y prueba múltiples binarizaciones + PSMs para maximizar la extracción.
    """
    from app.models.tomo import Tomo
    import re

    # Validar porcentajes
    if not (0 <= body.x_pct <= 1 and 0 <= body.y_pct <= 1 and
            0 < body.w_pct <= 1 and 0 < body.h_pct <= 1):
        raise HTTPException(status_code=400, detail="Coordenadas fuera de rango (deben ser 0.0-1.0)")

    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(status_code=404, detail="Tomo no encontrado")
    if not os.path.exists(tomo.ruta_archivo):
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado en el servidor")

    try:
        logger.info(f"OCR área tomo={tomo_id} pág={pagina} x={body.x_pct:.2f} y={body.y_pct:.2f} w={body.w_pct:.2f} h={body.h_pct:.2f}")

        # ── 0. PRIORIDAD: Intentar texto nativo del PDF (PyMuPDF) ────────────
        # Si el PDF tiene texto embebido (digital o post-OCR), extraerlo directamente
        # da 100% de precisión sin necesidad de Tesseract.
        try:
            import fitz  # PyMuPDF
            doc_fitz = fitz.open(tomo.ruta_archivo)
            page_fitz = doc_fitz[pagina - 1]
            page_rect = page_fitz.rect  # dimensiones reales de la página

            # Convertir porcentajes a coordenadas absolutas del PDF
            clip_x0 = body.x_pct * page_rect.width
            clip_y0 = body.y_pct * page_rect.height
            clip_x1 = (body.x_pct + body.w_pct) * page_rect.width
            clip_y1 = (body.y_pct + body.h_pct) * page_rect.height
            clip = fitz.Rect(clip_x0, clip_y0, clip_x1, clip_y1)

            texto_nativo = page_fitz.get_text("text", clip=clip).strip()
            doc_fitz.close()

            if len(texto_nativo) > 3:
                # Limpiar espacios múltiples y líneas vacías
                texto_nativo = re.sub(r'[ \t]+', ' ', texto_nativo)
                texto_nativo = re.sub(r'\n{3,}', '\n\n', texto_nativo)
                texto_nativo = texto_nativo.strip()

                logger.info(f"Texto nativo extraído: {len(texto_nativo)} chars (sin OCR)")
                return {
                    "success": True,
                    "texto": texto_nativo,
                    "confianza": 99,
                    "metodo": "texto_nativo"
                }
            else:
                logger.info("Sin texto nativo en el área, cayendo a OCR...")
        except Exception as e:
            logger.warning(f"Extracción nativa falló, usando OCR: {e}")

        # ── 1. OCR.space API (OCR en la nube, gratis) ────────────────────
        from app.config import settings as app_settings
        ocr_space_key = app_settings.OCR_SPACE_API_KEY
        logger.info(f"OCR.space key: {'SÍ' if ocr_space_key else 'NO'}")

        if ocr_space_key:
            try:
                texto_cloud = await _ocrspace_ocr(
                    tomo.ruta_archivo, pagina,
                    body.x_pct, body.y_pct, body.w_pct, body.h_pct,
                    ocr_space_key
                )
                if texto_cloud and len(texto_cloud.strip()) > 3:
                    logger.info(f"OCR.space extrajo: {len(texto_cloud)} chars")
                    return {
                        "success": True,
                        "texto": texto_cloud.strip(),
                        "confianza": 97,
                        "metodo": "ocr_space"
                    }
            except Exception as e:
                logger.warning(f"OCR.space falló: {e}")

        # ── 2. Renderizar página completa a 400 DPI con pdf2image ─────────────
        imagenes = convert_from_path(
            tomo.ruta_archivo,
            first_page=pagina,
            last_page=pagina,
            dpi=400
        )
        if not imagenes:
            raise HTTPException(status_code=404, detail=f"No se pudo renderizar la página {pagina}")

        img_full = imagenes[0]
        iw, ih = img_full.size

        # ── 2. Recortar el área seleccionada con margen ───────────────────────
        px = int(body.x_pct * iw)
        py = int(body.y_pct * ih)
        pw = int(body.w_pct * iw)
        ph = int(body.h_pct * ih)

        margin_x = max(10, int(pw * 0.05))
        margin_y = max(10, int(ph * 0.05))
        left   = max(0, px - margin_x)
        top    = max(0, py - margin_y)
        right  = min(iw, px + pw + margin_x)
        bottom = min(ih, py + ph + margin_y)

        recorte = img_full.crop((left, top, right, bottom))
        arr = np.array(recorte.convert('RGB'))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # ── 3. Preprocesamiento suave (NO destructivo) ────────────────────────
        # Shadow removal
        bg = cv2.dilate(gray, np.ones((21, 21), np.uint8))
        bg = cv2.GaussianBlur(bg, (21, 21), 0)
        enhanced = cv2.divide(gray, bg, scale=255.0).astype(np.uint8)

        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(enhanced)

        # Bilateral (suave)
        enhanced = cv2.bilateralFilter(enhanced, d=5, sigmaColor=25, sigmaSpace=25)

        # Unsharp mask (suave)
        _blur = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.5)
        enhanced = cv2.addWeighted(enhanced, 1.4, _blur, -0.4, 0).astype(np.uint8)

        # Escalar si es muy pequeño
        rh, rw = enhanced.shape[:2]
        if rw < 600:
            factor = max(2, 600 // max(rw, 1))
            enhanced = cv2.resize(enhanced, (rw * factor, rh * factor),
                                  interpolation=cv2.INTER_CUBIC)

        # ── 4. Binarización: Otsu + Adaptiva (sin Niblack para velocidad) ────
        _, bin_otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(bin_otsu) < 127:
            bin_otsu = cv2.bitwise_not(bin_otsu)

        blk = min(51, max(3, (min(enhanced.shape[:2]) // 4) * 2 + 1))
        bin_local = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=blk, C=12
        )
        if np.mean(bin_local) < 127:
            bin_local = cv2.bitwise_not(bin_local)

        # Cierre morfológico mínimo
        kern = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
        bin_otsu  = cv2.morphologyEx(bin_otsu,  cv2.MORPH_CLOSE, kern)
        bin_local = cv2.morphologyEx(bin_local, cv2.MORPH_CLOSE, kern)

        # ── 5. Tesseract: probar ambas binarizaciones × PSMs ─────────────────
        mejor = {'texto': '', 'confianza': 0, 'words': []}

        for img_bin, nombre in ((bin_otsu, 'otsu'), (bin_local, 'local')):
            img_pil = Image.fromarray(img_bin)
            for psm in (6, 4, 3):
                try:
                    cfg = f'--psm {psm} --oem 1'
                    data = pytesseract.image_to_data(
                        img_pil, lang='spa', config=cfg,
                        output_type=pytesseract.Output.DICT
                    )
                    # Construir texto solo con palabras de confianza >= 40
                    words = []
                    confs_all = []
                    for w, c in zip(data['text'], data['conf']):
                        c_str = str(c).lstrip('-')
                        if not c_str.isdigit():
                            continue
                        c_int = int(c)
                        if c_int < 0:
                            continue
                        confs_all.append(c_int)
                        w = str(w).strip()
                        if not w:
                            continue
                        if c_int >= 40:
                            words.append(w)

                    conf = int(statistics.mean(confs_all)) if confs_all else 0
                    texto = ' '.join(words)

                    if conf > mejor['confianza'] or (not mejor['texto'] and texto):
                        mejor = {'texto': texto, 'confianza': conf, 'words': words}
                    if conf >= 75:
                        break
                except Exception:
                    continue
            if mejor['confianza'] >= 75:
                break

        # ── 6. También probar con la imagen gris directa (sin binarizar) ─────
        if mejor['confianza'] < 60:
            try:
                img_gray_pil = Image.fromarray(enhanced)
                for psm_g in (6, 3):
                    cfg_g = f'--psm {psm_g} --oem 1'
                    data_g = pytesseract.image_to_data(
                        img_gray_pil, lang='spa', config=cfg_g,
                        output_type=pytesseract.Output.DICT
                    )
                    words_g = []
                    confs_g = []
                    for w, c in zip(data_g['text'], data_g['conf']):
                        c_str = str(c).lstrip('-')
                        if not c_str.isdigit():
                            continue
                        c_int = int(c)
                        if c_int < 0:
                            continue
                        confs_g.append(c_int)
                        w = str(w).strip()
                        if w and c_int >= 40:
                            words_g.append(w)
                    conf_g = int(statistics.mean(confs_g)) if confs_g else 0
                    if conf_g > mejor['confianza']:
                        mejor = {'texto': ' '.join(words_g), 'confianza': conf_g}
            except Exception:
                pass

        # ── 7. Limpieza de texto ──────────────────────────────────────────────
        texto_final = mejor['texto']

        lineas = texto_final.split('\n')
        lineas_ok = []
        for linea in lineas:
            # Quitar líneas que son solo símbolos de formulario
            linea_limpia = re.sub(r'^[\s|_\-─—.•·=~]+$', '', linea)
            # Quitar | sueltos al inicio/final
            linea_limpia = re.sub(r'^\s*[|]+\s*', '', linea_limpia)
            linea_limpia = re.sub(r'\s*[|]+\s*$', '', linea_limpia)
            # Quitar relleno de formulario (muchos puntos/guiones seguidos)
            linea_limpia = re.sub(r'[._\-]{4,}', ' ', linea_limpia)
            # Quitar puntos sueltos rodeados de espacios (artefactos de líneas)
            linea_limpia = re.sub(r'\s+\.\s+', ' ', linea_limpia)
            # Quitar punto al inicio de línea
            linea_limpia = re.sub(r'^\s*\.\s+', '', linea_limpia)
            linea_limpia = linea_limpia.strip()
            if linea_limpia:
                lineas_ok.append(linea_limpia)
        texto_final = '\n'.join(lineas_ok)

        # Quitar tokens de 1-3 chars que son solo consonantes (basura de bordes)
        # Ej: "ITA", "TÉ", "RA", "AE" — pero conservar "DE", "LA", "EN", "SI", "NO", "EL"
        palabras_validas_cortas = {
            'de', 'la', 'el', 'en', 'si', 'no', 'al', 'se', 'es', 'un', 'ya',
            'le', 'su', 'me', 'te', 'lo', 'tu', 'mi', 'ni', 'yo', 'ha', 'he',
            'del', 'las', 'los', 'una', 'uno', 'con', 'por', 'para', 'que',
            'son', 'fue', 'ser', 'sin', 'mas', 'sus', 'nos', 'les', 'fue',
            'art', 'ley', 'exp', 'est', 'its',
        }
        tokens = texto_final.split()
        tokens_ok = []
        for t in tokens:
            t_lower = t.lower().rstrip('.,;:')
            # Tokens de 1-3 chars: solo conservar si son palabras conocidas
            if len(t_lower) <= 3:
                if t_lower in palabras_validas_cortas:
                    tokens_ok.append(t)
                elif re.match(r'^[0-9]+$', t_lower):
                    tokens_ok.append(t)  # números cortos OK
                # else: descartar token corto sospechoso
            else:
                tokens_ok.append(t)
        texto_final = ' '.join(tokens_ok)

        # Entity correction
        try:
            from app.services.entity_correction_service import entity_correction
            texto_final = entity_correction.corregir_todo(texto_final)
        except Exception:
            pass

        confianza_final = min(99, int(mejor['confianza'] * 1.1)) if mejor['confianza'] > 0 else 0

        logger.info(f"OCR área completado: {len(texto_final)} chars, confianza={confianza_final}%")

        return {
            "success": True,
            "texto": texto_final,
            "confianza": confianza_final,
            "metodo": "tesseract"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en OCR de área: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar OCR: {str(e)}")


# ── OCR.space API (gratis, sin tarjeta de crédito) ─────────────────────────
async def _ocrspace_ocr(
    pdf_path: str,
    pagina: int,
    x_pct: float,
    y_pct: float,
    w_pct: float,
    h_pct: float,
    api_key: str
) -> str:
    """
    Usa OCR.space API para extraer texto del área seleccionada.
    Gratis: 25,000 requests/mes. Sin tarjeta de crédito.
    """
    from pdf2image import convert_from_path as _convert

    # Renderizar página a 300 DPI
    imgs = _convert(pdf_path, first_page=pagina, last_page=pagina, dpi=300)
    if not imgs:
        return ""

    img = imgs[0]
    iw, ih = img.size

    # Recortar al área seleccionada
    left   = max(0, int(x_pct * iw) - 5)
    top    = max(0, int(y_pct * ih) - 5)
    right  = min(iw, int((x_pct + w_pct) * iw) + 5)
    bottom = min(ih, int((y_pct + h_pct) * ih) + 5)
    recorte = img.crop((left, top, right, bottom))

    # Convertir a PNG en memoria
    buf = io.BytesIO()
    recorte.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Llamar a OCR.space API
    url = "https://api.ocr.space/parse/image"
    payload = {
        "base64Image": f"data:image/png;base64,{img_b64}",
        "language": "spa",
        "isOverlayRequired": False,
        "OCREngine": 2,  # Engine 2 es mejor para documentos
        "scale": True,
        "isTable": True,
    }
    headers = {"apikey": api_key}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=payload, headers=headers)
        resp.raise_for_status()

    result = resp.json()

    if result.get("IsErroredOnProcessing"):
        error_msg = result.get("ErrorMessage", ["Unknown error"])
        raise Exception(f"OCR.space error: {error_msg}")

    parsed = result.get("ParsedResults", [])
    if not parsed:
        return ""

    texto = parsed[0].get("ParsedText", "").strip()
    return texto
