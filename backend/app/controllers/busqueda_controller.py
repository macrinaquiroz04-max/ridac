# backend/app/controllers/busqueda_controller.py

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.models.tomo import Tomo, ContenidoOCR
from app.models.carpeta import Carpeta
from app.models.permiso import PermisoCarpeta, PermisoSistema
from app.utils.logger import logger

# Importaciones para búsqueda semántica (con manejo de errores)
try:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    from sentence_transformers import SentenceTransformer
    ML_DISPONIBLE = True
    logger.info("Librerías ML cargadas correctamente para búsqueda semántica")
except ImportError as e:
    ML_DISPONIBLE = False
    logger.info(f"Librerías ML opcionales no disponibles: {str(e)}")
    np = None
    cosine_similarity = None
    SentenceTransformer = None


class BusquedaController:
    """Controlador para búsquedas en contenido OCR"""

    def buscar_texto(
        self,
        db: Session,
        query: str,
        carpeta_id: Optional[int] = None,
        tomo_id: Optional[int] = None,
        case_sensitive: bool = False,
        skip: int = 0,
        limit: int = 100,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Buscar texto en contenido OCR

        Args:
            db: Sesión de base de datos
            query: Texto a buscar
            carpeta_id: Filtrar por carpeta específica
            tomo_id: Filtrar por tomo específico
            case_sensitive: Búsqueda sensible a mayúsculas/minúsculas
            skip: Número de registros a saltar
            limit: Número máximo de registros
            current_user_id: ID del usuario que busca

        Returns:
            dict: Resultados de búsqueda
        """
        try:
            if not query or len(query) < 3:
                return {
                    "success": False,
                    "message": "La búsqueda debe tener al menos 3 caracteres"
                }

            # Obtener carpetas permitidas para el usuario
            carpetas_permitidas = []
            if current_user_id:
                # Verificar si es administrador
                permisos_sistema = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                es_admin = permisos_sistema and permisos_sistema.ver_auditoria

                if not es_admin:
                    # Obtener carpetas con permiso de ver
                    permisos_carpetas = db.query(PermisoCarpeta.carpeta_id).filter(
                        PermisoCarpeta.usuario_id == current_user_id
                    ).all()

                    carpetas_permitidas = [p[0] for p in permisos_carpetas]

                    if not carpetas_permitidas:
                        return {
                            "success": True,
                            "total": 0,
                            "resultados": [],
                            "message": "No tiene acceso a ninguna carpeta"
                        }

            # Construir query base
            base_query = db.query(ContenidoOCR).join(Tomo).join(Carpeta)

            # Aplicar filtros de permisos
            if carpetas_permitidas:
                base_query = base_query.filter(Carpeta.id.in_(carpetas_permitidas))

            # Filtrar por carpeta
            if carpeta_id:
                # Verificar permiso sobre la carpeta
                if current_user_id and carpetas_permitidas and carpeta_id not in carpetas_permitidas:
                    return {
                        "success": False,
                        "message": "No tiene permisos para buscar en esta carpeta"
                    }

                base_query = base_query.filter(Carpeta.id == carpeta_id)

            # Filtrar por tomo
            if tomo_id:
                base_query = base_query.filter(Tomo.id == tomo_id)

            # Aplicar búsqueda de texto
            if case_sensitive:
                base_query = base_query.filter(ContenidoOCR.texto_extraido.like(f"%{query}%"))
            else:
                base_query = base_query.filter(ContenidoOCR.texto_extraido.ilike(f"%{query}%"))

            # Contar total
            total = base_query.count()

            # Obtener resultados con paginación
            resultados = base_query.order_by(
                Carpeta.nombre,
                Tomo.numero_tomo,
                ContenidoOCR.numero_pagina
            ).offset(skip).limit(limit).all()

            resultados_list = []
            for contenido in resultados:
                tomo = contenido.tomo
                carpeta = tomo.carpeta

                # Extraer contexto (texto alrededor de la coincidencia)
                texto = contenido.texto_extraido or ""
                pos = texto.lower().find(query.lower()) if not case_sensitive else texto.find(query)

                if pos >= 0:
                    # Contexto de 100 caracteres antes y después
                    start = max(0, pos - 100)
                    end = min(len(texto), pos + len(query) + 100)
                    contexto = texto[start:end]

                    if start > 0:
                        contexto = "..." + contexto
                    if end < len(texto):
                        contexto = contexto + "..."
                else:
                    contexto = texto[:200] if len(texto) > 200 else texto

                resultados_list.append({
                    "carpeta_id": carpeta.id,
                    "carpeta_nombre": carpeta.nombre,
                    "tomo_id": tomo.id,
                    "numero_tomo": tomo.numero_tomo,
                    "nombre_archivo": tomo.nombre_archivo,
                    "pagina": contenido.numero_pagina,
                    "contexto": contexto,
                    "confianza_porcentaje": float(contenido.confianza) if contenido.confianza else None,
                    "motor_usado": "paddle_ocr"
                })

            logger.info(f"Búsqueda realizada por usuario {current_user_id}: '{query}' - {total} resultados")

            return {
                "success": True,
                "query": query,
                "total": total,
                "skip": skip,
                "limit": limit,
                "resultados": resultados_list
            }

        except Exception as e:
            logger.error(f"Error en búsqueda: {str(e)}")
            return {
                "success": False,
                "message": f"Error en búsqueda: {str(e)}"
            }

    def buscar_avanzada(
        self,
        db: Session,
        query: str,
        carpeta_ids: Optional[List[int]] = None,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
        confianza_minima: Optional[float] = None,
        motor_ocr: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Búsqueda avanzada con múltiples filtros

        Args:
            db: Sesión de base de datos
            query: Texto a buscar
            carpeta_ids: Lista de IDs de carpetas
            fecha_desde: Fecha inicial (ISO format)
            fecha_hasta: Fecha final (ISO format)
            confianza_minima: Confianza mínima del OCR (0-100)
            motor_ocr: Motor OCR específico
            skip: Número de registros a saltar
            limit: Número máximo de registros
            current_user_id: ID del usuario que busca

        Returns:
            dict: Resultados de búsqueda avanzada
        """
        try:
            if not query or len(query) < 3:
                return {
                    "success": False,
                    "message": "La búsqueda debe tener al menos 3 caracteres"
                }

            # Obtener carpetas permitidas
            carpetas_permitidas = []
            if current_user_id:
                permisos_sistema = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                es_admin = permisos_sistema and permisos_sistema.ver_auditoria

                if not es_admin:
                    permisos_carpetas = db.query(PermisoCarpeta.carpeta_id).filter(
                        PermisoCarpeta.usuario_id == current_user_id
                    ).all()

                    carpetas_permitidas = [p[0] for p in permisos_carpetas]

                    if not carpetas_permitidas:
                        return {
                            "success": True,
                            "total": 0,
                            "resultados": []
                        }

            # Construir query
            base_query = db.query(ContenidoOCR).join(Tomo).join(Carpeta)

            # Filtro de permisos
            if carpetas_permitidas:
                base_query = base_query.filter(Carpeta.id.in_(carpetas_permitidas))

            # Filtro de carpetas específicas
            if carpeta_ids:
                # Verificar que todas las carpetas tengan permiso
                if carpetas_permitidas:
                    carpetas_validas = [c for c in carpeta_ids if c in carpetas_permitidas]
                    if not carpetas_validas:
                        return {
                            "success": False,
                            "message": "No tiene permisos para buscar en las carpetas especificadas"
                        }
                    carpeta_ids = carpetas_validas

                base_query = base_query.filter(Carpeta.id.in_(carpeta_ids))

            # Filtro de texto
            base_query = base_query.filter(ContenidoOCR.texto_extraido.ilike(f"%{query}%"))

            # Filtro de fecha
            if fecha_desde:
                try:
                    fecha_desde_dt = datetime.fromisoformat(fecha_desde)
                    base_query = base_query.filter(Tomo.fecha_subida >= fecha_desde_dt)
                except ValueError:
                    logger.warning(f"Fecha desde inválida: {fecha_desde}")

            if fecha_hasta:
                try:
                    fecha_hasta_dt = datetime.fromisoformat(fecha_hasta)
                    base_query = base_query.filter(Tomo.fecha_subida <= fecha_hasta_dt)
                except ValueError:
                    logger.warning(f"Fecha hasta inválida: {fecha_hasta}")

            # Filtro de confianza
            if confianza_minima is not None:
                base_query = base_query.filter(ContenidoOCR.confianza_porcentaje >= confianza_minima)

            # Filtro de motor OCR
            if motor_ocr:
                base_query = base_query.filter(ContenidoOCR.motor_usado == motor_ocr)

            # Contar total
            total = base_query.count()

            # Obtener resultados
            resultados = base_query.order_by(
                Tomo.fecha_subida.desc(),
                ContenidoOCR.confianza_porcentaje.desc()
            ).offset(skip).limit(limit).all()

            resultados_list = []
            for contenido in resultados:
                tomo = contenido.tomo
                carpeta = tomo.carpeta

                # Extraer contexto
                texto = contenido.texto_extraido or ""
                pos = texto.lower().find(query.lower())

                if pos >= 0:
                    start = max(0, pos - 100)
                    end = min(len(texto), pos + len(query) + 100)
                    contexto = texto[start:end]

                    if start > 0:
                        contexto = "..." + contexto
                    if end < len(texto):
                        contexto = contexto + "..."
                else:
                    contexto = texto[:200] if len(texto) > 200 else texto

                resultados_list.append({
                    "carpeta_id": carpeta.id,
                    "carpeta_nombre": carpeta.nombre,
                    "numero_expediente": carpeta.numero_expediente,
                    "tomo_id": tomo.id,
                    "numero_tomo": tomo.numero_tomo,
                    "nombre_archivo": tomo.nombre_archivo,
                    "pagina": contenido.numero_pagina,
                    "contexto": contexto,
                    "confianza_porcentaje": float(contenido.confianza) if contenido.confianza else None,
                    "motor_usado": "paddle_ocr",
                    "fecha_subida": tomo.fecha_subida.isoformat()
                })

            logger.info(f"Búsqueda avanzada por usuario {current_user_id}: '{query}' - {total} resultados")

            return {
                "success": True,
                "query": query,
                "filtros": {
                    "carpeta_ids": carpeta_ids,
                    "fecha_desde": fecha_desde,
                    "fecha_hasta": fecha_hasta,
                    "confianza_minima": confianza_minima,
                    "motor_ocr": motor_ocr
                },
                "total": total,
                "skip": skip,
                "limit": limit,
                "resultados": resultados_list
            }

        except Exception as e:
            logger.error(f"Error en búsqueda avanzada: {str(e)}")
            return {
                "success": False,
                "message": f"Error en búsqueda avanzada: {str(e)}"
            }

    def estadisticas_busqueda(
        self,
        db: Session,
        carpeta_id: Optional[int] = None,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtener estadísticas de contenido OCR disponible

        Args:
            db: Sesión de base de datos
            carpeta_id: Filtrar por carpeta específica
            current_user_id: ID del usuario que consulta

        Returns:
            dict: Estadísticas de búsqueda
        """
        try:
            # Obtener carpetas permitidas
            carpetas_permitidas = []
            if current_user_id:
                permisos_sistema = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                es_admin = permisos_sistema and permisos_sistema.ver_auditoria

                if not es_admin:
                    permisos_carpetas = db.query(PermisoCarpeta.carpeta_id).filter(
                        PermisoCarpeta.usuario_id == current_user_id
                    ).all()

                    carpetas_permitidas = [p[0] for p in permisos_carpetas]

            # Query base
            base_query_tomos = db.query(Tomo).join(Carpeta)
            base_query_ocr = db.query(ContenidoOCR).join(Tomo).join(Carpeta)

            # Filtros de permisos
            if carpetas_permitidas:
                base_query_tomos = base_query_tomos.filter(Carpeta.id.in_(carpetas_permitidas))
                base_query_ocr = base_query_ocr.filter(Carpeta.id.in_(carpetas_permitidas))

            # Filtro por carpeta
            if carpeta_id:
                if carpetas_permitidas and carpeta_id not in carpetas_permitidas:
                    return {
                        "success": False,
                        "message": "No tiene permisos para ver esta carpeta"
                    }

                base_query_tomos = base_query_tomos.filter(Carpeta.id == carpeta_id)
                base_query_ocr = base_query_ocr.filter(Carpeta.id == carpeta_id)

            # Estadísticas generales
            total_tomos = base_query_tomos.count()
            total_paginas_ocr = base_query_ocr.count()

            # Estadísticas por estado OCR
            tomos_por_estado = db.query(
                Tomo.estado_ocr,
                func.count(Tomo.id)
            ).join(Carpeta)

            if carpetas_permitidas:
                tomos_por_estado = tomos_por_estado.filter(Carpeta.id.in_(carpetas_permitidas))

            if carpeta_id:
                tomos_por_estado = tomos_por_estado.filter(Carpeta.id == carpeta_id)

            tomos_por_estado = tomos_por_estado.group_by(Tomo.estado_ocr).all()

            estados = {}
            for estado, count in tomos_por_estado:
                estados[estado] = count

            # Estadísticas por motor OCR
            paginas_por_motor = db.query(
                ContenidoOCR.motor_usado,
                func.count(ContenidoOCR.id)
            ).join(Tomo).join(Carpeta)

            if carpetas_permitidas:
                paginas_por_motor = paginas_por_motor.filter(Carpeta.id.in_(carpetas_permitidas))

            if carpeta_id:
                paginas_por_motor = paginas_por_motor.filter(Carpeta.id == carpeta_id)

            paginas_por_motor = paginas_por_motor.group_by(ContenidoOCR.motor_usado).all()

            motores = {}
            for motor, count in paginas_por_motor:
                motores[motor] = count

            # Confianza promedio
            confianza_promedio = db.query(
                func.avg(ContenidoOCR.confianza_porcentaje)
            ).join(Tomo).join(Carpeta)

            if carpetas_permitidas:
                confianza_promedio = confianza_promedio.filter(Carpeta.id.in_(carpetas_permitidas))

            if carpeta_id:
                confianza_promedio = confianza_promedio.filter(Carpeta.id == carpeta_id)

            confianza_promedio = confianza_promedio.scalar()

            return {
                "success": True,
                "estadisticas": {
                    "total_tomos": total_tomos,
                    "total_paginas_ocr": total_paginas_ocr,
                    "tomos_por_estado": estados,
                    "paginas_por_motor": motores,
                    "confianza_promedio": round(float(confianza_promedio), 2) if confianza_promedio else None
                }
            }

        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener estadísticas: {str(e)}"
            }

    def exportar_resultados(
        self,
        db: Session,
        query: str,
        carpeta_id: Optional[int] = None,
        formato: str = "txt",
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Exportar resultados de búsqueda (preparar datos)

        Args:
            db: Sesión de base de datos
            query: Texto a buscar
            carpeta_id: Filtrar por carpeta
            formato: Formato de exportación (txt, csv, json)
            current_user_id: ID del usuario que exporta

        Returns:
            dict: Datos para exportación
        """
        try:
            # Verificar permisos de exportación
            if current_user_id:
                permisos = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                if not permisos or not permisos.exportar_datos:
                    logger.warning(f"Usuario {current_user_id} sin permisos para exportar")
                    return {
                        "success": False,
                        "message": "No tiene permisos para exportar datos"
                    }

            # Realizar búsqueda sin límite
            resultado_busqueda = self.buscar_texto(
                db=db,
                query=query,
                carpeta_id=carpeta_id,
                skip=0,
                limit=10000,  # Límite alto para exportación
                current_user_id=current_user_id
            )

            if not resultado_busqueda.get("success"):
                return resultado_busqueda

            logger.info(f"Exportación de resultados por usuario {current_user_id}: '{query}' - formato: {formato}")

            return {
                "success": True,
                "query": query,
                "total_resultados": resultado_busqueda.get("total"),
                "formato": formato,
                "datos": resultado_busqueda.get("resultados"),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error al exportar resultados: {str(e)}")
            return {
                "success": False,
                "message": f"Error al exportar resultados: {str(e)}"
            }

    def generar_embedding(self, texto: str) -> List[float]:
        """
        Generar embedding vectorial para el texto
        
        Args:
            texto: Texto para generar embedding
            
        Returns:
            List[float]: Vector embedding
        """
        if not ML_DISPONIBLE:
            logger.warning("Librerías ML no disponibles para generar embeddings")
            return []
            
        try:
            # Modelo ligero y eficiente para embeddings en español
            model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            
            # Generar embedding
            embedding = model.encode(texto, convert_to_tensor=False)
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Error generando embedding: {str(e)}")
            return []

    def actualizar_embeddings_contenido(self, db: Session, tomo_id: Optional[int] = None):
        """
        Actualizar embeddings para contenido OCR existente
        
        Args:
            db: Sesión de base de datos
            tomo_id: ID del tomo específico (opcional)
        """
        try:
            query = db.query(ContenidoOCR)
            
            if tomo_id:
                query = query.filter(ContenidoOCR.tomo_id == tomo_id)
            
            # Solo actualizar registros sin embeddings o con texto modificado
            contenidos = query.filter(
                or_(
                    ContenidoOCR.embeddings.is_(None),
                    ContenidoOCR.embeddings == {}
                )
            ).all()
            
            total_actualizado = 0
            
            for contenido in contenidos:
                if contenido.texto_extraido:
                    # Generar embedding para el texto
                    embedding = self.generar_embedding(contenido.texto_extraido)
                    
                    if embedding:
                        contenido.embeddings = {"vector": embedding, "modelo": "paraphrase-multilingual-MiniLM-L12-v2"}
                        total_actualizado += 1
                        
                        # Commit cada 50 registros para evitar memoria excesiva
                        if total_actualizado % 50 == 0:
                            db.commit()
                            logger.info(f"Actualizados {total_actualizado} embeddings...")
            
            db.commit()
            logger.info(f"Embeddings actualizados para {total_actualizado} registros")
            
            return {
                "success": True,
                "total_actualizado": total_actualizado
            }
            
        except Exception as e:
            logger.error(f"Error actualizando embeddings: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "message": f"Error actualizando embeddings: {str(e)}"
            }

    def busqueda_semantica(
        self,
        db: Session,
        query: str,
        carpeta_id: Optional[int] = None,
        tomo_id: Optional[int] = None,
        similitud_minima: float = 0.5,
        skip: int = 0,
        limit: int = 100,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Búsqueda semántica usando embeddings vectoriales
        
        Args:
            db: Sesión de base de datos
            query: Consulta de búsqueda
            carpeta_id: Filtrar por carpeta específica
            tomo_id: Filtrar por tomo específico
            similitud_minima: Umbral mínimo de similitud (0.0 a 1.0)
            skip: Número de registros a saltar
            limit: Número máximo de registros
            current_user_id: ID del usuario que busca
            
        Returns:
            dict: Resultados de búsqueda semántica
        """
        try:
            if not query or len(query) < 3:
                return {
                    "success": False,
                    "message": "La búsqueda debe tener al menos 3 caracteres"
                }

            # Generar embedding de la consulta
            logger.info(f"🧠 Generando embedding para consulta: '{query}'")
            query_embedding = self.generar_embedding(query)
            if not query_embedding:
                logger.error(f"❌ No se pudo generar embedding para la consulta")
                return {
                    "success": False,
                    "message": "No se pudo generar embedding para la consulta"
                }
            logger.info(f"✅ Embedding de consulta generado exitosamente")

            # Obtener carpetas permitidas para el usuario
            carpetas_permitidas = []
            if current_user_id:
                logger.info(f"🔍 Verificando permisos para usuario {current_user_id}")
                # Verificar si es administrador
                permisos_sistema = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                es_admin = permisos_sistema and permisos_sistema.ver_auditoria
                logger.info(f"👑 Usuario {current_user_id} es admin: {es_admin}")

                if not es_admin:
                    # Obtener carpetas con permiso de ver
                    logger.info(f"🔍 Buscando permisos de carpetas para usuario {current_user_id}")
                    permisos_carpetas = db.query(PermisoCarpeta.carpeta_id).filter(
                        PermisoCarpeta.usuario_id == current_user_id
                    ).all()
                    logger.info(f"📋 Permisos raw encontrados: {permisos_carpetas}")

                    carpetas_permitidas = [p[0] for p in permisos_carpetas]
                    logger.info(f"📁 Carpetas permitidas procesadas: {carpetas_permitidas}")

                    if not carpetas_permitidas:
                        logger.warning(f"⚠️ Usuario {current_user_id} SIN CARPETAS => SALIENDO")
                        return {
                            "success": True,
                            "total": 0,
                            "resultados": [],
                            "message": "No tiene acceso a ninguna carpeta"
                        }
                else:
                    logger.info(f"👑 Usuario {current_user_id} es admin => ACCESO COMPLETO")

            # Construir query base - solo contenido con embeddings
            logger.info(f"🔨 Construyendo consulta base para documentos con embeddings")
            base_query = db.query(ContenidoOCR).join(Tomo).join(Carpeta).filter(
                ContenidoOCR.embeddings.isnot(None),
                ContenidoOCR.embeddings != {}
            )

            # Aplicar filtros de permisos
            if carpetas_permitidas:
                logger.info(f"🔐 Aplicando filtro de carpetas permitidas: {carpetas_permitidas}")
                base_query = base_query.filter(Carpeta.id.in_(carpetas_permitidas))
            else:
                logger.info(f"👑 Usuario con acceso completo (admin o sin restricciones)")

            # Filtrar por carpeta
            if carpeta_id:
                if current_user_id and carpetas_permitidas and carpeta_id not in carpetas_permitidas:
                    return {
                        "success": False,
                        "message": "No tiene permisos para buscar en esta carpeta"
                    }
                base_query = base_query.filter(Carpeta.id == carpeta_id)

            # Filtrar por tomo
            if tomo_id:
                base_query = base_query.filter(Tomo.id == tomo_id)

            # Obtener todos los contenidos con embeddings
            contenidos = base_query.all()
            logger.info(f"📊 Documentos encontrados con embeddings: {len(contenidos)}")
            
            # Verificar disponibilidad de librerías ML
            if not ML_DISPONIBLE:
                return {
                    "success": False,
                    "message": "Funcionalidad de búsqueda semántica no disponible - librerías ML no instaladas"
                }
            
            # Calcular similitud coseno
            resultados_similitud = []
            query_vector = np.array(query_embedding).reshape(1, -1)
            logger.info(f"🎯 Vector de consulta generado: shape={query_vector.shape}")
            
            documentos_procesados = 0
            documentos_con_embedding_valido = 0
            
            for contenido in contenidos:
                documentos_procesados += 1
                
                if contenido.embeddings and "vector" in contenido.embeddings:
                    try:
                        documentos_con_embedding_valido += 1
                        content_vector = np.array(contenido.embeddings["vector"]).reshape(1, -1)
                        similitud = cosine_similarity(query_vector, content_vector)[0][0]
                        
                        if documentos_con_embedding_valido <= 3:  # Log primeros 3 para debug
                            logger.info(f"📄 Doc {contenido.id}: similitud={similitud:.4f}, umbral={similitud_minima}")
                        
                        if similitud >= similitud_minima:
                            resultados_similitud.append({
                                "contenido": contenido,
                                "similitud": float(similitud)
                            })
                    except Exception as e:
                        logger.error(f"❌ Error procesando embedding del doc {contenido.id}: {str(e)}")
                else:
                    if documentos_procesados <= 3:  # Log primeros 3 para debug
                        logger.warning(f"⚠️ Doc {contenido.id}: embedding inválido o sin vector")
            
            logger.info(f"🔢 Procesados: {documentos_procesados}, con embedding válido: {documentos_con_embedding_valido}, similitudes>=umbral: {len(resultados_similitud)}")
            
            # Ordenar por similitud descendente
            resultados_similitud.sort(key=lambda x: x["similitud"], reverse=True)
            
            # Aplicar paginación
            total = len(resultados_similitud)
            resultados_paginados = resultados_similitud[skip:skip + limit]
            
            # Formatear resultados
            resultados_list = []
            for item in resultados_paginados:
                contenido = item["contenido"]
                tomo = contenido.tomo
                carpeta = tomo.carpeta
                
                # Extraer contexto relevante
                texto = contenido.texto_extraido or ""
                contexto = texto[:300] if len(texto) > 300 else texto
                
                resultados_list.append({
                    "carpeta_id": carpeta.id,
                    "carpeta_nombre": carpeta.nombre,
                    "tomo_id": tomo.id,
                    "numero_tomo": tomo.numero_tomo,
                    "nombre_archivo": tomo.nombre_archivo,
                    "pagina": contenido.numero_pagina,
                    "contexto": contexto,
                    "similitud": item["similitud"],
                    "confianza_porcentaje": float(contenido.confianza) if contenido.confianza else None,
                    "motor_usado": "paddle_ocr"
                })

            logger.info(f"Búsqueda semántica realizada por usuario {current_user_id}: '{query}' - {total} resultados")

            return {
                "success": True,
                "total": total,
                "resultados": resultados_list,
                "parametros": {
                    "query": query,
                    "similitud_minima": similitud_minima,
                    "tipo_busqueda": "semantica"
                }
            }

        except Exception as e:
            logger.error(f"Error en búsqueda semántica: {str(e)}")
            return {
                "success": False,
                "message": f"Error en búsqueda semántica: {str(e)}"
            }


# Instancia global del controlador
busqueda_controller = BusquedaController()
