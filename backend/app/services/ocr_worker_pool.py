"""
Worker Pool para procesamiento OCR concurrente
Permite múltiples usuarios procesando tomos simultáneamente sin bloquear el servidor
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Optional
from datetime import datetime
import threading
import os

logger = logging.getLogger(__name__)


class OCRWorkerPool:
    """
    Pool de workers para procesamiento OCR concurrente.
    Usa ThreadPoolExecutor para verdadero paralelismo.
    
    Permite que múltiples usuarios procesen tomos simultáneamente
    sin bloquear el servidor FastAPI.
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Inicializar pool de workers
        
        Args:
            max_workers: Número máximo de tomos procesándose simultáneamente
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="OCR-Worker"
        )
        self.active_tasks: Dict[str, dict] = {}
        self.lock = threading.Lock()
        
        logger.info(f"🔧 OCR Worker Pool inicializado con {max_workers} workers")
    
    def submit_ocr_task(
        self,
        task_id: str,
        ocr_function: Callable,
        *args,
        **kwargs
    ) -> asyncio.Future:
        """
        Enviar tarea de OCR al pool de workers
        
        Args:
            task_id: ID único de la tarea (ej: "ocr_tomo_123")
            ocr_function: Función a ejecutar en thread separado
            *args, **kwargs: Argumentos para la función
            
        Returns:
            Future que se completará cuando termine el procesamiento
            
        Raises:
            ValueError: Si la tarea ya está en proceso
        """
        with self.lock:
            if task_id in self.active_tasks:
                raise ValueError(f"Tarea {task_id} ya está en proceso")
            
            # Registrar tarea activa
            self.active_tasks[task_id] = {
                "inicio": datetime.now(),
                "estado": "iniciando",
                "thread_id": None
            }
        
        logger.info(f"📤 Enviando tarea {task_id} al worker pool")
        logger.info(f"📊 Tareas activas: {len(self.active_tasks)}/{self.max_workers}")
        
        # Obtener el event loop actual
        loop = asyncio.get_event_loop()
        
        # Ejecutar en thread separado
        future = loop.run_in_executor(
            self.executor,
            self._wrapper_function,
            task_id,
            ocr_function,
            args,
            kwargs
        )
        
        # Callback cuando termine
        future.add_done_callback(lambda f: self._on_task_complete(task_id, f))
        
        return future
    
    def _wrapper_function(self, task_id: str, func: Callable, args, kwargs):
        """
        Wrapper que ejecuta la función en el thread
        Maneja el estado y logging de la tarea
        """
        try:
            # Actualizar estado
            with self.lock:
                self.active_tasks[task_id]["estado"] = "procesando"
                self.active_tasks[task_id]["thread_id"] = threading.current_thread().name
            
            logger.info(f"🔄 Ejecutando {task_id} en {threading.current_thread().name}")
            
            # Ejecutar la función OCR
            result = func(*args, **kwargs)
            
            logger.info(f"✅ {task_id} completado exitosamente")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en {task_id}: {str(e)}", exc_info=True)
            raise
    
    def _on_task_complete(self, task_id: str, future: asyncio.Future):
        """
        Callback cuando una tarea se completa (exitosa o con error)
        """
        with self.lock:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
        
        if future.exception():
            logger.error(f"❌ Tarea {task_id} falló: {future.exception()}")
        else:
            logger.info(f"✅ Tarea {task_id} completada")
        
        logger.info(f"📊 Tareas activas restantes: {len(self.active_tasks)}/{self.max_workers}")
    
    def get_active_tasks(self) -> Dict[str, dict]:
        """
        Obtener lista de tareas activas
        
        Returns:
            Dict con información de cada tarea activa
        """
        with self.lock:
            return self.active_tasks.copy()
    
    def is_task_active(self, task_id: str) -> bool:
        """
        Verificar si una tarea está activa
        
        Args:
            task_id: ID de la tarea a verificar
            
        Returns:
            True si la tarea está en proceso, False si no
        """
        with self.lock:
            return task_id in self.active_tasks
    
    def get_available_workers(self) -> int:
        """
        Obtener número de workers disponibles
        
        Returns:
            Número de workers que pueden aceptar nuevas tareas
        """
        with self.lock:
            return self.max_workers - len(self.active_tasks)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Intentar cancelar una tarea en proceso
        
        Args:
            task_id: ID de la tarea a cancelar
            
        Returns:
            True si se pudo marcar para cancelación, False si no existe
            
        Note:
            La cancelación real depende de si la función OCR verifica
            el flag de cancelación. Este método solo marca la tarea.
        """
        with self.lock:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["estado"] = "cancelando"
                logger.warning(f"⚠️ Tarea {task_id} marcada para cancelación")
                return True
            return False
    
    def shutdown(self, wait: bool = True):
        """
        Apagar el pool de workers
        
        Args:
            wait: Si True, espera a que terminen las tareas activas
        """
        logger.info("🛑 Apagando OCR Worker Pool...")
        self.executor.shutdown(wait=wait)
        logger.info("✅ OCR Worker Pool apagado")


# Instancia global del worker pool
# Configurable vía variable de entorno OCR_MAX_WORKERS
MAX_OCR_WORKERS = int(os.getenv("OCR_MAX_WORKERS", "4"))

logger.info(f"🚀 Inicializando OCR Worker Pool global con {MAX_OCR_WORKERS} workers")
ocr_worker_pool = OCRWorkerPool(max_workers=MAX_OCR_WORKERS)
