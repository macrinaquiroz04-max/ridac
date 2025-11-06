# backend/app/routes/system_health.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime

from app.database import get_db
from app.middlewares.auth_middleware import get_current_user
from app.models.usuario import Usuario
from app.utils.error_logger import get_error_stats, get_recent_errors, get_logs_disk_usage, cleanup_old_logs

router = APIRouter(prefix="/api/system", tags=["System Health"])


@router.get("/errors/stats")
async def get_system_error_stats(
    current_user: Usuario = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtiene estadísticas de errores del sistema
    Solo accesible para administradores
    """
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver estadísticas de errores")
    
    stats = get_error_stats()
    disk_usage = get_logs_disk_usage()
    
    return {
        "status": "success",
        "data": {
            **stats,
            "disk_usage": disk_usage
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/errors/recent")
async def get_recent_system_errors(
    limit: int = 50,
    current_user: Usuario = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtiene los errores más recientes del sistema
    Solo accesible para administradores
    """
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver errores")
    
    errors = get_recent_errors(limit=limit)
    return {
        "status": "success",
        "data": errors,
        "count": len(errors),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health/detailed")
async def get_detailed_health(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Obtiene información detallada de salud del sistema
    Incluye errores, warnings, y estado de servicios
    """
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver salud del sistema")
    
    error_stats = get_error_stats()
    
    # Verificar estado de la base de datos
    db_healthy = True
    try:
        db.execute("SELECT 1")
    except Exception:
        db_healthy = False
    
    # Calcular salud general
    health_score = 100
    if error_stats["critical_errors"] > 0:
        health_score -= 30
    if error_stats["last_24h_errors"] > 10:
        health_score -= 20
    if not db_healthy:
        health_score -= 50
    
    health_status = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy"
    
    return {
        "status": health_status,
        "health_score": max(0, health_score),
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "backend": "healthy"
        },
        "errors": {
            "total": error_stats["total_errors"],
            "critical": error_stats["critical_errors"],
            "last_24h": error_stats["last_24h_errors"],
            "warnings": error_stats["warnings"]
        },
        "recommendations": _get_recommendations(error_stats, db_healthy)
    }


def _get_recommendations(error_stats: Dict, db_healthy: bool) -> List[str]:
    """Genera recomendaciones basadas en el estado del sistema"""
    recommendations = []
    
    if error_stats["critical_errors"] > 0:
        recommendations.append("⚠️ Hay errores críticos que requieren atención inmediata")
    
    if error_stats["last_24h_errors"] > 20:
        recommendations.append("⚠️ Alto número de errores en las últimas 24 horas")
    
    if not db_healthy:
        recommendations.append("🔴 La base de datos no está respondiendo correctamente")
    
    if error_stats["warnings"] > 50:
        recommendations.append("💡 Muchas advertencias acumuladas, considere revisar los logs")
    
    if len(recommendations) == 0:
        recommendations.append("✅ El sistema está funcionando correctamente")
    
    return recommendations


@router.post("/logs/cleanup")
async def cleanup_system_logs(
    days: int = 7,
    current_user: Usuario = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Limpia logs antiguos manualmente
    Solo accesible para administradores
    """
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden limpiar logs")
    
    try:
        cleanup_old_logs(days=days)
        disk_usage = get_logs_disk_usage()
        
        return {
            "status": "success",
            "message": f"Logs de más de {days} días eliminados",
            "disk_usage": disk_usage,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
