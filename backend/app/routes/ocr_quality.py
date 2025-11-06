# backend/app/routes/ocr_quality.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import json

from app.database import get_db
from app.models.usuario import Usuario
from app.models.tomo import Tomo, ContenidoOCR
from app.models.permiso_tomo import PermisoTomo
from app.middlewares.auth_middleware import get_current_user
from app.services.text_correction_service import TextCorrectionService
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/ocr",
    tags=["OCR Quality"]
)

@router.get("/quality/{tomo_id}")
async def analizar_calidad_ocr(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Analiza la calidad del OCR de un tomo específico"""
    
    # Verificar que el tomo existe
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tomo no encontrado"
        )
    
    # Obtener contenido OCR del tomo
    contenidos = db.query(ContenidoOCR).filter(
        ContenidoOCR.tomo_id == tomo_id
    ).all()
    
    if not contenidos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró contenido OCR para este tomo"
        )
    
    # Analizar calidad
    analisis = _analizar_calidad_contenido(contenidos)
    
    return {
        "success": True,
        "tomo_id": tomo_id,
        "total_paginas": len(contenidos),
        "analisis": analisis
    }

@router.post("/improve/{tomo_id}")
async def mejorar_calidad_ocr(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Aplica mejoras automáticas al contenido OCR de un tomo"""
    
    # Verificar que el tomo existe
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tomo no encontrado"
        )
    
    # Obtener contenido OCR del tomo
    contenidos = db.query(ContenidoOCR).filter(
        ContenidoOCR.tomo_id == tomo_id
    ).all()
    
    if not contenidos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró contenido OCR para este tomo"
        )
    
    correction_service = TextCorrectionService()
    mejoras_aplicadas = 0
    errores = []
    
    try:
        for contenido in contenidos:
            if contenido.texto_extraido and contenido.motor_usado != 'error':
                try:
                    # Aplicar corrección
                    texto_original = contenido.texto_extraido
                    texto_corregido = correction_service.corregir_texto(texto_original, "legal")
                    
                    # Validar calidad de corrección
                    validacion = correction_service.validar_calidad_correccion(
                        texto_original, texto_corregido
                    )
                    
                    # Actualizar solo si hay mejoras significativas
                    if validacion['cambios_realizados'] > 0:
                        contenido.texto_extraido = texto_corregido
                        # Ajustar confianza basada en la corrección
                        nueva_confianza = min(
                            contenido.confianza_porcentaje,
                            validacion['confianza_correccion']
                        )
                        contenido.confianza_porcentaje = nueva_confianza
                        contenido.motor_usado = f"{contenido.motor_usado}_corrected"
                        mejoras_aplicadas += 1
                        
                except Exception as e:
                    errores.append(f"Página {contenido.pagina}: {str(e)}")
                    logger.error(f"Error mejorando página {contenido.pagina}: {e}")
        
        # Guardar cambios
        db.commit()
        
        return {
            "success": True,
            "tomo_id": tomo_id,
            "mejoras_aplicadas": mejoras_aplicadas,
            "total_paginas": len(contenidos),
            "errores": errores
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error aplicando mejoras OCR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error aplicando mejoras automáticas"
        )

@router.get("/suggestions/{tomo_id}")
async def obtener_sugerencias_mejora(
    tomo_id: int,
    pagina: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene sugerencias para mejorar la calidad del OCR"""
    
    # Construir query base
    query = db.query(ContenidoOCR).filter(ContenidoOCR.tomo_id == tomo_id)
    
    # Filtrar por página si se especifica
    if pagina:
        query = query.filter(ContenidoOCR.pagina == pagina)
    
    contenidos = query.all()
    
    if not contenidos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró contenido OCR"
        )
    
    correction_service = TextCorrectionService()
    sugerencias_por_pagina = []
    
    for contenido in contenidos:
        if contenido.texto_extraido and contenido.motor_usado != 'error':
            sugerencias = correction_service.obtener_sugerencias_mejora(contenido.texto_extraido)
            
            if sugerencias:
                sugerencias_por_pagina.append({
                    "pagina": contenido.pagina,
                    "confianza_actual": contenido.confianza_porcentaje,
                    "motor_usado": contenido.motor_usado,
                    "sugerencias": sugerencias
                })
    
    return {
        "success": True,
        "tomo_id": tomo_id,
        "sugerencias_por_pagina": sugerencias_por_pagina
    }

@router.get("/stats/{tomo_id}")
async def obtener_estadisticas_ocr(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtiene estadísticas detalladas del OCR de un tomo"""
    
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
    ).all()
    
    if not contenidos:
        return {
            "success": True,
            "tomo_id": tomo_id,
            "estadisticas": {
                "total_paginas": 0,
                "paginas_procesadas": 0,
                "confianza_promedio": 0,
                "motores_utilizados": {},
                "distribucion_confianza": {},
                "paginas_con_errores": 0
            }
        }
    
    # Calcular estadísticas
    total_paginas = len(contenidos)
    paginas_procesadas = len([c for c in contenidos if c.motor_usado != 'error'])
    paginas_con_errores = total_paginas - paginas_procesadas
    
    # Confianza promedio
    confianzas = [c.confianza_porcentaje for c in contenidos if c.motor_usado != 'error']
    confianza_promedio = sum(confianzas) / len(confianzas) if confianzas else 0
    
    # Motores utilizados
    motores = {}
    for contenido in contenidos:
        motor = contenido.motor_usado
        motores[motor] = motores.get(motor, 0) + 1
    
    # Distribución de confianza
    distribucion = {
        "excelente (90-100%)": len([c for c in confianzas if c >= 90]),
        "buena (70-89%)": len([c for c in confianzas if 70 <= c < 90]),
        "regular (50-69%)": len([c for c in confianzas if 50 <= c < 70]),
        "baja (0-49%)": len([c for c in confianzas if c < 50])
    }
    
    # Análisis de texto
    total_caracteres = sum(len(c.texto_extraido or "") for c in contenidos)
    total_palabras = sum(len((c.texto_extraido or "").split()) for c in contenidos)
    
    return {
        "success": True,
        "tomo_id": tomo_id,
        "estadisticas": {
            "total_paginas": total_paginas,
            "paginas_procesadas": paginas_procesadas,
            "paginas_con_errores": paginas_con_errores,
            "confianza_promedio": round(confianza_promedio, 2),
            "motores_utilizados": motores,
            "distribucion_confianza": distribucion,
            "total_caracteres": total_caracteres,
            "total_palabras": total_palabras,
            "promedio_caracteres_por_pagina": round(total_caracteres / total_paginas, 0) if total_paginas > 0 else 0,
            "promedio_palabras_por_pagina": round(total_palabras / total_paginas, 0) if total_paginas > 0 else 0
        }
    }

