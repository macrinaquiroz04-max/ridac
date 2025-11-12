# app/services/legal_entity_extractor.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Año: 2025 - Extractor de Entidades Jurídicas

from typing import Dict, List, Set, Optional
import re
from datetime import datetime
from app.utils.logger import logger

class LegalEntityExtractor:
    """Extractor de entidades específicas para documentos legales mexicanos"""
    
    def __init__(self):
        # Importar corrector agresivo
        from app.services.legal_corrector_service import legal_corrector
        self.corrector = legal_corrector
        
        # Patrones de expresiones regulares para entidades
        self.patterns = {
            # Carpetas de investigación / Averiguaciones previas
            'carpetas': [
                r'(?:carpeta|C\.?I\.?|CI)\s*(?:de\s*investigación\s*)?(?:núm\.?|número|no\.?|N°)?\s*:?\s*([A-Z]{2,4}[-/][A-Z]{2,5}[-/][A-Z0-9]{1,4}[-/][A-Z0-9]{1,6}[-/]\d{2,6})',
                r'(?:averiguación\s*previa|A\.?P\.?|AP)\s*(?:núm\.?|número|no\.?)?\s*:?\s*([A-Z]{2,4}[-/]\d{1,2}[-/]\d{4,6})',
                r'\b(CI-[A-Z]{3}/[A-Z]{2}/[A-Z0-9-]{2,15}/\d{2,6})\b',  # Formato específico CI-FBJ/...
            ],
            
            # Oficios
            'oficios': [
                r'(?:oficio|circular|memorándum)\s*(?:núm\.?|número|no\.?|N°)?\s*:?\s*([A-Z]{2,6}[-/][A-Z]{2,6}[-/]\d{2,6}[-/]?\d{0,4})',
                r'\b(FGJ-?CDMX-?\d{4}-?\d{3,6})\b',  # Formato específico FGJ-CDMX
            ],
            
            # Teléfonos
            'telefonos': [
                r'\b(?:\+?52\s*)?(?:\d{2}[-\s]?)?\d{4}[-\s]?\d{4}\b',
                r'\b(?:tel\.?|teléfono|cel\.?|celular)[:.]?\s*(\d{2,4}[-\s]?\d{4}[-\s]?\d{4})\b',
            ],
            
            # Fechas
            'fechas': [
                r'\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?(\d{4})\b',
                r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b',
            ],
            
            # Nombres completos (MUY FLEXIBLES - captura nombres sin palabras clave)
            'nombres': [
                # Con palabras clave tradicionales
                r'(?:ciudadano|C\.|ciudadana|señor|sr\.|señora|sra\.|licenciado|lic\.|licenciada)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
                r'(?:víctima|ofendido|ofendida|imputado|imputada|testigo|perito|perita)[:.]?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
                # SIN palabras clave - captura 2-4 palabras capitalizadas seguidas
                r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,15}\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,15}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,15}){0,2})\b(?:\s+(?:Fecha|Número|CI-|Página))',
                # Nombres antes de palabras comunes de documentos
                r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,15}\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,15}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,15})?)\s+(?:Duarte|Lopez|Fecha|Número)',
                # Patrón después de "Por", "De", etc.
                r'(?:Por|De|Del)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,15}\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,15}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,15})?)',
            ],
            
            # Direcciones
            'direcciones': [
                r'(?:domicilio|calle|avenida|av\.|boulevard|blvd\.)?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,4})\s+(?:núm\.?|número|no\.?|#)\s*(\d+[A-Z]?)',
                r'(?:colonia|col\.)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+),\s*(?:alcaldía|delegación|municipio)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)',
            ],
            
            # Delitos
            'delitos': [
                r'(?:delito|delitos)\s+(?:de\s+)?([a-záéíóúñ\s,y]+?)(?:\s+previsto|\s+contemplado|\s+sancionado|,|\.|;)',
                r'(?:probable\s+responsabilidad|responsable)\s+(?:del?\s+)?(?:delito\s+de\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)',
            ],
            
            # Lugares (MUY FLEXIBLES - captura colonias, calles, alcaldías)
            'lugares': [
                r'(?:ciudad\s+de\s+méxico|cdmx|estado\s+de\s+méxico|edomex)',
                r'(?:alcaldía|delegación)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)',
                r'(?:municipio|mpio\.?)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)',
                # Colonias sin palabra clave "colonia"
                r'(?:colonia|col\.)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]{4,40})',
                # Calles
                r'(?:calle|c\.|avenida|av\.|boulevard|blvd\.)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]{4,40})',
                # Captura nombres de colonias populares
                r'\b(DOCTORES|Doctores|CENTRO|Centro|CONDESA|Condesa|ROMA|Roma|POLANCO|Polanco)\b',
            ],
            
            # Diligencias (MÁS FLEXIBLES - captura tipos de actuaciones)
            'diligencias': [
                r'(?:se\s+ordena|se\s+acuerda|se\s+dicta)\s+([^\.]{10,80})',
                r'(?:diligencia|actuación)\s+(?:de\s+)?([a-záéíóúñ\s]{5,50})',
                # Tipos de actuaciones comunes
                r'\b(Actuación\s+Ministerial|Acta\s+De\s+Hechos|Comunicado|Diligencia\s+General|Solicitud)\b',
            ],
            
            # Alertas MP (términos urgentes)
            'alertas': [
                r'\b(urgente|inmediato|prioritario|violación\s+grave|flagrancia|orden\s+de\s+aprehensión)\b',
                r'\b(plazo\s+\d+\s+(?:días|horas)|vencimiento|caducidad|prescripción)\b',
            ]
        }
        
        # Meses en español
        self.meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
    
    def extract_all(self, text: str) -> Dict[str, List[str]]:
        """
        Extraer todas las entidades del texto
        
        Args:
            text: Texto procesado por OCR
            
        Returns:
            Diccionario con entidades extraídas por categoría
        """
        if not text:
            return {}
        
        entities = {
            'carpetas': [],
            'oficios': [],
            'telefonos': [],
            'fechas': [],
            'nombres': [],
            'direcciones': [],
            'delitos': [],
            'lugares': [],
            'diligencias': [],
            'alertas': []
        }
        
        for entity_type, patterns in self.patterns.items():
            found = set()
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    if entity_type == 'fechas':
                        # Normalizar fechas al formato ISO
                        fecha = self._normalize_date(match)
                        if fecha:
                            found.add(fecha)
                    elif entity_type == 'telefonos':
                        # Normalizar teléfonos
                        tel = self._normalize_phone(match.group(0))
                        if tel:
                            found.add(tel)
                    elif entity_type == 'nombres':
                        # Limpiar nombres y CORREGIR AGRESIVAMENTE
                        if match.lastindex and match.lastindex >= 1:
                            nombre = match.group(1).strip()
                            if self._is_valid_name(nombre):
                                # Aplicar corrección agresiva al nombre
                                nombre_corregido = self.corrector.correct_field_aggressive(nombre, 'persona')
                                found.add(nombre_corregido.title())
                    elif entity_type == 'direcciones':
                        # Combinar partes de dirección y CORREGIR
                        direccion = match.group(0).strip()
                        direccion_corregida = self.corrector.correct_field_aggressive(direccion, 'lugar')
                        found.add(direccion_corregida)
                    elif entity_type == 'lugares':
                        # CORRECCIÓN AGRESIVA para lugares
                        lugar = match.group(0).strip() if not match.lastindex else match.group(1).strip()
                        lugar_corregido = self.corrector.correct_field_aggressive(lugar, 'lugar')
                        found.add(lugar_corregido)
                    elif entity_type == 'diligencias':
                        # CORRECCIÓN AGRESIVA para diligencias
                        diligencia = match.group(0).strip() if not match.lastindex else match.group(1).strip()
                        diligencia_corregida = self.corrector.correct_field_aggressive(diligencia, 'tipo')
                        found.add(diligencia_corregida)
                    else:
                        # Otras entidades - TAMBIÉN con corrección agresiva
                        if match.lastindex and match.lastindex >= 1:
                            value = match.group(1).strip()
                        else:
                            value = match.group(0).strip()
                        
                        # Aplicar corrección agresiva
                        value_corregido = self.corrector.correct_field_aggressive(value, entity_type)
                        
                        if len(value_corregido) > 3:  # Filtrar muy cortos
                            found.add(value_corregido)
            
            entities[entity_type] = sorted(list(found))
        
        return entities
    
    def _normalize_date(self, match: re.Match) -> Optional[str]:
        """Normalizar fecha al formato ISO YYYY-MM-DD"""
        try:
            groups = match.groups()
            
            if len(groups) == 3:
                # Formato: "15 de marzo de 2024" o "15/03/2024"
                dia = int(groups[0])
                
                if groups[1].lower() in self.meses:
                    # Formato con mes en texto
                    mes = self.meses[groups[1].lower()]
                else:
                    # Formato numérico
                    mes = int(groups[1])
                
                año = int(groups[2])
                
                # Validar
                if 1 <= mes <= 12 and 1 <= dia <= 31 and 1900 <= año <= 2100:
                    fecha = datetime(año, mes, dia)
                    return fecha.strftime('%Y-%m-%d')
        except Exception as e:
            logger.debug(f"Error normalizando fecha: {e}")
        
        return None
    
    def _normalize_phone(self, phone: str) -> Optional[str]:
        """Normalizar teléfono eliminando espacios y guiones"""
        # Extraer solo dígitos
        digits = re.sub(r'\D', '', phone)
        
        # Validar longitud (10 dígitos locales o 12 con código país)
        if len(digits) == 10:
            return f"+52 {digits[:2]} {digits[2:6]} {digits[6:]}"
        elif len(digits) == 12 and digits.startswith('52'):
            return f"+{digits[:2]} {digits[2:4]} {digits[4:8]} {digits[8:]}"
        
        return None
    
    def _is_valid_name(self, nombre: str) -> bool:
        """Validar que sea un nombre válido"""
        # Debe tener al menos 2 palabras
        palabras = nombre.split()
        if len(palabras) < 2:
            return False
        
        # Filtrar palabras muy comunes que no son nombres
        stop_words = {'de', 'la', 'el', 'los', 'las', 'del', 'y', 'e', 'o', 'u'}
        palabras_validas = [p for p in palabras if p.lower() not in stop_words]
        
        return len(palabras_validas) >= 2
    
    def deduplicate_entities(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Eliminar duplicados y entidades muy similares
        
        Args:
            entities: Diccionario de entidades
            
        Returns:
            Entidades sin duplicados
        """
        deduplicated = {}
        
        for entity_type, values in entities.items():
            unique = []
            seen = set()
            
            for value in values:
                # Normalizar para comparación
                normalized = value.lower().strip()
                normalized = re.sub(r'\s+', ' ', normalized)
                
                if normalized not in seen:
                    seen.add(normalized)
                    unique.append(value)
            
            deduplicated[entity_type] = unique
        
        return deduplicated
    
    def get_summary(self, entities: Dict[str, List[str]]) -> str:
        """
        Generar resumen de entidades extraídas
        
        Args:
            entities: Diccionario de entidades
            
        Returns:
            Resumen en texto
        """
        summary_parts = []
        
        for entity_type, values in entities.items():
            if values:
                count = len(values)
                label = {
                    'carpetas': 'Carpetas/APs',
                    'oficios': 'Oficios',
                    'telefonos': 'Teléfonos',
                    'fechas': 'Fechas',
                    'nombres': 'Nombres',
                    'direcciones': 'Direcciones',
                    'delitos': 'Delitos',
                    'lugares': 'Lugares',
                    'diligencias': 'Diligencias',
                    'alertas': 'Alertas'
                }.get(entity_type, entity_type.title())
                
                summary_parts.append(f"{label}: {count}")
        
        return " | ".join(summary_parts) if summary_parts else "Sin entidades extraídas"

# Instancia global
entity_extractor = LegalEntityExtractor()
