# backend/app/controllers/admin_ocr_controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.usuario import Usuario
from app.models.tomo import Tomo, ContenidoOCR
from app.controllers.auth_controller import get_current_user, require_admin
from app.services.caratula_detector_service import caratula_detector
from app.utils.logger import logger

router = APIRouter(prefix="/admin", tags=["Administración OCR"])


class ConfiguracionOCRRequest(BaseModel):
    """Configuración para procesamiento OCR"""
    ignorar_caratulas: bool = True
    palabras_minimas: int = 50
    densidad_minima: float = 0.05


class PaginasIgnoradasRequest(BaseModel):
    """Request para marcar páginas específicas como ignoradas"""
    paginas: List[int]


@router.get("/tomos/{tomo_id}/analizar-caratulas")
async def analizar_caratulas_tomo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Analiza un tomo para identificar páginas de carátula vs contenido real
    
    **Solo administradores**
    
    Returns:
        - Total de páginas
        - Páginas identificadas como carátula
        - Páginas con contenido real
        - Análisis detallado de cada página
    """
    try:
        # Verificar que el tomo existe
        tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
        if not tomo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tomo no encontrado"
            )
        
        # Obtener contenido OCR
        contenidos = db.query(ContenidoOCR).filter(
            ContenidoOCR.tomo_id == tomo_id
        ).order_by(ContenidoOCR.numero_pagina).all()
        
        if not contenidos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay contenido OCR procesado para este tomo"
            )
        
        # Preparar datos para análisis
        datos_ocr = [
            {
                'numero_pagina': c.numero_pagina,
                'texto_extraido': c.texto_extraido
            }
            for c in contenidos
        ]
        
        # Analizar
        resultado = caratula_detector.analizar_tomo_completo(datos_ocr)
        
        return {
            'tomo_id': tomo_id,
            'tomo_nombre': tomo.nombre_archivo,
            **resultado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analizando carátulas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al analizar carátulas: {str(e)}"
        )


@router.post("/tomos/{tomo_id}/marcar-paginas-ignoradas")
async def marcar_paginas_ignoradas(
    tomo_id: int,
    request: PaginasIgnoradasRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Marca páginas específicas como ignoradas (carátulas)
    
    **Solo administradores**
    
    Estas páginas no se incluirán en:
    - Búsquedas
    - Análisis de direcciones
    - Exportaciones
    """
    try:
        # Actualizar páginas
        for numero_pagina in request.paginas:
            contenido = db.query(ContenidoOCR).filter(
                ContenidoOCR.tomo_id == tomo_id,
                ContenidoOCR.numero_pagina == numero_pagina
            ).first()
            
            if contenido:
                # Agregar flag de ignorada
                if not contenido.datos_adicionales:
                    contenido.datos_adicionales = {}
                
                contenido.datos_adicionales['ignorada'] = True
                contenido.datos_adicionales['razon'] = 'Carátula/Portada sin contenido relevante'
                contenido.datos_adicionales['marcada_por_usuario'] = current_user.username
        
        db.commit()
        
        logger.info(
            f"Administrador {current_user.username} marcó {len(request.paginas)} "
            f"páginas como ignoradas en tomo {tomo_id}"
        )
        
        return {
            'success': True,
            'mensaje': f'{len(request.paginas)} páginas marcadas como ignoradas',
            'paginas_ignoradas': request.paginas
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error marcando páginas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al marcar páginas: {str(e)}"
        )


