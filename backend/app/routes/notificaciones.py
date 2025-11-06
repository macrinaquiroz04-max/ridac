from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.usuario import Usuario
from app.models.notificacion import Notificacion
from app.middlewares.auth_middleware import get_current_active_user
from app.services.notificacion_service import NotificacionService

router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones"]
)

class NotificacionResponse(BaseModel):
    id: int
    tipo: str
    mensaje: str
    leida: bool
    created_at: datetime
    datos_adicionales: Optional[str]

    class Config:
        from_attributes = True

@router.get("/", response_model=List[NotificacionResponse])
async def obtener_notificaciones(
    solo_no_leidas: bool = Query(False, description="Mostrar solo notificaciones no leídas"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /notificaciones
    Obtener notificaciones del usuario actual
    """
    service = NotificacionService(db)
    notificaciones = service.obtener_notificaciones_usuario(
        usuario_id=current_user.id,
        solo_no_leidas=solo_no_leidas,
        limit=limit
    )
    return notificaciones

@router.post("/{notificacion_id}/leer")
async def marcar_como_leida(
    notificacion_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    POST /notificaciones/{notificacion_id}/leer
    Marcar una notificación como leída
    """
    service = NotificacionService(db)
    notificacion = db.query(Notificacion).filter(
        Notificacion.id == notificacion_id,
        Notificacion.usuario_id == current_user.id
    ).first()

    if not notificacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada"
        )

    service.marcar_como_leida(notificacion_id)
    return {"message": "Notificación marcada como leída"}