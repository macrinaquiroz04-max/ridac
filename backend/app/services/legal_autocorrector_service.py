"""
Servicio de autocorrección legal para documentos OCR
Corrige errores comunes en:
- Alcaldías de CDMX
- Colonias
- Términos legales
- Direcciones
"""

import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher


class LegalAutocorrectorService:
    """Servicio de corrección automática de errores OCR en documentos legales"""
    
    # 16 Alcaldías de CDMX
    ALCALDIAS_CDMX = {
        'ÁLVARO OBREGÓN': ['alvaro obregon', 'a obregon', 'alv obregon', 'alvaro ovregon'],
        'AZCAPOTZALCO': ['azcapotzalco', 'azcapotzaico', 'azcapotsalco', 'azcapozalco'],
        'BENITO JUÁREZ': ['benito juarez', 'b juarez', 'ben juarez', 'venito juarez'],
        'COYOACÁN': ['coyoacan', 'coyoac', 'coyoacen', 'coyoacàn'],
        'CUAJIMALPA': ['cuajimalpa', 'cuajimaipa', 'cuajimapa', 'cuajimalp'],
        'CUAUHTÉMOC': ['cuauhtemoc', 'cuauhtemoc', 'cuautemoc', 'cuauthemoc', 'cuauhtemock', 'cuauhtemoc.'],
        'GUSTAVO A. MADERO': ['gustavo a madero', 'g a madero', 'gam', 'gustavo madero'],
        'IZTACALCO': ['iztacalco', 'iztacaico', 'iztakalco', 'istakalco'],
        'IZTAPALAPA': ['iztapalapa', 'iztapaapa', 'iztapalap', 'istapalapa'],
        'MAGDALENA CONTRERAS': ['magdalena contreras', 'la magdalena contreras', 'mag contreras'],
        'MIGUEL HIDALGO': ['miguel hidalgo', 'm hidalgo', 'mig hidalgo', 'miguel hidaigo'],
        'MILPA ALTA': ['milpa alta', 'miipa alta', 'milp alta'],
        'TLÁHUAC': ['tlahuac', 'tláhuac', 'tlahuak', 'tiahuac'],
        'TLALPAN': ['tlalpan', 'tialpan', 'tlalpam', 'tlalp'],
        'VENUSTIANO CARRANZA': ['venustiano carranza', 'v carranza', 'ven carranza', 'venustiano carran'],
        'XOCHIMILCO': ['xochimilco', 'xochimilko', 'xochimico', 'sochimilco']
    }
    
    # Colonias más comunes (se puede ampliar)
    COLONIAS_COMUNES = {
        'CONDESA': ['condesa', 'condes', 'condezza', 'cplonia condesa', 'hina condesa'],
        'ROMA': ['roma', 'rom', 'roman'],
        'POLANCO': ['polanco', 'polanico', 'polanko'],
        'SANTA MARÍA LA RIBERA': ['santa maria la ribera', 'sta maria la ribera', 'sta. maria la ribera', 'maria la ribera'],
        'DEL VALLE': ['del valle', 'd valle', 'dei valle'],
        'NARVARTE': ['narvarte', 'narv', 'narbarte'],
        'DOCTORES': ['doctores', 'doctor', 'doctres'],
        'GUERRERO': ['guerrero', 'guerr', 'gro'],
        'CENTRO': ['centro', 'centró', 'cen'],
        'JUÁREZ': ['juarez', 'juárez', 'juares']
    }
    
    # Términos legales comunes
    TERMINOS_LEGALES = {
        'MINISTERIO PÚBLICO': ['ministerio publico', 'min publico', 'mp', 'ministério publico'],
        'AVERIGUACIÓN PREVIA': ['averiguacion previa', 'av previa', 'aver previa'],
        'CARPETA DE INVESTIGACIÓN': ['carpeta de investigacion', 'carpeta inv', 'c.i.'],
        'CONSTITUCIÓN POLÍTICA': ['constitucion politica', 'constithcion politica', 'const politica'],
        'CÓDIGO PENAL': ['codigo penal', 'cod penal', 'c.p.'],
        'CÓDIGO PROCESAL PENAL': ['codigo procesal penal', 'cpp', 'c.p.p.'],
        'DECLARACIÓN': ['declaracion', 'declaracíon', 'deciaración'],
        'COMPARECENCIA': ['comparecencia', 'comparencencia', 'compareciencia'],
        'ENTREVISTA': ['entrevista', 'entrevist', 'entrebista'],
        'ACUERDO': ['acuerdo', 'acuerd', 'akuerdo'],
        'OFICIO': ['oficio', 'ofici', 'ofisio'],
        'FISCALÍA': ['fiscalia', 'físcalia', 'fiscal'],
        'PROCURADURÍA': ['procuraduria', 'proc', 'pgj'],
        'CIUDAD DE MÉXICO': ['ciudad de mexico', 'cdmx', 'cd mexico', 'ciudad mexico']
    }
    
    # Errores comunes de OCR
    ERRORES_OCR_COMUNES = {
        'cplonia': 'colonia',
        'hina': '',  # Ruido OCR
        'constithcion': 'constitución',
        'ciudadano': 'ciudadano',
        'ciudadanop': 'ciudadano',
        'alcaldia': 'alcaldía',
        'coloni': 'colonia',
        'nunmero': 'número',
        'sunmero': 'número',
        'gsabriel': 'gabriel',
        'ochoterena': 'ochoterena',
        'sin numnero': 'sin número',
        'sin nunmero': 'sin número'
    }
    
    def __init__(self):
        """Inicializar el corrector"""
        # Crear diccionario inverso para búsqueda rápida
        self._alcaldias_map = self._create_reverse_map(self.ALCALDIAS_CDMX)
        self._colonias_map = self._create_reverse_map(self.COLONIAS_COMUNES)
        self._terminos_map = self._create_reverse_map(self.TERMINOS_LEGALES)
    
    def _create_reverse_map(self, original_dict: Dict[str, List[str]]) -> Dict[str, str]:
        """Crear mapa inverso para búsqueda rápida"""
        reverse = {}
        for correcto, variantes in original_dict.items():
            reverse[correcto.lower()] = correcto
            for variante in variantes:
                reverse[variante.lower()] = correcto
        return reverse
    
    def similarity(self, a: str, b: str) -> float:
        """Calcular similitud entre dos strings (0-1)"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def corregir_alcaldia(self, texto: str) -> Tuple[str, bool]:
        """
        Corregir nombre de alcaldía
        Returns: (texto_corregido, fue_corregido)
        """
        texto_lower = texto.lower().strip()
        
        # Busqueda exacta en el mapa
        if texto_lower in self._alcaldias_map:
            return self._alcaldias_map[texto_lower], True
        
        # Búsqueda por similitud (>= 0.8)
        mejor_match = None
        mejor_similitud = 0.8  # Umbral mínimo
        
        for alcaldia_correcta in self.ALCALDIAS_CDMX.keys():
            sim = self.similarity(texto, alcaldia_correcta)
            if sim > mejor_similitud:
                mejor_similitud = sim
                mejor_match = alcaldia_correcta
        
        if mejor_match:
            return mejor_match, True
        
        return texto, False
    
    def corregir_colonia(self, texto: str) -> Tuple[str, bool]:
        """
        Corregir nombre de colonia
        Returns: (texto_corregido, fue_corregido)
        """
        if not texto:
            return texto, False
        
        texto_lower = texto.lower().strip()
        
        # Limpiar errores comunes de OCR primero
        for error, correccion in self.ERRORES_OCR_COMUNES.items():
            if error in texto_lower:
                texto_lower = texto_lower.replace(error, correccion)
                texto = texto_lower.title()
        
        # Busqueda exacta
        if texto_lower in self._colonias_map:
            return self._colonias_map[texto_lower], True
        
        # Búsqueda por similitud
        mejor_match = None
        mejor_similitud = 0.75
        
        for colonia_correcta in self.COLONIAS_COMUNES.keys():
            sim = self.similarity(texto_lower, colonia_correcta.lower())
            if sim > mejor_similitud:
                mejor_similitud = sim
                mejor_match = colonia_correcta
        
        if mejor_match:
            return mejor_match, True
        
        # Si no se encontró match, al menos limpiar errores OCR
        texto_limpio = ' '.join(texto.split()).title()
        return texto_limpio, (texto_limpio != texto)
    
    def corregir_termino_legal(self, texto: str) -> Tuple[str, bool]:
        """
        Corregir término legal
        Returns: (texto_corregido, fue_corregido)
        """
        texto_lower = texto.lower().strip()
        
        # Busqueda exacta
        if texto_lower in self._terminos_map:
            return self._terminos_map[texto_lower], True
        
        # Búsqueda por similitud
        mejor_match = None
        mejor_similitud = 0.8
        
        for termino_correcto in self.TERMINOS_LEGALES.keys():
            sim = self.similarity(texto_lower, termino_correcto.lower())
            if sim > mejor_similitud:
                mejor_similitud = sim
                mejor_match = termino_correcto
        
        if mejor_match:
            return mejor_match, True
        
        return texto, False
    
    def corregir_direccion(self, direccion: str) -> Tuple[str, bool, Dict[str, any]]:
        """
        Corregir dirección completa
        Returns: (direccion_corregida, fue_corregida, detalles)
        """
        if not direccion:
            return direccion, False, {}
        
        original = direccion
        correcciones = []
        
        # Limpiar errores OCR comunes
        for error, correccion in self.ERRORES_OCR_COMUNES.items():
            if error in direccion.lower():
                direccion = re.sub(re.escape(error), correccion, direccion, flags=re.IGNORECASE)
                correcciones.append(f"'{error}' → '{correccion}'")
        
        # Normalizar espacios múltiples
        direccion = ' '.join(direccion.split())
        
        # Capitalización correcta de palabras comunes
        palabras_mayusculas = ['C.', 'AV.', 'AVENIDA', 'CALLE', 'CALZADA', 'PRIVADA', 'ANDADOR']
        for palabra in palabras_mayusculas:
            direccion = re.sub(rf'\b{palabra}\b', palabra.upper(), direccion, flags=re.IGNORECASE)
        
        detalles = {
            'original': original,
            'corregida': direccion,
            'correcciones': correcciones,
            'cambios': len(correcciones)
        }
        
        fue_corregida = (original != direccion)
        return direccion, fue_corregida, detalles
    
    def corregir_texto_completo(self, texto: str) -> Dict[str, any]:
        """
        Corregir un texto completo (puede contener múltiples elementos)
        Returns: diccionario con resultados detallados
        """
        if not texto:
            return {
                'texto_original': texto,
                'texto_corregido': texto,
                'correcciones_realizadas': [],
                'total_correcciones': 0
            }
        
        texto_corregido = texto
        correcciones = []
        
        # 1. Corregir alcaldías
        for alcaldia_correcta, variantes in self.ALCALDIAS_CDMX.items():
            for variante in variantes:
                if variante in texto_corregido.lower():
                    patron = re.compile(re.escape(variante), re.IGNORECASE)
                    if patron.search(texto_corregido):
                        texto_corregido = patron.sub(alcaldia_correcta, texto_corregido)
                        correcciones.append({
                            'tipo': 'alcaldia',
                            'original': variante,
                            'corregido': alcaldia_correcta
                        })
        
        # 2. Corregir colonias
        for colonia_correcta, variantes in self.COLONIAS_COMUNES.items():
            for variante in variantes:
                if variante in texto_corregido.lower():
                    patron = re.compile(re.escape(variante), re.IGNORECASE)
                    if patron.search(texto_corregido):
                        texto_corregido = patron.sub(colonia_correcta, texto_corregido)
                        correcciones.append({
                            'tipo': 'colonia',
                            'original': variante,
                            'corregido': colonia_correcta
                        })
        
        # 3. Corregir términos legales
        for termino_correcto, variantes in self.TERMINOS_LEGALES.items():
            for variante in variantes:
                if variante in texto_corregido.lower():
                    patron = re.compile(re.escape(variante), re.IGNORECASE)
                    if patron.search(texto_corregido):
                        texto_corregido = patron.sub(termino_correcto, texto_corregido)
                        correcciones.append({
                            'tipo': 'termino_legal',
                            'original': variante,
                            'corregido': termino_correcto
                        })
        
        # 4. Corregir errores OCR comunes
        for error, correccion in self.ERRORES_OCR_COMUNES.items():
            if error in texto_corregido.lower():
                patron = re.compile(re.escape(error), re.IGNORECASE)
                if patron.search(texto_corregido):
                    texto_corregido = patron.sub(correccion, texto_corregido)
                    correcciones.append({
                        'tipo': 'error_ocr',
                        'original': error,
                        'corregido': correccion
                    })
        
        return {
            'texto_original': texto,
            'texto_corregido': texto_corregido,
            'correcciones_realizadas': correcciones,
            'total_correcciones': len(correcciones),
            'fue_corregido': (texto != texto_corregido)
        }
    
    def detectar_duplicados(
        self, 
        registros: List[Dict], 
        campos_comparar: List[str] = ['tipo_diligencia', 'fecha_diligencia', 'responsable'],
        umbral_similitud: float = 0.9
    ) -> List[List[int]]:
        """
        Detectar registros duplicados
        Returns: lista de grupos de IDs duplicados
        """
        if not registros:
            return []
        
        duplicados = []
        procesados = set()
        
        for i, reg1 in enumerate(registros):
            if i in procesados:
                continue
            
            grupo_duplicados = [i]
            
            for j, reg2 in enumerate(registros):
                if i >= j or j in procesados:
                    continue
                
                # Comparar campos
                similitud_total = 0
                campos_validos = 0
                
                for campo in campos_comparar:
                    val1 = str(reg1.get(campo, '')).lower().strip()
                    val2 = str(reg2.get(campo, '')).lower().strip()
                    
                    if val1 and val2:
                        sim = self.similarity(val1, val2)
                        similitud_total += sim
                        campos_validos += 1
                
                if campos_validos > 0:
                    similitud_promedio = similitud_total / campos_validos
                    
                    if similitud_promedio >= umbral_similitud:
                        grupo_duplicados.append(j)
                        procesados.add(j)
            
            if len(grupo_duplicados) > 1:
                duplicados.append(grupo_duplicados)
                procesados.add(i)
        
        return duplicados


# Instancia global del corrector
legal_autocorrector = LegalAutocorrectorService()
