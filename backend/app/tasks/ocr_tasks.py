# app/tasks/ocr_tasks.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Organización: Unidad de Análisis y Contexto (UAyC)
# Año: 2025 - Propiedad Intelectual Registrada
# Firma Digital: ELQ-ISC-UAYC-10112025

from celery import Task
from app.tasks.celery_app import celery_app
from app.utils.logger import logger
import time

class OCRTask(Task):
    """Clase base para tareas OCR con manejo de progreso"""
    
    def update_progress(self, current: int, total: int, mensaje: str = ""):
        """Actualizar progreso de la tarea"""
        self.update_state(
            state='PROGRESS',
            meta={
                'current': current,
                'total': total,
                'percent': int((current / total) * 100) if total > 0 else 0,
                'mensaje': mensaje
            }
        )

@celery_app.task(bind=True, base=OCRTask, name='app.tasks.ocr_tasks.procesar_tomo_ocr')
def procesar_tomo_ocr(self, tomo_id: int, usuario_id: int):
    """
    Procesar OCR de un tomo de forma asíncrona
    
    Args:
        tomo_id: ID del tomo a procesar
        usuario_id: ID del usuario que solicita el procesamiento
    """
    try:
        logger.info(f"📄 Iniciando procesamiento OCR asíncrono - Tomo ID: {tomo_id}")
        
        # Actualizar progreso: Iniciando
        self.update_progress(0, 100, "Iniciando procesamiento OCR...")
        
        # Importar aquí para evitar problemas de importación circular
        from app.controllers.ocr_controller import OCRController
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            ocr_controller = OCRController()
            
            # Actualizar progreso: Extrayendo PDF
            self.update_progress(10, 100, "Extrayendo contenido del PDF...")
            time.sleep(0.5)  # Simular procesamiento
            
            # Aquí iría la lógica real de OCR
            # resultado = ocr_controller.procesar_tomo(db, tomo_id, usuario_id)
            
            # Actualizar progreso: Procesando OCR
            self.update_progress(50, 100, "Aplicando OCR con Google Vision...")
            time.sleep(1)  # Simular procesamiento
            
            # Actualizar progreso: Guardando resultados
            self.update_progress(80, 100, "Guardando resultados en base de datos...")
            time.sleep(0.5)
            
            # Actualizar progreso: Completado
            self.update_progress(100, 100, "Procesamiento completado exitosamente")
            
            logger.info(f"✅ OCR completado - Tomo ID: {tomo_id}")
            
            return {
                'status': 'success',
                'tomo_id': tomo_id,
                'mensaje': 'OCR procesado correctamente'
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error en procesamiento OCR - Tomo ID {tomo_id}: {e}")
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'tomo_id': tomo_id
            }
        )
        raise

@celery_app.task(bind=True, base=OCRTask, name='app.tasks.ocr_tasks.procesar_lote_tomos')
def procesar_lote_tomos(self, tomo_ids: list, usuario_id: int):
    """
    Procesar múltiples tomos en lote
    
    Args:
        tomo_ids: Lista de IDs de tomos a procesar
        usuario_id: ID del usuario que solicita el procesamiento
    """
    try:
        total = len(tomo_ids)
        logger.info(f"📚 Procesando lote de {total} tomos")
        
        resultados = []
        for idx, tomo_id in enumerate(tomo_ids, 1):
            self.update_progress(
                idx - 1, 
                total, 
                f"Procesando tomo {idx} de {total}..."
            )
            
            # Procesar cada tomo
            resultado = procesar_tomo_ocr.apply_async(
                args=[tomo_id, usuario_id],
                queue='ocr'
            )
            resultados.append({
                'tomo_id': tomo_id,
                'task_id': resultado.id
            })
        
        self.update_progress(total, total, "Lote procesado completamente")
        
        return {
            'status': 'success',
            'total': total,
            'resultados': resultados
        }
        
    except Exception as e:
        logger.error(f"❌ Error procesando lote: {e}")
        raise
