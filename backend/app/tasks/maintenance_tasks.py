# app/tasks/maintenance_tasks.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Año: 2025

from app.tasks.celery_app import celery_app
from app.utils.logger import logger
import os
from datetime import datetime, timedelta

@celery_app.task(name='app.tasks.maintenance_tasks.limpiar_cache')
def limpiar_cache():
    """Limpiar caché de Redis"""
    try:
        logger.info("🧹 Limpiando caché de Redis...")
        from app.redis_config import redis_config
        
        client = redis_config.get_client()
        if client:
            # Limpiar claves antiguas (pattern: cache:*)
            keys = client.keys("cache:*")
            if keys:
                client.delete(*keys)
                logger.info(f"✅ {len(keys)} claves de caché eliminadas")
        
        return {'status': 'success', 'keys_deleted': len(keys) if keys else 0}
    except Exception as e:
        logger.error(f"❌ Error limpiando caché: {e}")
        raise

@celery_app.task(name='app.tasks.maintenance_tasks.limpiar_logs_antiguos')
def limpiar_logs_antiguos():
    """Limpiar logs de más de 30 días"""
    try:
        logger.info("🧹 Limpiando logs antiguos...")
        
        logs_dir = "/app/logs"
        if not os.path.exists(logs_dir):
            return {'status': 'success', 'mensaje': 'Directorio de logs no existe'}
        
        cutoff_date = datetime.now() - timedelta(days=30)
        archivos_eliminados = 0
        
        for filename in os.listdir(logs_dir):
            filepath = os.path.join(logs_dir, filename)
            if os.path.isfile(filepath):
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_time < cutoff_date:
                    os.remove(filepath)
                    archivos_eliminados += 1
        
        logger.info(f"✅ {archivos_eliminados} archivos de log eliminados")
        return {'status': 'success', 'archivos_eliminados': archivos_eliminados}
        
    except Exception as e:
        logger.error(f"❌ Error limpiando logs: {e}")
        raise

@celery_app.task(name='app.tasks.maintenance_tasks.backup_database')
def backup_database():
    """Realizar backup automático de la base de datos"""
    try:
        logger.info("💾 Iniciando backup automático de base de datos...")
        # Aquí iría la lógica de backup
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"❌ Error en backup: {e}")
        raise
