# backend/app/routes/busqueda_tomos.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import date

from app.database import get_db
from app.controllers.busqueda_tomo_controller import BusquedaTomoController
from app.middlewares.auth_middleware import get_current_user
from app.models.usuario import Usuario

router = APIRouter()

# Modelos Pydantic para requests
class BusquedaSimple(BaseModel):
    termino: str
    pagina_inicio: Optional[int] = None
    pagina_fin: Optional[int] = None
    confianza_minima: Optional[float] = 0.0

class BusquedaMultiple(BaseModel):
    termino: str
    tomos_ids: Optional[List[int]] = None
    carpeta_id: Optional[int] = None
    pagina_inicio: Optional[int] = None
    pagina_fin: Optional[int] = None
    confianza_minima: Optional[float] = 0.0

class BusquedaCronologica(BaseModel):
    termino: str
    carpeta_id: Optional[int] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    confianza_minima: Optional[float] = 0.0

class BusquedaAvanzada(BaseModel):
    terminos: List[str] = []
    operador: str = "AND"  # AND, OR
    frase_exacta: str = ""
    excluir_terminos: List[str] = []
    filtros: Dict = {}

@router.post("/tomo/{tomo_id}/buscar")
async def buscar_en_tomo(
    tomo_id: int,
    busqueda: BusquedaSimple,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Busca un término específico dentro del contenido OCR de un tomo
    """
    try:
        filtros = {
            "pagina_inicio": busqueda.pagina_inicio,
            "pagina_fin": busqueda.pagina_fin,
            "confianza_minima": busqueda.confianza_minima
        }
        
        resultado = BusquedaTomoController.buscar_en_tomo(
            db=db,
            usuario_id=current_user.id,
            tomo_id=tomo_id,
            termino_busqueda=busqueda.termino,
            **filtros
        )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la búsqueda: {str(e)}"
        )

@router.post("/multiple/buscar")
async def buscar_en_multiples_tomos(
    busqueda: BusquedaMultiple,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Busca un término en múltiples tomos con permisos del usuario
    """
    try:
        filtros = {
            "pagina_inicio": busqueda.pagina_inicio,
            "pagina_fin": busqueda.pagina_fin,
            "confianza_minima": busqueda.confianza_minima,
            "carpeta_id": busqueda.carpeta_id
        }
        
        resultado = BusquedaTomoController.buscar_en_multiples_tomos(
            db=db,
            usuario_id=current_user.id,
            termino_busqueda=busqueda.termino,
            tomos_ids=busqueda.tomos_ids,
            **filtros
        )
        
        return resultado
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la búsqueda múltiple: {str(e)}"
        )

@router.post("/cronologica/buscar")
async def busqueda_cronologica(
    busqueda: BusquedaCronologica,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Realiza búsqueda cronológica por fecha de procesamiento de tomos
    """
    try:
        filtros = {
            "fecha_inicio": busqueda.fecha_inicio,
            "fecha_fin": busqueda.fecha_fin,
            "confianza_minima": busqueda.confianza_minima
        }
        
        resultado = BusquedaTomoController.busqueda_cronologica(
            db=db,
            usuario_id=current_user.id,
            termino_busqueda=busqueda.termino,
            carpeta_id=busqueda.carpeta_id,
            **filtros
        )
        
        return resultado
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la búsqueda cronológica: {str(e)}"
        )

@router.post("/avanzada/buscar")
async def busqueda_avanzada(
    busqueda: BusquedaAvanzada,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Búsqueda avanzada con múltiples criterios y operadores lógicos
    """
    try:
        # Validar parámetros
        if not busqueda.terminos and not busqueda.frase_exacta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar al menos un término de búsqueda o una frase exacta"
            )
        
        if busqueda.operador not in ["AND", "OR"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El operador debe ser 'AND' u 'OR'"
            )
        
        parametros = {
            "terminos": busqueda.terminos,
            "operador": busqueda.operador,
            "frase_exacta": busqueda.frase_exacta,
            "excluir_terminos": busqueda.excluir_terminos,
            "filtros": busqueda.filtros
        }
        
        resultado = BusquedaTomoController.busqueda_avanzada(
            db=db,
            usuario_id=current_user.id,
            parametros=parametros
        )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la búsqueda avanzada: {str(e)}"
        )

