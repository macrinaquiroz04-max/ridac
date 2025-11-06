# backend/app/services/background_service.py

import threading
import time
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.tarea_ocr import TareaOCR
from app.models.tomo import Tomo
from app.utils.logger import logger

class BackgroundOCRService:
    """Servicio de procesamiento OCR en background sin Celery"""

    def __init__(self):
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        """Iniciar worker de procesamiento"""
        with self.lock:
            if self.running:
                logger.warning("Worker ya está corriendo")
                return

            self.running = True
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
            logger.info("✓ Worker de OCR iniciado")

    def stop(self):
        """Detener worker"""
        with self.lock:
            self.running = False

        if self.worker_thread:
            self.worker_thread.join(timeout=10)

        logger.info("✓ Worker de OCR detenido")

    def _process_queue(self):
        """Procesar cola de tareas continuamente"""
        logger.info("Worker de OCR: Iniciando loop de procesamiento")

        while self.running:
            db = None
            try:
                db = SessionLocal()

                # Buscar tarea pendiente con mayor prioridad
                tarea = db.query(TareaOCR).filter(
                    TareaOCR.estado == 'pendiente',
                    TareaOCR.reintentos < TareaOCR.maximo_reintentos
                ).order_by(TareaOCR.prioridad.desc(), TareaOCR.created_at.asc()).first()

                if tarea:
                    logger.info(f"Procesando tarea OCR #{tarea.id} para tomo #{tarea.tomo_id}")
                    self._process_task(db, tarea)
                else:
                    # No hay tareas, esperar 5 segundos
                    time.sleep(5)

            except Exception as e:
                logger.error(f"Error en worker: {e}", exc_info=True)
                time.sleep(10)
            finally:
                if db:
                    db.close()

    def _process_task(self, db: Session, tarea: TareaOCR):
        """Procesar una tarea específica"""
        try:
            # Marcar como procesando
            tarea.estado = 'procesando'
            tarea.tiempo_inicio = datetime.utcnow()
            tarea.reintentos += 1
            db.commit()

            # Obtener tomo
            tomo = db.query(Tomo).filter(Tomo.id == tarea.tomo_id).first()

            if not tomo:
                raise Exception("Tomo no encontrado")

            # Actualizar estado del tomo
            tomo.estado_ocr = 'procesando'
            tomo.progreso_ocr = 0
            db.commit()

            # Procesar OCR
            logger.info(f"Iniciando OCR para tomo {tomo.id}: {tomo.nombre_archivo}")

            # Importar aquí para evitar dependencias circulares
            from app.services.ocr_service import OCRService
            ocr_service = OCRService()
            ocr_service.procesar_pdf(db, tomo)

            # Marcar como completado
            tarea.estado = 'completado'
            tarea.tiempo_fin = datetime.utcnow()
            tomo.estado_ocr = 'completado'
            tomo.progreso_ocr = 100
            db.commit()

            logger.info(f"✓ OCR completado para tomo {tomo.id}")

        except Exception as e:
            logger.error(f"Error procesando tarea {tarea.id}: {e}", exc_info=True)

            # Marcar error
            tarea.error_mensaje = str(e)
            if tomo:
                tomo.error_ocr = str(e)

            if tarea.reintentos >= tarea.maximo_reintentos:
                tarea.estado = 'error'
                if tomo:
                    tomo.estado_ocr = 'error'
                logger.error(f"✗ Tarea {tarea.id} falló después de {tarea.reintentos} intentos")
            else:
                tarea.estado = 'pendiente'  # Reintentar
                logger.warning(f"⚠ Tarea {tarea.id} reintentará ({tarea.reintentos}/{tarea.maximo_reintentos})")

            db.commit()

    def agregar_tarea(self, tomo_id: int, prioridad: int = 0) -> int:
        """Agregar nueva tarea a la cola"""
        db = SessionLocal()
        try:
            # Verificar si ya existe una tarea pendiente para este tomo
            tarea_existente = db.query(TareaOCR).filter(
                TareaOCR.tomo_id == tomo_id,
                TareaOCR.estado.in_(['pendiente', 'procesando'])
            ).first()

            if tarea_existente:
                logger.warning(f"Ya existe una tarea para el tomo {tomo_id}")
                return tarea_existente.id

            # Crear nueva tarea
            nueva_tarea = TareaOCR(
                tomo_id=tomo_id,
                estado='pendiente',
                prioridad=prioridad
            )
            db.add(nueva_tarea)
            db.commit()
            db.refresh(nueva_tarea)

            logger.info(f"✓ Tarea OCR #{nueva_tarea.id} creada para tomo #{tomo_id}")
            return nueva_tarea.id

        except Exception as e:
            logger.error(f"Error creando tarea: {e}")
            db.rollback()
            raise
        finally:
            db.close()

# Instancia global
background_service = BackgroundOCRService()
