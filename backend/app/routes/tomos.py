# backend/app/routes/tomos.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import shutil

from app.database import get_db
from app.models.tomo import Tomo, ContenidoOCR
from app.models.carpeta import Carpeta
from app.models.usuario import Usuario
from app.middlewares.auth_middleware import get_current_active_user
from app.utils.pdf_utils import extraer_info_pdf, validar_pdf
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Tomos"]
)


# Schemas
class TomoResponse(BaseModel):
    id: int
    nombre_archivo: str
    numero_tomo: int
    tamanio_bytes: Optional[int]
    numero_paginas: Optional[int]
    estado: str
    fecha_subida: str
    carpeta_id: int

    class Config:
        from_attributes = True


class TomoDetailResponse(BaseModel):
    id: int
    nombre_archivo: str
    numero_tomo: int
    tamanio_bytes: Optional[int]
    numero_paginas: Optional[int]
    estado: str
    fecha_subida: str
    fecha_procesamiento: Optional[str]
    carpeta_id: int
    usuario_subida: Optional[str]

    class Config:
        from_attributes = True


# ==================== CRUD TOMOS ====================

@router.get("/todos", response_model=List[TomoDetailResponse])
async def listar_todos_los_tomos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /tomos/todos
    Listar todos los tomos del sistema.
    """
    try:
        tomos = db.query(Tomo).order_by(Tomo.carpeta_id, Tomo.numero_tomo).all()

        return [
            TomoDetailResponse(
                id=t.id,
                nombre_archivo=t.nombre_archivo,
                numero_tomo=t.numero_tomo,
                tamanio_bytes=t.tamanio_bytes,
                numero_paginas=t.numero_paginas,
                estado=t.estado,
                fecha_subida=t.fecha_subida.isoformat() if t.fecha_subida else "",
                fecha_procesamiento=t.fecha_procesamiento.isoformat() if t.fecha_procesamiento else None,
                carpeta_id=t.carpeta_id,
                usuario_subida=t.usuario_subida.username if t.usuario_subida else None
            )
            for t in tomos
        ]
    except Exception as e:
        logger.error(f"Error listando tomos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al obtener tomos"
        )

@router.get("/{carpeta_id}", response_model=List[TomoDetailResponse])
async def listar_tomos_carpeta(
    carpeta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /tomos/{carpeta_id}
    Listar tomos de una carpeta específica.
    """
    # Verificar que la carpeta exista
    carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()
    if not carpeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada"
        )

    tomos = db.query(Tomo).filter(Tomo.carpeta_id == carpeta_id).order_by(Tomo.numero_tomo).all()

    return [
        TomoDetailResponse(
            id=t.id,
            nombre_archivo=t.nombre_archivo,
            numero_tomo=t.numero_tomo,
            tamanio_bytes=t.tamanio_bytes,
            numero_paginas=t.numero_paginas,
            estado=t.estado,
            fecha_subida=t.fecha_subida.isoformat() if t.fecha_subida else "",
            fecha_procesamiento=t.fecha_procesamiento.isoformat() if t.fecha_procesamiento else None,
            carpeta_id=t.carpeta_id,
            usuario_subida=t.usuario_subida.username if t.usuario_subida else None
        )
        for t in tomos
    ]


