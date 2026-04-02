# backend/app/routes/carpetas.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
import re
from datetime import datetime

from app.database import get_db
from app.models.carpeta import Carpeta
from app.models.tomo import Tomo
from app.models.usuario import Usuario
from app.models.analisis_ia import AnalisisIA
from app.middlewares.auth_middleware import get_current_active_user
from app.services.cache_service import cache_service
from app.utils.auditoria_utils import registrar_auditoria
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Carpetas"]
)


# ---- helper A03 ----
def _sanitize_text(v: str, max_len: int = 200) -> str:
    v = v.strip()[:max_len]
    if re.search(r'[<>"\';\x00-\x08\x0b\x0c\x0e-\x1f]', v):
        raise ValueError('El campo contiene caracteres no permitidos')
    return v


# Schemas
class CarpetaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

    @field_validator('nombre', mode='before')
    @classmethod
    def sanitizar_nombre(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        return _sanitize_text(v, max_len=150)

    @field_validator('descripcion', mode='before')
    @classmethod
    def sanitizar_descripcion(cls, v) -> str:
        if not isinstance(v, str):
            return v
        return _sanitize_text(v, max_len=500)


class CarpetaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None

    @field_validator('nombre', mode='before')
    @classmethod
    def sanitizar_nombre(cls, v) -> str:
        if not isinstance(v, str):
            return v
        return _sanitize_text(v, max_len=150)

    @field_validator('descripcion', mode='before')
    @classmethod
    def sanitizar_descripcion(cls, v) -> str:
        if not isinstance(v, str):
            return v
        return _sanitize_text(v, max_len=500)


class CarpetaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    estado: str
    total_tomos: int
    creador: str
    created_at: str

    class Config:
        from_attributes = True


# ==================== CRUD CARPETAS ====================

@router.get("", response_model=List[CarpetaResponse])
async def listar_carpetas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    buscar: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /carpetas
    Listar carpetas con filtros opcionales.
    ⚡ OPTIMIZADO: Usa caché Redis para listado de carpetas
    """
    # Crear clave de caché
    cache_key = f"carpetas:lista:{skip}:{limit}:{buscar or 'all'}"
    
    # Intentar obtener desde caché
    cached_data = cache_service.get(cache_key)
    if cached_data:
        logger.info("✅ Carpetas obtenidas desde caché")
        return cached_data
    
    query = db.query(Carpeta)

    # Búsqueda por nombre o descripción
    if buscar:
        search_pattern = f"%{buscar}%"
        query = query.filter(
            or_(
                Carpeta.nombre.ilike(search_pattern),
                Carpeta.descripcion.ilike(search_pattern)
            )
        )

    carpetas = query.offset(skip).limit(limit).all()

    # Obtener el conteo de tomos para cada carpeta
    carpetas_response = []
    for c in carpetas:
        total_tomos = db.query(func.count(Tomo.id)).filter(Tomo.carpeta_id == c.id).scalar() or 0
        
        carpetas_response.append(CarpetaResponse(
            id=c.id,
            nombre=c.nombre,
            descripcion=c.descripcion,
            estado=c.estado or "activo",
            total_tomos=total_tomos,
            creador=c.creador.username if c.creador else "Sistema",
            created_at=c.created_at.isoformat() if c.created_at else ""
        ))

    # Guardar en caché por 5 minutos (convertir a dict para serialización)
    carpetas_dict = [c.model_dump() for c in carpetas_response]
    cache_service.set(cache_key, carpetas_dict, ttl=300)
    logger.info(f"💾 {len(carpetas_response)} carpetas guardadas en caché")
    
    return carpetas_response


@router.get("/{carpeta_id}", response_model=CarpetaResponse)
async def obtener_carpeta(
    carpeta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /carpetas/{carpeta_id}
    Obtener detalles de una carpeta específica.
    """
    carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

    if not carpeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada"
        )

    # Obtener el conteo de tomos
    total_tomos = db.query(func.count(Tomo.id)).filter(Tomo.carpeta_id == carpeta.id).scalar() or 0

    return CarpetaResponse(
        id=carpeta.id,
        nombre=carpeta.nombre,
        descripcion=carpeta.descripcion,
        estado=carpeta.estado or "activo",
        total_tomos=total_tomos,
        creador=carpeta.creador.username if carpeta.creador else "Sistema",
        created_at=carpeta.created_at.isoformat() if carpeta.created_at else ""
    )