def _analizar_calidad_contenido(contenidos: List[ContenidoOCR]) -> Dict[str, Any]:
    """Analiza la calidad del contenido OCR"""
    
    total_paginas = len(contenidos)
    paginas_buena_calidad = 0
    paginas_calidad_media = 0
    paginas_baja_calidad = 0
    paginas_error = 0
    
    total_confianza = 0
    caracteres_por_pagina = []
    motores_performance = {}
    
    for contenido in contenidos:
        # Clasificar por confianza
        confianza = contenido.confianza_porcentaje
        motor = contenido.motor_usado
        
        if motor == 'error':
            paginas_error += 1
        elif confianza >= 80:
            paginas_buena_calidad += 1
        elif confianza >= 50:
            paginas_calidad_media += 1
        else:
            paginas_baja_calidad += 1
        
        total_confianza += confianza
        
        # Analizar longitud de texto
        texto_length = len(contenido.texto_extraido or "")
        caracteres_por_pagina.append(texto_length)
        
        # Performance por motor
        if motor not in motores_performance:
            motores_performance[motor] = {"count": 0, "confianza_total": 0}
        motores_performance[motor]["count"] += 1
        motores_performance[motor]["confianza_total"] += confianza
    
    # Calcular promedios por motor
    for motor in motores_performance:
        count = motores_performance[motor]["count"]
        motores_performance[motor]["confianza_promedio"] = round(
            motores_performance[motor]["confianza_total"] / count, 2
        ) if count > 0 else 0
    
    # Calcular promedio de caracteres
    promedio_chars = sum(caracteres_por_pagina) / len(caracteres_por_pagina) if caracteres_por_pagina else 0
    
    # Determinar calidad general
    porcentaje_buena = (paginas_buena_calidad / total_paginas) * 100 if total_paginas > 0 else 0
    
    if porcentaje_buena >= 80:
        calidad_general = "Excelente"
    elif porcentaje_buena >= 60:
        calidad_general = "Buena"
    elif porcentaje_buena >= 40:
        calidad_general = "Regular"
    else:
        calidad_general = "Necesita Mejoras"
    
    return {
        "calidad_general": calidad_general,
        "confianza_promedio": round(total_confianza / total_paginas, 2) if total_paginas > 0 else 0,
        "distribucion_calidad": {
            "buena_calidad": paginas_buena_calidad,
            "calidad_media": paginas_calidad_media,
            "baja_calidad": paginas_baja_calidad,
            "errores": paginas_error
        },
        "porcentajes": {
            "buena_calidad": round((paginas_buena_calidad / total_paginas) * 100, 1) if total_paginas > 0 else 0,
            "calidad_media": round((paginas_calidad_media / total_paginas) * 100, 1) if total_paginas > 0 else 0,
            "baja_calidad": round((paginas_baja_calidad / total_paginas) * 100, 1) if total_paginas > 0 else 0,
            "errores": round((paginas_error / total_paginas) * 100, 1) if total_paginas > 0 else 0
        },
        "performance_motores": motores_performance,
        "promedio_caracteres_por_pagina": round(promedio_chars, 0),
        "recomendaciones": _generar_recomendaciones(
            porcentaje_buena, paginas_error, total_paginas, motores_performance
        )
    }

def _generar_recomendaciones(porcentaje_buena: float, paginas_error: int, 
                           total_paginas: int, motores_performance: Dict) -> List[str]:
    """Genera recomendaciones basadas en el análisis"""
    recomendaciones = []
    
    if porcentaje_buena < 60:
        recomendaciones.append("Se recomienda reprocesar el documento con configuraciones OCR mejoradas")
    
    if paginas_error > 0:
        porcentaje_error = (paginas_error / total_paginas) * 100
        if porcentaje_error > 10:
            recomendaciones.append(f"Alto porcentaje de errores ({porcentaje_error:.1f}%). Verificar calidad del documento original")
    
    # Analizar performance de motores
    mejor_motor = None
    mejor_confianza = 0
    for motor, data in motores_performance.items():
        if motor != 'error' and data['confianza_promedio'] > mejor_confianza:
            mejor_confianza = data['confianza_promedio']
            mejor_motor = motor
    
    if mejor_motor and mejor_confianza > 80:
        recomendaciones.append(f"Motor {mejor_motor} mostró mejor performance. Considerar usarlo como principal")
    
    if not recomendaciones:
        recomendaciones.append("La calidad del OCR es satisfactoria")
    
    return recomendaciones