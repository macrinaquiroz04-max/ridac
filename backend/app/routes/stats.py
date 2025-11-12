# app/routes/stats.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Año: 2025

from fastapi import APIRouter, Depends
from app.models.usuario import Usuario
from app.routes.auth import get_current_user
from app.services.cache_service import cache_service
from app.services.elasticsearch_service import elasticsearch_service
from app.services.minio_service import minio_service
from app.redis_config import redis_config

router = APIRouter(prefix="/api/stats", tags=["Statistics"])

@router.get("/system")
async def get_system_stats(current_user: Usuario = Depends(get_current_user)):
    """Obtener estadísticas del sistema"""
    
    stats = {
        'cache': cache_service.get_stats(),
        'redis': {
            'enabled': redis_config.is_available(),
            'url': redis_config.redis_url if redis_config.is_available() else None
        },
        'elasticsearch': {
            'enabled': elasticsearch_service.enabled,
            'index': elasticsearch_service.index_name if elasticsearch_service.enabled else None
        },
        'minio': {
            'enabled': minio_service.enabled,
            'buckets': [minio_service.bucket_pdfs, minio_service.bucket_thumbnails] if minio_service.enabled else []
        }
    }
    
    return stats

@router.get("/cache")
async def get_cache_stats(current_user: Usuario = Depends(get_current_user)):
    """Obtener estadísticas detalladas del caché"""
    return cache_service.get_stats()
