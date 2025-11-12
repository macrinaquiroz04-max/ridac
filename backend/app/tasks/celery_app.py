# app/tasks/celery_app.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Organización: Unidad de Análisis y Contexto (UAyC)
# Año: 2025 - Propiedad Intelectual Registrada
# Firma Digital: ELQ-ISC-UAYC-10112025

import os
from celery import Celery
from app.utils.logger import logger

# Configuración de Celery
celery_app = Celery(
    "sistema_ocr",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
    include=[
        "app.tasks.ocr_tasks",
        "app.tasks.search_tasks",
        "app.tasks.maintenance_tasks"
    ]
)

# Configuración de Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Mexico_City',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hora máximo por tarea
    task_soft_time_limit=3300,  # 55 minutos soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # Los resultados expiran en 1 hora
)

# Tareas programadas (Celery Beat)
celery_app.conf.beat_schedule = {
    # Limpiar caché cada 6 horas
    'limpiar-cache-6h': {
        'task': 'app.tasks.maintenance_tasks.limpiar_cache',
        'schedule': 21600.0,  # 6 horas
    },
    # Limpiar logs antiguos cada día
    'limpiar-logs-diario': {
        'task': 'app.tasks.maintenance_tasks.limpiar_logs_antiguos',
        'schedule': 86400.0,  # 24 horas
        'options': {'queue': 'maintenance'}
    },
    # Actualizar índices de Elasticsearch cada hora
    'actualizar-indices-1h': {
        'task': 'app.tasks.search_tasks.actualizar_indices',
        'schedule': 3600.0,  # 1 hora
    },
}

logger.info("✅ Celery configurado correctamente")