@router.post("", response_model=CarpetaResponse, status_code=status.HTTP_201_CREATED)
async def crear_carpeta(
    carpeta_data: CarpetaCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    POST /carpetas
    Crear nueva carpeta.
    """
    # Verificar que no exista carpeta con mismo nombre
    existing = db.query(Carpeta).filter(
        Carpeta.nombre == carpeta_data.nombre
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una carpeta con ese nombre"
        )

    # Crear carpeta
    nueva_carpeta = Carpeta(
        nombre=carpeta_data.nombre,
        descripcion=carpeta_data.descripcion,
        numero_expediente=f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}",  # Auto-generado
        estado="activo",
        usuario_creador_id=current_user.id
    )

    db.add(nueva_carpeta)
    db.commit()
    db.refresh(nueva_carpeta)

    # ⚡ Invalidar caché de carpetas
    cache_service.invalidate_pattern("carpetas:lista:*")
    logger.info(f"Carpeta creada: {nueva_carpeta.nombre} por {current_user.username}")
    logger.info("🔄 Caché de carpetas invalidado")

    # 📝 AUDITORÍA
    # Registrar auditoría
    registrar_auditoria(
        usuario_id=current_user.id,
        accion="CREAR_CARPETA",
        request=request,
        tabla_afectada="carpetas",
        registro_id=nueva_carpeta.id,
        valores_nuevos={
            "nombre": nueva_carpeta.nombre,
            "descripcion": nueva_carpeta.descripcion,
            "numero_expediente": nueva_carpeta.numero_expediente
        }
    )

    return CarpetaResponse(
        id=nueva_carpeta.id,
        nombre=nueva_carpeta.nombre,
        descripcion=nueva_carpeta.descripcion,
        estado=nueva_carpeta.estado,
        total_tomos=0,
        creador=current_user.username,
        created_at=nueva_carpeta.created_at.isoformat()
    )


@router.put("/{carpeta_id}", response_model=CarpetaResponse)
async def actualizar_carpeta(
    carpeta_id: int,
    carpeta_data: CarpetaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    PUT /carpetas/{carpeta_id}
    Actualizar carpeta existente.
    """
    carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

    if not carpeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada"
        )

    # Guardar valores anteriores para auditoría
    valores_anteriores = {
        "nombre": carpeta.nombre,
        "descripcion": carpeta.descripcion
    }

    # Actualizar campos
    if carpeta_data.nombre is not None:
        # Verificar que no exista otra carpeta con ese nombre
        existing = db.query(Carpeta).filter(
            Carpeta.nombre == carpeta_data.nombre,
            Carpeta.id != carpeta_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una carpeta con ese nombre"
            )

        carpeta.nombre = carpeta_data.nombre

    if carpeta_data.descripcion is not None:
        carpeta.descripcion = carpeta_data.descripcion

    carpeta.updated_at = datetime.now()
    db.commit()
    db.refresh(carpeta)

    # ⚡ Invalidar caché de carpetas
    cache_service.invalidate_pattern("carpetas:lista:*")
    logger.info(f"🔄 Caché de carpetas invalidado")

    logger.info(f"Carpeta actualizada: {carpeta.nombre} por {current_user.username}")

    # Registrar auditoría
    registrar_auditoria(
        usuario_id=current_user.id,
        accion="MODIFICAR_CARPETA",
        request=request,
        tabla_afectada="carpetas",
        registro_id=carpeta_id,
        valores_anteriores=valores_anteriores,
        valores_nuevos={
            "nombre": carpeta.nombre,
            "descripcion": carpeta.descripcion
        }
    )

    # Obtener el conteo de tomos actualizado
    total_tomos = db.query(func.count(Tomo.id)).filter(Tomo.carpeta_id == carpeta.id).scalar() or 0

    return CarpetaResponse(
        id=carpeta.id,
        nombre=carpeta.nombre,
        descripcion=carpeta.descripcion,
        estado=carpeta.estado,
        total_tomos=total_tomos,
        creador=carpeta.creador.username if carpeta.creador else "Sistema",
        created_at=carpeta.created_at.isoformat()
    )


@router.delete("/{carpeta_id}")
async def eliminar_carpeta(
    carpeta_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    DELETE /carpetas/{carpeta_id}
    Eliminar carpeta.
    """
    try:
        carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

        if not carpeta:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Carpeta no encontrada"
            )

        carpeta_nombre = carpeta.nombre
        
        # Guardar información para auditoría antes de eliminar
        valores_anteriores = {
            "nombre": carpeta.nombre,
            "descripcion": carpeta.descripcion,
            "estado": carpeta.estado,
            "total_tomos": db.query(func.count(Tomo.id)).filter(Tomo.carpeta_id == carpeta_id).scalar() or 0
        }

        # Borrar análisis IA en sesión independiente para no contaminar la transacción principal
        try:
            from app.database import SessionLocal
            analisis_db = SessionLocal()
            try:
                tomo_ids = [r[0] for r in analisis_db.query(Tomo.id).filter(Tomo.carpeta_id == carpeta_id).all()]
                if tomo_ids:
                    deleted_analisis = analisis_db.query(AnalisisIA).filter(AnalisisIA.tomo_id.in_(tomo_ids)).delete(synchronize_session=False)
                    analisis_db.commit()
                    if deleted_analisis:
                        logger.info(f"Se eliminaron {deleted_analisis} registros de analisis_ia de carpeta {carpeta_id}")
            finally:
                analisis_db.close()
        except Exception:
            logger.warning("analisis_ia: tabla no existe o sin registros — omitiendo")

        # Eliminar carpeta (las relaciones cascade en modelos deberían encargarse de tomos, contenidos, etc.)
        db.delete(carpeta)
        db.commit()

        # ⚡ Invalidar caché de carpetas y tomos
        cache_service.invalidate_pattern("carpetas:lista:*")
        cache_service.delete(f"tomos:carpeta:{carpeta_id}")
        logger.info(f"🔄 Caché invalidado para carpeta {carpeta_id}")

        logger.info(f"Carpeta eliminada: {carpeta_nombre} por {current_user.username}")

        # Registrar auditoría
        registrar_auditoria(
            usuario_id=current_user.id,
            accion="ELIMINAR_CARPETA",
            request=request,
            tabla_afectada="carpetas",
            registro_id=carpeta_id,
            valores_anteriores=valores_anteriores
        )

        return {
            "message": "Carpeta eliminada correctamente",
            "carpeta_id": carpeta_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar carpeta {carpeta_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor al eliminar la carpeta: {str(e)}"
        )
