# app/services/legal_entity_extractor.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Año: 2025 - Extractor de Entidades Jurídicas

from typing import Dict, List, Set, Optional
import re
from datetime import datetime
from difflib import SequenceMatcher
from app.utils.logger import logger

class LegalEntityExtractor:
    """Extractor de entidades específicas para documentos legales mexicanos"""
    
    def __init__(self):
        # Importar corrector agresivo
        from app.services.legal_corrector_service import legal_corrector
        self.corrector = legal_corrector

        # ── Lista negra: palabras que NO pueden ser parte de un nombre de persona ──
        self._palabras_no_nombre = {
            # Estados de México
            'AGUASCALIENTES','BAJACALIFORNIA','CAMPECHE','CHIAPAS','CHIHUAHUA',
            'COAHUILA','COLIMA','DURANGO','GUANAJUATO','GUERRERO','HIDALGO',
            'JALISCO','MEXIO','MEXICO','MÉXICO','MICHOACAN','MICHOACÁN','MORELOS',
            'NAYARIT','OAXACA','PUEBLA','QUERETARO','QUERÉTARO','SINALOA',
            'SONORA','TABASCO','TAMAULIPAS','TLAXCALA','VERACRUZ','YUCATAN',
            'YUCATÁN','ZACATECAS','LEON','NUEVO','ROO','QUINTANA','POTOSI',
            'POTOSÍ','FEDERAL','CDMX','DISTRITO',
            # Ciudades de Guerrero y zonas frecuentes en documentos PGR/FGJ
            'IGUALA','COCULA','CHILPANCINGO','ACAPULCO','TAXCO','TIXTLA',
            'TELOLOAPAN','TEPECOACUILCO','ATOYAC','ZIHUATANEJO','AYOTZINAPA',
            'APANGO','HUITZUCO','COPALILLO','BUENAVISTA','CUETZALA','COYUCA',
            # Términos legales/normativos
            'NORMA','OFICIAL','MEXICANA','ARTÍCULO','ARTICULO','FRACCION',
            'FRACCIÓN','INCISO','PÁRRAFO','PARRAFO','REGLAMENTO','CÓDIGO',
            'CODIGO','DECRETO','ACUERDO','RESOLUCION','RESOLUCIÓN',
            # Términos institucionales y corporativos
            'MINISTERIO','PUBLICO','PÚBLICO','SECRETARÍA','SECRETARIA',
            'PROCURADURIA','PROCURADURÍA','FISCALÍA','FISCALIA',
            'SUBPROCURADURIA','SUBPROCURADURÍA',
            'SEDENA','SEMAR','PGR','FGR','SSP','CISEN','SEIDOC','UEIDOS','ADSC',
            'POLICIA','POLICÍA','EJERCITO','EJÉRCITO','ARMADA','MARINA',
            'BATALLÓN','BATALLON','REGIMIENTO','BRIGADA','DIVISION','DIVISIÓN',
            'JUZGADO','TRIBUNAL','CORTE','JUEZ','MAGISTRADO',
            # Tipos de documento
            'OFICIO','CIRCULAR','MEMORANDUM','MEMORÁNDUM','CARPETA',
            'EXPEDIENTE','AVERIGUACIÓN','AVERIGUACION','DILIGENCIA',
            'ACTUACIÓN','ACTUACION','ACTA','CONSTANCIA','CERTIFICADO',
            # Palabras de dirección
            'CALLE','AVENIDA','COLONIA','BOULEVARD','CALZADA','CARRETERA',
            'MUNICIPIO','ALCALDÍA','ALCALDIA','DELEGACIÓN','DELEGACION',
            # Meses (nombres de calle a veces se confunden)
            'ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO',
            'SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE',
            # Títulos solos (válidos como prefijo de patrón, no como componente)
            'GENERAL','CORONEL','MAYOR','CAPITAN','CAPITÁN','TENIENTE',
            'SARGENTO','CABO','SOLDADO','LICENCIADO','LICENCIADA',
            'INGENIERO','DOCTOR','MAESTRO','AGENTE','DIRECTOR','SUBDIRECTOR',
        }

        # Términos que indican texto forense/balístico, no una dirección
        self._terminos_no_lugar = {
            'casquillo','casquillos','cartucho','cartuchos','bala','balas',
            'balín','fusil','pistola','rifle','calibre','percutor',
            'vaina','vainas','ateflonado','ateflonados','enjaulado',
            'enjaulados','punta de bala','mm de','narcotico','narcótico',
            'estupefaciente','droga','cocaína','heroína','marihuana',
        }
        
        # Patrones de expresiones regulares para entidades
        self.patterns = {


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
                # Abreviaturas militares/notariales: "15-MAR-2024", "15/ENE/2024", "01 ENE 2024"
                r'\b(\d{1,2})[/\-\s](ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)[/\-\s](\d{4})\b',
                # Solo mes+año: "octubre de 2014", "mes de octubre de 2014"
                r'(?:mes\s+de\s+)?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+(\d{4})\b',
                # ── FECHAS ESCRITAS EN TEXTO (formato mexicano legal) ──
                # "siete de abril del dos mil veintiséis", "PRIMERO DE ENERO DEL DOS MIL VEINTICUATRO"
                r'\b(primero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|diecis[eé]is|diecisiete|dieciocho|diecinueve|veinte|veintiuno|veintiun|veintid[oó]s|veintitr[eé]s|veinticuatro|veinticinco|veintis[eé]is|veintisiete|veintiocho|veintinueve|treinta|treinta\s+y\s+uno)\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+(\d{4})\b',
                # Con año escrito: "siete de abril del dos mil veintiséis"
                r'\b(primero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|diecis[eé]is|diecisiete|dieciocho|diecinueve|veinte|veintiuno|veintiun|veintid[oó]s|veintitr[eé]s|veinticuatro|veinticinco|veintis[eé]is|veintisiete|veintiocho|veintinueve|treinta|treinta\s+y\s+uno)\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+((?:dos\s+mil|mil\s+novecientos)(?:\s+\w+){0,3})\b',
                # "a los DD días del mes de MES de/del YEAR" (con día escrito)
                r'\ba\s+los\s+(\w+)\s+d[ií]as\s+del\s+mes\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+(\d{4})\b',
                # "a los DD días del mes de MES de/del año escrito"
                r'\ba\s+los\s+(\w+)\s+d[ií]as\s+del\s+mes\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+((?:dos\s+mil|mil\s+novecientos)(?:\s+\w+){0,3})\b',
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
                # Con apellidos compuestos anclados a campos conocidos: "DE LA ROSA", "DEL TORO"
                r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+(?:de\s+(?:la|los|las)\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2})\b(?:\s+(?:Fecha|Número|CI-|Página))',
            ],

            # ── LUGARES ── estados, municipios, colonias, calles ─────────────
            'lugares': [
                # Ciudad de México
                r'(?:ciudad\s+de\s+méxico|cdmx|d\.f\.|distrito\s+federal)',
                # Estados de la República
                r'\b(Aguascalientes|Baja\s+California(?:\s+Sur)?|Campeche|Chiapas|Chihuahua|'
                r'Coahuila|Colima|Durango|Guanajuato|Guerrero|Hidalgo|Jalisco|'
                r'Estado\s+de\s+México|Michoacán|Morelos|Nayarit|Nuevo\s+León|Oaxaca|'
                r'Puebla|Querétaro|Quintana\s+Roo|San\s+Luis\s+Potosí|Sinaloa|Sonora|'
                r'Tabasco|Tamaulipas|Tlaxcala|Veracruz|Yucatán|Zacatecas)\b',
                # Alcaldías/delegaciones CDMX  ([^\S\n] = espacio o tab, no salto de línea)
                r'(?:alcaldía|delegación)[^\S\n]+([A-ZÁÉÍÓÚÑ][a-záéíóúñ \t]{3,30})',
                # Municipios
                r'(?:municipio|mpio\.?)[^\S\n]+([A-ZÁÉÍÓÚÑ][a-záéíóúñ \t]{3,30})',
                # Colonias
                r'(?:colonia|col\.)[^\S\n]+([A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ \t]{3,35})',
                # CALLES/AVENIDAS — nombre de calle debe empezar con LETRA, no número
                # Se captura incl. el prefijo para distinguir "Calle Guerrero" del estado "Guerrero"
                r'((?:calle|c\.|avenida|av\.|boulevard|blvd\.|calzada|privada|andador|'
                r'cerrada|retorno|paseo|prol(?:ongaci[oó]n|\.)?|circuito|vía)[^\S\n]+'
                r'[A-ZÁÉÍÓÚÑa-záéíóúñ][^\n,;:]{2,42})',
                # Dirección completa: calle + número
                r'(?:domicilio|calle|avenida|av\.|boulevard|blvd\.)[^\S\n]+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:[^\S\n]+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,4})[^\S\n]+(?:núm\.?|número|no\.?|#)[^\S\n]*(\d+[A-Z]?)',
                # Colonia + alcaldía/delegación
                r'(?:colonia|col\.)[^\S\n]+([A-ZÁÉÍÓÚÑ][a-záéíóúñ \t]+),\s*(?:alcaldía|delegación|municipio)[^\S\n]+([A-ZÁÉÍÓÚÑ][a-záéíóúñ \t]+)',
                # Código postal
                r'\b(?:C\.?P\.?|código\s+postal)\s*:?\s*(\d{5})\b',
                # Colonias conocidas (hardcoded)
                r'\b(DOCTORES|Doctores|CENTRO|Centro|CONDESA|Condesa|ROMA|Roma|POLANCO|Polanco|TEPITO|Tepito|IZTAPALAPA|Iztapalapa)\b',
                # Instalaciones militares
                r'\b(Campo\s+Mil(?:itar)?\.\s+N[oú](?:m\.?)?\s+[\d\-A-Z]+)',
                r'\b(Base\s+A[eé]rea\s+[A-ZÁÉÍÓÚÑ][\w \t]{2,30}|Zona\s+Militar\s+N[oú](?:m\.)?\s+\d+|Regi[oó]n\s+Militar\s+N[oú](?:m\.)?\s+\d+)',
                # Predios
                r'\b(Predio\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ \t]{2,30})',
                # Instituciones
                r'\b(SEDENA|SEMAR|SEIDOC|UEIDOS|PGR|FGR|ADSC|CISEN)\b',
                # Batallón / Regimiento
                r'\b(\d+[oOaA]?\s+(?:Batall[oó]n|Regimiento|Escuadr[oó]n)\s+(?:de\s+)?[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ \t]{2,30})',
            ],
        }
        
        # Meses en español
        self.meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }

        # Abreviaturas de mes (documentos militares, notariales, PGR)
        self._abrev_meses = {
            'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12,
        }

        # Números escritos en texto → valor numérico (para fechas mexicanas escritas)
        self._numeros_texto = {
            'primero': 1, 'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4,
            'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
            'diez': 10, 'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14,
            'quince': 15, 'dieciséis': 16, 'dieciseis': 16, 'diecisiete': 17,
            'dieciocho': 18, 'diecinueve': 19, 'veinte': 20,
            'veintiuno': 21, 'veintiun': 21, 'veintidós': 22, 'veintidos': 22,
            'veintitrés': 23, 'veintitres': 23, 'veinticuatro': 24,
            'veinticinco': 25, 'veintiséis': 26, 'veintiseis': 26,
            'veintisiete': 27, 'veintiocho': 28, 'veintinueve': 29,
            'treinta': 30, 'treinta y uno': 31,
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
            'fechas': [],
            'nombres': [],
            'lugares': [],
        }
        
        for entity_type, patterns in self.patterns.items():
            found = set()
            
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    if entity_type == 'fechas':
                        fecha = self._normalize_date(match)
                        if fecha:
                            found.add(fecha)
                    elif entity_type == 'nombres':
                        if match.lastindex and match.lastindex >= 1:
                            nombre = match.group(1).strip()
                            if self._is_valid_name(nombre):
                                nombre_corregido = self.corrector.correct_field_aggressive(nombre, 'persona')
                                found.add(nombre_corregido.title())
                    elif entity_type == 'lugares':
                        # Combinar grupos múltiples (ej: nombre_calle + número, colonia + delegación)
                        if match.lastindex and match.lastindex >= 2:
                            partes = [match.group(i).strip() for i in range(1, match.lastindex + 1) if match.group(i)]
                            lugar = ' '.join(partes)
                        elif match.lastindex == 1:
                            lugar = match.group(1).strip()
                        else:
                            lugar = match.group(0).strip()
                        lugar = lugar.strip()
                        if not self._is_valid_location(lugar):
                            continue
                        lugar_corregido = self.corrector.correct_field_aggressive(lugar, 'lugar')
                        found.add(lugar_corregido)
            
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
                    año = self._parse_year(groups[1])
                    if año and 1900 <= año <= 2100:
                        return f"{año}-{self.meses[mes_texto]:02d}"
                return None

            if len(groups) == 3:
                g0, g1, g2 = groups[0], groups[1], groups[2]

                # Formato ISO invertido: "2024/03/15"
                if len(str(g0)) == 4 and str(g0).isdigit():
                    año, mes, dia = int(g0), int(g1), int(g2)
                elif g1.lower() in self.meses:
                    # Día puede ser número o texto: "15 de marzo de 2024" o "siete de abril del 2024"
                    dia = self._parse_day(g0)
                    año = self._parse_year(g2)
                    if dia is None or año is None:
                        return None
                    mes = self.meses[g1.lower()]
                elif g1.upper() in self._abrev_meses:
                    # "15-MAR-2024" (abreviatura militar/notarial)
                    dia, año = int(g0), int(g2)
                    mes = self._abrev_meses[g1.upper()]
                else:
                    # "15/03/2024"
                    try:
                        dia, mes, año = int(g0), int(g1), int(g2)
                    except ValueError:
                        return None

                if 1 <= mes <= 12 and 1 <= dia <= 31 and 1900 <= año <= 2100:
                    fecha = datetime(año, mes, dia)
                    return fecha.strftime('%Y-%m-%d')

        except Exception as e:
            logger.debug(f"Error normalizando fecha: {e}")

        return None

    def _parse_day(self, value: str) -> Optional[int]:
        """Convertir día a número, ya sea dígito o texto escrito"""
        value = value.strip().lower()
        # Si es número directo
        if value.isdigit():
            return int(value)
        # Si es texto escrito
        if value in self._numeros_texto:
            return self._numeros_texto[value]
        # "treinta y uno" puede venir como match con espacios
        value_norm = re.sub(r'\s+', ' ', value)
        if value_norm in self._numeros_texto:
            return self._numeros_texto[value_norm]
        return None

    def _parse_year(self, value: str) -> Optional[int]:
        """Convertir año a número, ya sea dígito o texto escrito en español"""
        value = value.strip().lower()
        # Si es número directo
        if value.isdigit():
            return int(value)
        # Parsear año escrito en texto: "dos mil veintiséis", "mil novecientos noventa y nueve"
        return self._year_text_to_number(value)

    def _year_text_to_number(self, texto: str) -> Optional[int]:
        """Convertir año escrito en texto español a número entero"""
        texto = re.sub(r'\s+', ' ', texto.strip().lower())

        _unidades = {
            'cero': 0, 'uno': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4,
            'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
        }
        _especiales = {
            'diez': 10, 'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14,
            'quince': 15, 'dieciséis': 16, 'dieciseis': 16, 'diecisiete': 17,
            'dieciocho': 18, 'diecinueve': 19,
        }
        _decenas = {
            'veinte': 20, 'veintiuno': 21, 'veintiún': 21, 'veintiun': 21,
            'veintidós': 22, 'veintidos': 22, 'veintitrés': 23, 'veintitres': 23,
            'veinticuatro': 24, 'veinticinco': 25,
            'veintiséis': 26, 'veintiseis': 26, 'veintisiete': 27,
            'veintiocho': 28, 'veintinueve': 29,
            'treinta': 30, 'cuarenta': 40, 'cincuenta': 50,
            'sesenta': 60, 'setenta': 70, 'ochenta': 80, 'noventa': 90,
        }
        _centenas = {
            'cien': 100, 'ciento': 100, 'doscientos': 200, 'trescientos': 300,
            'cuatrocientos': 400, 'quinientos': 500, 'seiscientos': 600,
            'setecientos': 700, 'ochocientos': 800, 'novecientos': 900,
        }

        try:
            total = 0
            # "dos mil veintiséis" → 2000 + 26
            # "mil novecientos noventa y nueve" → 1000 + 900 + 99
            partes = texto.replace(' y ', ' ').split()

            i = 0
            while i < len(partes):
                palabra = partes[i]

                if palabra == 'mil':
                    # Si total es 0 y "mil" es la primera, es 1000
                    if total == 0:
                        total = 1000
                    else:
                        total *= 1000
                    i += 1
                elif palabra in _centenas:
                    total += _centenas[palabra]
                    i += 1
                elif palabra in _decenas:
                    total += _decenas[palabra]
                    i += 1
                elif palabra in _especiales:
                    total += _especiales[palabra]
                    i += 1
                elif palabra in _unidades:
                    val = _unidades[palabra]
                    # Check if next word is "mil"
                    if i + 1 < len(partes) and partes[i + 1] == 'mil':
                        total += val * 1000
                        i += 2
                    else:
                        total += val
                        i += 1
                else:
                    # Palabra desconocida, saltar
                    i += 1

            if 1900 <= total <= 2100:
                return total
        except Exception:
            pass
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
    
    def _is_valid_location(self, lugar: str) -> bool:
        """Rechazar capturas de lugar que son claramente texto OCR-basura."""
        lugar = lugar.strip()
        if not lugar or len(lugar) < 4:
            return False

        # Demasiado largo para un nombre de lugar real (> 80 caracteres = frase, no lugar)
        if len(lugar) > 80:
            return False

        # Demasiadas palabras = es una oración, no un topónimo
        if len(lugar.split()) > 8:
            return False

        # Contiene terminología armamentística/forense — no es una dirección
        texto_lower = lugar.lower()
        if any(t in texto_lower for t in self._terminos_no_lugar):
            return False

        # Contiene dígitos mezclados con letras en forma no-postal (OCR garbage)
        # Permitir patrones postales tipo "762" o "Col. 123" pero rechazar "762 X 39 mm"
        if re.search(r'\d+\s+[Xx]\s+\d+', lugar):
            return False

        # ── NUEVOS FILTROS ──

        # Rechazar calibres de municin/armas: "9 MM", "7.62", ".308", ".223", "5.56", etc.
        if re.search(r'\b\d+\.?\d*\s*[Mm][Mm]\b', lugar):
            return False
        if re.search(r'\.\d{2,3}["\']?\s', lugar):
            return False
        # Patrones balísticos específicos
        if re.search(r'\b(?:WIN|PARABELLUM|BMG|REM|AUTO|MAUSSER|GA)\b', lugar, re.IGNORECASE):
            return False
        if re.search(r'\bCALIBRE\b', lugar, re.IGNORECASE):
            return False

        # Rechazar "coloniaa" con doble 'a' (artefacto OCR común)
        if re.search(r'coloniaa', texto_lower):
            return False

        # Rechazar si después del tipo de vía (CALLE/AVENIDA) hay verbos/frases
        # Ej: "CALLE se llevaran a cabo", "CALLE por su importancia"
        verbo_patterns = [
            r'(?:calle|avenida|av\.|blvd\.)\s+(?:se|por|de|en|que|las|los|con|sin|fue|era|son|hay|del|una|el|la|al)\b',
            r'(?:calle|avenida)\s+[a-záéíóú]{2,}\s+[a-záéíóú]{2,}',  # minusculas tras calle = frase
        ]
        for vp in verbo_patterns:
            if re.search(vp, texto_lower):
                return False

        # Rechazar si contiene palabras de documentos legales
        terminos_legales = [
            'investigación', 'investigacion', 'rev.:', 'ref.:', 'pgr', 'lftaipg',
            'ministerio', 'agencia', 'coordinación', 'dictamen', 'acuerdo',
            'carpeta', 'expediente', 'indiciado', 'constitución', 'constitucion',
            'certificado', 'paradero', 'memorandum', 'requerimiento',
            'diligencia', 'perito', 'pericial', 'fraccion', 'fracción',
            'artículo', 'articulo', 'república', 'republica',
        ]
        if any(t in texto_lower for t in terminos_legales):
            return False

        # Rechazar si es mayormente números y fragmentos cortos sin sentido
        # Contar ratio de dígitos vs letras
        digitos = sum(1 for c in lugar if c.isdigit())
        letras = sum(1 for c in lugar if c.isalpha())
        if letras > 0 and digitos / letras > 0.3:
            return False

        # Rechazar frases demasiado largas que son texto corrido, no nombres de lugar
        palabras_lugar = lugar.split()
        if len(palabras_lugar) > 4:
            # Si tiene más de 4 palabras y muchas en minúscula, es frase
            minusculas = sum(1 for p in palabras_lugar if p[0].islower())
            if minusculas > len(palabras_lugar) // 2:
                return False

        return True

    def _is_valid_name(self, nombre: str) -> bool:
        """Validar que sea un nombre válido"""
        nombre = nombre.strip()

        # Debe tener al menos 2 palabras
        palabras = nombre.split()
        if len(palabras) < 2:
            return False

        # Longitud total razonable
        if len(nombre) > 80:
            return False

        # Filtrar palabras muy comunes que no son nombres
        stop_words = {'de', 'la', 'el', 'los', 'las', 'del', 'y', 'e', 'o', 'u'}
        palabras_validas = [p for p in palabras if p.lower() not in stop_words]

        if len(palabras_validas) < 2:
            return False

        # Rechazar si algún token pertenece a la lista negra institucional/geográfica
        for p in palabras:
            if p.upper() in self._palabras_no_nombre:
                return False

        # Cada token válido no debe contener dígitos (OCR garbage)
        for p in palabras_validas:
            if re.search(r'\d', p):
                return False
            # Cada palabra de contenido debe tener mín 3 caracteres
            if len(p) < 3 or len(p) > 30:
                return False
            # No debe tener caracteres extraños (símbolos, slash, etc.)
            if re.search(r'[/\\|@#$%^&*()_+=\[\]{}<>]', p):
                return False

        # Rechazar si primera palabra es título/rango/geográfico
        _titulos_no_nombre = {
            'comandante','general','coronel','teniente','sargento','cabo',
            'soldado','almirante','capitán','capitan','mayor','director',
            'subdirector','unidos','rlo','rio','río','san','santa','santo',
            'norma','oficial',
        }
        if palabras_validas[0].lower() in _titulos_no_nombre:
            return False

        # Rechazar palabras con 3+ consonantes seguidas (artefacto OCR)
        for p in palabras_validas:
            p_low = p.lower()
            if re.search(r'[bcdfghjklmnpqrstvwxyz]{3,}', p_low):
                # Excepciones reales en español
                if not re.search(r'(?:sch|str|ndr|nst|mpr|mbr|ntr|nsp|rst)', p_low):
                    return False

        # Rechazar nombres con sufijo OCR pegado (ej: Jacoboituve, Navaly)
        try:
            from app.services.legal_entity_filter_service import LegalEntityFilterService
            for p in palabras_validas:
                p_low = p.lower()
                if len(p_low) > 9:
                    for ap in LegalEntityFilterService.APELLIDOS_COMUNES:
                        if p_low.startswith(ap) and len(p_low) > len(ap) + 1 and p_low != ap:
                            return False
        except ImportError:
            pass

        return True
    
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
            if entity_type == 'nombres':
                # Deduplicación difusa: si dos nombres son >78% similares,
                # conservar solo el más largo (más información OCR)
                unique: List[str] = []
                for name in sorted(values, key=len, reverse=True):
                    name_norm = name.lower().strip()
                    is_dup = False
                    for kept in unique:
                        kept_norm = kept.lower().strip()
                        ratio = SequenceMatcher(None, name_norm, kept_norm).ratio()
                        if ratio > 0.78:
                            is_dup = True
                            break
                        # También detectar si uno es prefijo del otro
                        # Ej: "Salvador Reza" vs "Salvador Reza Jacobo"
                        if name_norm in kept_norm or kept_norm in name_norm:
                            is_dup = True
                            break
                    if not is_dup:
                        unique.append(name)
                deduplicated[entity_type] = unique
                continue

            unique_list = []
            seen = set()
            
            for value in values:
                # Normalizar para comparación
                normalized = value.lower().strip()
                normalized = re.sub(r'\s+', ' ', normalized)
                
                if normalized not in seen:
                    seen.add(normalized)
                    unique_list.append(value)
            
            deduplicated[entity_type] = unique_list
        
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
                    'fechas': 'Fechas',
                    'nombres': 'Nombres',
                    'lugares': 'Lugares',
                }.get(entity_type, entity_type.title())
                
                summary_parts.append(f"{label}: {count}")
        
        return " | ".join(summary_parts) if summary_parts else "Sin entidades extraídas"

# Instancia global
entity_extractor = LegalEntityExtractor()
