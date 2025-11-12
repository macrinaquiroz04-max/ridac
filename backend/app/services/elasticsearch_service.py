# app/services/elasticsearch_service.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Organización: Unidad de Análisis y Contexto (UAyC)
# Año: 2025 - Propiedad Intelectual Registrada
# Firma Digital: ELQ-ISC-UAYC-10112025

import os
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from app.utils.logger import logger

class ElasticsearchService:
    """Servicio de búsqueda avanzada con Elasticsearch"""
    
    def __init__(self):
        self.es_client: Optional[Elasticsearch] = None
        self.enabled = False
        self.index_name = "sistema_ocr_tomos"
        self._initialize()
    
    def _initialize(self):
        """Inicializar conexión con Elasticsearch"""
        try:
            es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
            self.es_client = Elasticsearch([es_url], request_timeout=30)
            
            # Verificar conexión
            if self.es_client.ping():
                logger.info("✅ Elasticsearch conectado exitosamente")
                self.enabled = True
                self._crear_indice()
            else:
                logger.warning("⚠️ Elasticsearch no disponible")
                self.enabled = False
                
        except Exception as e:
            logger.error(f"❌ Error conectando a Elasticsearch: {e}")
            self.enabled = False
    
    def _crear_indice(self):
        """Crear índice con configuración optimizada para español"""
        if not self.enabled:
            return
        
        try:
            # Verificar si el índice ya existe
            if self.es_client.indices.exists(index=self.index_name):
                logger.info(f"📇 Índice '{self.index_name}' ya existe")
                return
            
            # Configuración del índice
            index_config = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "spanish_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "spanish_stop",
                                    "spanish_stemmer",
                                    "asciifolding"
                                ]
                            }
                        },
                        "filter": {
                            "spanish_stop": {
                                "type": "stop",
                                "stopwords": "_spanish_"
                            },
                            "spanish_stemmer": {
                                "type": "stemmer",
                                "language": "spanish"
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "tomo_id": {"type": "integer"},
                        "carpeta_numero": {"type": "keyword"},
                        "nombre_archivo": {"type": "text", "analyzer": "spanish_analyzer"},
                        "contenido_ocr": {
                            "type": "text",
                            "analyzer": "spanish_analyzer",
                            "term_vector": "with_positions_offsets"
                        },
                        "folio": {"type": "integer"},
                        "num_pagina": {"type": "integer"},
                        "fecha_creacion": {"type": "date"},
                        "usuario_id": {"type": "integer"},
                        "metadatos": {"type": "object"}
                    }
                }
            }
            
            self.es_client.indices.create(index=self.index_name, body=index_config)
            logger.info(f"✅ Índice '{self.index_name}' creado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error creando índice: {e}")
    
    def indexar_tomo(self, tomo_id: int, datos: Dict[str, Any]):
        """
        Indexar un tomo en Elasticsearch
        
        Args:
            tomo_id: ID del tomo
            datos: Datos a indexar
        """
        if not self.enabled:
            return
        
        try:
            self.es_client.index(
                index=self.index_name,
                id=tomo_id,
                body=datos
            )
            logger.info(f"📇 Tomo {tomo_id} indexado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error indexando tomo {tomo_id}: {e}")
    
    def buscar(
        self,
        query: str,
        campos: List[str] = None,
        size: int = 100,
        fuzzy: bool = True,
        highlight: bool = True
    ) -> Dict[str, Any]:
        """
        Realizar búsqueda avanzada
        
        Args:
            query: Texto a buscar
            campos: Campos donde buscar (default: contenido_ocr)
            size: Número máximo de resultados
            fuzzy: Habilitar búsqueda difusa para tolerar errores
            highlight: Resaltar coincidencias
            
        Returns:
            Resultados de la búsqueda
        """
        if not self.enabled:
            return {'hits': {'total': {'value': 0}, 'hits': []}}
        
        try:
            if campos is None:
                campos = ["contenido_ocr"]
            
            # Construir query
            search_query = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": campos,
                        "type": "best_fields",
                        "fuzziness": "AUTO" if fuzzy else 0,
                        "operator": "or"
                    }
                },
                "size": size,
                "_source": True
            }
            
            # Agregar highlighting
            if highlight:
                search_query["highlight"] = {
                    "fields": {
                        "contenido_ocr": {
                            "pre_tags": ["<mark>"],
                            "post_tags": ["</mark>"],
                            "fragment_size": 150,
                            "number_of_fragments": 3
                        }
                    }
                }
            
            resultados = self.es_client.search(
                index=self.index_name,
                body=search_query
            )
            
            logger.info(f"🔍 Búsqueda '{query}': {resultados['hits']['total']['value']} resultados")
            return resultados
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda: {e}")
            return {'hits': {'total': {'value': 0}, 'hits': []}}
    
    def eliminar_tomo(self, tomo_id: int):
        """Eliminar un tomo del índice"""
        if not self.enabled:
            return
        
        try:
            self.es_client.delete(index=self.index_name, id=tomo_id)
            logger.info(f"🗑️ Tomo {tomo_id} eliminado del índice")
        except Exception as e:
            logger.error(f"❌ Error eliminando tomo {tomo_id}: {e}")
    
    def reindexar_todo(self):
        """Reindexar todos los tomos desde PostgreSQL"""
        if not self.enabled:
            return
        
        try:
            logger.info("🔄 Iniciando reindexación completa...")
            from app.database import SessionLocal
            from app.models.tomo import Tomo, ContenidoOCR
            
            db = SessionLocal()
            try:
                tomos = db.query(Tomo).all()
                total = len(tomos)
                
                for idx, tomo in enumerate(tomos, 1):
                    contenidos = db.query(ContenidoOCR).filter(
                        ContenidoOCR.tomo_id == tomo.id
                    ).all()
                    
                    for contenido in contenidos:
                        datos = {
                            'tomo_id': tomo.id,
                            'carpeta_numero': tomo.carpeta_numero,
                            'nombre_archivo': tomo.nombre_archivo,
                            'contenido_ocr': contenido.contenido_ocr,
                            'folio': contenido.folio,
                            'num_pagina': contenido.num_pagina,
                            'fecha_creacion': tomo.fecha_creacion.isoformat() if tomo.fecha_creacion else None,
                            'usuario_id': tomo.usuario_id
                        }
                        self.indexar_tomo(f"{tomo.id}_{contenido.id}", datos)
                    
                    if idx % 10 == 0:
                        logger.info(f"📊 Progreso: {idx}/{total} tomos reindexados")
                
                logger.info(f"✅ Reindexación completa: {total} tomos procesados")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error en reindexación: {e}")

# Instancia global
elasticsearch_service = ElasticsearchService()
