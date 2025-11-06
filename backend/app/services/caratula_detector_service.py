# backend/app/services/caratula_detector_service.py

import re
from typing import Dict, List, Tuple
from app.utils.logger import logger

class CaratulaDetectorService:
    """
    Servicio para detectar y filtrar páginas de carátula/portada
    que no contienen información relevante del caso
    """
    
    def __init__(self):
        # Patrones que indican que es una carátula
        self.patrones_caratula = [
            # Texto típico de carátulas
            r'^\s*TOMO\s*\d+\s*$',
            r'^\s*PÁGINA\s*\d+\s*DE\s*TOMO\s*\d+\s*$',
            r'^\s*PÁGINA\s*\d+\s*$',
            r'^\s*EXPEDIENTE\s*$',
            r'^\s*PORTADA\s*$',
            r'^\s*CARÁTULA\s*$',
            
            # Encabezados genéricos
            r'^\s*ÍNDICE\s*$',
            r'^\s*CONTENIDO\s*$',
            r'^\s*TABLA\s+DE\s+CONTENIDO\s*$',
            
            # Separadores
            r'^[-=_\s]+$',
            r'^\s*\*+\s*$',
        ]
        
        # Palabras clave que indican contenido real
        self.palabras_clave_contenido = [
            'FISCALÍA',
            'AGENCIA',
            'INVESTIGACIÓN',
            'CARPETA',
            'DELITO',
            'VICTIMA',
            'IMPUTADO',
            'MINISTERIO PÚBLICO',
            'DECLARACIÓN',
            'TESTIMONIO',
            'DILIGENCIA',
            'ACTUACIÓN',
            'FECHA',
            'HORA',
            'LUGAR',
            'HECHOS',
            'NARRACIÓN',
        ]
        
        # Compilar patrones
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) 
            for p in self.patrones_caratula
        ]
    
    def es_caratula(self, texto: str, numero_pagina: int = None) -> Tuple[bool, str]:
        """
        Determina si una página es una carátula o contiene información real
        
        Args:
            texto: Texto extraído de la página
            numero_pagina: Número de página (opcional)
        
        Returns:
            (es_caratula, razon)
            - es_caratula: True si es carátula, False si es contenido real
            - razon: Explicación de por qué se consideró carátula
        """
        if not texto or not texto.strip():
            return True, "Página vacía o sin texto"
        
        # Limpiar texto
        texto_limpio = texto.strip()
        lineas = [l.strip() for l in texto_limpio.split('\n') if l.strip()]
        
        # Si tiene muy pocas líneas, probablemente es carátula
        if len(lineas) < 3:
            # Verificar si alguna línea coincide con patrones de carátula
            for linea in lineas:
                for pattern in self.compiled_patterns:
                    if pattern.match(linea):
                        return True, f"Coincide con patrón de carátula: '{linea}'"
            
            # Si solo tiene números de página
            if all(self._es_solo_numero_pagina(l) for l in lineas):
                return True, "Solo contiene números de página"
        
        # Verificar si contiene palabras clave de contenido real
        texto_upper = texto_limpio.upper()
        palabras_encontradas = sum(
            1 for palabra in self.palabras_clave_contenido 
            if palabra in texto_upper
        )
        
        if palabras_encontradas >= 2:
            return False, f"Contiene {palabras_encontradas} palabras clave de contenido real"
        
        # Si tiene más de 100 palabras, probablemente es contenido real
        palabras_totales = len(texto_limpio.split())
        if palabras_totales > 100:
            return False, f"Contiene {palabras_totales} palabras (suficiente contenido)"
        
        # Verificar densidad de texto
        if self._tiene_densidad_baja(texto_limpio):
            return True, "Densidad de texto muy baja (probablemente carátula)"
        
        # Si llegamos aquí y tiene contenido significativo, no es carátula
        if palabras_totales > 50:
            return False, f"Contiene {palabras_totales} palabras de contenido"
        
        # Por defecto, si tiene menos de 50 palabras y no tiene palabras clave, es carátula
        return True, f"Texto muy corto ({palabras_totales} palabras) sin palabras clave"
    
    def _es_solo_numero_pagina(self, texto: str) -> bool:
        """Verifica si el texto es solo un número de página"""
        # Eliminar espacios y guiones
        texto_limpio = texto.replace(' ', '').replace('-', '')
        
        # Patrones de número de página
        patrones = [
            r'^\d+$',  # Solo número
            r'^PÁGINA\d+$',
            r'^PÁG\.\d+$',
            r'^P\.\d+$',
        ]
        
        for patron in patrones:
            if re.match(patron, texto_limpio, re.IGNORECASE):
                return True
        
        return False
    
    def _tiene_densidad_baja(self, texto: str) -> bool:
        """
        Verifica si el texto tiene densidad muy baja
        (muchos espacios en blanco, pocas palabras)
        """
        if not texto:
            return True
        
        palabras = len(texto.split())
        caracteres = len(texto)
        
        if caracteres == 0:
            return True
        
        # Densidad = palabras / caracteres
        densidad = palabras / caracteres
        
        # Si la densidad es muy baja, probablemente es carátula
        return densidad < 0.05  # Menos de 5% de densidad
    
    def analizar_tomo_completo(self, contenidos_ocr: List[Dict]) -> Dict:
        """
        Analiza un tomo completo y clasifica cada página
        
        Args:
            contenidos_ocr: Lista de diccionarios con:
                {
                    'numero_pagina': int,
                    'texto_extraido': str
                }
        
        Returns:
            {
                'total_paginas': int,
                'paginas_caratula': int,
                'paginas_contenido': int,
                'paginas_ignoradas': List[int],
                'analisis': List[Dict]
            }
        """
        resultado = {
            'total_paginas': len(contenidos_ocr),
            'paginas_caratula': 0,
            'paginas_contenido': 0,
            'paginas_ignoradas': [],
            'analisis': []
        }
        
        for contenido in contenidos_ocr:
            numero_pagina = contenido.get('numero_pagina')
            texto = contenido.get('texto_extraido', '')
            
            es_caratula, razon = self.es_caratula(texto, numero_pagina)
            
            analisis_pagina = {
                'numero_pagina': numero_pagina,
                'es_caratula': es_caratula,
                'razon': razon,
                'palabras': len(texto.split()) if texto else 0,
                'caracteres': len(texto) if texto else 0
            }
            
            resultado['analisis'].append(analisis_pagina)
            
            if es_caratula:
                resultado['paginas_caratula'] += 1
                resultado['paginas_ignoradas'].append(numero_pagina)
            else:
                resultado['paginas_contenido'] += 1
        
        logger.info(
            f"Análisis de tomo: {resultado['paginas_contenido']} páginas de contenido, "
            f"{resultado['paginas_caratula']} carátulas ignoradas"
        )
        
        return resultado
    
    def filtrar_contenido_real(self, contenidos_ocr: List[Dict]) -> List[Dict]:
        """
        Filtra y retorna solo las páginas con contenido real
        
        Args:
            contenidos_ocr: Lista de contenidos OCR
        
        Returns:
            Lista filtrada solo con páginas de contenido real
        """
        contenido_filtrado = []
        
        for contenido in contenidos_ocr:
            texto = contenido.get('texto_extraido', '')
            es_caratula, razon = self.es_caratula(texto)
            
            if not es_caratula:
                contenido_filtrado.append(contenido)
            else:
                logger.debug(
                    f"Página {contenido.get('numero_pagina')} ignorada: {razon}"
                )
        
        return contenido_filtrado


# Instancia global
caratula_detector = CaratulaDetectorService()
