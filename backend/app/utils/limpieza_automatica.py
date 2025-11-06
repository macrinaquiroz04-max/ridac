# backend/app/utils/limpieza_automatica.py

from sqlalchemy.orm import Session
from app.models.permiso_tomo import PermisoTomo
from app.models.usuario import Usuario
from app.utils.logger import logger
from typing import Dict, Any
import asyncio

class LimpiezaAutomatica:
    """Sistema de limpieza automática para optimizar la base de datos"""
    
    @staticmethod
    def limpiar_permisos_vacios(db: Session) -> Dict[str, Any]:
        """
        Elimina permisos donde todos los campos están en False
        Optimizado para sistemas con hasta 50 usuarios
        """
        try:
            # Buscar permisos vacíos
            permisos_vacios = db.query(PermisoTomo).filter(
                PermisoTomo.puede_ver == False,
                PermisoTomo.puede_buscar == False,
                PermisoTomo.puede_exportar == False
            ).all()
            
            eliminados = len(permisos_vacios)
            
            if eliminados > 0:
                # Eliminar en lote para mejor rendimiento
                db.query(PermisoTomo).filter(
                    PermisoTomo.puede_ver == False,
                    PermisoTomo.puede_buscar == False,
                    PermisoTomo.puede_exportar == False
                ).delete(synchronize_session=False)
                
                db.commit()
                logger.info(f"🧹 Limpieza automática: {eliminados} permisos vacíos eliminados")
            
            return {
                "permisos_eliminados": eliminados,
                "mensaje": f"Limpieza completada: {eliminados} registros eliminados"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error en limpieza automática: {str(e)}")
            return {
                "permisos_eliminados": 0,
                "error": str(e)
            }
    
    @staticmethod
    def verificar_y_limpiar_usuario(db: Session, usuario_id: int) -> bool:
        """
        Limpia permisos vacíos de un usuario específico
        """
        try:
            eliminados = db.query(PermisoTomo).filter(
                PermisoTomo.usuario_id == usuario_id,
                PermisoTomo.puede_ver == False,
                PermisoTomo.puede_buscar == False,
                PermisoTomo.puede_exportar == False
            ).delete(synchronize_session=False)
            
            if eliminados > 0:
                db.commit()
                logger.info(f"🧹 Usuario {usuario_id}: {eliminados} permisos vacíos eliminados")
            
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error limpiando usuario {usuario_id}: {str(e)}")
            return False
    
    @staticmethod
    def optimizar_base_datos(db: Session) -> Dict[str, Any]:
        """
        Ejecuta optimizaciones completas para desarrollo
        """
        resultados = {
            "permisos_limpiados": 0,
            "usuarios_optimizados": 0,
            "errores": []
        }
        
        try:
            # 1. Limpiar permisos vacíos
            limpieza = LimpiezaAutomatica.limpiar_permisos_vacios(db)
            resultados["permisos_limpiados"] = limpieza["permisos_eliminados"]
            
            # 2. Verificar usuarios activos
            usuarios_activos = db.query(Usuario).filter(Usuario.activo == True).count()
            resultados["usuarios_activos"] = usuarios_activos
            
            # 3. Conteo de permisos totales
            permisos_totales = db.query(PermisoTomo).count()
            resultados["permisos_activos"] = permisos_totales
            
            logger.info(f"✅ Optimización completada: {resultados}")
            
        except Exception as e:
            logger.error(f"❌ Error en optimización: {str(e)}")
            resultados["errores"].append(str(e))
        
        return resultados