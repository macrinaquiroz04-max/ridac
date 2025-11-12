# app/routes/tasks.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Año: 2025

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.routes.auth import get_current_user
from app.utils.logger import logger
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener estado de una tarea asíncrona"""
    try:
        task = AsyncResult(task_id, app=celery_app)
        
        if task.state == 'PENDING':
            response = {
                'task_id': task_id,
                'status': 'pending',
                'mensaje': 'Tarea en cola de espera'
            }
        elif task.state == 'PROGRESS':
            response = {
                'task_id': task_id,
                'status': 'processing',
                'progreso': task.info,
                'mensaje': task.info.get('mensaje', 'Procesando...')
            }
        elif task.state == 'SUCCESS':
            response = {
                'task_id': task_id,
                'status': 'completed',
                'resultado': task.result,
                'mensaje': 'Tarea completada exitosamente'
            }
        elif task.state == 'FAILURE':
            response = {
                'task_id': task_id,
                'status': 'failed',
                'error': str(task.info),
                'mensaje': 'Error al procesar la tarea'
            }
        else:
            response = {
                'task_id': task_id,
                'status': task.state.lower(),
                'mensaje': f'Estado: {task.state}'
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de tarea {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ocr/{tomo_id}")
async def iniciar_ocr_asincrono(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Iniciar procesamiento OCR asíncrono"""
    try:
        from app.tasks.ocr_tasks import procesar_tomo_ocr
        
        # Iniciar tarea asíncrona
        task = procesar_tomo_ocr.apply_async(
            args=[tomo_id, current_user.id],
            queue='ocr'
        )
        
        logger.info(f"🚀 Tarea OCR iniciada - Task ID: {task.id}, Tomo: {tomo_id}")
        
        return {
            'task_id': task.id,
            'tomo_id': tomo_id,
            'status': 'initiated',
            'mensaje': 'Procesamiento OCR iniciado'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando tarea OCR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ocr/batch")
async def iniciar_ocr_lote(
    tomo_ids: list,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Iniciar procesamiento OCR de múltiples tomos"""
    try:
        from app.tasks.ocr_tasks import procesar_lote_tomos
        
        task = procesar_lote_tomos.apply_async(
            args=[tomo_ids, current_user.id],
            queue='ocr'
        )
        
        logger.info(f"🚀 Lote OCR iniciado - Task ID: {task.id}, Tomos: {len(tomo_ids)}")
        
        return {
            'task_id': task.id,
            'total_tomos': len(tomo_ids),
            'status': 'initiated',
            'mensaje': f'Procesamiento de {len(tomo_ids)} tomos iniciado'
        }
        
    except Exception as e:
        logger.error(f"Error iniciando lote OCR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}")
async def cancelar_tarea(
    task_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Cancelar una tarea en ejecución"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        
        logger.info(f"🛑 Tarea cancelada: {task_id}")
        
        return {
            'task_id': task_id,
            'status': 'cancelled',
            'mensaje': 'Tarea cancelada exitosamente'
        }
        
    except Exception as e:
        logger.error(f"Error cancelando tarea {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