@router.get("/info/{tomo_id}", response_model=TomoDetailResponse)
async def obtener_info_tomo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /tomos/info/{tomo_id}
    Obtener información detallada de un tomo específico.
    """
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()

    if not tomo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tomo no encontrado"
        )

    return TomoDetailResponse(
        id=tomo.id,
        nombre_archivo=tomo.nombre_archivo,
        numero_tomo=tomo.numero_tomo,
        tamanio_bytes=tomo.tamanio_bytes,
        numero_paginas=tomo.numero_paginas,
        estado=tomo.estado,
        fecha_subida=tomo.fecha_subida.isoformat() if tomo.fecha_subida else "",
        fecha_procesamiento=tomo.fecha_procesamiento.isoformat() if tomo.fecha_procesamiento else None,
        carpeta_id=tomo.carpeta_id,
        usuario_subida=tomo.usuario_subida.username if tomo.usuario_subida else None
    )


@router.post("/upload", response_model=TomoResponse, status_code=status.HTTP_201_CREATED)
async def subir_tomo(
    archivo: UploadFile = File(...),
    nombre: str = Form(...),
    descripcion: Optional[str] = Form(None),
    carpeta_id: int = Form(...),
    auto_process_ocr: bool = Form(default=False, description="Procesar OCR automáticamente al subir"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    POST /tomos/upload
    Subir un nuevo tomo PDF a una carpeta.
    
    Parámetros:
    - auto_process_ocr: Si es True, inicia procesamiento OCR automáticamente en background
    """
    try:
        # Verificar que la carpeta exista
        carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()
        if not carpeta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Carpeta no encontrada"
            )

        # Verificar que sea un PDF
        if not archivo.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se permiten archivos PDF"
            )

        # Verificar tamaño del archivo (máximo 500MB)
        content = await archivo.read()
        file_size = len(content)
        
        if file_size > 500 * 1024 * 1024:  # 500MB
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="El archivo es demasiado grande. Máximo permitido: 500MB"
            )
            
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo está vacío"
            )

        # Resetear el archivo para poder leerlo nuevamente
        archivo.file.seek(0)

        # Obtener siguiente número de tomo
        ultimo_tomo = db.query(Tomo).filter(
            Tomo.carpeta_id == carpeta_id
        ).order_by(Tomo.numero_tomo.desc()).first()
        
        numero_tomo = 1 if not ultimo_tomo else ultimo_tomo.numero_tomo + 1

        # Crear directorio usando el NOMBRE del expediente (no el número)
        # Limpiar el nombre para que sea válido como nombre de carpeta
        nombre_carpeta = carpeta.nombre.replace('/', '_').replace('\\', '_').replace(':', '_')
        upload_dir = os.path.join("uploads", "tomos", nombre_carpeta)
        os.makedirs(upload_dir, exist_ok=True)

        # Generar nombre del archivo como: {nombre_expediente}_Tomo_{numero}.pdf
        filename = f"{carpeta.nombre}_Tomo_{numero_tomo}.pdf"
        # Limpiar el nombre del archivo
        filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_')
        file_path = os.path.join(upload_dir, filename)
        full_path = os.path.abspath(file_path)

        # Guardar archivo
        with open(full_path, "wb") as buffer:
            buffer.write(content)

        logger.info(f"Archivo guardado: {full_path} ({file_size / 1024 / 1024:.2f} MB)")

        # Analizar PDF para obtener información
        pdf_info = extraer_info_pdf(full_path)
        
        # Validar PDF
        validacion = validar_pdf(full_path)
        if not validacion["es_valido"]:
            # Eliminar archivo si es inválido
            os.remove(full_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF inválido: {', '.join(validacion['errores'])}"
            )

        # Determinar estado inicial
        estado_inicial = "procesado" if pdf_info["numero_paginas"] > 0 else "error"
        
        # Crear registro en base de datos
        nuevo_tomo = Tomo(
            carpeta_id=carpeta_id,
            numero_tomo=numero_tomo,
            nombre_archivo=nombre or archivo.filename,
            ruta_archivo=full_path,
            tamanio_bytes=file_size,
            numero_paginas=pdf_info["numero_paginas"],
            estado=estado_inicial,
            usuario_subida_id=current_user.id
        )

        db.add(nuevo_tomo)
        db.commit()
        db.refresh(nuevo_tomo)

        # Si hay advertencias del PDF, agregarlas al log
        if 'advertencias' in validacion and validacion['advertencias']:
            logger.warning(f"Advertencias para tomo {nuevo_tomo.id}: {validacion['advertencias']}")

        logger.info(f"Tomo subido: {nuevo_tomo.nombre_archivo} a carpeta {carpeta_id} por {current_user.username} - {pdf_info['numero_paginas']} páginas")

        # 🚀 PROCESAR OCR AUTOMÁTICAMENTE SI SE SOLICITA
        if auto_process_ocr:
            try:
                import asyncio
                from app.services.ocr_service import OCRService
                
                logger.info(f"🚀 Iniciando procesamiento OCR automático para tomo {nuevo_tomo.id}")
                
                # Iniciar procesamiento en background
                ocr_service = OCRService()
                asyncio.create_task(asyncio.to_thread(ocr_service.procesar_pdf, db, nuevo_tomo))
                
                logger.info(f"✅ OCR automático iniciado en background para tomo {nuevo_tomo.id}")
                
            except Exception as e:
                logger.error(f"⚠️ Error iniciando OCR automático: {e}")
                # No fallar el upload si el OCR falla, solo registrar el error

        return TomoResponse(
            id=nuevo_tomo.id,
            nombre_archivo=nuevo_tomo.nombre_archivo,
            numero_tomo=nuevo_tomo.numero_tomo,
            tamanio_bytes=nuevo_tomo.tamanio_bytes,
            numero_paginas=nuevo_tomo.numero_paginas,
            estado=nuevo_tomo.estado,
            fecha_subida=nuevo_tomo.fecha_subida.isoformat(),
            carpeta_id=nuevo_tomo.carpeta_id
        )

    except HTTPException:
        raise
    except Exception as e:
        # Eliminar archivo si hubo error
        if 'full_path' in locals() and os.path.exists(full_path):
            os.remove(full_path)

        logger.error(f"Error al subir tomo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar archivo: {str(e)}"
        )


