# app/redis_config.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Organización: Unidad de Análisis y Contexto (UAyC)
# Año: 2025 - Propiedad Intelectual Registrada
# Firma Digital: ELQ-ISC-UAYC-10112025

import os
import redis
from typing import Optional
from app.utils.logger import logger

class RedisConfig:
    """Configuración de Redis para caché y sesiones"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client: Optional[redis.Redis] = None
        
    def get_client(self) -> redis.Redis:
        """Obtener cliente de Redis con reconexión automática"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Probar conexión
                self.redis_client.ping()
                logger.info("✅ Redis conectado exitosamente")
            except Exception as e:
                logger.error(f"❌ Error conectando a Redis: {e}")
                logger.warning("⚠️ Sistema funcionará sin caché")
                self.redis_client = None
        
        return self.redis_client
    
    def is_available(self) -> bool:
        """Verificar si Redis está disponible"""
        try:
            client = self.get_client()
            if client:
                client.ping()
                return True
        except:
            pass
        return False

# Instancia global
redis_config = RedisConfig()
