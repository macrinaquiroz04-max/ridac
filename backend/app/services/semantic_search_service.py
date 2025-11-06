"""
🚀 SERVICIO DE BÚSQUEDA SEMÁNTICA AVANZADA
Búsqueda por conceptos y similitud semántica usando embeddings
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import logging
from datetime import datetime
import math

from app.models.tomo import ContenidoOCR, Tomo
from app.models.usuario import Usuario
from app.models.permiso_tomo import PermisoTomo
from app.utils.logger import logger

try:
    from sentence_transformers import SentenceTransformer
    SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    SEMANTIC_SEARCH_AVAILABLE = False
    logger.warning("⚠️ SentenceTransformers no disponible - búsqueda semántica limitada")

class SemanticSearchService:
    """Servicio de búsqueda semántica usando embeddings vectoriales"""

    def __init__(self):
        self.model = None
        self.model_name = 'paraphrase-multilingual-MiniLM-L12-v2'  # Modelo multilingüe español-inglés
        self.embedding_dimension = 384  # Dimensión del modelo MiniLM
        self.initialize_model()

    def initialize_model(self):
        """Inicializar el modelo de embeddings"""
        if not SEMANTIC_SEARCH_AVAILABLE:
            logger.error("❌ SentenceTransformers no disponible")
            return

        try:
            logger.info(f"🤖 Inicializando modelo semántico: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("✅ Modelo semántico inicializado correctamente")
        except Exception as e:
            logger.error(f"❌ Error inicializando modelo semántico: {e}")
            self.model = None

    def generate_embeddings(self, text: str) -> Optional[np.ndarray]:
        """Generar embeddings para un texto"""
        if not self.model or not text or len(text.strip()) < 10:
            return None

        try:
            # Limpiar y preparar texto
            clean_text = self.preprocess_text(text)

            # Generar embeddings
            embeddings = self.model.encode([clean_text], convert_to_numpy=True)[0]

            # Normalizar para mejor similitud coseno
            norm = np.linalg.norm(embeddings)
            if norm > 0:
                embeddings = embeddings / norm

            return embeddings

        except Exception as e:
            logger.error(f"❌ Error generando embeddings: {e}")
            return None

    def preprocess_text(self, text: str) -> str:
        """Preprocesar texto para mejor embeddings"""
        if not text:
            return ""

        # Limpiar caracteres especiales pero mantener acentos
        import re
        text = re.sub(r'[^\w\sáéíóúüñÁÉÍÓÚÜÑ]', ' ', text)

        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)

        # Limitar longitud para evitar textos muy largos
        if len(text) > 1000:
            text = text[:1000] + "..."

        return text.strip()

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calcular similitud coseno entre dos vectores"""
        try:
            return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        except:
            return 0.0

    def buscar_semantica(
        self,
        db: Session,
        query: str,
        usuario_id: int,
        limite: int = 50,
        umbral_similitud: float = 0.3,
        carpeta_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Búsqueda semántica por conceptos

        Args:
            db: Sesión de base de datos
            query: Consulta semántica
            usuario_id: ID del usuario
            limite: Número máximo de resultados
            umbral_similitud: Umbral mínimo de similitud (0-1)
            carpeta_id: Filtrar por carpeta específica

        Returns:
            dict: Resultados de búsqueda semántica
        """
        try:
            start_time = datetime.now()

            if not self.model:
                return {
                    "success": False,
                    "message": "Servicio de búsqueda semántica no disponible"
                }

            # Generar embeddings de la consulta
            query_embeddings = self.generate_embeddings(query)
            if query_embeddings is None:
                return {
                    "success": False,
                    "message": "No se pudieron generar embeddings para la consulta"
                }

            logger.info(f"🔍 Iniciando búsqueda semántica: '{query}' (usuario: {usuario_id})")

            # Obtener permisos del usuario
            permisos_query = db.query(PermisoTomo.tomo_id).filter(
                PermisoTomo.usuario_id == usuario_id,
                PermisoTomo.puede_buscar == True
            )

            tomos_permitidos = [p[0] for p in permisos_query.all()]

            if not tomos_permitidos:
                return {
                    "success": True,
                    "total": 0,
                    "resultados": [],
                    "message": "No tiene permisos para buscar en ningún tomo"
                }

            # Construir query base con permisos
            base_query = db.query(
                ContenidoOCR.id,
                ContenidoOCR.tomo_id,
                ContenidoOCR.numero_pagina,
                ContenidoOCR.texto_extraido,
                ContenidoOCR.confianza,
                ContenidoOCR.embeddings,
                Tomo.nombre_archivo,
                Tomo.carpeta_id
            ).join(Tomo).filter(
                ContenidoOCR.tomo_id.in_(tomos_permitidos),
                ContenidoOCR.embeddings.isnot(None),  # Solo páginas con embeddings
                ContenidoOCR.texto_extraido.isnot(None)
            )

            # Filtrar por carpeta si se especifica
            if carpeta_id:
                base_query = base_query.filter(Tomo.carpeta_id == carpeta_id)

            # Obtener todos los registros con embeddings
            registros_con_embeddings = base_query.all()

            if not registros_con_embeddings:
                return {
                    "success": True,
                    "total": 0,
                    "resultados": [],
                    "message": "No hay contenido con embeddings disponibles para búsqueda semántica"
                }

            logger.info(f"📊 Procesando {len(registros_con_embeddings)} registros con embeddings")

            # Calcular similitudes
            resultados_similitud = []

            for registro in registros_con_embeddings:
                try:
                    # Convertir embeddings de la BD a numpy array
                    if isinstance(registro.embeddings, list):
                        doc_embeddings = np.array(registro.embeddings)
                    else:
                        continue  # Skip si no es lista

                    # Calcular similitud
                    similitud = self.cosine_similarity(query_embeddings, doc_embeddings)

                    if similitud >= umbral_similitud:
                        resultados_similitud.append({
                            'id': registro.id,
                            'tomo_id': registro.tomo_id,
                            'numero_pagina': registro.numero_pagina,
                            'texto_extraido': registro.texto_extraido,
                            'confianza': float(registro.confianza) if registro.confianza else None,
                            'nombre_archivo': registro.nombre_archivo,
                            'carpeta_id': registro.carpeta_id,
                            'similitud': float(similitud),
                            'embeddings': registro.embeddings
                        })

                except Exception as e:
                    logger.warning(f"⚠️ Error procesando registro {registro.id}: {e}")
                    continue

            # Ordenar por similitud descendente
            resultados_similitud.sort(key=lambda x: x['similitud'], reverse=True)

            # Limitar resultados
            resultados_finales = resultados_similitud[:limite]

            # Agregar contexto a cada resultado
            for resultado in resultados_finales:
                resultado['contexto'] = self.generar_contexto_semantico(
                    resultado['texto_extraido'], query, resultado['similitud']
                )

            tiempo_total = (datetime.now() - start_time).total_seconds()

            logger.info(f"✅ Búsqueda semántica completada: {len(resultados_finales)} resultados en {tiempo_total:.2f}s")

            return {
                "success": True,
                "query": query,
                "tipo_busqueda": "semantica",
                "total": len(resultados_finales),
                "umbral_similitud": umbral_similitud,
                "tiempo_procesamiento": tiempo_total,
                "resultados": resultados_finales,
                "estadisticas": {
                    "total_registros_procesados": len(registros_con_embeddings),
                    "similitud_promedio": np.mean([r['similitud'] for r in resultados_finales]) if resultados_finales else 0,
                    "similitud_maxima": max([r['similitud'] for r in resultados_finales]) if resultados_finales else 0,
                    "similitud_minima": min([r['similitud'] for r in resultados_finales]) if resultados_finales else 0
                }
            }

        except Exception as e:
            logger.error(f"❌ Error en búsqueda semántica: {e}")
            return {
                "success": False,
                "message": f"Error en búsqueda semántica: {str(e)}"
            }

    def generar_contexto_semantico(self, texto_completo: str, query: str, similitud: float) -> str:
        """Generar contexto semántico para mostrar al usuario"""
        if not texto_completo:
            return "Sin contenido disponible"

        # Extraer fragmento más relevante basado en palabras clave de la query
        query_palabras = set(query.lower().split())
        texto_lower = texto_completo.lower()

        # Buscar la mejor coincidencia
        mejor_pos = -1
        mejor_score = 0

        for palabra in query_palabras:
            pos = texto_lower.find(palabra)
            if pos != -1:
                # Calcular score basado en proximidad al inicio y frecuencia
                score = 1.0 / (pos + 1)  # Mejor si está al inicio
                if score > mejor_score:
                    mejor_score = score
                    mejor_pos = pos

        if mejor_pos >= 0:
            # Extraer contexto alrededor de la mejor coincidencia
            inicio = max(0, mejor_pos - 100)
            fin = min(len(texto_completo), mejor_pos + len(query) + 100)

            contexto = texto_completo[inicio:fin]
            if inicio > 0:
                contexto = "..." + contexto
            if fin < len(texto_completo):
                contexto = contexto + "..."

            return contexto

        # Fallback: primeros 200 caracteres
        return texto_completo[:200] + ("..." if len(texto_completo) > 200 else "")

    def actualizar_embeddings_pagina(self, db: Session, contenido_ocr_id: int) -> bool:
        """Actualizar embeddings de una página específica"""
        try:
            contenido = db.query(ContenidoOCR).filter(ContenidoOCR.id == contenido_ocr_id).first()

            if not contenido or not contenido.texto_extraido:
                return False

            # Generar nuevos embeddings
            nuevos_embeddings = self.generate_embeddings(contenido.texto_extraido)

            if nuevos_embeddings is not None:
                contenido.embeddings = nuevos_embeddings.tolist()
                db.commit()
                logger.info(f"✅ Embeddings actualizados para página {contenido.numero_pagina}")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error actualizando embeddings: {e}")
            return False

    def reconstruir_embeddings_tomo(self, db: Session, tomo_id: int) -> Dict[str, Any]:
        """Reconstruir embeddings para todas las páginas de un tomo"""
        try:
            contenidos = db.query(ContenidoOCR).filter(
                ContenidoOCR.tomo_id == tomo_id,
                ContenidoOCR.texto_extraido.isnot(None)
            ).all()

            if not contenidos:
                return {"success": False, "message": "No hay contenido OCR en este tomo"}

            actualizados = 0
            errores = 0

            for contenido in contenidos:
                try:
                    embeddings = self.generate_embeddings(contenido.texto_extraido)
                    if embeddings is not None:
                        contenido.embeddings = embeddings.tolist()
                        actualizados += 1
                    else:
                        errores += 1
                except Exception as e:
                    logger.warning(f"⚠️ Error procesando página {contenido.numero_pagina}: {e}")
                    errores += 1

            db.commit()

            return {
                "success": True,
                "tomo_id": tomo_id,
                "total_paginas": len(contenidos),
                "actualizados": actualizados,
                "errores": errores
            }

        except Exception as e:
            logger.error(f"❌ Error reconstruyendo embeddings: {e}")
            return {"success": False, "message": str(e)}

    def buscar_conceptos_legales(
        self,
        db: Session,
        conceptos: List[str],
        usuario_id: int,
        limite: int = 30
    ) -> Dict[str, Any]:
        """
        Búsqueda por conceptos legales específicos

        Args:
            conceptos: Lista de conceptos legales a buscar
            usuario_id: ID del usuario
            limite: Número máximo de resultados por concepto
        """
        try:
            resultados_por_concepto = {}

            for concepto in conceptos:
                logger.info(f"🔍 Buscando concepto legal: '{concepto}'")

                resultado = self.buscar_semantica(
                    db=db,
                    query=concepto,
                    usuario_id=usuario_id,
                    limite=limite,
                    umbral_similitud=0.2  # Umbral más bajo para conceptos legales
                )

                if resultado["success"]:
                    resultados_por_concepto[concepto] = resultado

            # Consolidar resultados únicos
            todos_resultados = []
            resultados_vistos = set()

            for concepto, resultado in resultados_por_concepto.items():
                for res in resultado["resultados"]:
                    # Crear clave única
                    clave = f"{res['tomo_id']}-{res['numero_pagina']}"
                    if clave not in resultados_vistos:
                        res['conceptos_encontrados'] = [concepto]
                        todos_resultados.append(res)
                        resultados_vistos.add(clave)
                    else:
                        # Agregar concepto a resultado existente
                        for existing_res in todos_resultados:
                            if f"{existing_res['tomo_id']}-{existing_res['numero_pagina']}" == clave:
                                if 'conceptos_encontrados' not in existing_res:
                                    existing_res['conceptos_encontrados'] = []
                                existing_res['conceptos_encontrados'].append(concepto)
                                break

            # Ordenar por número de conceptos encontrados y similitud
            todos_resultados.sort(key=lambda x: (len(x.get('conceptos_encontrados', [])), x['similitud']), reverse=True)

            return {
                "success": True,
                "tipo_busqueda": "conceptos_legales",
                "conceptos_buscados": conceptos,
                "total": len(todos_resultados),
                "resultados": todos_resultados[:limite],
                "estadisticas_por_concepto": {
                    concepto: {
                        "total": resultado["total"],
                        "similitud_promedio": resultado.get("estadisticas", {}).get("similitud_promedio", 0)
                    }
                    for concepto, resultado in resultados_por_concepto.items()
                }
            }

        except Exception as e:
            logger.error(f"❌ Error en búsqueda por conceptos legales: {e}")
            return {
                "success": False,
                "message": f"Error en búsqueda por conceptos: {str(e)}"
            }

    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del servicio de búsqueda semántica"""
        return {
            "disponible": SEMANTIC_SEARCH_AVAILABLE and self.model is not None,
            "modelo": self.model_name if self.model else None,
            "dimension_embeddings": self.embedding_dimension,
            "sentence_transformers": SEMANTIC_SEARCH_AVAILABLE
        }

# Instancia global del servicio
semantic_search_service = SemanticSearchService()
