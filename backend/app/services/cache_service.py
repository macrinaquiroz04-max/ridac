# app/services/cache_service.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Organización: Unidad de Análisis y Contexto (UAyC)
# Año: 2025 - Propiedad Intelectual Registrada
# Firma Digital: ELQ-ISC-UAYC-10112025

import json
import hashlib
from typing import Any, Optional
from app.redis_config import redis_config
from app.utils.logger import logger

class CacheService:
    """Servicio de caché con Redis"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        self._initialize()
    
    def _initialize(self):
        """Inicializar conexión con Redis"""
        try:
            self.redis_client = redis_config.get_client()
            self.enabled = redis_config.is_available()
        except Exception as e:
            logger.warning(f"⚠️ Caché deshabilitado: {e}")
            self.enabled = False
    
    def _generate_key(self, prefix: str, params: dict) -> str:
        """Generar clave única para el caché"""
        params_str = json.dumps(params, sort_keys=True)
        hash_key = hashlib.md5(params_str.encode()).hexdigest()
        return f"{prefix}:{hash_key}"
    
    def get(self, prefix: str, params: dict = None) -> Optional[Any]:
        """
        Obtener valor del caché
        
        Args:
            prefix: Prefijo de la clave o clave completa si params es None
            params: Parámetros para generar la clave (opcional)
            
        Returns:
            Valor del caché o None si no existe
        """
        if not self.enabled:
            return None
        
        try:
            # Si no hay params, usar prefix como clave directa
            if params is None:
                key = prefix
            else:
                key = self._generate_key(prefix, params)
            
            value = self.redis_client.get(key)
            
            if value:
                logger.debug(f"✅ Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"❌ Cache MISS: {key}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo del caché: {e}")
            return None
    
    def set(self, prefix: str, value: Any, params: dict = None, ttl: int = 3600):
        """
        Guardar valor en el caché
        
        Args:
            prefix: Prefijo de la clave o clave completa si params es None
            value: Valor a guardar
            params: Parámetros para generar la clave (opcional)
            ttl: Tiempo de vida en segundos (default: 1 hora)
        """
        if not self.enabled:
            return
        
        try:
            # Si no hay params, usar prefix como clave directa
            if params is None:
                key = prefix
            else:
                key = self._generate_key(prefix, params)
            value_str = json.dumps(value, ensure_ascii=False, default=str)
            self.redis_client.setex(key, ttl, value_str)
            logger.debug(f"💾 Cache SET: {key} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"❌ Error guardando en caché: {e}")
    
    def delete(self, key: str):
        """
        Eliminar valor del caché por clave directa
        
        Args:
            key: Clave a eliminar (puede incluir wildcards con invalidate_pattern)
        """
        if not self.enabled:
            return
        
        try:
            self.redis_client.delete(key)
            logger.debug(f"🗑️ Cache DELETE: {key}")
                    
        except Exception as e:
            logger.error(f"❌ Error eliminando del caché: {e}")
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidar todas las claves que coincidan con un patrón
        
        Args:
            pattern: Patrón de búsqueda (ej: 'busqueda:*', 'tomo:123:*')
        """
        if not self.enabled:
            return
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"🗑️ Invalidadas {len(keys)} claves: {pattern}")
        except Exception as e:
            logger.error(f"❌ Error invalidando patrón {pattern}: {e}")
    
    def get_stats(self) -> dict:
        """Obtener estadísticas del caché"""
        if not self.enabled:
            return {'enabled': False}
        
        try:
            info = self.redis_client.info('stats')
            return {
                'enabled': True,
                'total_keys': self.redis_client.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'memory_used': info.get('used_memory_human', 'N/A')
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo stats: {e}")
            return {'enabled': False, 'error': str(e)}

# Instancia global
cache_service = CacheService()
