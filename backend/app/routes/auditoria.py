# backend/app/routes/auditoria.py

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

from app.database import get_db
from app.models.auditoria import Auditoria
from app.models.usuario import Usuario, Rol
from app.middlewares.auth_middleware import get_current_active_user
from app.middlewares.permission_middleware import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auditoria",
    tags=["Auditoría"]
)


class AuditoriaResponse(BaseModel):
    id: int
    usuario_id: Optional[int]
    username: Optional[str]
    nombre_completo: Optional[str]
    rol: Optional[str]
    accion: str
    tabla_afectada: Optional[str]
    registro_id: Optional[int]
    valores_anteriores: Optional[dict]
    valores_nuevos: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditoriaStats(BaseModel):
    total_eventos: int
    logins_exitosos: int
    logins_fallidos: int
    acciones_criticas: int
    usuarios_activos: int


@router.get("/eventos", response_model=List[AuditoriaResponse])
async def obtener_eventos(
    periodo: Optional[str] = Query(None, description="today, week, month, year, all"),
    usuario: Optional[str] = Query(None, description="Username para filtrar"),
    accion: Optional[str] = Query(None, description="Tipo de acción para filtrar"),
    ip: Optional[str] = Query(None, description="IP address para filtrar"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Obtener eventos de auditoría con filtros.
    Solo usuarios con permiso ver_auditoria pueden acceder.
    """
    # Verificar permisos
    from app.models.permiso import PermisoSistema
    
    permisos_sistema = db.query(PermisoSistema).filter(
        PermisoSistema.usuario_id == current_user.id
    ).first()
    
    if not permisos_sistema or not permisos_sistema.ver_auditoria:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver la auditoría del sistema"
        )
    
    # Construir query base con JOIN a usuarios
    query = db.query(
        Auditoria,
        Usuario.username,
        Usuario.nombre_completo,
        Usuario.rol_id
    ).outerjoin(
        Usuario, Auditoria.usuario_id == Usuario.id
    )
    
    # Aplicar filtros de período
    if periodo and periodo != "all":
        now = datetime.now()
        if periodo == "today":
            fecha_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif periodo == "week":
            fecha_inicio = now - timedelta(days=7)
        elif periodo == "month":
            fecha_inicio = now - timedelta(days=30)
        elif periodo == "year":
            fecha_inicio = now - timedelta(days=365)
        else:
            fecha_inicio = None
        
        if fecha_inicio:
            query = query.filter(Auditoria.created_at >= fecha_inicio)
    
    # Filtro por usuario
    if usuario:
        query = query.filter(Usuario.username == usuario)
    
    # Filtro por acción
    if accion and accion != "all":
        query = query.filter(Auditoria.accion == accion)
    
    # Filtro por IP
    if ip:
        query = query.filter(Auditoria.ip_address.like(f"%{ip}%"))
    
    # Ordenar por fecha descendente y aplicar paginación
    query = query.order_by(desc(Auditoria.created_at))
    total = query.count()
    resultados = query.offset(offset).limit(limit).all()
    
    # Formatear respuesta
    eventos = []
    for auditoria, username, nombre_completo, rol_id in resultados:
        # Obtener el nombre del rol si existe
        rol_nombre = None
        if rol_id:
            rol = db.query(Rol).filter(Rol.id == rol_id).first()
            if rol:
                rol_nombre = rol.nombre
        
        eventos.append(AuditoriaResponse(
            id=auditoria.id,
            usuario_id=auditoria.usuario_id,
            username=username,
            nombre_completo=nombre_completo,
            rol=rol_nombre,
            accion=auditoria.accion,
            tabla_afectada=auditoria.tabla_afectada,
            registro_id=auditoria.registro_id,
            valores_anteriores=auditoria.valores_anteriores,
            valores_nuevos=auditoria.valores_nuevos,
            ip_address=str(auditoria.ip_address) if auditoria.ip_address else None,
            user_agent=auditoria.user_agent,
            created_at=auditoria.created_at
        ))
    
    return eventos


@router.get("/estadisticas", response_model=AuditoriaStats)
async def obtener_estadisticas(
    periodo: Optional[str] = Query("month", description="today, week, month, year, all"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Obtener estadísticas de auditoría
    """
    # Verificar permisos
    from app.models.permiso import PermisoSistema
    permisos_sistema = db.query(PermisoSistema).filter(
        PermisoSistema.usuario_id == current_user.id
    ).first()
    
    if not permisos_sistema or not permisos_sistema.ver_auditoria:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver la auditoría del sistema"
        )
    
    # Calcular fecha de inicio según período
    query = db.query(Auditoria)
    
    if periodo != "all":
        now = datetime.now()
        if periodo == "today":
            fecha_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif periodo == "week":
            fecha_inicio = now - timedelta(days=7)
        elif periodo == "month":
            fecha_inicio = now - timedelta(days=30)
        elif periodo == "year":
            fecha_inicio = now - timedelta(days=365)
        else:
            fecha_inicio = None
        
        if fecha_inicio:
            query = query.filter(Auditoria.created_at >= fecha_inicio)
    
    # Obtener estadísticas
    total_eventos = query.count()
    logins_exitosos = query.filter(Auditoria.accion == "LOGIN_EXITOSO").count()
    logins_fallidos = query.filter(Auditoria.accion == "LOGIN_FALLIDO").count()
    
    # Acciones críticas (eliminar, modificar permisos, etc.)
    acciones_criticas = query.filter(
        or_(
            Auditoria.accion.like("%ELIMINAR%"),
            Auditoria.accion.like("%MODIFICAR_PERMISOS%"),
            Auditoria.accion == "CREAR_USUARIO"
        )
    ).count()
    
    # Usuarios únicos activos
    usuarios_activos = db.query(Auditoria.usuario_id).filter(
        Auditoria.usuario_id.isnot(None)
    ).distinct().count()
    
    return AuditoriaStats(
        total_eventos=total_eventos,
        logins_exitosos=logins_exitosos,
        logins_fallidos=logins_fallidos,
        acciones_criticas=acciones_criticas,
        usuarios_activos=usuarios_activos
    )


@router.get("/usuarios-activos")
async def obtener_usuarios_activos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Obtener lista de usuarios que han tenido actividad registrada
    """
    # Verificar permisos
    from app.models.permiso import PermisoSistema
    permisos_sistema = db.query(PermisoSistema).filter(
        PermisoSistema.usuario_id == current_user.id
    ).first()
    
    if not permisos_sistema or not permisos_sistema.ver_auditoria:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver la auditoría del sistema"
        )
    
    # Obtener usuarios únicos de auditoría
    usuarios = db.query(
        Usuario.id,
        Usuario.username,
        Usuario.nombre_completo
    ).join(
        Auditoria, Usuario.id == Auditoria.usuario_id
    ).distinct().all()
    
    return [
        {
            "id": u.id,
            "username": u.username,
            "nombre_completo": u.nombre_completo
        }
        for u in usuarios
    ]


@router.post("/registrar-acceso")
async def registrar_acceso_auditoria(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Registrar que un usuario accedió a ver la auditoría.
    Se llama solo una vez cuando carga la página, no en cada actualización.
    """
    # Verificar permisos
    from app.models.permiso import PermisoSistema
    from app.utils.auditoria_utils import AuditoriaLogger
    
    permisos_sistema = db.query(PermisoSistema).filter(
        PermisoSistema.usuario_id == current_user.id
    ).first()
    
    if not permisos_sistema or not permisos_sistema.ver_auditoria:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver la auditoría del sistema"
        )
    
    # Registrar acceso
    ip_address, user_agent = AuditoriaLogger.extraer_info_request(request)
    try:
        AuditoriaLogger.registrar_evento(
            usuario_id=current_user.id,
            accion="ACCEDER_AUDITORIA",
            tabla_afectada="auditoria",
            valores_nuevos={
                "evento": "acceso_pagina_auditoria"
            },
            ip_address=ip_address,
            user_agent=user_agent,
            db=db
        )
        return {"message": "Acceso registrado"}
    except Exception as e:
        logger.warning(f"Error registrando acceso a auditoría: {e}")
        return {"message": "Error registrando acceso"}
