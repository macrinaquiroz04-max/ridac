# backend/app/services/search_service.py

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from app.models.tomo import Tomo, ContenidoOCR
from app.models.carpeta import Carpeta
from app.models.permiso import PermisoCarpeta
from app.utils.logger import logger

class SearchService:
    """Servicio de búsqueda en contenido OCR"""

    def buscar_texto(
        self,
        db: Session,
        query: str,
        usuario_id: int,
        carpeta_id: int = None,
        limite: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Buscar texto en contenido OCR

        Args:
            db: Sesión de base de datos
            query: Texto a buscar
            usuario_id: ID del usuario que realiza la búsqueda
            carpeta_id: ID de carpeta específica (opcional)
            limite: Número máximo de resultados

        Returns:
            Lista de diccionarios con resultados
        """
        try:
            # Obtener carpetas a las que el usuario tiene acceso
            carpetas_permitidas = db.query(PermisoCarpeta.carpeta_id).filter(
                PermisoCarpeta.usuario_id == usuario_id
            ).all()

            carpetas_ids = [c[0] for c in carpetas_permitidas]

            if not carpetas_ids:
                logger.warning(f"Usuario {usuario_id} no tiene acceso a ninguna carpeta")
                return []

            # Construir query base
            base_query = db.query(
                ContenidoOCR,
                Tomo,
                Carpeta
            ).join(
                Tomo, ContenidoOCR.tomo_id == Tomo.id
            ).join(
                Carpeta, Tomo.carpeta_id == Carpeta.id
            ).filter(
                Carpeta.id.in_(carpetas_ids)
            )

            # Filtrar por carpeta específica si se proporciona
            if carpeta_id:
                base_query = base_query.filter(Carpeta.id == carpeta_id)

            # Búsqueda de texto (case-insensitive)
            # Usar búsqueda de texto completo de PostgreSQL
            search_condition = ContenidoOCR.texto_extraido.ilike(f'%{query}%')

            resultados_query = base_query.filter(search_condition).limit(limite).all()

            # Formatear resultados
            resultados = []
            for contenido, tomo, carpeta in resultados_query:
                # Extraer fragmento relevante
                texto = contenido.texto_extraido or ""
                query_lower = query.lower()
                texto_lower = texto.lower()

                # Encontrar posición del query
                pos = texto_lower.find(query_lower)

                if pos != -1:
                    # Extraer contexto (100 caracteres antes y después)
                    inicio = max(0, pos - 100)
                    fin = min(len(texto), pos + len(query) + 100)
                    fragmento = texto[inicio:fin]

                    # Agregar ... si no es el inicio/fin
                    if inicio > 0:
                        fragmento = "..." + fragmento
                    if fin < len(texto):
                        fragmento = fragmento + "..."
                else:
                    # Si no se encuentra (no debería pasar), usar los primeros 200 caracteres
                    fragmento = texto[:200] + ("..." if len(texto) > 200 else "")

                resultados.append({
                    "carpeta_id": carpeta.id,
                    "carpeta_nombre": carpeta.nombre,
                    "numero_expediente": carpeta.numero_expediente,
                    "tomo_id": tomo.id,
                    "tomo_numero": tomo.numero_tomo,
                    "tomo_nombre": tomo.nombre_archivo,
                    "pagina": contenido.pagina,
                    "fragmento": fragmento,
                    "confianza": float(contenido.confianza_porcentaje) if contenido.confianza_porcentaje else 0,
                    "motor_usado": contenido.motor_usado
                })

            logger.info(f"Búsqueda '{query}': {len(resultados)} resultados encontrados")
            return resultados

        except Exception as e:
            logger.error(f"Error en búsqueda: {e}", exc_info=True)
            raise

    def buscar_avanzada(
        self,
        db: Session,
        usuario_id: int,
        filtros: Dict[str, Any],
        limite: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda avanzada con múltiples filtros

        Filtros disponibles:
        - texto: Búsqueda de texto
        - carpeta_id: ID de carpeta
        - numero_expediente: Número de expediente
        - fecha_desde: Fecha desde
        - fecha_hasta: Fecha hasta
        - confianza_minima: Confianza mínima (0-100)
        """
        try:
            # Obtener carpetas permitidas
            carpetas_permitidas = db.query(PermisoCarpeta.carpeta_id).filter(
                PermisoCarpeta.usuario_id == usuario_id
            ).all()

            carpetas_ids = [c[0] for c in carpetas_permitidas]

            if not carpetas_ids:
                return []

            # Query base
            query = db.query(
                ContenidoOCR,
                Tomo,
                Carpeta
            ).join(
                Tomo, ContenidoOCR.tomo_id == Tomo.id
            ).join(
                Carpeta, Tomo.carpeta_id == Carpeta.id
            ).filter(
                Carpeta.id.in_(carpetas_ids)
            )

            # Aplicar filtros
            if filtros.get('texto'):
                query = query.filter(ContenidoOCR.texto_extraido.ilike(f'%{filtros["texto"]}%'))

            if filtros.get('carpeta_id'):
                query = query.filter(Carpeta.id == filtros['carpeta_id'])

            if filtros.get('numero_expediente'):
                query = query.filter(Carpeta.numero_expediente.ilike(f'%{filtros["numero_expediente"]}%'))

            if filtros.get('fecha_desde'):
                query = query.filter(Tomo.fecha_subida >= filtros['fecha_desde'])

            if filtros.get('fecha_hasta'):
                query = query.filter(Tomo.fecha_subida <= filtros['fecha_hasta'])

            if filtros.get('confianza_minima'):
                query = query.filter(ContenidoOCR.confianza_porcentaje >= filtros['confianza_minima'])

            # Ejecutar query
            resultados_query = query.limit(limite).all()

            # Formatear resultados
            resultados = []
            for contenido, tomo, carpeta in resultados_query:
                texto = contenido.texto_extraido or ""
                preview = texto[:200] + ("..." if len(texto) > 200 else "")

                resultados.append({
                    "carpeta_id": carpeta.id,
                    "carpeta_nombre": carpeta.nombre,
                    "numero_expediente": carpeta.numero_expediente,
                    "tomo_id": tomo.id,
                    "tomo_numero": tomo.numero_tomo,
                    "tomo_nombre": tomo.nombre_archivo,
                    "pagina": contenido.pagina,
                    "fragmento": preview,
                    "confianza": float(contenido.confianza_porcentaje) if contenido.confianza_porcentaje else 0,
                    "motor_usado": contenido.motor_usado,
                    "fecha_subida": tomo.fecha_subida.isoformat() if tomo.fecha_subida else None
                })

            logger.info(f"Búsqueda avanzada: {len(resultados)} resultados encontrados")
            return resultados

        except Exception as e:
            logger.error(f"Error en búsqueda avanzada: {e}", exc_info=True)
            raise
