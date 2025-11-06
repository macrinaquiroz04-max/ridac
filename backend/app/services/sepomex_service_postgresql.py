"""
🗺️ SERVICIO SEPOMEX CON POSTGRESQL
===================================

Versión actualizada del servicio SEPOMEX que usa PostgreSQL en lugar de
diccionario Python.

VENTAJAS:
- ✅ Búsquedas ultrarrápidas con índices
- ✅ Fácil actualizar/agregar colonias (SQL)
- ✅ Búsqueda fuzzy con similitud de texto
- ✅ Full-text search en español
- ✅ Misma BD que la aplicación (transacciones consistentes)
- ✅ Backup automático con el resto de datos

"""

from typing import Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.database import SessionLocal

logger = logging.getLogger(__name__)

class SepomexServicePostgreSQL:
    """
    Servicio de validación SEPOMEX usando PostgreSQL
    """
    
    def __init__(self):
        self.use_database = True
        
        # Diccionario local como fallback (los 220 CPs actuales)
        self.diccionario_fallback = {
            # ... Tu diccionario actual aquí como backup
        }
    
    async def validar_codigo_postal(self, cp: str) -> Dict:
        """
        Valida un código postal y retorna información completa
        
        Args:
            cp: Código postal de 5 dígitos
            
        Returns:
            Dict con información del CP o error si no es válido
        """
        if not cp or len(cp) != 5:
            return {"valido": False, "codigo_postal": cp, "error": "CP debe tener 5 dígitos"}
        
        db = SessionLocal()
        
        try:
            # Consulta optimizada con índices
            result = db.execute(text("""
                SELECT DISTINCT 
                    estado,
                    municipio,
                    array_agg(DISTINCT colonia ORDER BY colonia) as colonias
                FROM sepomex_codigos_postales
                WHERE cp = :cp
                GROUP BY estado, municipio;
            """), {"cp": cp})
            
            row = result.fetchone()
            
            if row:
                return {
                    "valido": True,
                    "codigo_postal": cp,
                    "estado": row.estado,
                    "municipio": row.municipio,
                    "colonias": row.colonias,
                    "total_colonias": len(row.colonias),
                    "fuente": "postgresql"
                }
            else:
                return {
                    "valido": False,
                    "codigo_postal": cp,
                    "mensaje": f"CP {cp} no encontrado en catálogo"
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Error consultando BD SEPOMEX: {e}")
            # Fallback al diccionario local
            return await self._validar_desde_diccionario(cp)
        finally:
            db.close()
    
    async def buscar_colonias_por_cp(self, cp: str) -> List[str]:
        """
        Busca todas las colonias de un código postal
        
        Args:
            cp: Código postal de 5 dígitos
            
        Returns:
            Lista de nombres de colonias
        """
        db = SessionLocal()
        
        try:
            result = db.execute(text("""
                SELECT colonia
                FROM sepomex_codigos_postales
                WHERE cp = :cp
                ORDER BY colonia;
            """), {"cp": cp})
            
            return [row.colonia for row in result.fetchall()]
            
        except SQLAlchemyError as e:
            logger.error(f"Error buscando colonias: {e}")
            return []
        finally:
            db.close()
    
    async def validar_colonia_en_cp(self, colonia: str, cp: str) -> Dict:
        """
        Valida que una colonia pertenezca a un código postal específico
        
        Args:
            colonia: Nombre de la colonia
            cp: Código postal
            
        Returns:
            Dict con resultado de validación y sugerencias si hay error
        """
        db = SessionLocal()
        
        try:
            # Buscar colonia exacta (case-insensitive)
            result = db.execute(text("""
                SELECT EXISTS(
                    SELECT 1 
                    FROM sepomex_codigos_postales
                    WHERE cp = :cp 
                    AND UPPER(colonia) = UPPER(:colonia)
                ) as existe;
            """), {"cp": cp, "colonia": colonia})
            
            existe = result.scalar()
            
            if existe:
                return {
                    "valida": True,
                    "colonia": colonia,
                    "codigo_postal": cp,
                    "mensaje": "Colonia válida para este código postal",
                    "fuente": "postgresql"
                }
            
            # Si no es exacta, buscar similares (fuzzy search)
            result = db.execute(text("""
                SELECT 
                    colonia,
                    similarity(colonia, :colonia) as similitud
                FROM sepomex_codigos_postales
                WHERE cp = :cp
                AND similarity(colonia, :colonia) > 0.3
                ORDER BY similitud DESC
                LIMIT 5;
            """), {"cp": cp, "colonia": colonia})
            
            sugerencias = result.fetchall()
            
            if sugerencias:
                return {
                    "valida": False,
                    "colonia": colonia,
                    "codigo_postal": cp,
                    "mensaje": "Colonia no encontrada, posibles opciones:",
                    "fuente": "postgresql",
                    "sugerencias": [
                        {
                            "colonia": sug.colonia,
                            "similitud": round(sug.similitud, 2)
                        }
                        for sug in sugerencias
                    ]
                }
            else:
                # Verificar si la colonia existe en otro CP
                result = db.execute(text("""
                    SELECT cp, municipio
                    FROM sepomex_codigos_postales
                    WHERE UPPER(colonia) = UPPER(:colonia)
                    LIMIT 1;
                """), {"colonia": colonia})
                
                otra_ubicacion = result.fetchone()
                
                if otra_ubicacion:
                    return {
                        "valida": False,
                        "colonia": colonia,
                        "codigo_postal": cp,
                        "mensaje": f"La colonia '{colonia}' pertenece al CP {otra_ubicacion.cp} ({otra_ubicacion.municipio}), no al CP {cp}",
                        "fuente": "postgresql"
                    }
                else:
                    return {
                        "valida": False,
                        "colonia": colonia,
                        "codigo_postal": cp,
                        "mensaje": "Colonia no encontrada en catálogo SEPOMEX",
                        "fuente": "postgresql"
                    }
                    
        except SQLAlchemyError as e:
            logger.error(f"Error validando colonia: {e}")
            return {
                "valida": False,
                "error": "Error al consultar base de datos",
                "fuente": "postgresql"
            }
        finally:
            db.close()
    
    async def buscar_colonias_por_texto(self, texto: str, limite: int = 10) -> List[Dict]:
        """
        Busca colonias por texto (búsqueda fuzzy)
        Útil para autocompletado
        
        Args:
            texto: Texto a buscar
            limite: Máximo de resultados
            
        Returns:
            Lista de colonias con sus CPs
        """
        db = SessionLocal()
        
        try:
            result = db.execute(text("""
                SELECT 
                    colonia,
                    cp,
                    municipio,
                    similarity(colonia, :texto) as similitud
                FROM sepomex_codigos_postales
                WHERE similarity(colonia, :texto) > 0.2
                OR colonia ILIKE :texto_like
                ORDER BY similitud DESC, colonia
                LIMIT :limite;
            """), {
                "texto": texto,
                "texto_like": f"%{texto}%",
                "limite": limite
            })
            
            return [
                {
                    "colonia": row.colonia,
                    "cp": row.cp,
                    "municipio": row.municipio,
                    "similitud": round(row.similitud, 2) if row.similitud else 0
                }
                for row in result.fetchall()
            ]
            
        except SQLAlchemyError as e:
            logger.error(f"Error buscando por texto: {e}")
            return []
        finally:
            db.close()
    
    async def obtener_estadisticas(self) -> Dict:
        """
        Obtiene estadísticas del catálogo SEPOMEX
        
        Returns:
            Dict con estadísticas
        """
        db = SessionLocal()
        
        try:
            # Estadísticas generales
            result = db.execute(text("""
                SELECT 
                    COUNT(*) as total_registros,
                    COUNT(DISTINCT cp) as total_cps,
                    COUNT(DISTINCT municipio) as total_municipios,
                    COUNT(DISTINCT colonia) as total_colonias_unicas
                FROM sepomex_codigos_postales;
            """))
            
            stats = result.fetchone()
            
            # Por alcaldía
            result = db.execute(text("""
                SELECT 
                    municipio,
                    COUNT(DISTINCT cp) as cps,
                    COUNT(*) as colonias
                FROM sepomex_codigos_postales
                GROUP BY municipio
                ORDER BY colonias DESC;
            """))
            
            por_alcaldia = [
                {
                    "alcaldia": row.municipio,
                    "cps": row.cps,
                    "colonias": row.colonias
                }
                for row in result.fetchall()
            ]
            
            return {
                "total_registros": stats.total_registros,
                "total_cps": stats.total_cps,
                "total_municipios": stats.total_municipios,
                "total_colonias_unicas": stats.total_colonias_unicas,
                "por_alcaldia": por_alcaldia,
                "fuente": "postgresql"
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    async def _validar_desde_diccionario(self, cp: str) -> Dict:
        """
        Fallback al diccionario local si PostgreSQL falla
        """
        if cp in self.diccionario_fallback:
            info = self.diccionario_fallback[cp]
            return {
                "valido": True,
                "codigo_postal": cp,
                "estado": info["estado"],
                "municipio": info["municipio"],
                "colonias": info["colonias"],
                "fuente": "diccionario_local_fallback",
                "nota": "Datos del diccionario local (fallback)"
            }
        else:
            return {
                "valido": False,
                "codigo_postal": cp,
                "mensaje": "CP no encontrado"
            }

# Instancia global del servicio
sepomex_service_postgresql = SepomexServicePostgreSQL()
