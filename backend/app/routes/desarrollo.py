# backend/app/routes/desarrollo.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.middlewares.auth_middleware import get_current_user
from app.utils.limpieza_automatica import LimpiezaAutomatica
from typing import Dict, Any

router = APIRouter(prefix="/dev", tags=["desarrollo"])

@router.post("/limpiar-permisos")
async def limpiar_permisos_desarrollo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Endpoint para limpieza manual en desarrollo
    Solo para administradores
    """
    # Verificar que es administrador
    if current_user.rol.nombre != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ejecutar limpieza"
        )
    
    try:
        resultado = LimpiezaAutomatica.limpiar_permisos_vacios(db)
        return {
            "success": True,
            "mensaje": "Limpieza ejecutada correctamente",
            "detalles": resultado
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en limpieza: {str(e)}"
        )

@router.get("/optimizar-sistema")
async def optimizar_sistema_desarrollo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Optimización completa del sistema para desarrollo
    """
    if current_user.rol.nombre != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden optimizar el sistema"
        )
    
    try:
        resultado = LimpiezaAutomatica.optimizar_base_datos(db)
        return {
            "success": True,
            "mensaje": "Optimización completada",
            "estadisticas": resultado
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en optimización: {str(e)}"
        )

@router.get("/desarrollo/estadisticas")
async def estadisticas_desarrollo(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Estadísticas del sistema para monitoreo en desarrollo
    """
    try:
        from app.models.permiso_tomo import PermisoTomo
        from app.models.tomo import Tomo
        from app.models.carpeta import Carpeta
        
        stats = {
            "usuarios_activos": db.query(Usuario).filter(Usuario.activo == True).count(),
            "usuarios_totales": db.query(Usuario).count(),
            "permisos_activos": db.query(PermisoTomo).count(),
            "tomos_totales": db.query(Tomo).count(),
            "carpetas_totales": db.query(Carpeta).count()
        }
        
        # Usuarios con más permisos
        usuarios_con_permisos = db.query(Usuario).join(PermisoTomo).group_by(Usuario.id).limit(5).all()
        
        return {
            "success": True,
            "estadisticas": stats,
            "top_usuarios": [{"id": u.id, "username": u.username} for u in usuarios_con_permisos]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )