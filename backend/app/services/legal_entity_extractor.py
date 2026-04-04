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
                r'\b(CI-[A-Z]{3}/[A-Z]{2}/[A-Z0-9-]{2,15}/\d{2,6})\b',
            ],

            # Oficios
            'oficios': [
                r'(?:oficio|circular|memorándum)\s*(?:núm\.?|número|no\.?|N°)?\s*:?\s*([A-Z]{2,6}[-/][A-Z]{2,6}[-/]\d{2,6}[-/]?\d{0,4})',
                r'\b(FGJ-?CDMX-?\d{4}-?\d{3,6})\b',
            ],

            # Teléfonos
            'telefonos': [
                r'\b(?:\+?52\s*)?(?:\d{2}[-\s]?)?\d{4}[-\s]?\d{4}\b',
                r'\b(?:tel\.?|teléfono|cel\.?|celular)[:.]?\s*(\d{2,4}[-\s]?\d{4}[-\s]?\d{4})\b',
            ],

            # ── FECHAS ── máxima cobertura ───────────────────────────────────
            'fechas': [
                # "15 de marzo de 2024" / "15 de marzo 2024"
                r'\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?(\d{4})\b',
                # "15/03/2024" | "15-03-2024" | "15.03.2024"
                r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b',
                # "2024/03/15" (ISO invertido)
                r'\b(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})\b',
                # "a 11 de noviembre del 2014" — usa "DEL" (muy común en oficio mexicano)
                r'\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+del\s+(\d{4})\b',
                # "Ciudad de México / Campo Mil., a 15 de marzo de/del 2024"
                r'(?:ciudad|méxico|d\.f\.|cdmx|campo\s+mil(?:itar)?)[,\.\s]+a\s+(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?:\s+(?:de|del))?\s+(\d{4})',
                # Cualquier lugar + ", a DD de MES de/del YEAR" (patrón de oficio)
                r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s,\.]+,\s+a\s+(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+(\d{4})',
                # "a los quince días del mes de marzo" — solo captura el mes+año si hay año
                r'mes\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?:\s+(?:de|del)\s+(\d{4}))?',
                # "noviembre del presente año" / "del año en curso" (sin año explícito)
                r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+del\s+(?:presente\s+año|año\s+en\s+curso|año\s+actual)',
            ],

            # ── NOMBRES ── captura nombres normales Y en MAYÚSCULAS ──────────
            'nombres': [
                # Con título o rol — normal y mayúsculas
                r'(?:ciudadano|ciudadana|señor|sr\.|señora|sra\.|licenciado|lic\.|licenciada|ing\.|ingeniero|doctor|dr\.|dra\.)\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+){1,3})',
                r'(?:víctima|ofendido|ofendida|imputado|imputada|testigo|perito|perita|denunciante|querellante|detenido|detenida)[:.]?\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+){1,3})',
                # Roles militares / institucionales con nombre a continuación
                r'(?:General|Coronel|Teniente\s+Coronel|Mayor|Capit[aá]n|Teniente|Subteniente|Sargento|Cabo|Soldado|Almirante|Comandante|Director\s+General|Subprocurador|Procurador|Agente(?:\s+del\s+Ministerio\s+P[uú]blico)?)\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+){1,3})',
                # Suscrito / firmante
                r'(?:El\s+suscrito|La\s+suscrita|El\s+que\s+suscribe|quien\s+suscribe)[,\s]+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+){1,3})',
                # Etiquetas tipo formulario: "NOMBRE: JUAN GARCIA LOPEZ"
                r'(?:NOMBRE|NOMBRE COMPLETO|DENUNCIANTE|VÍCTIMA|IMPUTADO|DECLARANTE|DE LA PERSONA)[:\s]+([A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,}){1,4})',
                # Nombres en MAYÚSCULAS (muy común en docs escaneados de PGR/FGJ)
                r'\b([A-ZÁÉÍÓÚÑ]{3,20}\s+[A-ZÁÉÍÓÚÑ]{3,20}(?:\s+[A-ZÁÉÍÓÚÑ]{2,20}){0,2})\b(?=\s*(?:,|\n|\.|\s+(?:nació|de|con|cuyo|quien|comparece|manifiesta|declara)))',
                # Con apellidos compuestos: "DE LA ROSA", "DEL TORO"
                r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+(?:de\s+(?:la|los|las)\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2})\b(?:\s+(?:Fecha|Número|CI-|Página))',
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

            # ── LUGARES ── incluye estados y municipios de México ─────────────
            'lugares': [
                # Ciudad de México
                r'(?:ciudad\s+de\s+méxico|cdmx|d\.f\.|distrito\s+federal)',
                # Estados de la República
                r'\b(Aguascalientes|Baja\s+California(?:\s+Sur)?|Campeche|Chiapas|Chihuahua|'
                r'Coahuila|Colima|Durango|Guanajuato|Guerrero|Hidalgo|Jalisco|'
                r'Estado\s+de\s+México|Michoacán|Morelos|Nayarit|Nuevo\s+León|Oaxaca|'
                r'Puebla|Querétaro|Quintana\s+Roo|San\s+Luis\s+Potosí|Sinaloa|Sonora|'
                r'Tabasco|Tamaulipas|Tlaxcala|Veracruz|Yucatán|Zacatecas)\b',
                # Alcaldías/delegaciones CDMX
                r'(?:alcaldía|delegación)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)',
                # Municipios
                r'(?:municipio|mpio\.?)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)',
                # Colonias
                r'(?:colonia|col\.)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]{4,40})',
                # Calles y avenidas
                r'(?:calle|c\.|avenida|av\.|boulevard|blvd\.)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]{4,40})',
                # Código postal
                r'\b(?:C\.?P\.?|código\s+postal)\s*:?\s*(\d{5})\b',
                # Colonias conocidas
                r'\b(DOCTORES|Doctores|CENTRO|Centro|CONDESA|Condesa|ROMA|Roma|POLANCO|Polanco|TEPITO|Tepito|IZTAPALAPA|Iztapalapa)\b',
                # Instalaciones militares: "Campo Militar No. 1-J", "Campo Mil. No. 1-A"
                r'\b(Campo\s+Mil(?:itar)?\.\s+N[oú](?:m\.?)?\s+[\d\-A-Z]+)',
                r'\b(Base\s+A[eé]rea\s+[A-ZÁÉÍÓÚÑ][\w\s]+|Zona\s+Militar\s+N[oú](?:m\.)?\s+\d+|Regi[oó]n\s+Militar\s+N[oú](?:m\.)?\s+\d+)',
                # Predios con nombre: "Predio Reforma", "Predio Los Pinos"
                r'\b(Predio\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]{2,30})',
                # Instituciones militares/procuradurías
                r'\b(SEDENA|SEMAR|SEIDOC|UEIDOS|PGR|FGR|ADSC|CISEN)\b',
                # Batallón / Regimiento
                r'\b(\d+[oOaA]?\s+(?:Batall[oó]n|Regimiento|Escuadr[oó]n)\s+(?:de\s+)?[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]+)',
            ],

            # Diligencias
            'diligencias': [
                r'(?:se\s+ordena|se\s+acuerda|se\s+dicta)\s+([^\.]{10,80})',
                r'(?:diligencia|actuación)\s+(?:de\s+)?([a-záéíóúñ\s]{5,50})',
                r'\b(Actuación\s+Ministerial|Acta\s+De\s+Hechos|Comunicado|Diligencia\s+General|Solicitud)\b',
            ],

            # Alertas MP
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
        """Normalizar fecha al formato ISO YYYY-MM-DD (o YYYY-MM si no hay día)"""
        try:
            groups = match.groups()
            # Limpiar grupos None
            groups = [g for g in groups if g is not None]

            if len(groups) == 0:
                return None

            if len(groups) == 1:
                # Solo mes en texto — devolver nombre del mes
                mes_texto = groups[0].lower()
                if mes_texto in self.meses:
                    return f"(mes) {groups[0].capitalize()}"
                return None

            if len(groups) == 2:
                # Mes + año
                mes_texto = groups[0].lower()
                if mes_texto in self.meses:
                    año = int(groups[1])
                    if 1900 <= año <= 2100:
                        return f"{año}-{self.meses[mes_texto]:02d}"
                return None

            if len(groups) == 3:
                g0, g1, g2 = groups[0], groups[1], groups[2]

                # Formato ISO invertido: "2024/03/15"
                if len(str(g0)) == 4 and str(g0).isdigit():
                    año, mes, dia = int(g0), int(g1), int(g2)
                elif g1.lower() in self.meses:
                    # "15 de marzo de 2024"
                    dia, año = int(g0), int(g2)
                    mes = self.meses[g1.lower()]
                else:
                    # "15/03/2024"
                    dia, mes, año = int(g0), int(g1), int(g2)

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
