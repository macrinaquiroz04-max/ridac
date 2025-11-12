# backend/app/utils/auditoria_decorator.py
"""
Decorador para auditoría automática de operaciones CRUD
"""
from functools import wraps
from app.utils.auditoria_utils import registrar_auditoria
import logging

logger = logging.getLogger(__name__)

def auditar(accion: str, tabla: str = None):
    """
    Decorador para registrar automáticamente acciones en la auditoría
    
    Uso:
        @auditar("CREAR_TOMO", "tomos")
        async def crear_tomo(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Obtener current_user de los kwargs
            current_user = kwargs.get('current_user')
            
            # Ejecutar la función original
            result = await func(*args, **kwargs)
            
            # Registrar auditoría si hay usuario
            if current_user:
                try:
                    # Extraer información del resultado
                    valores_nuevos = {}
                    registro_id = None
                    
                    if hasattr(result, 'id'):
                        registro_id = result.id
                    if hasattr(result, '__dict__'):
                        valores_nuevos = {k: v for k, v in result.__dict__.items() 
                                        if not k.startswith('_')}
                    
                    registrar_auditoria(
                        usuario_id=current_user.id,
                        accion=accion,
                        tabla_afectada=tabla,
                        registro_id=registro_id,
                        valores_nuevos=valores_nuevos if valores_nuevos else None
                    )
                except Exception as e:
                    logger.error(f"Error registrando auditoría: {e}")
            
            return result
        return wrapper
    return decorator