@router.get("/rapida")
async def busqueda_rapida(
    q: str = Query(..., description="Término de búsqueda"),
    carpeta_id: Optional[int] = Query(None, description="ID de carpeta específica"),
    limite: int = Query(50, description="Límite de resultados", le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Búsqueda rápida con parámetros GET para facilitar integración
    """
    try:
        if not q or len(q.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El término de búsqueda debe tener al menos 2 caracteres"
            )
        
        filtros = {}
        if carpeta_id:
            filtros["carpeta_id"] = carpeta_id
        
        resultado = BusquedaTomoController.buscar_en_multiples_tomos(
            db=db,
            usuario_id=current_user.id,
            termino_busqueda=q.strip(),
            **filtros
        )
        
        # Limitar resultados para búsqueda rápida
        for tomo_resultado in resultado["resultados_por_tomo"]:
            if len(tomo_resultado["coincidencias"]) > limite:
                tomo_resultado["coincidencias"] = tomo_resultado["coincidencias"][:limite]
                tomo_resultado["coincidencias_truncadas"] = True
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la búsqueda rápida: {str(e)}"
        )

@router.get("/estadisticas")
async def obtener_estadisticas_busqueda(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene estadísticas de búsqueda disponibles para el usuario
    """
    try:
        estadisticas = BusquedaTomoController.obtener_estadisticas_busqueda(
            db=db,
            usuario_id=current_user.id
        )
        
        return estadisticas
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )

@router.get("/sugerencias")
async def obtener_sugerencias_busqueda(
    parcial: str = Query(..., description="Texto parcial para sugerencias", min_length=2),
    carpeta_id: Optional[int] = Query(None, description="ID de carpeta para filtrar"),
    limite: int = Query(10, description="Número máximo de sugerencias", le=20),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene sugerencias de búsqueda basadas en contenido OCR disponible
    """
    try:
        # Esta es una implementación básica de sugerencias
        # En un sistema real, podrías usar índices de texto completo o Elasticsearch
        
        from sqlalchemy import func, text
        from app.models.tomo import ContenidoOCR
        from app.models.permiso_tomo import PermisoTomo
        
        # Query para obtener palabras frecuentes que coincidan con el texto parcial
        query = db.query(
            func.regexp_split_to_table(
                func.lower(ContenidoOCR.texto_extraido), 
                r'[^a-záéíóúñü]+'
            ).label('palabra')
        ).select_from(ContenidoOCR).join(
            PermisoTomo, and_(
                PermisoTomo.tomo_id == ContenidoOCR.tomo_id,
                PermisoTomo.usuario_id == current_user.id,
                PermisoTomo.puede_buscar == True
            )
        ).filter(
            func.regexp_split_to_table(
                func.lower(ContenidoOCR.texto_extraido), 
                r'[^a-záéíóúñü]+'
            ).like(f"{parcial.lower()}%")
        )
        
        if carpeta_id:
            from app.models.tomo import Tomo
            query = query.join(Tomo, ContenidoOCR.tomo_id == Tomo.id).filter(
                Tomo.carpeta_id == carpeta_id
            )
        
        # Agrupar y contar frecuencia
        resultados = query.group_by('palabra').order_by(
            func.count('palabra').desc()
        ).limit(limite).all()
        
        sugerencias = [
            {
                "texto": resultado.palabra,
                "frecuencia": "alta"  # Simplificado para esta implementación
            }
            for resultado in resultados 
            if resultado.palabra and len(resultado.palabra) >= 3
        ]
        
        return {
            "texto_parcial": parcial,
            "total_sugerencias": len(sugerencias),
            "sugerencias": sugerencias
        }
        
    except Exception as e:
        # Si falla la búsqueda avanzada, devolver sugerencias básicas
        sugerencias_basicas = [
            f"{parcial}a", f"{parcial}e", f"{parcial}i", f"{parcial}o", f"{parcial}u"
        ][:limite]
        
        return {
            "texto_parcial": parcial,
            "total_sugerencias": len(sugerencias_basicas),
            "sugerencias": [{"texto": s, "frecuencia": "desconocida"} for s in sugerencias_basicas],
            "error": "Modo de sugerencias simplificado"
        }

@router.get("/historial")
async def obtener_historial_busquedas(
    limite: int = Query(20, description="Número de búsquedas recientes", le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene el historial de búsquedas del usuario (si está implementado)
    """
    try:
        # Placeholder para funcionalidad futura de historial
        # En una implementación completa, mantendrías un log de búsquedas
        
        return {
            "usuario_id": current_user.id,
            "historial": [],
            "mensaje": "Funcionalidad de historial no implementada aún",
            "total_busquedas": 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo historial: {str(e)}"
        )