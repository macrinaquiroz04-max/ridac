"""
🧠 SERVICIO DE NLP AVANZADO PARA DOCUMENTOS LEGALES MEXICANOS
Integra spaCy + NER personalizado para fiscalía
"""

import warnings
import re
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import json

try:
    import spacy
    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False
    spacy = None

# Suprimir advertencias de spaCy sobre transformers
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*resume_download.*deprecated.*")

logger = logging.getLogger("ridac_ocr")

@dataclass
class LegalEntity:
    """Entidad legal detectada"""
    text: str
    label: str
    start: int
    end: int
    confidence: float
    context: str
    legal_type: str

class LegalNLPService:
    """Servicio NLP especializado para documentos legales mexicanos"""
    
    def __init__(self):
        self.nlp = None
        self.matcher = None
        self.legal_patterns = self._create_legal_patterns()
        self.initialize_spacy()
    
    def initialize_spacy(self):
        """Inicializar spaCy con modelo en español optimizado"""
        if not _SPACY_AVAILABLE:
            logger.info("spaCy no disponible — NLP deshabilitado")
            return
        try:
            # 🎯 MODELO GRANDE OPTIMIZADO - Mejor precisión para documentos legales
            self.nlp = spacy.load("es_core_news_lg")
            
            # 🚀 OPTIMIZACIONES DE RENDIMIENTO
            self.nlp.max_length = 2000000  # Documentos grandes hasta 2MB
            
            # Configurar pipeline para máxima precisión en entidades legales
            if self.nlp.has_pipe("ner"):
                ner = self.nlp.get_pipe("ner")
                ner.cfg["beam_width"] = 32  # Mayor precisión en NER
            
            logger.info("✅ spaCy MODELO GRANDE (es_core_news_lg) cargado con optimizaciones")
            logger.info(f"📊 Componentes activos: {self.nlp.pipe_names}")
            
        except OSError:
            try:
                # Fallback a modelo mediano
                self.nlp = spacy.load("es_core_news_md")
                self.nlp.max_length = 1500000  # Reducir para modelo mediano
                logger.info("✅ spaCy modelo mediano (es_core_news_md) cargado")
            except OSError:
                try:
                    # Fallback a modelo pequeño
                    self.nlp = spacy.load("es_core_news_sm")
                    self.nlp.max_length = 1000000  # Reducir para modelo pequeño
                    logger.info("⚠️ spaCy modelo pequeño (es_core_news_sm) cargado")
                except OSError:
                    logger.error("❌ No se encontró ningún modelo de spaCy en español")
                    logger.error("💡 Instala un modelo con: python -m spacy download es_core_news_lg")
                    self.nlp = None
        
        if self.nlp:
            # Agregar patrones personalizados para documentos legales mexicanos
            self._add_legal_patterns()
    
    def _create_legal_patterns(self) -> Dict[str, List[Dict]]:
        """Crear patrones específicos para documentos legales mexicanos"""
        
        return {
            # Cargos y títulos legales
            'CARGO_LEGAL': [
                {"label": "FISCAL", "pattern": r"\b(?:FISCAL|AGENTE DEL MINISTERIO PÚBLICO|AMP)\b"},
                {"label": "JUEZ", "pattern": r"\b(?:JUEZ|MAGISTRADO|MINISTRO)\b"},
                {"label": "ABOGADO", "pattern": r"\b(?:LIC\.|LICENCIADO|ABOGADO|DEFENSOR)\b"},
                {"label": "PERITO", "pattern": r"\b(?:PERITO|ESPECIALISTA|TÉCNICO)\b"},
            ],
            
            # Tipos de delitos comunes en México
            'TIPO_DELITO': [
                {"label": "DELITO_PATRIMONIAL", "pattern": r"\b(?:ROBO|FRAUDE|EXTORSIÓN|DESPOJO)\b"},
                {"label": "DELITO_VIOLENTO", "pattern": r"\b(?:HOMICIDIO|LESIONES|SECUESTRO|VIOLACIÓN)\b"},
                {"label": "DELITO_DROGAS", "pattern": r"\b(?:NARCOMENUDEO|POSESIÓN|TRÁFICO|ESTUPEFACIENTES)\b"},
                {"label": "DELITO_FAMILIAR", "pattern": r"\b(?:VIOLENCIA FAMILIAR|ABANDONO|INCUMPLIMIENTO)\b"},
            ],
            
            # Documentos legales mexicanos
            'DOCUMENTO_LEGAL': [
                {"label": "CARPETA", "pattern": r"\b(?:CARPETA DE INVESTIGACIÓN|CI-[A-Z]+-\d+)\b"},
                {"label": "OFICIO", "pattern": r"\b(?:OFICIO|OF\.|CIRCULAR)\s+[\w\/-]+\b"},
                {"label": "ACUERDO", "pattern": r"\b(?:ACUERDO|AUTO|RESOLUCIÓN)\b"},
                {"label": "DICTAMEN", "pattern": r"\b(?:DICTAMEN|PERITAJE|INFORME PERICIAL)\b"},
            ],
            
            # Instituciones mexicanas
            'INSTITUCION': [
                {"label": "FISCALIA", "pattern": r"\b(?:FISCALÍA GENERAL|FGJ|PGJ|MINISTERIO PÚBLICO)\b"},
                {"label": "TRIBUNAL", "pattern": r"\b(?:TRIBUNAL|JUZGADO|PODER JUDICIAL)\b"},
                {"label": "POLICIA", "pattern": r"\b(?:POLICÍA|SSC|SECRETARÍA DE SEGURIDAD)\b"},
                {"label": "HOSPITAL", "pattern": r"\b(?:HOSPITAL|CLÍNICA|CENTRO DE SALUD|IMSS|ISSSTE)\b"},
            ],
            
            # Lugares específicos de CDMX
            'LUGAR_CDMX': [
                {"label": "ALCALDIA", "pattern": r"\b(?:ALCALDÍA|DELEGACIÓN)\s+(?:CUAUHTÉMOC|BENITO JUÁREZ|MIGUEL HIDALGO|COYOACÁN|TLALPAN|XOCHIMILCO|IZTACALCO|IZTAPALAPA|GUSTAVO A\. MADERO|VENUSTIANO CARRANZA|ÁLVARO OBREGÓN|AZCAPOTZALCO|CUAJIMALPA|MAGDALENA CONTRERAS|MILPA ALTA|TLÁHUAC)\b"},
                {"label": "COLONIA", "pattern": r"\b(?:COLONIA|COL\.)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+\b"},
                {"label": "ZONA", "pattern": r"\b(?:CENTRO HISTÓRICO|ZONA ROSA|POLANCO|SANTA FE|DOCTORES|ROMA|CONDESA)\b"},
            ]
        }
    
    def _add_legal_patterns(self):
        """Agregar patrones personalizados al pipeline de spaCy"""
        if not self.nlp:
            return
        
        from spacy.matcher import Matcher
        
        # Crear matcher para patrones legales
        matcher = Matcher(self.nlp.vocab)
        
        for category, patterns in self.legal_patterns.items():
            for pattern_info in patterns:
                pattern_name = f"{category}_{pattern_info['label']}"
                # Convertir regex a patrón de spaCy (simplificado)
                pattern = [{"TEXT": {"REGEX": pattern_info['pattern']}}]
                matcher.add(pattern_name, [pattern])
        
        # Guardar matcher como atributo de la clase
        self.matcher = matcher
        
        # Agregar componente personalizado al pipeline
        if "legal_matcher" not in self.nlp.pipe_names:
            @self.nlp.component("legal_matcher")
            def legal_matcher_component(doc):
                matches = self.matcher(doc)
                # Procesar matches si es necesario
                return doc
            
            self.nlp.add_pipe("legal_matcher", last=True)
    
    def extract_legal_entities(self, text: str) -> List[LegalEntity]:
        """Extraer entidades legales específicas del texto"""
        
        if not self.nlp:
            return self._fallback_pattern_extraction(text)
        
        entities = []
        
        try:
            # Procesar texto con spaCy
            doc = self.nlp(text)
            
            # Extraer entidades nombradas estándar
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'GPE', 'DATE', 'MONEY']:
                    legal_type = self._classify_entity_type(ent.text, ent.label_)
                    
                    entities.append(LegalEntity(
                        text=ent.text,
                        label=ent.label_,
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=0.8,  # spaCy no da confianza directa
                        context=self._get_context(text, ent.start_char, ent.end_char),
                        legal_type=legal_type
                    ))
            
            # Agregar patrones personalizados
            custom_entities = self._extract_custom_patterns(text)
            entities.extend(custom_entities)
            
        except Exception as e:
            logger.error(f"Error en extracción NLP: {e}")
            return self._fallback_pattern_extraction(text)
        
        return entities
    
    def _extract_custom_patterns(self, text: str) -> List[LegalEntity]:
        """Extraer patrones personalizados con regex"""
        
        entities = []
        
        for category, patterns in self.legal_patterns.items():
            for pattern_info in patterns:
                regex = pattern_info['pattern']
                
                for match in re.finditer(regex, text, re.IGNORECASE):
                    entities.append(LegalEntity(
                        text=match.group(0),
                        label=pattern_info['label'],
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9,  # Alta confianza para patrones específicos
                        context=self._get_context(text, match.start(), match.end()),
                        legal_type=category
                    ))
        
        return entities
    
    def _classify_entity_type(self, text: str, spacy_label: str) -> str:
        """Clasificar tipo de entidad en contexto legal"""
        
        if spacy_label == 'PERSON':
            # Determinar si es víctima, testigo, acusado, etc.
            if any(word in text.upper() for word in ['LIC.', 'DR.', 'ING.']):
                return 'PROFESIONAL'
            elif re.match(r'^[A-Z]\.([A-Z]\.)+$', text):
                return 'MENOR_PROTEGIDO'
            else:
                return 'PERSONA'
        
        elif spacy_label == 'ORG':
            if any(word in text.upper() for word in ['FISCALÍA', 'TRIBUNAL', 'JUZGADO']):
                return 'INSTITUCION_LEGAL'
            else:
                return 'ORGANIZACION'
        
        elif spacy_label == 'GPE':
            return 'LUGAR'
        
        elif spacy_label == 'DATE':
            return 'FECHA'
        
        elif spacy_label == 'MONEY':
            return 'MONTO'
        
        return 'OTRO'
    
    def _get_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Obtener contexto alrededor de una entidad"""
        
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        
        return text[context_start:context_end].strip()
    
    def _fallback_pattern_extraction(self, text: str) -> List[LegalEntity]:
        """Extracción básica con regex si spaCy no está disponible"""
        
        entities = []
        
        # Patrones básicos de fallback
        fallback_patterns = {
            'NOMBRES': r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?\b',
            'FECHAS': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
            'CARPETAS': r'\bCI-[A-Z]+-\d+[-/]\d+\b',
            'DIRECCIONES': r'\b(?:CALLE|AV\.|AVENIDA)\s+[^,\n]{5,50}\b'
        }
        
        for label, pattern in fallback_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(LegalEntity(
                    text=match.group(0),
                    label=label,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.7,
                    context=self._get_context(text, match.start(), match.end()),
                    legal_type='BASICO'
                ))
        
        return entities
    
    def analyze_document_legal_context(self, text: str) -> Dict[str, Any]:
        """Análisis completo del contexto legal del documento"""
        
        entities = self.extract_legal_entities(text)
        
        # Agrupar entidades por tipo
        grouped_entities = {}
        for entity in entities:
            if entity.legal_type not in grouped_entities:
                grouped_entities[entity.legal_type] = []
            grouped_entities[entity.legal_type].append(entity)
        
        # Análisis estadístico
        stats = {
            'total_entities': len(entities),
            'entities_by_type': {k: len(v) for k, v in grouped_entities.items()},
            'confidence_avg': sum(e.confidence for e in entities) / len(entities) if entities else 0,
            'protected_minors': len([e for e in entities if e.legal_type == 'MENOR_PROTEGIDO']),
            'legal_institutions': len([e for e in entities if e.legal_type == 'INSTITUCION_LEGAL']),
            'document_complexity': self._calculate_complexity(entities)
        }
        
        # Detectar tipo de documento
        document_type = self._detect_document_type(text, entities)
        
        return {
            'entities': [self._entity_to_dict(e) for e in entities],
            'grouped_entities': {k: [self._entity_to_dict(e) for e in v] for k, v in grouped_entities.items()},
            'statistics': stats,
            'document_type': document_type,
            'legal_summary': self._generate_legal_summary(entities, stats)
        }
    
    def _entity_to_dict(self, entity: LegalEntity) -> Dict:
        """Convertir entidad a diccionario"""
        return {
            'text': entity.text,
            'label': entity.label,
            'start': entity.start,
            'end': entity.end,
            'confidence': entity.confidence,
            'context': entity.context,
            'legal_type': entity.legal_type
        }
    
    def _calculate_complexity(self, entities: List[LegalEntity]) -> str:
        """Calcular complejidad del documento"""
        
        if len(entities) > 50:
            return 'ALTA'
        elif len(entities) > 20:
            return 'MEDIA'
        else:
            return 'BAJA'
    
    def _detect_document_type(self, text: str, entities: List[LegalEntity]) -> str:
        """Detectar tipo de documento legal"""
        
        text_upper = text.upper()
        
        if 'CARPETA DE INVESTIGACIÓN' in text_upper:
            return 'CARPETA_INVESTIGACION'
        elif 'DECLARACIÓN' in text_upper or 'COMPARECENCIA' in text_upper:
            return 'DECLARACION'
        elif 'DICTAMEN' in text_upper or 'PERITAJE' in text_upper:
            return 'DICTAMEN_PERICIAL'
        elif 'OFICIO' in text_upper:
            return 'OFICIO'
        elif 'ACUERDO' in text_upper:
            return 'ACUERDO'
        else:
            return 'DOCUMENTO_GENERAL'
    
    def _generate_legal_summary(self, entities: List[LegalEntity], stats: Dict) -> str:
        """Generar resumen legal del documento"""
        
        summary_parts = []
        
        if stats['protected_minors'] > 0:
            summary_parts.append(f"Documento contiene {stats['protected_minors']} menores protegidos")
        
        if stats['legal_institutions'] > 0:
            summary_parts.append(f"Involucra {stats['legal_institutions']} instituciones legales")
        
        complexity = stats['document_complexity']
        summary_parts.append(f"Complejidad: {complexity}")
        
        if stats['total_entities'] > 30:
            summary_parts.append("Caso con múltiples personas/entidades involucradas")
        
        return ". ".join(summary_parts) if summary_parts else "Documento legal estándar"

# Instancia global del servicio
legal_nlp_service = LegalNLPService()

# Función de integración para el controlador
async def analyze_legal_document_nlp(text: str) -> Dict[str, Any]:
    """Función de análisis NLP para integrar con el controlador existente"""
    return legal_nlp_service.analyze_document_legal_context(text)