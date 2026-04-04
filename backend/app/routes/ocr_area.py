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
import numpy as np
import cv2
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
    Extrae texto de un área (o página completa) de un tomo almacenado.
    Usa el mismo pipeline avanzado que el OCR batch: CLAHE + bilateral +
    unsharp + huella dactilar + bleed-through + multi-binarización (Otsu +
    Adaptive + Niblack) × 3 PSMs + entity correction.

    Las coordenadas son porcentajes (0.0-1.0) del ancho/alto de la página.
    Para página completa, enviar x=0, y=0, w=1, h=1.
    """
    from app.models.tomo import Tomo
    import fitz

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

        # ── 1. Renderizar con PyMuPDF a 400 DPI ──────────────────────────────
        doc = fitz.open(tomo.ruta_archivo)
        if pagina < 1 or pagina > len(doc):
            doc.close()
            raise HTTPException(status_code=404, detail=f"Página {pagina} no existe (total: {len(doc)})")

        page = doc[pagina - 1]  # fitz es 0-indexed
        # 400 DPI = 400/72 ≈ 5.56
        mat = fitz.Matrix(5.56, 5.56)

        # Si es un área parcial, definir clip en coordenadas de la página
        page_rect = page.rect
        clip = fitz.Rect(
            page_rect.x0 + body.x_pct * page_rect.width,
            page_rect.y0 + body.y_pct * page_rect.height,
            page_rect.x0 + (body.x_pct + body.w_pct) * page_rect.width,
            page_rect.y0 + (body.y_pct + body.h_pct) * page_rect.height,
        )
        # Margen de 3% para no cortar texto en bordes
        margin_x = clip.width * 0.03
        margin_y = clip.height * 0.03
        clip = fitz.Rect(
            max(page_rect.x0, clip.x0 - margin_x),
            max(page_rect.y0, clip.y0 - margin_y),
            min(page_rect.x1, clip.x1 + margin_x),
            min(page_rect.y1, clip.y1 + margin_y),
        )

        pix = page.get_pixmap(matrix=mat, clip=clip)
        img_data = pix.tobytes("png")
        doc.close()

        img = Image.open(io.BytesIO(img_data))

        # ── 2. Pipeline avanzado (mismo que ocr_service) ─────────────────────
        arr = np.array(img.convert('RGB'))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # Eliminación de sombras por iluminación no uniforme
        bg = cv2.dilate(gray, np.ones((21, 21), np.uint8))
        bg = cv2.GaussianBlur(bg, (21, 21), 0)
        enhanced = cv2.divide(gray, bg, scale=255.0).astype(np.uint8)

        # CLAHE con clipLimit 3.5 para documentos envejecidos
        clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(enhanced)

        # Bilateral filter: suaviza grano de copia-de-copia preservando bordes
        enhanced = cv2.bilateralFilter(enhanced, d=5, sigmaColor=30, sigmaSpace=30)

        # Unsharp mask: recupera bordes de letras desdibujadas
        _blur = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=2)
        enhanced = cv2.addWeighted(enhanced, 1.6, _blur, -0.6, 0).astype(np.uint8)

        # Escalar si el recorte es pequeño
        rh, rw = enhanced.shape[:2]
        if rw < 800 or rh < 400:
            factor = max(2, int(np.ceil(800 / max(rw, 1))))
            enhanced = cv2.resize(enhanced, (rw * factor, rh * factor),
                                  interpolation=cv2.INTER_CUBIC)
            # Re-aplicar bilateral + unsharp tras escalar
            enhanced = cv2.bilateralFilter(enhanced, d=3, sigmaColor=20, sigmaSpace=20)
            _blur2 = cv2.GaussianBlur(enhanced, (0, 0), sigmaX=1.5)
            enhanced = cv2.addWeighted(enhanced, 1.4, _blur2, -0.4, 0).astype(np.uint8)

        # ── 2b. Eliminar líneas horizontales y verticales de formularios ──────
        # Los formularios PGR tienen líneas gruesas que Tesseract lee como |, -, etc.
        # Detectamos las líneas con kernels morfológicos largos y las quitamos.
        rh, rw = enhanced.shape[:2]

        # Binarización temporal para detectar líneas
        _, _bin_temp = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Detectar líneas horizontales (kernel ancho, bajo)
        h_kernel_len = max(40, rw // 15)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_len, 1))
        h_lines = cv2.morphologyEx(_bin_temp, cv2.MORPH_OPEN, h_kernel, iterations=1)

        # Detectar líneas verticales (kernel alto, angosto)
        v_kernel_len = max(40, rh // 15)
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_len))
        v_lines = cv2.morphologyEx(_bin_temp, cv2.MORPH_OPEN, v_kernel, iterations=1)

        # Combinar líneas detectadas
        all_lines = cv2.add(h_lines, v_lines)

        # Dilatar un poco las líneas para cubrir bordes difusos
        all_lines = cv2.dilate(all_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)

        # Quitar las líneas: donde hay línea → poner blanco (255 en la imagen enhanced)
        enhanced = np.where(all_lines > 0, 255, enhanced).astype(np.uint8)

        # ── 3. Triple binarización ────────────────────────────────────────────
        # Candidato A: Otsu
        _, bin_otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(bin_otsu) < 127:
            bin_otsu = cv2.bitwise_not(bin_otsu)

        # Candidato B: Adaptivo Gaussiano
        bin_local = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=51, C=15
        )
        if np.mean(bin_local) < 127:
            bin_local = cv2.bitwise_not(bin_local)

        # Candidato C: Niblack simplificado (media + k*std local)
        try:
            win = 51
            if enhanced.shape[0] < win or enhanced.shape[1] < win:
                win = max(3, min(enhanced.shape[0], enhanced.shape[1]) // 2 * 2 + 1)
            mean_local = cv2.blur(enhanced.astype(np.float32), (win, win))
            mean_sq = cv2.blur((enhanced.astype(np.float32)) ** 2, (win, win))
            std_local = np.sqrt(np.maximum(mean_sq - mean_local ** 2, 0))
            k_niblack = -0.2
            threshold_map = mean_local + k_niblack * std_local
            bin_niblack = np.where(enhanced > threshold_map, 255, 0).astype(np.uint8)
            if np.mean(bin_niblack) < 127:
                bin_niblack = cv2.bitwise_not(bin_niblack)
        except Exception:
            bin_niblack = bin_otsu.copy()

        # Cierre morfológico para reconectar trazos rotos
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
        bin_otsu = cv2.morphologyEx(bin_otsu, cv2.MORPH_CLOSE, kernel)
        bin_local = cv2.morphologyEx(bin_local, cv2.MORPH_CLOSE, kernel)
        bin_niblack = cv2.morphologyEx(bin_niblack, cv2.MORPH_CLOSE, kernel)

        # ── 4. Tesseract: 3 binarizaciones × 3 PSMs → mejor confianza ────────
        mejor = {'texto': '', 'confianza': 0}

        for img_bin, nombre in ((bin_otsu, 'otsu'), (bin_local, 'local'), (bin_niblack, 'niblack')):
            img_pil = Image.fromarray(img_bin)
            for psm in (6, 4, 3):
                try:
                    cfg = f'--psm {psm} --oem 1'
                    data = pytesseract.image_to_data(
                        img_pil, lang='spa', config=cfg,
                        output_type=pytesseract.Output.DICT
                    )
                    confs = [int(c) for c in data['conf']
                             if str(c).lstrip('-').isdigit() and int(c) >= 0]
                    texto = pytesseract.image_to_string(
                        img_pil, lang='spa', config=cfg
                    ).strip()
                    conf = int(statistics.mean(confs)) if confs else 0
                    if conf > mejor['confianza'] or (not mejor['texto'] and texto):
                        mejor = {'texto': texto, 'confianza': conf}
                    if conf >= 80:
                        break
                except Exception:
                    continue
            if mejor['confianza'] >= 80:
                break

        # ── 5. Rescue: si confianza < 40, intentar con imagen invertida ───────
        if mejor['confianza'] < 40:
            try:
                inv = cv2.bitwise_not(enhanced)
                clahe_inv = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
                inv = clahe_inv.apply(inv)
                _, bin_inv = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                if np.mean(bin_inv) < 127:
                    bin_inv = cv2.bitwise_not(bin_inv)
                for psm_r in (6, 4):
                    cfg_r = f'--psm {psm_r} --oem 1'
                    data_r = pytesseract.image_to_data(
                        Image.fromarray(bin_inv), lang='spa', config=cfg_r,
                        output_type=pytesseract.Output.DICT
                    )
                    confs_r = [int(c) for c in data_r['conf']
                               if str(c).lstrip('-').isdigit() and int(c) >= 0]
                    texto_r = pytesseract.image_to_string(
                        Image.fromarray(bin_inv), lang='spa', config=cfg_r
                    ).strip()
                    conf_r = int(statistics.mean(confs_r)) if confs_r else 0
                    if conf_r > mejor['confianza']:
                        mejor = {'texto': texto_r, 'confianza': conf_r}
            except Exception:
                pass

        # ── 6. Post-procesamiento y corrección de entidades ───────────────────
        texto_final = mejor['texto']

        # Limpiar líneas basura y restos de líneas de formulario
        import re
        lineas = texto_final.split('\n')
        lineas_ok = []
        for linea in lineas:
            # Quitar caracteres típicos de líneas mal leídas: |, _, ─, —, ., solo guiones
            linea_limpia = re.sub(r'^[\s|_\-─—.•·=~]+$', '', linea)
            # Quitar | al inicio y final de líneas (bordes de tabla)
            linea_limpia = re.sub(r'^\s*\|+\s*', '', linea_limpia)
            linea_limpia = re.sub(r'\s*\|+\s*$', '', linea_limpia)
            # Quitar secuencias de puntos/guiones sueltos (relleno de formulario)
            linea_limpia = re.sub(r'[._\-]{5,}', ' ', linea_limpia)
            # Solo conservar líneas con al menos 2 chars alfanuméricos
            alfa = re.sub(r'[^a-záéíóúñA-ZÁÉÍÓÚÑ0-9]', '', linea_limpia)
            if len(alfa) >= 2:
                lineas_ok.append(linea_limpia.strip())
        texto_final = '\n'.join(lineas_ok)

        # Entity correction (fechas, nombres, ubicaciones)
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
            "confianza": confianza_final
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en OCR de área: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar OCR: {str(e)}")