@router.put("/{tomo_id}/reanalizar")
async def reanalizar_tomo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    PUT /tomos/{tomo_id}/reanalizar
    Reanalizar un tomo para actualizar información del PDF.
    """
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()

    if not tomo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tomo no encontrado"
        )

    if not os.path.exists(tomo.ruta_archivo):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo PDF no encontrado en el servidor"
        )

    try:
        # Reanalizar PDF
        pdf_info = extraer_info_pdf(tomo.ruta_archivo)
        validacion = validar_pdf(tomo.ruta_archivo)

        # Actualizar información
        tomo.numero_paginas = pdf_info["numero_paginas"]
        tomo.estado = "procesado" if validacion["es_valido"] and pdf_info["numero_paginas"] > 0 else "error"
        tomo.fecha_procesamiento = datetime.now()

        db.commit()
        db.refresh(tomo)

        logger.info(f"Tomo reanalizado: {tomo.nombre_archivo} - {pdf_info['numero_paginas']} páginas")

        return {
            "message": "Tomo reanalizado correctamente",
            "tomo_id": tomo_id,
            "numero_paginas": pdf_info["numero_paginas"],
            "estado": tomo.estado,
            "advertencias": validacion.get("advertencias", [])
        }

    except Exception as e:
        logger.error(f"Error al reanalizar tomo {tomo_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al reanalizar tomo: {str(e)}"
        )


@router.put("/carpeta/{carpeta_id}/reanalizar-todos")
async def reanalizar_todos_tomos_carpeta(
    carpeta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    PUT /tomos/carpeta/{carpeta_id}/reanalizar-todos
    Reanalizar todos los tomos de una carpeta.
    """
    # Verificar que la carpeta exista
    carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()
    if not carpeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada"
        )

    try:
        # Obtener todos los tomos de la carpeta
        tomos = db.query(Tomo).filter(Tomo.carpeta_id == carpeta_id).all()
        
        if not tomos:
            return {
                "message": "No hay tomos en esta carpeta",
                "procesados": 0,
                "errores": 0
            }

        procesados = 0
        errores = 0
        
        for tomo in tomos:
            try:
                if not os.path.exists(tomo.ruta_archivo):
                    logger.warning(f"Archivo no encontrado: {tomo.ruta_archivo}")
                    tomo.estado = "error"
                    errores += 1
                    continue

                # Reanalizar PDF
                pdf_info = extraer_info_pdf(tomo.ruta_archivo)
                validacion = validar_pdf(tomo.ruta_archivo)

                # Actualizar información
                tomo.numero_paginas = pdf_info["numero_paginas"]
                tomo.estado = "procesado" if validacion["es_valido"] and pdf_info["numero_paginas"] > 0 else "error"
                tomo.fecha_procesamiento = datetime.now()
                
                procesados += 1
                
            except Exception as e:
                logger.error(f"Error al reanalizar tomo {tomo.id}: {str(e)}")
                tomo.estado = "error"
                errores += 1

        db.commit()

        logger.info(f"Reanálisis completado para carpeta {carpeta_id}: {procesados} exitosos, {errores} errores")

        return {
            "message": "Reanálisis completado",
            "carpeta_id": carpeta_id,
            "total_tomos": len(tomos),
            "procesados": procesados,
            "errores": errores
        }

    except Exception as e:
        logger.error(f"Error al reanalizar tomos de carpeta {carpeta_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al reanalizar tomos: {str(e)}"
        )