@router.post("/tomos/{tomo_id}/auto-ignorar-caratulas")
async def auto_ignorar_caratulas(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Detecta y marca automáticamente las carátulas para ignorarlas
    
    **Solo administradores**
    
    Usa IA para detectar:
    - Páginas con solo "TOMO X"
    - Páginas con solo números
    - Páginas casi vacías
    - Portadas sin contenido legal
    """
    try:
        # Obtener contenido OCR
        contenidos = db.query(ContenidoOCR).filter(
            ContenidoOCR.tomo_id == tomo_id
        ).all()
        
        if not contenidos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No hay contenido OCR procesado"
            )
        
        paginas_ignoradas = []
        
        for contenido in contenidos:
            es_caratula, razon = caratula_detector.es_caratula(
                contenido.texto_extraido,
                contenido.numero_pagina
            )
            
            if es_caratula:
                # Marcar como ignorada
                if not contenido.datos_adicionales:
                    contenido.datos_adicionales = {}
                
                contenido.datos_adicionales['ignorada'] = True
                contenido.datos_adicionales['razon'] = razon
                contenido.datos_adicionales['auto_detectada'] = True
                contenido.datos_adicionales['detectada_por'] = current_user.username
                
                paginas_ignoradas.append({
                    'numero_pagina': contenido.numero_pagina,
                    'razon': razon
                })
        
        db.commit()
        
        logger.info(
            f"Auto-detectadas y marcadas {len(paginas_ignoradas)} carátulas "
            f"en tomo {tomo_id} por {current_user.username}"
        )
        
        return {
            'success': True,
            'tomo_id': tomo_id,
            'total_paginas': len(contenidos),
            'paginas_ignoradas': len(paginas_ignoradas),
            'detalles': paginas_ignoradas
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error auto-detectando carátulas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al auto-detectar carátulas: {str(e)}"
        )


@router.get("/tomos/{tomo_id}/contenido-filtrado")
async def obtener_contenido_filtrado(
    tomo_id: int,
    solo_contenido_real: bool = True,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Obtiene el contenido del tomo filtrado (sin carátulas)
    
    **Solo administradores**
    
    Args:
        solo_contenido_real: Si True, excluye páginas marcadas como ignoradas
    
    Returns:
        Lista de páginas con contenido real
    """
    try:
        query = db.query(ContenidoOCR).filter(ContenidoOCR.tomo_id == tomo_id)
        
        if solo_contenido_real:
            # Filtrar páginas ignoradas
            contenidos = query.all()
            contenidos_filtrados = [
                c for c in contenidos
                if not (c.datos_adicionales and c.datos_adicionales.get('ignorada', False))
            ]
        else:
            contenidos_filtrados = query.all()
        
        return {
            'tomo_id': tomo_id,
            'total_paginas': query.count(),
            'paginas_contenido': len(contenidos_filtrados),
            'paginas': [
                {
                    'numero_pagina': c.numero_pagina,
                    'texto_extraido': c.texto_extraido[:500] + '...',  # Primeros 500 chars
                    'confianza': c.confianza,
                    'palabras': len(c.texto_extraido.split()) if c.texto_extraido else 0
                }
                for c in contenidos_filtrados
            ]
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo contenido filtrado: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener contenido: {str(e)}"
        )


@router.delete("/tomos/{tomo_id}/limpiar-ignoradas")
async def limpiar_paginas_ignoradas(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Quita la marca de ignorada de todas las páginas
    
    **Solo administradores**
    
    Útil si se marcaron páginas incorrectamente
    """
    try:
        contenidos = db.query(ContenidoOCR).filter(
            ContenidoOCR.tomo_id == tomo_id
        ).all()
        
        paginas_limpiadas = 0
        
        for contenido in contenidos:
            if contenido.datos_adicionales and contenido.datos_adicionales.get('ignorada'):
                contenido.datos_adicionales['ignorada'] = False
                paginas_limpiadas += 1
        
        db.commit()
        
        logger.info(
            f"Administrador {current_user.username} limpió marcas de ignoradas "
            f"en {paginas_limpiadas} páginas del tomo {tomo_id}"
        )
        
        return {
            'success': True,
            'mensaje': f'Se limpiaron {paginas_limpiadas} páginas',
            'paginas_limpiadas': paginas_limpiadas
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error limpiando páginas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al limpiar páginas: {str(e)}"
        )
