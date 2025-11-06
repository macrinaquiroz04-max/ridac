"""
Servicio avanzado de detección de patrones específicos para documentos legales mexicanos
"""
import re
from typing import Dict, List, Set, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PatternDetectionService:
    """Servicio especializado en detectar patrones específicos en documentos legales"""
    
    def __init__(self):
        self.meses_nombres = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }
        
        self.numeros_escritos = {
            'un': 1, 'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
            'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
            'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14, 'quince': 15,
            'dieciséis': 16, 'diecisiete': 17, 'dieciocho': 18, 'diecinueve': 19,
            'veinte': 20, 'veintiuno': 21, 'veintidós': 22, 'veintitrés': 23,
            'veinticuatro': 24, 'veinticinco': 25, 'veintiséis': 26, 'veintisiete': 27,
            'veintiocho': 28, 'veintinueve': 29, 'treinta': 30, 'treinta y uno': 31
        }
        
        self.anos_escritos = {
            'dos mil': 2000, 'dos mil uno': 2001, 'dos mil dos': 2002, 'dos mil tres': 2003,
            'dos mil cuatro': 2004, 'dos mil cinco': 2005, 'dos mil seis': 2006, 'dos mil siete': 2007,
            'dos mil ocho': 2008, 'dos mil nueve': 2009, 'dos mil diez': 2010, 'dos mil once': 2011,
            'dos mil doce': 2012, 'dos mil trece': 2013, 'dos mil catorce': 2014, 'dos mil quince': 2015,
            'dos mil dieciséis': 2016, 'dos mil diecisiete': 2017, 'dos mil dieciocho': 2018,
            'dos mil diecinueve': 2019, 'dos mil veinte': 2020, 'dos mil veintiuno': 2021,
            'dos mil veintidós': 2022, 'dos mil veintitrés': 2023, 'dos mil veinticuatro': 2024,
            'dos mil veinticinco': 2025, 'dos mil veintiséis': 2026, 'dos mil veintisiete': 2027,
            'dos mil veintiocho': 2028, 'dos mil veintinueve': 2029, 'dos mil treinta': 2030
        }

    def extraer_fechas_avanzadas(self, texto: str) -> List[Dict]:
        """Extrae fechas con múltiples formatos específicos para documentos legales"""
        fechas_encontradas = []
        
        # Patrón 1: Fechas numéricas (DD/MM/AAAA, DD-MM-AAAA, DD.MM.AAAA)
        patron_numerico = r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})'
        for match in re.finditer(patron_numerico, texto):
            dia, mes, ano = match.groups()
            if 1 <= int(dia) <= 31 and 1 <= int(mes) <= 12:
                fechas_encontradas.append({
                    'texto': match.group(0),
                    'tipo': 'numérica',
                    'dia': int(dia),
                    'mes': int(mes),
                    'año': int(ano),
                    'posicion': match.span()
                })
        
        # Patrón 2: Fechas escritas completas (QUINCE DE OCTUBRE DE DOS MIL VEINTICINCO)
        patron_completo = r'([A-ZÁÉÍÓÚÑ]+(?:\s+Y\s+[A-ZÁÉÍÓÚÑ]+)?)\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+DE\s+([A-ZÁÉÍÓÚÑ\s]+)'
        for match in re.finditer(patron_completo, texto, re.IGNORECASE):
            dia_texto, mes_texto, ano_texto = match.groups()
            
            # Convertir día escrito a número
            dia_num = self._convertir_numero_escrito(dia_texto.lower())
            
            # Convertir mes a número
            mes_num = self.meses_nombres.get(mes_texto.lower())
            
            # Convertir año escrito a número
            ano_num = self._convertir_ano_escrito(ano_texto.lower())
            
            if dia_num and mes_num and ano_num:
                fechas_encontradas.append({
                    'texto': match.group(0),
                    'tipo': 'escrita_completa',
                    'dia': dia_num,
                    'mes': mes_num,
                    'año': ano_num,
                    'posicion': match.span()
                })
        
        # Patrón 3: Fechas mixtas (15 DE OCTUBRE DE 2025)
        patron_mixto = r'(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+DE\s+(\d{4})'
        for match in re.finditer(patron_mixto, texto, re.IGNORECASE):
            dia, mes_texto, ano = match.groups()
            mes_num = self.meses_nombres.get(mes_texto.lower())
            
            if mes_num and 1 <= int(dia) <= 31:
                fechas_encontradas.append({
                    'texto': match.group(0),
                    'tipo': 'mixta',
                    'dia': int(dia),
                    'mes': mes_num,
                    'año': int(ano),
                    'posicion': match.span()
                })
        
        # Patrón 4: Contextos legales específicos
        patron_legal = r'A\s+LOS\s+([A-ZÁÉÍÓÚÑ]+(?:\s+Y\s+[A-ZÁÉÍÓÚÑ]+)?)\s+DÍAS?\s+DEL\s+MES\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+DEL?\s+AÑO\s+([A-ZÁÉÍÓÚÑ\s]+)'
        for match in re.finditer(patron_legal, texto, re.IGNORECASE):
            dia_texto, mes_texto, ano_texto = match.groups()
            
            dia_num = self._convertir_numero_escrito(dia_texto.lower())
            mes_num = self.meses_nombres.get(mes_texto.lower())
            ano_num = self._convertir_ano_escrito(ano_texto.lower())
            
            if dia_num and mes_num and ano_num:
                fechas_encontradas.append({
                    'texto': match.group(0),
                    'tipo': 'legal_formal',
                    'dia': dia_num,
                    'mes': mes_num,
                    'año': ano_num,
                    'posicion': match.span()
                })
        
        return fechas_encontradas

    def extraer_nombres_completos(self, texto: str) -> List[Dict]:
        """Extrae nombres completos con títulos profesionales"""
        nombres_encontrados = []
        
        # Patrón para títulos profesionales
        titulos = r'(?:C\.|LIC\.|ING\.|DR\.|DRA\.|ARQ\.|PROF\.|C\.P\.|MTRO\.|MTRA\.|CIUDADAN[OA])\s+'
        
        # Patrón principal: TÍTULO + NOMBRE(S) + PATERNO + MATERNO
        patron_completo = rf'({titulos})?([A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+)*)\s+([A-ZÁÉÍÓÚÑ]+)\s+([A-ZÁÉÍÓÚÑ]+)'
        
        for match in re.finditer(patron_completo, texto):
            titulo, nombres, paterno, materno = match.groups()
            
            # Filtrar palabras que no son nombres
            palabras_excluir = {'MINISTERIO', 'PÚBLICO', 'FISCALÍA', 'GENERAL', 'NACIONAL', 'FEDERAL', 
                               'ESTADO', 'MÉXICO', 'CIUDAD', 'DELEGACIÓN', 'MUNICIPIO', 'SERVICIOS',
                               'COORDINACIÓN', 'DIRECCIÓN', 'DEPARTAMENTO', 'OFICINA', 'HOSPITAL',
                               'INSTITUTO', 'UNIVERSIDAD', 'COLEGIO', 'ESCUELA', 'CENTRO'}
            
            if not any(palabra in nombres.upper() for palabra in palabras_excluir):
                nombres_encontrados.append({
                    'texto_completo': match.group(0).strip(),
                    'titulo': titulo.strip() if titulo else None,
                    'nombres': nombres.strip(),
                    'apellido_paterno': paterno.strip(),
                    'apellido_materno': materno.strip(),
                    'tipo': 'nombre_completo',
                    'posicion': match.span()
                })
        
        # Patrón para nombres sin título pero con formato completo
        patron_sin_titulo = r'\b([A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{3,})*)\s+([A-ZÁÉÍÓÚÑ]{3,})\s+([A-ZÁÉÍÓÚÑ]{3,})\b'
        
        for match in re.finditer(patron_sin_titulo, texto):
            nombres, paterno, materno = match.groups()
            
            # Verificar que no sea una dirección o institución
            if (not any(palabra in nombres.upper() for palabra in palabras_excluir) and
                len(nombres.split()) <= 3):  # Máximo 3 nombres
                
                nombres_encontrados.append({
                    'texto_completo': match.group(0).strip(),
                    'titulo': None,
                    'nombres': nombres.strip(),
                    'apellido_paterno': paterno.strip(),
                    'apellido_materno': materno.strip(),
                    'tipo': 'nombre_sin_titulo',
                    'posicion': match.span()
                })
        
        return nombres_encontrados

    def extraer_direcciones_completas(self, texto: str) -> List[Dict]:
        """Extrae direcciones con formato mexicano completo"""
        direcciones_encontradas = []
        
        # Patrón para tipo de vía
        tipos_via = r'(?:CALLE|C\.|CLLE\.|AVENIDA|AV\.|BOULEVARD|BLVD\.|PRIVADA|PRIV\.|CALZADA|CALZ\.|PASEO|PSO\.|ANDADOR|AND\.)'
        
        # Patrón para números
        numeros = r'(?:NÚMERO|No\.|NUM\.|#)\s*(\d+(?:-[A-Z])?(?:\s+INT\.\s*\d+)?)'
        
        # Patrón principal de dirección
        patron_direccion = rf'({tipos_via})\s+([A-ZÁÉÍÓÚÑ\s\.]+?)\s+{numeros}'
        
        for match in re.finditer(patron_direccion, texto, re.IGNORECASE):
            tipo_via, nombre_via, numero = match.groups()
            
            direcciones_encontradas.append({
                'texto': match.group(0),
                'tipo_via': tipo_via.strip(),
                'nombre_via': nombre_via.strip(),
                'numero': numero.strip(),
                'tipo': 'direccion_basica',
                'posicion': match.span()
            })
        
        # Patrón para direcciones con colonia y CP
        patron_completo = rf'({tipos_via})\s+([A-ZÁÉÍÓÚÑ\s\.]+?)\s+{numeros}(?:\s+(?:COL\.|COLONIA)\s+([A-ZÁÉÍÓÚÑ\s]+?))?(?:\s+(?:C\.P\.|CÓDIGO POSTAL)\s*(\d{{5}}))?'
        
        for match in re.finditer(patron_completo, texto, re.IGNORECASE):
            tipo_via, nombre_via, numero, colonia, cp = match.groups()
            
            direcciones_encontradas.append({
                'texto': match.group(0),
                'tipo_via': tipo_via.strip(),
                'nombre_via': nombre_via.strip(),
                'numero': numero.strip(),
                'colonia': colonia.strip() if colonia else None,
                'codigo_postal': cp if cp else None,
                'tipo': 'direccion_completa',
                'posicion': match.span()
            })
        
        return direcciones_encontradas

    def extraer_lugares_geograficos(self, texto: str) -> List[Dict]:
        """Extrae referencias geográficas específicas de México"""
        lugares_encontrados = []
        
        # Patrón para entidades federativas
        estados_mx = [
            'AGUASCALIENTES', 'BAJA CALIFORNIA', 'BAJA CALIFORNIA SUR', 'CAMPECHE', 'CHIAPAS', 
            'CHIHUAHUA', 'CIUDAD DE MÉXICO', 'COAHUILA', 'COLIMA', 'DURANGO', 'ESTADO DE MÉXICO',
            'GUANAJUATO', 'GUERRERO', 'HIDALGO', 'JALISCO', 'MICHOACÁN', 'MORELOS', 'NAYARIT',
            'NUEVO LEÓN', 'OAXACA', 'PUEBLA', 'QUERÉTARO', 'QUINTANA ROO', 'SAN LUIS POTOSÍ',
            'SINALOA', 'SONORA', 'TABASCO', 'TAMAULIPAS', 'TLAXCALA', 'VERACRUZ', 'YUCATÁN', 'ZACATECAS',
            'D.F.', 'CDMX', 'EDO. DE MÉXICO', 'EDO. MEX.', 'EDOMEX'
        ]
        
        # Buscar estados
        for estado in estados_mx:
            patron = rf'\b({re.escape(estado)})\b'
            for match in re.finditer(patron, texto, re.IGNORECASE):
                lugares_encontrados.append({
                    'texto': match.group(0),
                    'tipo': 'estado',
                    'nombre': estado,
                    'posicion': match.span()
                })
        
        # Patrón para municipios/alcaldías
        patron_municipio = r'(?:MUNICIPIO|ALCALDÍA|DELEGACIÓN)\s+([A-ZÁÉÍÓÚÑ\s]+?)(?:\s*,|\s+(?:ESTADO|EDO\.))'
        for match in re.finditer(patron_municipio, texto, re.IGNORECASE):
            municipio = match.group(1).strip()
            lugares_encontrados.append({
                'texto': match.group(0),
                'tipo': 'municipio_alcaldia',
                'nombre': municipio,
                'posicion': match.span()
            })
        
        # Patrón para colonias/fraccionamientos
        patron_colonia = r'(?:COL\.|COLONIA|FRACCIONAMIENTO|FRAC\.)\s+([A-ZÁÉÍÓÚÑ\s]+?)(?:\s*,|\s+(?:C\.P\.|CÓDIGO))'
        for match in re.finditer(patron_colonia, texto, re.IGNORECASE):
            colonia = match.group(1).strip()
            lugares_encontrados.append({
                'texto': match.group(0),
                'tipo': 'colonia_fraccionamiento',
                'nombre': colonia,
                'posicion': match.span()
            })
        
        # Patrón para referencias jurídicas
        patron_juridico = r'(CIRCUNSCRIPCIÓN JUDICIAL|PARTIDO JUDICIAL|DISTRITO JUDICIAL|JUZGADO DE LO [A-ZÁÉÍÓÚÑ\s]+ DE [A-ZÁÉÍÓÚÑ\s]+)'
        for match in re.finditer(patron_juridico, texto, re.IGNORECASE):
            lugares_encontrados.append({
                'texto': match.group(0),
                'tipo': 'referencia_juridica',
                'nombre': match.group(0),
                'posicion': match.span()
            })
        
        return lugares_encontrados

    def _convertir_numero_escrito(self, numero_texto: str) -> int:
        """Convierte números escritos a enteros"""
        numero_texto = numero_texto.strip().lower()
        
        # Casos especiales para números compuestos
        if 'treinta y' in numero_texto:
            partes = numero_texto.split('y')
            if len(partes) == 2:
                unidad = self.numeros_escritos.get(partes[1].strip(), 0)
                return 30 + unidad
        
        return self.numeros_escritos.get(numero_texto, None)

    def _convertir_ano_escrito(self, ano_texto: str) -> int:
        """Convierte años escritos a enteros"""
        ano_texto = ano_texto.strip().lower()
        return self.anos_escritos.get(ano_texto, None)

    def analizar_documento_completo(self, texto: str) -> Dict:
        """Analiza todo el documento y extrae todos los patrones"""
        try:
            resultado = {
                'fechas': self.extraer_fechas_avanzadas(texto),
                'nombres': self.extraer_nombres_completos(texto),
                'direcciones': self.extraer_direcciones_completas(texto),
                'lugares': self.extraer_lugares_geograficos(texto),
                'estadisticas': {
                    'total_fechas': 0,
                    'total_nombres': 0,
                    'total_direcciones': 0,
                    'total_lugares': 0
                }
            }
            
            # Calcular estadísticas
            resultado['estadisticas']['total_fechas'] = len(resultado['fechas'])
            resultado['estadisticas']['total_nombres'] = len(resultado['nombres'])
            resultado['estadisticas']['total_direcciones'] = len(resultado['direcciones'])
            resultado['estadisticas']['total_lugares'] = len(resultado['lugares'])
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error en análisis completo: {str(e)}")
            return {
                'fechas': [],
                'nombres': [],
                'direcciones': [],
                'lugares': [],
                'estadisticas': {'total_fechas': 0, 'total_nombres': 0, 'total_direcciones': 0, 'total_lugares': 0},
                'error': str(e)
            }