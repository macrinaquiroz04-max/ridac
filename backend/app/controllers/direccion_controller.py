# backend/app/controllers/direccion_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.database import get_db
from app.models.usuario import Usuario
from app.controllers.auth_controller import get_current_user
from app.services.direccion_detector_service import direccion_detector
from app.utils.logger import logger

router = APIRouter(prefix="/tomos", tags=["Direcciones"])


class GuardarDireccionesRequest(BaseModel):
    """Request para guardar direcciones corregidas"""
    direcciones: List[Dict[str, Any]]


@router.get("/{tomo_id}/detectar-direcciones")
async def detectar_direcciones(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Detecta y valida todas las direcciones en un tomo
    
    - **tomo_id**: ID del tomo a analizar
    
    Returns:
        - Lista de direcciones detectadas con validación SEPOMEX
        - Estadísticas de detección
    """
    try:
        logger.info(f"Usuario {current_user.username} detectando direcciones en tomo {tomo_id}")
        
        resultado = await direccion_detector.detectar_direcciones_en_tomo(db, tomo_id)
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error detectando direcciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al detectar direcciones: {str(e)}"
        )


@router.post("/{tomo_id}/guardar-direcciones")
async def guardar_direcciones_corregidas(
    tomo_id: int,
    request: GuardarDireccionesRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Guarda las direcciones corregidas por el usuario
    
    - **tomo_id**: ID del tomo
    - **direcciones**: Lista de direcciones con correcciones
    
    Returns:
        - Confirmación de guardado
        - Número de direcciones guardadas
    """
    try:
        logger.info(f"Usuario {current_user.username} guardando {len(request.direcciones)} direcciones")
        
        resultado = await direccion_detector.guardar_direcciones_corregidas(
            db,
            tomo_id,
            request.direcciones,
            current_user.id
        )
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error guardando direcciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar direcciones: {str(e)}"
        )


@router.get("/{tomo_id}/direcciones-corregidas")
async def obtener_direcciones_corregidas(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene las direcciones ya corregidas de un tomo
    
    - **tomo_id**: ID del tomo
    
    Returns:
        - Lista de direcciones corregidas guardadas
    """
    try:
        from app.models.direccion import DireccionCorregida
        
        direcciones = db.query(DireccionCorregida).filter(
            DireccionCorregida.tomo_id == tomo_id
        ).order_by(DireccionCorregida.pagina, DireccionCorregida.linea).all()
        
        return {
            'tomo_id': tomo_id,
            'total': len(direcciones),
            'direcciones': [d.to_dict() for d in direcciones]
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo direcciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener direcciones: {str(e)}"
        )


@router.get("/{tomo_id}/estadisticas-direcciones")
async def obtener_estadisticas_direcciones(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene estadísticas de las direcciones en un tomo
    
    - **tomo_id**: ID del tomo
    
    Returns:
        - Total de direcciones detectadas
        - Total validadas con SEPOMEX
        - Total editadas manualmente
        - Alcaldías más frecuentes
    """
    try:
        from app.models.direccion import DireccionCorregida
        from sqlalchemy import func
        
        # Contar direcciones por estado
        total = db.query(func.count(DireccionCorregida.id)).filter(
            DireccionCorregida.tomo_id == tomo_id
        ).scalar()
        
        validadas = db.query(func.count(DireccionCorregida.id)).filter(
            DireccionCorregida.tomo_id == tomo_id,
            DireccionCorregida.validada_sepomex == True
        ).scalar()
        
        editadas = db.query(func.count(DireccionCorregida.id)).filter(
            DireccionCorregida.tomo_id == tomo_id,
            DireccionCorregida.editada_manualmente == True
        ).scalar()
        
        ignoradas = db.query(func.count(DireccionCorregida.id)).filter(
            DireccionCorregida.tomo_id == tomo_id,
            DireccionCorregida.ignorada == True
        ).scalar()
        
        # Alcaldías más frecuentes
        alcaldias = db.query(
            DireccionCorregida.alcaldia,
            func.count(DireccionCorregida.id).label('count')
        ).filter(
            DireccionCorregida.tomo_id == tomo_id,
            DireccionCorregida.alcaldia.isnot(None),
            DireccionCorregida.alcaldia != ''
        ).group_by(
            DireccionCorregida.alcaldia
        ).order_by(
            func.count(DireccionCorregida.id).desc()
        ).limit(5).all()
        
        return {
            'tomo_id': tomo_id,
            'total_direcciones': total,
            'validadas_sepomex': validadas,
            'editadas_manualmente': editadas,
            'ignoradas': ignoradas,
            'porcentaje_validadas': round((validadas / total * 100), 1) if total > 0 else 0,
            'alcaldias_frecuentes': [
                {'alcaldia': alc[0], 'count': alc[1]} 
                for alc in alcaldias
            ]
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )
