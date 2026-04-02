# backend/app/routes/auditoria.py

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging
import csv
import io

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
    descripcion: Optional[str]
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
    
    es_admin = current_user.rol is not None and current_user.rol.nombre in ["admin", "administrador"]
    if not es_admin:
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
            descripcion=auditoria.descripcion,
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
    es_admin = current_user.rol is not None and current_user.rol.nombre in ["admin", "administrador"]
    if not es_admin:
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
    es_admin = current_user.rol is not None and current_user.rol.nombre in ["admin", "administrador"]
    if not es_admin:
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
    
    es_admin = current_user.rol is not None and current_user.rol.nombre in ["admin", "administrador"]
    if not es_admin:
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


@router.get("/exportar")
async def exportar_auditoria_csv(
    request: Request,
    periodo: Optional[str] = Query(None, description="today, week, month, year, all"),
    usuario: Optional[str] = Query(None, description="Username para filtrar"),
    accion: Optional[str] = Query(None, description="Tipo de acción para filtrar"),
    ip: Optional[str] = Query(None, description="IP address para filtrar"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Exportar eventos de auditoría a formato CSV.
    Solo usuarios con permiso ver_auditoria pueden acceder.
    """
    # Verificar permisos
    from app.models.permiso import PermisoSistema
    from app.utils.auditoria_utils import AuditoriaLogger
    
    es_admin = current_user.rol is not None and current_user.rol.nombre in ["admin", "administrador"]
    if not es_admin:
        permisos_sistema = db.query(PermisoSistema).filter(
            PermisoSistema.usuario_id == current_user.id
        ).first()
        if not permisos_sistema or not permisos_sistema.ver_auditoria:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para exportar la auditoría del sistema"
            )
    
    # Construir query base con JOIN a usuarios (misma lógica que obtener_eventos)
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
    
    # Ordenar por fecha descendente
    query = query.order_by(desc(Auditoria.created_at))
    resultados = query.all()
    
    # Registrar la exportación en auditoría
    ip_address, user_agent = AuditoriaLogger.extraer_info_request(request)
    try:
        AuditoriaLogger.registrar_evento(
            usuario_id=current_user.id,
            accion="EXPORTAR_DATOS",
            tabla_afectada="auditoria",
            valores_nuevos={
                "tipo": "auditoria_csv",
                "total_registros": len(resultados),
                "filtros": {
                    "periodo": periodo,
                    "usuario": usuario,
                    "accion": accion,
                    "ip": ip
                }
            },
            descripcion=f"Exportación de {len(resultados)} registros de auditoría a CSV",
            ip_address=ip_address,
            user_agent=user_agent,
            db=db
        )
    except Exception as e:
        logger.warning(f"Error registrando exportación: {e}")
    
    # Crear CSV en memoria con codificación UTF-8 con BOM para Excel
    output = io.StringIO()
    # Agregar BOM (Byte Order Mark) para que Excel reconozca UTF-8
    output.write('\ufeff')
    
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    # Escribir encabezados más descriptivos
    writer.writerow([
        'ID',
        'Fecha y Hora',
        'Usuario',
        'Nombre Completo',
        'Acción Realizada',
        'Tabla Afectada',
        'ID Registro',
        'Descripción',
        'Dirección IP',
        'Navegador/Sistema'
    ])
    
    # Escribir datos de forma más limpia
    for auditoria, username, nombre_completo, rol_id in resultados:
        # Limpiar y formatear User Agent para mejor legibilidad
        user_agent_clean = ''
        if auditoria.user_agent:
            # Extraer solo la información relevante del user agent
            ua = auditoria.user_agent
            if 'Mozilla' in ua:
                # Intentar extraer el navegador principal
                if 'Chrome' in ua:
                    user_agent_clean = 'Chrome'
                elif 'Firefox' in ua:
                    user_agent_clean = 'Firefox'
                elif 'Safari' in ua and 'Chrome' not in ua:
                    user_agent_clean = 'Safari'
                elif 'Edge' in ua:
                    user_agent_clean = 'Edge'
                else:
                    user_agent_clean = 'Navegador Web'
                    
                # Agregar SO
                if 'Windows' in ua:
                    user_agent_clean += ' (Windows)'
                elif 'Linux' in ua:
                    user_agent_clean += ' (Linux)'
                elif 'Mac' in ua:
                    user_agent_clean += ' (Mac)'
            else:
                user_agent_clean = 'Sistema/API'
        
        writer.writerow([
            auditoria.id,
            auditoria.created_at.strftime('%Y-%m-%d %H:%M:%S') if auditoria.created_at else '',
            username or 'Sistema',
            nombre_completo or '-',
            auditoria.accion or '-',
            auditoria.tabla_afectada or '-',
            auditoria.registro_id or '-',
            (auditoria.descripcion or '-').replace('\n', ' ').replace('\r', ''),  # Limpiar saltos de línea
            auditoria.ip_address or '-',
            user_agent_clean or '-'
        ])
    
    # Preparar el archivo para descarga
    output.seek(0)
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"auditoria_export_{timestamp}.csv"
    
    # Codificar correctamente para UTF-8
    csv_content = output.getvalue().encode('utf-8')
    
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )
