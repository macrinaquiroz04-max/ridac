# app/services/legal_corrector_service.py
# Sistema OCR con Análisis Jurídico - SUPER CORRECTOR AVANZADO
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Año: 2025 - Corrector Ortográfico Legal Mexicano con IA

from typing import Dict, Set, Tuple, List, Optional
import re
from difflib import SequenceMatcher, get_close_matches
from app.utils.logger import logger

class LegalCorrectorService:
    """
    Corrector ortográfico AVANZADO especializado en términos legales mexicanos
    con auto-completado, fuzzy matching agresivo y corrección contextual
    """
    
    def __init__(self):
        # Diccionario EXPANDIDO de términos legales mexicanos (200+ términos)
        self.legal_terms = {
            # Instituciones
            'fiscalía', 'ministerio', 'público', 'procuraduría', 'tribunal',
            'juzgado', 'audiencia', 'secretaría', 'delegación', 'agencia',
            'fiscalía general', 'procurador', 'procuraduría', 'juez', 'magistrado',
            'agente', 'investigación', 'investigador', 'coordinación', 'coordinador',
            'dirección', 'director', 'directora', 'titular', 'responsable',
            'administración', 'administrador', 'fiscal', 'subfiscal', 'subfiscalía',
            
            # Delitos
            'homicidio', 'robo', 'fraude', 'lesiones', 'violación',
            'secuestro', 'extorsión', 'amenazas', 'allanamiento',
            'narcotráfico', 'lavado de dinero', 'peculado', 'cohecho',
            'delito', 'delincuencia', 'criminal', 'crimen',
            
            # Documentos
            'carpeta de investigación', 'averiguación previa', 'denuncia',
            'querella', 'acta circunstanciada', 'oficio', 'exhorto',
            'mandamiento', 'citatorio', 'requerimiento', 'auto',
            'sentencia', 'resolución', 'acuerdo', 'providencia',
            'oficio', 'oficial', 'documento', 'constancia', 'certificado',
            'circular', 'memorándum', 'memorandum', 'notificación',
            
            # Personas y roles
            'víctima', 'ofendido', 'imputado', 'indiciado', 'procesado',
            'acusado', 'testigo', 'perito', 'defensor', 'asesor jurídico',
            'representante legal', 'tutor', 'curador', 'licenciado', 'abogado',
            'pasante', 'notario', 'actuario', 'secretario', 'escribiente',
            
            # Acciones legales
            'diligencia', 'notificación', 'emplazamiento', 'comparecencia',
            'declaración', 'interrogatorio', 'careo', 'inspección',
            'cateo', 'aseguramiento', 'decomiso', 'embargo',
            'actuación', 'ministerial', 'policial', 'judicial',
            'investigativa', 'pericial', 'probatoria',
            
            # Plazos y términos
            'término', 'plazo', 'prescripción', 'caducidad', 'prórroga',
            'suspensión', 'interrupción', 'continuación', 'fecha',
            
            # Lugares
            'domicilio', 'residencia', 'paradero', 'ubicación',
            'colonia', 'municipio', 'alcaldía', 'demarcación',
            'distrito', 'federal', 'ciudad', 'estado', 'calle',
            'avenida', 'número', 'interior', 'exterior',
            
            # Documentación
            'legajo', 'expediente', 'tomo', 'foja', 'constancia',
            'certificación', 'legalización', 'apostilla', 'ratificación',
            'página', 'folio', 'anexo', 'adjunto',
            
            # Términos jurídicos generales
            'constitución', 'constitucional', 'política', 'político',
            'código', 'penal', 'procesal', 'civil', 'mercantil',
            'artículo', 'fracción', 'inciso', 'párrafo', 'capítulo',
            'título', 'libro', 'sección', 'presente', 'anterior',
            'siguiente', 'referido', 'mencionado', 'citado',
            
            # Verbos y acciones comunes
            'solicitar', 'solicito', 'solicita', 'requerir', 'requiero',
            'ordenar', 'ordeno', 'girar', 'giro', 'dirigir', 'dirijo',
            'notificar', 'notifico', 'emplazar', 'emplazo',
            'comparecer', 'comparezco', 'declarar', 'declaro'
        }
        
        # Términos compuestos frecuentes
        self.compound_terms = [
            'ministerio público', 'fiscalía general', 'carpeta de investigación',
            'averiguación previa', 'acta circunstanciada', 'defensor público',
            'asesor jurídico', 'representante legal', 'domicilio conocido',
            'ciudad de méxico', 'código penal', 'código procesal',
            'derechos humanos', 'orden de aprehensión', 'mandato judicial'
        ]
        
        # MAPEO MASIVO de errores OCR comunes (100+ correcciones)
        self.common_ocr_errors = {
            # Instituciones - SOLO variaciones específicas (6+ caracteres)
            'fisclia': 'fiscalía', 'fiscal1a': 'fiscalía', 'f1scalía': 'fiscalía',
            'fisca1ía': 'fiscalía', 'fiscai1a': 'fiscalía', 'flscalía': 'fiscalía',
            'ministrerio': 'ministerio', 'ministeno': 'ministerio', 'min1sterio': 'ministerio',
            'ministerl0': 'ministerio', 'miniaterio': 'ministerio',
            'publ1co': 'público', 'públ1co': 'público', 'pub1ico': 'público',
            'publlco': 'público', 'publíco': 'público',
            'procuradurí': 'procuraduría', 'procuradur1a': 'procuraduría',
            'procuraduria': 'procuraduría', 'procuraduríaurador': 'procuraduría',
            'juzgad0': 'juzgado', 'juzgadc': 'juzgado',
            'tribuna1': 'tribunal', 'tr1bunal': 'tribunal', 'trlbunal': 'tribunal',
            
            # Delitos
            'hom1cidio': 'homicidio', 'homlcidio': 'homicidio', 'homicid1o': 'homicidio',
            'vict1ma': 'víctima', 'victima': 'víctima',
            
            # Documentos - MUY IMPORTANTE
            'of1cio': 'oficio', '0ficio': 'oficio', 'ofic1o': 'oficio',
            'oficioo': 'oficio', 'oficlo': 'oficio',
            'oficial': 'oficial', 'ofic1al': 'oficial', '0ficial': 'oficial',
            'oficiaal': 'oficial', 'oficioa': 'oficial', 'oficioal': 'oficial',
            'c1tatorio': 'citatorio', 'citator1o': 'citatorio', 'cltatorio': 'citatorio',
            'sentenc1a': 'sentencia', 'sentencla': 'sentencia', 'sentenma': 'sentencia',
            'reso1ución': 'resolución', 'resoluci0n': 'resolución', 'resolucion': 'resolución',
            
            # Acciones y diligencias
            'di1igencia': 'diligencia', 'diligencla': 'diligencia', 'diligenci': 'diligencia',
            'notif1cación': 'notificación', 'notificaci0n': 'notificación',
            'notificacion': 'notificación',
            'dec1aración': 'declaración', 'declaraci0n': 'declaración',
            'declaracion': 'declaración',
            'actuaci0n': 'actuación', 'actuacion': 'actuación',
            
            # Personas
            'ofend1do': 'ofendido', 'ofendldo': 'ofendido',
            '1mputado': 'imputado', 'imputad0': 'imputado',
            'test1go': 'testigo', 'testlgo': 'testigo',
            'per1to': 'perito', 'perlto': 'perito',
            'licenciado': 'licenciado', 'l1cenciado': 'licenciado', 'licenciad': 'licenciado',
            'licentro': 'licenciado', 'licentrociado': 'licenciado',
            
            # Lugares (SOLO 6+ caracteres)
            'co1onia': 'colonia', 'colonla': 'colonia',
            'mun1cipio': 'municipio', 'municip1o': 'municipio', 'munlcipio': 'municipio',
            'ciudad': 'ciudad', 'c1udad': 'ciudad', 'cludad': 'ciudad',
            'méxico': 'méxico', 'mex1co': 'méxico', 'mexlco': 'méxico',
            'domic1lio': 'domicilio', 'domicil1o': 'domicilio', 'domlcilio': 'domicilio',
            
            # Documentación (SOLO 6+ caracteres)
            'exped1ente': 'expediente', 'expedlente': 'expediente',
            'constanc1a': 'constancia', 'constancla': 'constancia',
            'pag1na': 'página', 'paglna': 'página',
            'págína': 'página',
            
            # Términos jurídicos (SOLO 6+ caracteres)
            'const1tución': 'constitución', 'constituci0n': 'constitución',
            'constitucion': 'constitución', 'constituclon': 'constitución',
            'constituerion': 'constitución', 'constituclón': 'constitución',
            'pol1tica': 'política', 'politica': 'política',
            'pelitica': 'política', 'politlca': 'política',
            'c0digo': 'código', 'cod1go': 'código', 'codigc': 'código',
            'codigo': 'código',
            
            # Palabras específicas del screenshot (SOLO 6+ caracteres)
            'centrotral': 'central', 'centroi': 'central', 'centro': 'central',
            'miniaterio': 'ministerio', 'iisterio': 'ministerio',
            'miniaterio': 'ministerio', 'miniaterio': 'ministerio',
            
            # Errores específicos de tu screenshot
            'conellycadn': 'comunicación', 'coneliycadn': 'comunicación',
            'catificado': 'certificado', 'catif': 'certificado',
            'nisterio': 'ministerio',
            'clinica': 'clínica', 'directora': 'directora',
            'coloniaA': 'colonia', 'coloniaa': 'colonia',
            'doctores': 'doctores', 'codígo': 'código',
            'alcaldía': 'alcaldía', 'alcaldia': 'alcaldía',
                        'girado': 'girado', 'uraduría': 'procuraduría',
            'averiguación': 'averiguación',
            'previa': 'previa'
        }
        
        # Construir índice inverso para búsqueda rápida
        self._build_index()
    
    def _build_index(self):
        """Construir índice de términos para búsqueda rápida"""
        self.all_terms = self.legal_terms.copy()
        for compound in self.compound_terms:
            for word in compound.split():
                self.all_terms.add(word.lower())
    
    def correct_text(self, text: str) -> str:
        """
        Corregir texto completo con términos legales - AGRESIVO
        Aplica múltiples estrategias de corrección para maximizar precisión
        
        Args:
            text: Texto a corregir
            
        Returns:
            Texto corregido
        """
        if not text:
            return text
        
        try:
            # Paso 1: Reemplazos de caracteres confusos ANTES de cualquier cosa
            corrected = self._normalize_ocr_chars(text)
            
            # Paso 2: Correcciones directas de errores conocidos (100+ patrones)
            for error, correction in self.common_ocr_errors.items():
                # Buscar con y sin límites de palabra para capturar más casos
                # Con límites
                pattern = r'\b' + re.escape(error) + r'\b'
                corrected = re.sub(pattern, correction, corrected, flags=re.IGNORECASE)
                
                # Sin límites para palabras parciales
                corrected = corrected.replace(error, correction)
                corrected = corrected.replace(error.upper(), correction.upper())
                corrected = corrected.replace(error.capitalize(), correction.capitalize())
            
            # Paso 3: Corrección de términos compuestos con fuzzy matching
            for compound in self.compound_terms:
                # Crear patrón flexible tolerante a errores
                pattern_parts = []
                for word in compound.split():
                    # Patrón super tolerante: permite 1, l, I para i y 0, O para o
                    tolerant_word = (word
                        .replace('i', '[i1lI]')
                        .replace('o', '[o0O]')
                        .replace('a', '[a@]')
                        .replace('e', '[e3]')
                    )
                    pattern_parts.append(tolerant_word)
                
                pattern = r'\b' + r'\s+'.join(pattern_parts) + r'\b'
                corrected = re.sub(pattern, compound, corrected, flags=re.IGNORECASE)
            
            # Paso 4: Corrección AGRESIVA palabra por palabra con fuzzy matching
            words = corrected.split()
            corrected_words = []
            
            for word in words:
                # Extraer palabra sin puntuación pero mantener puntuación
                match = re.match(r'^([^\w]*)([\w]+)([^\w]*)$', word)
                if not match:
                    corrected_words.append(word)
                    continue
                    
                prefix, clean_word, suffix = match.groups()
                clean_lower = clean_word.lower()
                
                # Skip palabras muy cortas o números
                if len(clean_lower) < 3 or clean_lower.isdigit():
                    corrected_words.append(word)
                    continue
                
                # Buscar corrección con múltiples estrategias
                corrected_word = None
                
                # Estrategia 1: Búsqueda exacta en términos conocidos
                if clean_lower in self.all_terms:
                    corrected_word = clean_lower
                
                # Estrategia 2: Fuzzy matching con umbral 75% para precisión
                if not corrected_word:
                    corrected_word = self._find_best_match(clean_lower, threshold=0.75)
                
                # Estrategia 3: Auto-completado para palabras truncadas
                if not corrected_word:
                    corrected_word = self._autocomplete_word(clean_lower)
                
                # Aplicar corrección preservando capitalización
                if corrected_word and corrected_word != clean_lower:
                    if clean_word.isupper():
                        corrected_word = corrected_word.upper()
                    elif clean_word[0].isupper():
                        corrected_word = corrected_word.capitalize()
                    
                    corrected_words.append(prefix + corrected_word + suffix)
                    logger.info(f"OCR Corrección: '{word}' → '{prefix}{corrected_word}{suffix}'")
                else:
                    corrected_words.append(word)
            
            final_text = ' '.join(corrected_words)
            
            # Paso 5: Normalización final de espacios y caracteres
            final_text = re.sub(r'\s+', ' ', final_text)
            final_text = final_text.strip()
            
            return final_text
            
        except Exception as e:
            logger.error(f"Error en corrección de texto: {str(e)}")
            return text
    
    def _normalize_ocr_chars(self, text: str) -> str:
        """
        Normalizar caracteres confusos comunes de OCR
        Convierte: 1->i, 0->o, l->I, etc. en contexto apropiado
        """
        # Reemplazos contextuales de caracteres confusos
        replacements = {
            # Números que deberían ser letras en palabras
            r'(?<=[a-záéíóúñ])1(?=[a-záéíóúñ])': 'i',  # fiscal1a → fiscalia
            r'(?<=[a-záéíóúñ])0(?=[a-záéíóúñ])': 'o',  # hom0cidio → homocidio
            r'(?<=[a-záéíóúñ])5(?=[a-záéíóúñ])': 's',  # ca5o → caso
            r'(?<=[a-záéíóúñ])3(?=[a-záéíóúñ])': 'e',  # t3rminó → terminó
            r'(?<=[a-záéíóúñ])8(?=[a-záéíóúñ])': 'b',  # ca8o → cabo
            
            # Caracteres extraños comunes
            r'\|': 'I',  # | → I
            r'©': 'c',   # © → c
            r'ñ(?=[^a-záéíóúñ])': 'en',  # ñ solo → en
        }
        
        result = text
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _autocomplete_word(self, word: str) -> Optional[str]:
        """
        Auto-completar palabra truncada buscando coincidencias por prefijo
        
        Args:
            word: Palabra posiblemente truncada
            
        Returns:
            Palabra completa o None
        """
        # Buscar términos que empiecen con esta palabra
        matches = [term for term in self.all_terms if term.startswith(word.lower())]
        
        if matches:
            # Si hay una coincidencia exacta en longitud similar, usarla
            close_matches = [m for m in matches if len(m) - len(word) <= 4]
            if close_matches:
                # Retornar la más corta (más probable)
                return min(close_matches, key=len)
        
        return None
    
    def _find_best_match(self, word: str, threshold: float = 0.75) -> Optional[str]:
        """
        Encontrar mejor coincidencia para una palabra usando fuzzy matching PRECISO
        
        Args:
            word: Palabra a corregir
            threshold: Umbral de similitud mínima (default 0.75 = 75% de precisión)
            
        Returns:
            Mejor coincidencia o None
        """
        if not word or len(word) < 3:
            return None
        
        word_lower = word.lower()
        best_match = None
        best_ratio = threshold
        
        # Estrategia 1: Usar get_close_matches de difflib (rápido y efectivo)
        close_matches = get_close_matches(word_lower, self.all_terms, n=3, cutoff=threshold)
        if close_matches:
            return close_matches[0]  # Retornar la mejor coincidencia
        
        # Estrategia 2: Fuzzy matching manual con SequenceMatcher
        for term in self.all_terms:
            # Calcular similitud
            ratio = SequenceMatcher(None, word_lower, term).ratio()
            
            # Bonificación si la palabra empieza igual (probablemente truncada)
            if term.startswith(word_lower[:3]):
                ratio += 0.1
            
            # Bonificación si tiene longitud similar
            if abs(len(word) - len(term)) <= 2:
                ratio += 0.05
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = term
        
        if best_match:
            logger.debug(f"Fuzzy match: '{word}' → '{best_match}' (confianza: {best_ratio:.2f})")
        
        return best_match
    
    def correct_field_aggressive(self, text: str, field_type: str = 'generic') -> str:
        """
        Corrección INTELIGENTE para campos específicos de diligencias
        Aplica solo correcciones del diccionario + normalización de caracteres
        NO usa fuzzy matching para evitar correcciones erróneas
        
        Args:
            text: Texto a corregir
            field_type: Tipo de campo ('persona', 'lugar', 'responsable', 'tipo', 'generic')
            
        Returns:
            Texto corregido
        """
        if not text or not text.strip():
            return text
            
        original = text
        
        # Paso 1: Normalizar caracteres problemáticos PRIMERO
        text = self._normalize_ocr_chars(text)
        
        # Paso 2: Aplicar SOLO correcciones exactas del diccionario (no fuzzy)
        for error, correction in self.common_ocr_errors.items():
            if len(error) >= 6:  # Solo reglas largas y específicas
                # Usar palabra completa para evitar reemplazos parciales
                pattern = r'\b' + re.escape(error) + r'\b'
                text = re.sub(pattern, correction, text, flags=re.IGNORECASE)
        
        # Log solo si hubo cambios significativos
        if text != original and text.lower() != original.lower():
            logger.info(f"Corrección [{field_type}]: '{original}' → '{text}'")
        
        return text
    
    def correct_entities(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Corregir entidades extraídas (nombres, lugares, etc.) con AGRESIVIDAD
        
        Args:
            entities: Diccionario de entidades
            
        Returns:
            Entidades corregidas y deduplicadas
        """
        corrected = {}
        
        for entity_type, values in entities.items():
            corrected_values = set()
            
            for value in values:
                # Corregir el valor
                corrected_value = self.correct_text(value)
                # Normalizar espacios
                corrected_value = ' '.join(corrected_value.split())
                if corrected_value:
                    corrected_values.add(corrected_value)
            
            corrected[entity_type] = sorted(list(corrected_values))
        
        return corrected

# Instancia global
legal_corrector = LegalCorrectorService()
