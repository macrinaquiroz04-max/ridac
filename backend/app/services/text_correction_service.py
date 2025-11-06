# backend/app/services/text_correction_service.py

import re
from typing import Dict, List, Tuple, Optional
from app.utils.logger import logger

class TextCorrectionService:
    """Servicio para corrección automática de texto extraído por OCR"""

    def __init__(self):
        # Diccionario de correcciones comunes en documentos legales
        self.correcciones_legales = {
            # Palabras legales comunes mal interpretadas
            'MINISTERIO PUBLICO': 'MINISTERIO PÚBLICO',
            'MINISTERIO P BLICO': 'MINISTERIO PÚBLICO',
            'MINISTERIO PÚ8LICO': 'MINISTERIO PÚBLICO',
            'FlSCALlA': 'FISCALÍA',
            'F1SCALIA': 'FISCALÍA',
            'FISCAL|A': 'FISCALÍA',
            'CARPETA DE |NVESTIGACION': 'CARPETA DE INVESTIGACIÓN',
            'CARPETA DE INVESTIGAC|ON': 'CARPETA DE INVESTIGACIÓN',
            'CARPETA DE INVESTIGAC10N': 'CARPETA DE INVESTIGACIÓN',
            'AVER|GUACION': 'AVERIGUACIÓN',
            'AVER1GUACION': 'AVERIGUACIÓN',
            'DECLARAC|ON': 'DECLARACIÓN',
            'DECLARAC1ON': 'DECLARACIÓN',
            'COMPARECENC|A': 'COMPARECENCIA',
            'COMPARECENC1A': 'COMPARECENCIA',
            'DICTAMEN': 'DICTAMEN',
            'D|CTAMEN': 'DICTAMEN',
            'D1CTAMEN': 'DICTAMEN',
            'PERICIAL': 'PERICIAL',
            'PER|CIAL': 'PERICIAL',
            'PER1CIAL': 'PERICIAL',
            'TESTIGO': 'TESTIGO',
            'TEST|GO': 'TESTIGO',
            'TEST1GO': 'TESTIGO',
            'OFICIO': 'OFICIO',
            'OF|CIO': 'OFICIO',
            'OF1CIO': 'OFICIO',
            'DILIGENCIA': 'DILIGENCIA',
            'D|LIGENCIA': 'DILIGENCIA',
            'D1LIGENCIA': 'DILIGENCIA',
            
            # Fechas y números comunes
            'ENERO': 'ENERO',
            'FEBRERO': 'FEBRERO',
            'MARZO': 'MARZO',
            'ABRIL': 'ABRIL',
            'MAYO': 'MAYO',
            'JUNIO': 'JUNIO',
            'JULIO': 'JULIO',
            'AGOSTO': 'AGOSTO',
            'SEPTIEMBRE': 'SEPTIEMBRE',
            'OCTUBRE': 'OCTUBRE',
            'NOVIEMBRE': 'NOVIEMBRE',
            'DICIEMBRE': 'DICIEMBRE',
            
            # Correcciones de números/letras
            '0': 'O',  # En contextos de letras
            '1': 'I',  # En contextos de letras
            '5': 'S',  # En contextos de letras
            '8': 'B',  # En contextos de letras
            '9': 'g',  # En contextos de letras minúsculas
            
            # Instituciones
            'CIUDAD DE MEX|CO': 'CIUDAD DE MÉXICO',
            'CIUDAD DE MEX1CO': 'CIUDAD DE MÉXICO',
            'CDMX': 'CDMX',
            'FGJCDMX': 'FGJCDMX',
            'PGJ': 'PGJ',
            'PGJDF': 'PGJDF',
            
            # Palabras comunes mal interpretadas
            'QUE': 'QUE',
            'Q_UE': 'QUE',
            'Q UE': 'QUE',
            'QUIEN': 'QUIEN',
            'QU|EN': 'QUIEN',
            'QU1EN': 'QUIEN',
            'CUANDO': 'CUANDO',
            'CUAND0': 'CUANDO',
            'DONDE': 'DONDE',
            'D0NDE': 'DONDE',
            'COMO': 'COMO',
            'C0MO': 'COMO',
            'PORQUE': 'PORQUE',
            'P0RQUE': 'PORQUE',
            'PORQU_E': 'PORQUE',
        }
        
        # Patrones para corrección contextual
        self.patrones_contexto = [
            # Corrección de l/I en contextos específicos
            (r'\bIa\b', 'la'),
            (r'\bIe\b', 'le'),
            (r'\bIo\b', 'lo'),
            (r'\bIos\b', 'los'),
            (r'\bIas\b', 'las'),
            (r'\bIes\b', 'les'),
            (r'\bI\s+(?=[a-záéíóúñ])', 'l '),  # I espaciada antes de minúscula
            
            # Corrección de O/0 en contextos específicos
            (r'\b0(?=[a-záéíóúñ])', 'o'),  # 0 seguido de minúscula
            (r'(?<=[a-záéíóúñ])0\b', 'o'),  # 0 precedido de minúscula
            
            # Corrección de fechas
            (r'(\d{1,2})/0(\d)', r'\1/\2'),  # 01/02 -> 1/2
            (r'(\d{1,2})-0(\d)', r'\1-\2'),  # 01-02 -> 1-2
            
            # Corrección de horas
            (r'(\d{1,2}):0(\d)', r'\1:\2'),  # 01:02 -> 1:02
            
            # Espaciado incorrecto
            (r'([A-ZÁÉÍÓÚÑ])\s+([a-záéíóúñ])', r'\1\2'),  # Letra mayúscula espaciada con minúscula
            (r'([a-záéíóúñ])\s+([A-ZÁÉÍÓÚÑ])', r'\1 \2'),  # Preservar espacio antes de mayúscula
            
            # Signos de puntuación mal espaciados
            (r'\s+([,;:.!?])', r'\1'),  # Quitar espacio antes de puntuación
            (r'([,;:.!?])\s*([A-ZÁÉÍÓÚÑ])', r'\1 \2'),  # Asegurar espacio después de puntuación
            
            # Números mal interpretados en nombres
            (r'\b1([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)', r'I\1'),  # 1osé -> José
            (r'\b0([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)', r'O\1'),  # 0scar -> Oscar
            
            # Corrección de artículos
            (r'\bIa\s+(?=[A-ZÁÉÍÓÚÑ])', 'la '),  # Ia CASA -> la CASA
            (r'\bIos\s+(?=[A-ZÁÉÍÓÚÑ])', 'los '),  # Ios HECHOS -> los HECHOS
        ]

    def corregir_texto(self, texto: str, contexto: str = "legal") -> str:
        """
        Corrige errores comunes de OCR en el texto
        
        Args:
            texto: Texto a corregir
            contexto: Contexto del documento (legal, general)
        
        Returns:
            Texto corregido
        """
        if not texto:
            return texto
        
        texto_corregido = texto
        
        try:
            # 1. Correcciones de diccionario
            texto_corregido = self._aplicar_correcciones_diccionario(texto_corregido)
            
            # 2. Correcciones por patrones contextuales
            texto_corregido = self._aplicar_correcciones_contextuales(texto_corregido)
            
            # 3. Correcciones específicas del contexto
            if contexto == "legal":
                texto_corregido = self._correcciones_legales_especificas(texto_corregido)
            
            # 4. Limpieza final
            texto_corregido = self._limpieza_final(texto_corregido)
            
            logger.debug(f"Texto corregido exitosamente")
            
        except Exception as e:
            logger.warning(f"Error en corrección de texto: {e}")
            return texto  # Devolver texto original si hay error
        
        return texto_corregido

    def _aplicar_correcciones_diccionario(self, texto: str) -> str:
        """Aplica correcciones basadas en diccionario"""
        for incorrecto, correcto in self.correcciones_legales.items():
            # Corrección exacta de palabras completas
            patron = r'\b' + re.escape(incorrecto) + r'\b'
            texto = re.sub(patron, correcto, texto, flags=re.IGNORECASE)
        
        return texto

    def _aplicar_correcciones_contextuales(self, texto: str) -> str:
        """Aplica correcciones basadas en patrones contextuales"""
        for patron, reemplazo in self.patrones_contexto:
            texto = re.sub(patron, reemplazo, texto)
        
        return texto

    def _correcciones_legales_especificas(self, texto: str) -> str:
        """Aplicar correcciones específicas para documentos legales"""
        
        # Corrección de formatos de carpeta de investigación
        texto = re.sub(
            r'C[|I1]\s*-\s*[A-Z]+\s*-\s*[A-Z]+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+\s*-\s*\d+',
            lambda m: self._corregir_carpeta_investigacion(m.group()),
            texto
        )
        
        # Corrección de números de oficio
        texto = re.sub(
            r'[A-Z]+[/|\\][A-Z]*\d+[/|\\]\d+',
            lambda m: self._corregir_numero_oficio(m.group()),
            texto
        )
        
        # Corrección de fechas en formato dd/mm/yyyy
        texto = re.sub(
            r'\b(\d{1,2})[/|\\](\d{1,2})[/|\\](\d{4})\b',
            lambda m: f"{m.group(1)}/{m.group(2)}/{m.group(3)}",
            texto
        )
        
        # Corrección de nombres propios comunes en el ámbito legal
        nombres_comunes = {
            'IOSE': 'JOSE',
            'IUAN': 'JUAN',
            'MARIA': 'MARIA',
            'CARLOS': 'CARLOS',
            'ANA': 'ANA',
            'LUIS': 'LUIS',
            'MIGUEL': 'MIGUEL',
            'PEDRO': 'PEDRO',
            'FRANCISCO': 'FRANCISCO',
            'ANTONIO': 'ANTONIO',
            'MANUEL': 'MANUEL',
            'RAFAEL': 'RAFAEL'
        }
        
        for incorrecto, correcto in nombres_comunes.items():
            texto = re.sub(r'\b' + incorrecto + r'\b', correcto, texto)
        
        return texto

    def _corregir_carpeta_investigacion(self, carpeta: str) -> str:
        """Corrige formato de carpeta de investigación"""
        # Limpiar caracteres mal interpretados
        carpeta = carpeta.replace('|', 'I').replace('1', 'I')
        carpeta = re.sub(r'\s+', '-', carpeta)  # Normalizar espacios a guiones
        return carpeta

    def _corregir_numero_oficio(self, oficio: str) -> str:
        """Corrige formato de número de oficio"""
        # Normalizar separadores
        oficio = oficio.replace('|', '/').replace('\\', '/')
        return oficio

    def _limpieza_final(self, texto: str) -> str:
        """Limpieza final del texto"""
        # Eliminar espacios múltiples
        texto = re.sub(r'\s+', ' ', texto)
        
        # Eliminar espacios al inicio/final de líneas
        lineas = [linea.strip() for linea in texto.split('\n')]
        texto = '\n'.join(lineas)
        
        # Eliminar líneas vacías múltiples
        texto = re.sub(r'\n\s*\n\s*\n', '\n\n', texto)
        
        return texto.strip()

    def validar_calidad_correccion(self, texto_original: str, texto_corregido: str) -> Dict[str, any]:
        """Valida la calidad de la corrección aplicada"""
        
        # Calcular métricas de cambio
        palabras_originales = len(texto_original.split())
        palabras_corregidas = len(texto_corregido.split())
        
        # Contar cambios realizados
        cambios = self._contar_cambios(texto_original, texto_corregido)
        
        # Calcular porcentaje de cambio
        porcentaje_cambio = (cambios / palabras_originales * 100) if palabras_originales > 0 else 0
        
        # Evaluar calidad
        calidad = "excelente"
        if porcentaje_cambio > 20:
            calidad = "alta_modificacion"
        elif porcentaje_cambio > 10:
            calidad = "moderada"
        elif porcentaje_cambio < 1:
            calidad = "minima"
        
        return {
            "palabras_originales": palabras_originales,
            "palabras_corregidas": palabras_corregidas,
            "cambios_realizados": cambios,
            "porcentaje_cambio": round(porcentaje_cambio, 2),
            "calidad": calidad,
            "confianza_correccion": max(50, 100 - porcentaje_cambio * 2)
        }

    def _contar_cambios(self, texto1: str, texto2: str) -> int:
        """Cuenta el número de cambios entre dos textos"""
        palabras1 = texto1.split()
        palabras2 = texto2.split()
        
        cambios = 0
        max_len = max(len(palabras1), len(palabras2))
        
        for i in range(max_len):
            palabra1 = palabras1[i] if i < len(palabras1) else ""
            palabra2 = palabras2[i] if i < len(palabras2) else ""
            
            if palabra1 != palabra2:
                cambios += 1
        
        return cambios

    def obtener_sugerencias_mejora(self, texto: str) -> List[Dict[str, str]]:
        """Obtiene sugerencias para mejorar la calidad del texto"""
        sugerencias = []
        
        # Detectar posibles errores no corregidos
        if re.search(r'[|]', texto):
            sugerencias.append({
                "tipo": "caracter_especial",
                "descripcion": "Se detectaron caracteres '|' que podrían ser 'I' o 'l'",
                "sugerencia": "Revisar manualmente estos caracteres"
            })
        
        if re.search(r'\b[0-9]+[a-zA-Z]', texto):
            sugerencias.append({
                "tipo": "numero_letra",
                "descripcion": "Se detectaron números seguidos de letras",
                "sugerencia": "Verificar si son errores de OCR (ej: 1osé por José)"
            })
        
        if re.search(r'[A-Z]{10,}', texto):
            sugerencias.append({
                "tipo": "mayusculas_excesivas",
                "descripcion": "Se detectaron secuencias largas de mayúsculas",
                "sugerencia": "Verificar si es el formato correcto del documento"
            })
        
        # Detectar posibles fechas mal formateadas
        fechas_raras = re.findall(r'\b\d{1,2}[/\\]\d{1,2}[/\\]\d{2,4}\b', texto)
        if fechas_raras:
            sugerencias.append({
                "tipo": "formato_fecha",
                "descripcion": f"Se detectaron {len(fechas_raras)} fechas con formato inconsistente",
                "sugerencia": "Verificar formato de fechas encontradas"
            })
        
        return sugerencias