@router.delete("/{tomo_id}")
async def eliminar_tomo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    DELETE /tomos/{tomo_id}
    Eliminar tomo y todos sus datos relacionados.
    """
    from app.services.notificacion_service import NotificacionService

    try:
        tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()

        if not tomo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tomo no encontrado"
            )

        # Guardar información antes de eliminar
        file_path = tomo.ruta_archivo
        tomo_nombre = tomo.nombre_archivo
        carpeta_id = tomo.carpeta_id

        # Eliminar registro de la base de datos (esto eliminará en cascada todos los registros relacionados)
        db.delete(tomo)
        db.commit()

        # Intentar eliminar archivo físico
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Archivo eliminado: {file_path}")
            except Exception as e:
                logger.error(f"Error al eliminar archivo físico: {str(e)}")
                # No fallar por este error

        # Crear notificación para el usuario que subió el tomo y el usuario que lo eliminó
        notificacion_service = NotificacionService(db)
        
        # Notificar al usuario que subió el tomo
        if tomo.usuario_subida_id and tomo.usuario_subida_id != current_user.id:
            notificacion_service.notificar_eliminacion_tomo(
                usuario_id=tomo.usuario_subida_id,
                tomo_nombre=tomo_nombre,
                tomo_id=tomo_id,
                carpeta_id=carpeta_id
            )
        
        # Notificar al usuario que eliminó el tomo
        notificacion_service.notificar_eliminacion_tomo(
            usuario_id=current_user.id,
            tomo_nombre=tomo_nombre,
            tomo_id=tomo_id,
            carpeta_id=carpeta_id
        )

        logger.info(f"Tomo eliminado: {tomo_nombre} por {current_user.username}")

        return {
            "message": "Tomo eliminado correctamente",
            "tomo_id": tomo_id,
            "notificacion_enviada": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar tomo {tomo_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor al eliminar el tomo: {str(e)}"
        )


@router.get("/info/{tomo_id}", response_model=TomoDetailResponse)
async def obtener_info_tomo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /tomos/info/{tomo_id}
    Obtener información de un tomo específico para el visor.
    """
    # Verificar que el tomo existe
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tomo no encontrado"
        )

    # Verificar permisos del usuario sobre este tomo
    from app.models.permiso_tomo import PermisoTomo
    
    # Solo admin puede ver sin restricciones
    es_admin = current_user.rol.nombre in ["admin", "administrador"]
    
    if not es_admin:
        # Buscar permiso específico para este tomo
        permiso = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == current_user.id,
            PermisoTomo.tomo_id == tomo_id
        ).first()

        # Validar que existe el permiso Y que puede_ver es True
        if not permiso:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos asignados para este tomo"
            )
        
        if not permiso.puede_ver:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso de visualización para este tomo"
            )

    return TomoDetailResponse(
        id=tomo.id,
        nombre_archivo=tomo.nombre_archivo,
        numero_tomo=tomo.numero_tomo,
        tamanio_bytes=tomo.tamanio_bytes,
        numero_paginas=tomo.numero_paginas,
        estado=tomo.estado,
        fecha_subida=tomo.fecha_subida.isoformat() if tomo.fecha_subida else "",
        fecha_procesamiento=tomo.fecha_procesamiento.isoformat() if tomo.fecha_procesamiento else None,
        carpeta_id=tomo.carpeta_id,
        usuario_subida=tomo.usuario_subida.username if tomo.usuario_subida else None
    )


