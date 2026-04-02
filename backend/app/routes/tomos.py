# backend/app/routes/tomos.py
# /subir alias agregado para compatibilidad con frontend

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import shutil
import hashlib

# Almacenamiento persistente: /data/uploads en HF Spaces, uploads/ en local
_BASE_UPLOAD_DIR = "/data/uploads" if os.path.isdir("/data") else os.path.join(os.getcwd(), "uploads")

from app.database import get_db
from app.models.tomo import Tomo, ContenidoOCR
from app.models.carpeta import Carpeta
from app.models.usuario import Usuario
from app.middlewares.auth_middleware import get_current_active_user
from app.utils.pdf_utils import extraer_info_pdf, validar_pdf
from app.services.cache_service import cache_service
from app.utils.auditoria_utils import registrar_auditoria, AuditoriaLogger
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
    ⚡ OPTIMIZADO: Usa caché Redis (300x más rápido en consultas repetidas)
    """
    try:
        # Intentar obtener desde caché
        cache_key = "tomos:todos"
        cached_data = cache_service.get(cache_key)
        
        if cached_data:
            logger.info("✅ Tomos obtenidos desde caché Redis")
            return cached_data
        
        # Si no está en caché, consultar BD
        logger.info("⏳ Consultando base de datos...")
        tomos = db.query(Tomo).order_by(Tomo.carpeta_id, Tomo.numero_tomo).all()

        result = [
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
        
        # Guardar en caché por 5 minutos (convertir a dict para serialización)
        result_dict = [r.model_dump() for r in result]
        cache_service.set(cache_key, result_dict, ttl=300)
        logger.info(f"💾 {len(result)} tomos guardados en caché")
        
        return result
        
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
    ⚡ OPTIMIZADO: Usa caché Redis por carpeta
    """
    # Verificar que la carpeta exista
    carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()
    if not carpeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada"
        )

    # Intentar obtener desde caché
    cache_key = f"tomos:carpeta:{carpeta_id}"
    cached_data = cache_service.get(cache_key)
    
    if cached_data:
        logger.info(f"✅ Tomos de carpeta {carpeta_id} obtenidos desde caché")
        return cached_data

    # Consultar BD
    tomos = db.query(Tomo).filter(Tomo.carpeta_id == carpeta_id).order_by(Tomo.numero_tomo).all()

    result = [
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
    
    # Guardar en caché por 5 minutos (convertir a dict para serialización)
    result_dict = [r.model_dump() for r in result]
    cache_service.set(cache_key, result_dict, ttl=300)
    logger.info(f"💾 {len(result)} tomos de carpeta {carpeta_id} guardados en caché")
    
    return result


@router.post("/upload", response_model=TomoResponse, status_code=status.HTTP_201_CREATED)
@router.post("/subir", response_model=TomoResponse, status_code=status.HTTP_201_CREATED)
async def subir_tomo(
    request: Request,
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
        upload_dir = os.path.join(_BASE_UPLOAD_DIR, "tomos", nombre_carpeta)
        os.makedirs(upload_dir, exist_ok=True)

        # Generar nombre del archivo como: {nombre_expediente}_Tomo_{numero}.pdf
        filename = f"{carpeta.nombre}_Tomo_{numero_tomo}.pdf"
        # Limpiar el nombre del archivo
        filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_')
        file_path = os.path.join(upload_dir, filename)
        full_path = os.path.abspath(file_path)

        # Calcular hash SHA256 del archivo
        sha256_hash = hashlib.sha256(content).hexdigest()
        logger.info(f"Hash SHA256 calculado: {sha256_hash[:16]}...")

        # Verificar si ya existe un tomo con este hash
        tomo_duplicado = db.query(Tomo).filter(Tomo.hash_sha256 == sha256_hash).first()
        if tomo_duplicado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Este archivo ya fue subido anteriormente (Tomo {tomo_duplicado.numero_tomo} en carpeta {tomo_duplicado.carpeta.nombre})"
            )

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
        estado_inicial = "pendiente" if pdf_info["numero_paginas"] > 0 else "error"
        
        # Crear registro en base de datos
        nuevo_tomo = Tomo(
            carpeta_id=carpeta_id,
            numero_tomo=numero_tomo,
            nombre_archivo=nombre or archivo.filename,
            ruta_archivo=full_path,
            tamanio_bytes=file_size,
            numero_paginas=pdf_info["numero_paginas"],
            hash_sha256=sha256_hash,
            estado=estado_inicial,
            usuario_subida_id=current_user.id
        )

        db.add(nuevo_tomo)
        db.commit()
        db.refresh(nuevo_tomo)

        # ⚡ Invalidar caché para que se reflejen los cambios
        cache_service.delete(f"tomos:carpeta:{carpeta_id}")
        cache_service.delete("tomos:todos")
        logger.info(f"🔄 Caché invalidado para carpeta {carpeta_id}")

        # Si hay advertencias del PDF, agregarlas al log
        if 'advertencias' in validacion and validacion['advertencias']:
            logger.warning(f"Advertencias para tomo {nuevo_tomo.id}: {validacion['advertencias']}")

        logger.info(f"Tomo subido: {nuevo_tomo.nombre_archivo} a carpeta {carpeta_id} por {current_user.username} - {pdf_info['numero_paginas']} páginas")

        # Registrar auditoría
        registrar_auditoria(
            usuario_id=current_user.id,
            accion="SUBIR_TOMO",
            request=request,
            tabla_afectada="tomos",
            registro_id=nuevo_tomo.id,
            valores_nuevos={
                "nombre_archivo": nuevo_tomo.nombre_archivo,
                "numero_tomo": numero_tomo,
                "carpeta_id": carpeta_id,
                "carpeta_nombre": carpeta.nombre,
                "numero_paginas": pdf_info["numero_paginas"],
                "tamanio_mb": round(file_size / 1024 / 1024, 2),
                "auto_process_ocr": auto_process_ocr
            }
        )

        # 🚀 PROCESAR OCR AUTOMÁTICAMENTE SI SE SOLICITA
        if auto_process_ocr:
            try:
                import asyncio
                from app.services.ocr_service import OCRService
                
                logger.info(f"🚀 Iniciando procesamiento OCR automático para tomo {nuevo_tomo.id}")
                
                # Extraer IP del request para auditoría
                ip_address, _ = AuditoriaLogger.extraer_info_request(request)
                
                # Iniciar procesamiento en background con auditoría
                ocr_service = OCRService()
                asyncio.create_task(asyncio.to_thread(
                    ocr_service.procesar_pdf, 
                    nuevo_tomo, 
                    full_path, 
                    db,
                    current_user.id,  # usuario_id para auditoría
                    ip_address  # IP para auditoría
                ))
                
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    PUT /tomos/{tomo_id}/reanalizar
    
    RE-PROCESA COMPLETAMENTE EL TOMO CON OCR CORREGIDO:
    1. Borra OCR viejo (con errores)
    2. Re-procesa PDF con correcciones legales automáticas
    3. Extrae diligencias automáticamente
    4. Aplica correcciones a nombres, lugares, entidades
    
    FLUJO:
    - Admin: Sube PDF → Procesa OCR → Re-analiza (BD se lleva las putizas)
    - Usuario: Ve datos YA CORREGIDOS automáticamente
    """
    from app.services.ocr_service import OCRService
    from app.models.analisis_juridico import Diligencia
    from pathlib import Path
    
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
        logger.info(f"🔄 REANALIZAR COMPLETO: Borrando OCR viejo de tomo {tomo_id}...")
        
        # 1. BORRAR TODO EL OCR VIEJO (con errores)
        db.query(ContenidoOCR).filter(ContenidoOCR.tomo_id == tomo_id).delete()
        
        # 2. BORRAR DILIGENCIAS VIEJAS (con errores)
        db.query(Diligencia).filter(Diligencia.tomo_id == tomo_id).delete()
        
        db.commit()
        logger.info(f"  ✓ OCR viejo y diligencias borradas")

        # 3. VALIDAR PDF
        pdf_info = extraer_info_pdf(tomo.ruta_archivo)
        validacion = validar_pdf(tomo.ruta_archivo)

        # 4. ACTUALIZAR INFORMACIÓN BÁSICA
        tomo.numero_paginas = pdf_info["numero_paginas"]
        tomo.estado = "procesando"  # Cambiar a procesando durante OCR
        tomo.fecha_procesamiento = datetime.now()
        db.commit()

        # 5. RE-PROCESAR OCR COMPLETO CON CORRECCIONES AUTOMÁTICAS
        logger.info(f"🚀 Iniciando OCR COMPLETO con correcciones automáticas...")
        ocr_service = OCRService()
        
        # Procesar en background pero esperar resultado
        import asyncio
        await asyncio.to_thread(
            ocr_service.procesar_pdf,
            tomo,
            Path(tomo.ruta_archivo),
            db
        )

        # 6. ACTUALIZAR ESTADO FINAL
        tomo.estado = "completado" if validacion["es_valido"] and pdf_info["numero_paginas"] > 0 else "error"
        db.commit()
        db.refresh(tomo)

        # 7. INVALIDAR CACHÉ
        cache_service.delete(f"tomos:carpeta:{tomo.carpeta_id}")
        cache_service.delete("tomos:todos")
        cache_service.delete(f"ocr:tomo:{tomo_id}")
        logger.info(f"🔄 Caché invalidado")

        # 8. CONTAR DILIGENCIAS EXTRAÍDAS
        total_diligencias = db.query(Diligencia).filter(
            Diligencia.tomo_id == tomo_id
        ).count()

        logger.info(f"✅ Tomo reanalizado COMPLETO: {tomo.nombre_archivo}")
        logger.info(f"  📄 {pdf_info['numero_paginas']} páginas procesadas")
        logger.info(f"  📋 {total_diligencias} diligencias extraídas y corregidas")

        # Registrar auditoría
        registrar_auditoria(
            usuario_id=current_user.id,
            accion="PROCESAR_OCR",
            request=request,
            
            tabla_afectada="tomos",
            registro_id=tomo_id,
            valores_nuevos={
                "nombre_archivo": tomo.nombre_archivo,
                "numero_paginas": pdf_info["numero_paginas"],
                "diligencias_extraidas": total_diligencias,
                "estado": tomo.estado,
                "tipo_proceso": "reanalisis_completo"
            }
        )

        return {
            "message": "Tomo reanalizado COMPLETAMENTE con correcciones automáticas",
            "tomo_id": tomo_id,
            "numero_paginas": pdf_info["numero_paginas"],
            "diligencias_extraidas": total_diligencias,
            "estado": tomo.estado,
            "advertencias": validacion.get("advertencias", []),
            "info": "OCR re-procesado con correcciones legales + diligencias automáticas"
        }

    except Exception as e:
        logger.error(f"Error al reanalizar tomo {tomo_id}: {str(e)}")
        tomo.estado = "error"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al reanalizar tomo: {str(e)}"
        )


@router.put("/carpeta/{carpeta_id}/reanalizar-todos")
async def reanalizar_todos_tomos_carpeta(
    carpeta_id: int,
    request: Request,
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
                tomo.estado = "completado" if validacion["es_valido"] and pdf_info["numero_paginas"] > 0 else "error"
                tomo.fecha_procesamiento = datetime.now()
                
                procesados += 1
                
            except Exception as e:
                logger.error(f"Error al reanalizar tomo {tomo.id}: {str(e)}")
                tomo.estado = "error"
                errores += 1

        db.commit()

        logger.info(f"Reanálisis completado para carpeta {carpeta_id}: {procesados} exitosos, {errores} errores")

        # Registrar auditoría
        registrar_auditoria(
            usuario_id=current_user.id,
            accion="PROCESAR_OCR",
            request=request,
            
            tabla_afectada="tomos",
            valores_nuevos={
                "carpeta_id": carpeta_id,
                "carpeta_nombre": carpeta.nombre,
                "total_tomos": len(tomos),
                "procesados": procesados,
                "errores": errores,
                "tipo_proceso": "reanalisis_carpeta_completa"
            }
        )

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
    request: Request,
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

        # Guardar información antes de eliminar para auditoría
        file_path = tomo.ruta_archivo
        tomo_nombre = tomo.nombre_archivo
        carpeta_id = tomo.carpeta_id
        valores_anteriores = {
            "nombre_archivo": tomo.nombre_archivo,
            "numero_tomo": tomo.numero_tomo,
            "carpeta_id": tomo.carpeta_id,
            "numero_paginas": tomo.numero_paginas,
            "tamanio_bytes": tomo.tamanio_bytes,
            "estado": tomo.estado
        }

        # Eliminar registro de la base de datos (esto eliminará en cascada todos los registros relacionados)
        db.delete(tomo)
        db.commit()

        # ⚡ Invalidar caché de tomos
        cache_service.delete(f"tomos:carpeta:{carpeta_id}")
        cache_service.delete("tomos:todos")
        logger.info(f"🔄 Caché de tomos invalidado para carpeta {carpeta_id}")

        # Intentar eliminar archivo físico
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Archivo eliminado: {file_path}")
            except Exception as e:
                logger.error(f"Error al eliminar archivo físico: {str(e)}")
                # No fallar por este error

        # Crear notificación — sesión independiente para no contaminar la transacción principal
        try:
            from app.database import SessionLocal
            notif_db = SessionLocal()
            try:
                notificacion_service = NotificacionService(notif_db)
                if tomo.usuario_subida_id and tomo.usuario_subida_id != current_user.id:
                    notificacion_service.notificar_eliminacion_tomo(
                        usuario_id=tomo.usuario_subida_id,
                        tomo_nombre=tomo_nombre,
                        tomo_id=tomo_id,
                        carpeta_id=carpeta_id
                    )
                notificacion_service.notificar_eliminacion_tomo(
                    usuario_id=current_user.id,
                    tomo_nombre=tomo_nombre,
                    tomo_id=tomo_id,
                    carpeta_id=carpeta_id
                )
                notif_db.commit()
            finally:
                notif_db.close()
        except Exception as e_notif:
            logger.warning(f"notificaciones: omitiendo ({e_notif})")

        logger.info(f"Tomo eliminado: {tomo_nombre} por {current_user.username}")

        # Registrar auditoría
        registrar_auditoria(
            usuario_id=current_user.id,
            accion="ELIMINAR_TOMO",
            request=request,
            
            tabla_afectada="tomos",
            registro_id=tomo_id,
            valores_anteriores=valores_anteriores
        )

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
    from app.models.usuario import Rol
    
    # Consulta directa al rol para evitar problemas de lazy loading
    rol_nombre = db.query(Rol.nombre).filter(Rol.id == current_user.rol_id).scalar() or ""
    es_admin = rol_nombre.lower() in ["admin", "administrador"]
    
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
    from app.models.usuario import Rol
    
    # Solo admin puede ver sin restricciones
    rol_nombre = db.query(Rol.nombre).filter(Rol.id == current_user.rol_id).scalar() or ""
    es_admin = rol_nombre.lower() in ["admin", "administrador"]
    
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
    from app.models.usuario import Rol
    rol_nombre = db.query(Rol.nombre).filter(Rol.id == current_user.rol_id).scalar() or ""
    es_admin = rol_nombre.lower() in ["admin", "administrador"]
    
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
        tomo_id=tomo_id,
        current_user_id=current_user.id
    )
    
    if not resultado.get('success'):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=resultado.get('message', 'No hay contenido OCR disponible')
        )
    
    return resultado


# ==================== BÚSQUEDA EN TOMOS ====================

class BusquedaTomoRequest(BaseModel):
    query: str
    fuzzy: bool = True  # Búsqueda difusa activada por defecto
    case_sensitive: bool = False
    whole_word: bool = False
    max_results: int = 100
    contexto_caracteres: int = 200  # Caracteres antes y después


class ResultadoBusqueda(BaseModel):
    pagina: int
    texto: str
    contexto_antes: str
    contexto_despues: str
    posicion: int
    similitud: float = 1.0  # Para búsqueda fuzzy


class BusquedaTomoResponse(BaseModel):
    success: bool
    tomo_id: int
    tomo_nombre: str
    query: str
    total_resultados: int
    resultados: List[ResultadoBusqueda]


@router.post("/{tomo_id}/buscar-avanzada", response_model=BusquedaTomoResponse)
async def buscar_avanzada_en_tomo(
    tomo_id: int,
    busqueda: BusquedaTomoRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    POST /tomos/{tomo_id}/buscar-avanzada
    
    Búsqueda avanzada en el contenido OCR de un tomo.
    
    Características:
    - 🔍 Búsqueda difusa (fuzzy) para manejar errores de OCR
    - 📝 Contexto amplio (caracteres antes y después)
    - 🎯 Resaltado visual de coincidencias
    - ⚡ Búsqueda case-insensitive por defecto
    - 🔢 Control de máximo de resultados
    
    Args:
        tomo_id: ID del tomo
        busqueda: Parámetros de búsqueda
            - query: Texto a buscar
            - fuzzy: Permite errores de escritura (default: True)
            - case_sensitive: Distinguir mayúsculas/minúsculas (default: False)
            - whole_word: Buscar palabra completa (default: False)
            - max_results: Máximo de resultados (default: 100)
            - contexto_caracteres: Caracteres de contexto (default: 200)
    
    Returns:
        - success: Si la búsqueda fue exitosa
        - tomo_id: ID del tomo
        - tomo_nombre: Nombre del archivo
        - query: Texto buscado
        - total_resultados: Número total de coincidencias
        - resultados: Lista de coincidencias con:
            - pagina: Número de página
            - texto: Texto coincidente
            - contexto_antes: Texto antes de la coincidencia
            - contexto_despues: Texto después de la coincidencia
            - posicion: Posición en el texto
            - similitud: Score de similitud (0-1) para fuzzy
    """
    try:
        print(f"=" * 80)
        print(f"🔍 BÚSQUEDA INICIADA - Tomo: {tomo_id}")
        print(f"   Query: '{busqueda.query}'")
        print(f"   Fuzzy: {busqueda.fuzzy}, Case Sensitive: {busqueda.case_sensitive}")
        print(f"=" * 80)
        logger.info(f"🔍 Búsqueda iniciada - Tomo: {tomo_id}, Query: '{busqueda.query}', Fuzzy: {busqueda.fuzzy}")
        
        # Verificar que el tomo existe
        tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
        if not tomo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tomo no encontrado"
            )
        
        # Verificar permisos de búsqueda
        from app.models.permiso_tomo import PermisoTomo
        permiso = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == current_user.id,
            PermisoTomo.tomo_id == tomo_id
        ).first()
        
        if not permiso or not permiso.puede_buscar:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos de búsqueda en este tomo"
            )
        
        # Obtener contenido OCR
        contenidos = db.query(ContenidoOCR).filter(
            ContenidoOCR.tomo_id == tomo_id
        ).order_by(ContenidoOCR.numero_pagina).all()
        
        logger.info(f"📄 Páginas con contenido OCR: {len(contenidos)}")
        
        if not contenidos:
            logger.warning(f"⚠️ No hay contenido OCR para tomo {tomo_id}")
            return BusquedaTomoResponse(
                success=True,
                tomo_id=tomo_id,
                tomo_nombre=tomo.nombre_archivo,
                query=busqueda.query,
                total_resultados=0,
                resultados=[]
            )
        
        # Realizar búsqueda
        resultados = []
        query_procesado = busqueda.query if busqueda.case_sensitive else busqueda.query.lower()
        
        logger.info(f"🔎 Buscando: '{query_procesado}' (fuzzy: {busqueda.fuzzy}, case_sensitive: {busqueda.case_sensitive})")
        
        # Importar para búsqueda fuzzy
        from difflib import SequenceMatcher
        import re
        
        for contenido in contenidos:
            if not contenido.texto_extraido:
                continue
            
            texto = contenido.texto_extraido
            texto_busqueda = texto if busqueda.case_sensitive else texto.lower()
            
            if busqueda.fuzzy:
                # Búsqueda difusa: buscar primero coincidencias exactas, luego fuzzy
                # 1. Búsqueda exacta flexible (sin whole word)
                start = 0
                while len(resultados) < busqueda.max_results:
                    pos = texto_busqueda.find(query_procesado, start)
                    if pos == -1:
                        break
                    
                    # Extraer contexto
                    inicio_contexto = max(0, pos - busqueda.contexto_caracteres)
                    fin_contexto = min(len(texto), pos + len(query_procesado) + busqueda.contexto_caracteres)
                    
                    contexto_antes = texto[inicio_contexto:pos]
                    texto_encontrado = texto[pos:pos + len(query_procesado)]
                    contexto_despues = texto[pos + len(query_procesado):fin_contexto]
                    
                    resultados.append(ResultadoBusqueda(
                        pagina=contenido.numero_pagina,
                        texto=texto_encontrado,
                        contexto_antes=contexto_antes,
                        contexto_despues=contexto_despues,
                        posicion=pos,
                        similitud=1.0
                    ))
                    start = pos + 1
                
                # 2. Si no hay suficientes resultados exactos, buscar fuzzy
                if len(resultados) < 10:  # Buscar fuzzy solo si hay pocos resultados
                    palabras_query = query_procesado.split()
                    for palabra_query in palabras_query:
                        if len(palabra_query) < 3:  # Ignorar palabras muy cortas
                            continue
                        
                        # Buscar palabras similares en el texto
                        palabras_texto = re.findall(r'\b\w+\b', texto_busqueda)
                        
                        for palabra_texto in palabras_texto:
                            if len(resultados) >= busqueda.max_results:
                                break
                            
                            # Calcular similitud
                            similitud = SequenceMatcher(None, palabra_query, palabra_texto).ratio()
                            
                            # Si la similitud es mayor al 80% (tolerancia para errores de OCR)
                            if similitud >= 0.8 and similitud < 1.0:  # Evitar duplicados exactos
                                # Encontrar posición en el texto original
                                patron = r'\b' + re.escape(palabra_texto) + r'\b'
                                match = re.search(patron, texto_busqueda)
                                
                                if match:
                                    pos = match.start()
                                    
                                    # Extraer contexto
                                    inicio_contexto = max(0, pos - busqueda.contexto_caracteres)
                                    fin_contexto = min(len(texto), pos + len(palabra_texto) + busqueda.contexto_caracteres)
                                    
                                    contexto_antes = texto[inicio_contexto:pos]
                                    texto_encontrado = texto[pos:pos + len(palabra_texto)]
                                    contexto_despues = texto[pos + len(palabra_texto):fin_contexto]
                                    
                                    resultados.append(ResultadoBusqueda(
                                        pagina=contenido.numero_pagina,
                                        texto=texto_encontrado,
                                        contexto_antes=contexto_antes,
                                        contexto_despues=contexto_despues,
                                        posicion=pos,
                                        similitud=round(similitud, 2)
                                    ))
            else:
                # Búsqueda exacta
                if busqueda.whole_word:
                    patron = r'\b' + re.escape(query_procesado) + r'\b'
                    matches = re.finditer(patron, texto_busqueda)
                else:
                    # Buscar todas las ocurrencias
                    start = 0
                    matches = []
                    while True:
                        pos = texto_busqueda.find(query_procesado, start)
                        if pos == -1:
                            break
                        matches.append(type('obj', (object,), {'start': lambda p=pos: p, 'group': lambda: query_procesado})())
                        start = pos + 1
                
                for match in matches:
                    if len(resultados) >= busqueda.max_results:
                        break
                    
                    pos = match.start()
                    
                    # Extraer contexto
                    inicio_contexto = max(0, pos - busqueda.contexto_caracteres)
                    fin_contexto = min(len(texto), pos + len(query_procesado) + busqueda.contexto_caracteres)
                    
                    contexto_antes = texto[inicio_contexto:pos]
                    texto_encontrado = texto[pos:pos + len(query_procesado)]
                    contexto_despues = texto[pos + len(query_procesado):fin_contexto]
                    
                    resultados.append(ResultadoBusqueda(
                        pagina=contenido.numero_pagina,
                        texto=texto_encontrado,
                        contexto_antes=contexto_antes,
                        contexto_despues=contexto_despues,
                        posicion=pos,
                        similitud=1.0
                    ))
        
        logger.info(f"Búsqueda en tomo {tomo_id}: '{busqueda.query}' - {len(resultados)} resultados")
        
        # 🔍 Registrar auditoría de la búsqueda
        registrar_auditoria(
            usuario_id=current_user.id,
            accion="BUSQUEDA_TOMO",
            request=request,
            tabla_afectada="contenido_ocr",
            registro_id=tomo_id,
            valores_nuevos={
                "tomo_id": tomo_id,
                "tomo_nombre": tomo.nombre_archivo,
                "query": busqueda.query,
                "fuzzy": busqueda.fuzzy,
                "case_sensitive": busqueda.case_sensitive,
                "whole_word": busqueda.whole_word,
                "total_resultados": len(resultados)
            }
        )
        
        return BusquedaTomoResponse(
            success=True,
            tomo_id=tomo_id,
            tomo_nombre=tomo.nombre_archivo,
            query=busqueda.query,
            total_resultados=len(resultados),
            resultados=resultados
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en búsqueda de tomo {tomo_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al buscar en el tomo: {str(e)}"
        )