@router.get("/pdf/{tomo_id}")
async def visualizar_tomo_pdf(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /tomos/pdf/{tomo_id}
    Servir PDF para visualización sin descarga con validación de permisos.
    """
    # Verificar que el tomo existe
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tomo no encontrado"
        )

    # Verificar permisos del usuario sobre este tomo
    from app.models.permiso_tomo import PermisoTomo
    
    # Solo admin puede ver sin restricciones
    es_admin = current_user.rol.nombre in ["admin", "administrador"]
    
    if not es_admin:
        # Buscar permiso específico para este tomo
        permiso = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == current_user.id,
            PermisoTomo.tomo_id == tomo_id
        ).first()

        # Validar que existe el permiso Y que puede_ver es True
        if not permiso:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos asignados para este tomo"
            )
        
        if not permiso.puede_ver:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso de visualización para este tomo"
            )

    # Verificar que el archivo existe
    if not os.path.exists(tomo.ruta_archivo):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado en el servidor"
        )

    from fastapi.responses import FileResponse
    return FileResponse(
        path=tomo.ruta_archivo,
        media_type='application/pdf',
        headers={
            "Content-Disposition": "inline",  # Para visualizar en el navegador, no descargar
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.get("/ocr/{tomo_id}/pagina/{numero_pagina}")
async def obtener_texto_ocr_pagina(
    tomo_id: int,
    numero_pagina: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /tomos/ocr/{tomo_id}/pagina/{numero_pagina}
    Obtener texto OCR de una página específica de un tomo.
    Útil para PDFs escaneados que no tienen texto nativo.
    """
    # Verificar que el tomo existe
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tomo no encontrado"
        )

    # Verificar permisos del usuario
    from app.models.permiso_tomo import PermisoTomo
    es_admin = current_user.rol.nombre in ["admin", "administrador"]
    
    if not es_admin:
        permiso = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == current_user.id,
            PermisoTomo.tomo_id == tomo_id
        ).first()

        if not permiso or not permiso.puede_ver:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para visualizar este tomo"
            )

    # Buscar texto OCR de la página
    contenido_ocr = db.query(ContenidoOCR).filter(
        ContenidoOCR.tomo_id == tomo_id,
        ContenidoOCR.numero_pagina == numero_pagina
    ).first()

    if not contenido_ocr:
        return {
            "tomo_id": tomo_id,
            "numero_pagina": numero_pagina,
            "texto_extraido": "",
            "confianza": None,
            "mensaje": "No se encontró texto OCR para esta página"
        }

    return {
        "tomo_id": tomo_id,
        "numero_pagina": numero_pagina,
        "texto_extraido": contenido_ocr.texto_extraido or "",
        "confianza": float(contenido_ocr.confianza) if contenido_ocr.confianza else None,
        "created_at": contenido_ocr.created_at.isoformat() if contenido_ocr.created_at else None
    }


@router.get("/download/{tomo_id}")
async def descargar_tomo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /tomos/download/{tomo_id}
    Descargar archivo PDF de un tomo.
    """
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()

    if not tomo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tomo no encontrado"
        )

    if not os.path.exists(tomo.ruta_archivo):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo no encontrado en el servidor"
        )

    from fastapi.responses import FileResponse
    return FileResponse(
        path=tomo.ruta_archivo,
        filename=tomo.nombre_archivo,
        media_type='application/pdf'
    )


@router.get("/{tomo_id}/contenido-ocr")
async def obtener_contenido_ocr(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /tomos/{tomo_id}/contenido-ocr
    
    Obtiene el contenido OCR extraído de un tomo.
    Muestra el número de página FÍSICO del PDF (1, 2, 3...).
    
    **IMPORTANTE:**
    - numero_pagina = Página física del PDF original
    - No es el número que aparece impreso en el documento
    - Ejemplo: Página 3 del PDF puede tener escrito "1" en el documento
    
    Returns:
        - tomo_id: ID del tomo
        - tomo_nombre: Nombre del archivo
        - total_paginas: Total de páginas procesadas
        - contenido: Lista de páginas con:
            - numero_pagina: Número físico de la página en el PDF
            - texto_extraido: Texto extraído por OCR
            - confianza: Confianza del OCR (0-1)
            - es_caratula: Si fue detectada como carátula
            - razon: Razón por la que se marcó como carátula
    """
    from app.controllers.tomo_controller import tomo_controller
    
    resultado = tomo_controller.obtener_contenido_ocr(
        db=db,
        tomo_id=tomo_id,
        current_user_id=current_user.id
    )
    
    if not resultado.get('success'):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=resultado.get('message', 'No hay contenido OCR disponible')
        )
    
    return resultado
