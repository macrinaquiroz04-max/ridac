"""
Servicio para extraer párrafos estructurados del texto OCR
Identifica bloques de texto que contienen información legal relevante
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date

logger = logging.getLogger(__name__)


class ExtractorParrafosEstructurados:
    """Extrae párrafos completos con estructura legal"""
    
    # Palabras clave que indican inicio de bloque relevante
    INICIO_BLOQUE = [
        r'^(EN|POR)\s+(ESTE|EL\s+PRESENTE|MEDIO\s+DEL?\s+CUAL)',
        r'^(MEDIO\s+DEL?\s+CUAL)',
        r'^(SE\s+(HACE\s+CONSTAR|INFORMA|SOLICITA|ORDENA))',
        r'^(C\.|CIUDADAN[AO]|LIC\.|DR\.|DRA\.)',
        r'^(OFICIO\s+(N[ÚU]M|NÚMERO))',
        r'^(ATENTAMENTE)',
        r'^(CARPETA\s+DE\s+INVESTIGACI[ÓO]N)',
        r'^(MINISTERIO\s+P[ÚU]BLICO)',
    ]
    
    # Patrones de separadores de párrafos
    SEPARADORES = [
        r'\n\n+',  # Doble salto de línea o más
        r'\n-{3,}\n',  # Línea de guiones
        r'\n={3,}\n',  # Línea de igual
        r'\n\*{3,}\n',  # Línea de asteriscos
    ]
    
    # Elementos que debe contener un párrafo relevante
    ELEMENTOS_RELEVANTES = {
        'fecha': r'\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}',
        'oficio': r'oficio\s+n[úu]m(?:ero)?\s*[.:]?\s*([A-Z0-9/-]+)',
        'nombre_titular': r'(?:C\.|CIUDADAN[AO]|LIC\.|DR\.|DRA\.)\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ]+){1,4})',
        'carpeta': r'CARPETA\s+DE\s+INVESTIGACI[ÓO]N\s*:?\s*([A-Z0-9/-]+)',
        'delito': r'DELITO\s+DE\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s]+?)(?:\.|,|\n)',
        'unidad': r'UNIDAD\s+DE\s+INVESTIGACI[ÓO]N\s+([A-Z0-9-]+)',
    }
    
    def __init__(self):
        """Inicializar extractor"""
        self.compiled_patterns = {
            key: re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for key, pattern in self.ELEMENTOS_RELEVANTES.items()
        }
    
    def extraer_parrafos_estructurados(
        self,
        texto: str,
        numero_pagina: int,
        min_longitud: int = 100,
        max_longitud: int = 3000
    ) -> List[Dict]:
        """
        Extrae párrafos estructurados del texto
        
        Args:
            texto: Texto completo de la página
            numero_pagina: Número de página
            min_longitud: Longitud mínima del párrafo (caracteres)
            max_longitud: Longitud máxima del párrafo (caracteres)
            
        Returns:
            Lista de párrafos estructurados con metadatos
        """
        if not texto or len(texto.strip()) < min_longitud:
            return []
        
        # Dividir en párrafos
        parrafos_raw = self._dividir_en_parrafos(texto)
        
        # Filtrar y analizar párrafos
        parrafos_estructurados = []
        
        for idx, parrafo_texto in enumerate(parrafos_raw):
            # Limpiar el párrafo
            parrafo_limpio = self._limpiar_parrafo(parrafo_texto)
            
            # Validar longitud
            if len(parrafo_limpio) < min_longitud or len(parrafo_limpio) > max_longitud:
                continue
            
            # Extraer elementos del párrafo
            elementos = self._extraer_elementos(parrafo_limpio)
            
            # Calcular score de relevancia
            relevancia = self._calcular_relevancia(elementos, parrafo_limpio)
            
            # Solo incluir párrafos relevantes
            if relevancia >= 2:  # Al menos 2 elementos relevantes
                parrafo_estructurado = {
                    "numero_parrafo": idx + 1,
                    "numero_pagina": numero_pagina,
                    "texto_completo": parrafo_limpio,
                    "longitud": len(parrafo_limpio),
                    "elementos": elementos,
                    "relevancia": relevancia,
                    "tipo_documento": self._clasificar_tipo_documento(parrafo_limpio, elementos),
                    "resumen": self._generar_resumen(parrafo_limpio, elementos),
                }
                
                parrafos_estructurados.append(parrafo_estructurado)
        
        return parrafos_estructurados
    
    def _dividir_en_parrafos(self, texto: str) -> List[str]:
        """Divide el texto en párrafos usando separadores inteligentes"""
        # Primero intentar con dobles saltos de línea
        parrafos = re.split(r'\n\n+', texto)
        
        # Si hay muy pocos párrafos, intentar con saltos simples más contexto
        if len(parrafos) < 3:
            # Buscar patrones de inicio de bloque
            parrafos = []
            bloques = []
            lineas = texto.split('\n')
            bloque_actual = []
            
            for linea in lineas:
                linea_limpia = linea.strip()
                
                # Verificar si es inicio de nuevo bloque
                es_inicio = any(
                    re.match(patron, linea_limpia, re.IGNORECASE)
                    for patron in self.INICIO_BLOQUE
                )
                
                if es_inicio and bloque_actual:
                    # Guardar bloque anterior
                    bloques.append('\n'.join(bloque_actual))
                    bloque_actual = [linea]
                else:
                    bloque_actual.append(linea)
            
            # Agregar último bloque
            if bloque_actual:
                bloques.append('\n'.join(bloque_actual))
            
            parrafos = bloques if bloques else [texto]
        
        return [p for p in parrafos if p.strip()]
    
    def _limpiar_parrafo(self, texto: str) -> str:
        """Limpia el párrafo de caracteres extraños y espacios innecesarios"""
        # Remover saltos de página
        texto = texto.replace('\f', ' ')
        
        # Normalizar espacios
        texto = re.sub(r'\s+', ' ', texto)
        
        # Remover espacios al inicio y final
        texto = texto.strip()
        
        return texto
    
    def _extraer_elementos(self, parrafo: str) -> Dict:
        """Extrae todos los elementos relevantes del párrafo"""
        elementos = {}
        
        for key, pattern in self.compiled_patterns.items():
            matches = pattern.findall(parrafo)
            if matches:
                # Si hay captura de grupo, usar eso; si no, usar todo el match
                if isinstance(matches[0], tuple):
                    elementos[key] = [m[0].strip() if m[0] else m for m in matches if m]
                else:
                    elementos[key] = [m.strip() for m in matches if m]
        
        # Extraer fechas más precisamente
        fechas_encontradas = self._extraer_fechas_detalladas(parrafo)
        if fechas_encontradas:
            elementos['fechas_detalladas'] = fechas_encontradas
        
        # Extraer nombres adicionales
        nombres_adicionales = self._extraer_nombres_mencionados(parrafo)
        if nombres_adicionales:
            elementos['nombres_mencionados'] = nombres_adicionales
        
        return elementos
    
    def _extraer_fechas_detalladas(self, texto: str) -> List[Dict]:
        """Extrae fechas con su contexto"""
        patron_fecha = r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})'
        
        fechas = []
        for match in re.finditer(patron_fecha, texto, re.IGNORECASE):
            # Extraer contexto alrededor de la fecha
            inicio = max(0, match.start() - 50)
            fin = min(len(texto), match.end() + 50)
            contexto = texto[inicio:fin].strip()
            
            fechas.append({
                'fecha_texto': match.group(0),
                'dia': int(match.group(1)),
                'mes': match.group(2).lower(),
                'anio': int(match.group(3)),
                'contexto': contexto
            })
        
        return fechas
    
    def _extraer_nombres_mencionados(self, texto: str) -> List[str]:
        """Extrae nombres de personas mencionadas (más conservador)"""
        # Patrón para nombres completos (2-4 palabras con mayúsculas)
        patron = r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b'
        
        nombres = []
        palabras_excluir = {
            'MINISTERIO PUBLICO', 'CARPETA DE', 'UNIDAD DE', 'DELITO DE',
            'EN ATENCION', 'POR MEDIO', 'SE HACE', 'OFICIO NUM',
            'DE LA', 'EN LA', 'A LA', 'POR LA', 'CON LA'
        }
        
        for match in re.finditer(patron, texto):
            nombre = match.group(1).strip()
            
            # Validar que no sea una palabra común
            if (len(nombre) >= 10 and  # Al menos 10 caracteres
                nombre.upper() not in palabras_excluir and
                not re.match(r'^(DE|LA|EL|EN|POR|CON|SIN)\s', nombre, re.IGNORECASE)):
                nombres.append(nombre)
        
        # Eliminar duplicados manteniendo orden
        nombres_unicos = []
        for nombre in nombres:
            if nombre not in nombres_unicos:
                nombres_unicos.append(nombre)
        
        return nombres_unicos[:10]  # Máximo 10 nombres
    
    def _calcular_relevancia(self, elementos: Dict, texto: str) -> int:
        """Calcula score de relevancia del párrafo"""
        score = 0
        
        # Puntos por elementos encontrados
        if elementos.get('fecha') or elementos.get('fechas_detalladas'):
            score += 2
        if elementos.get('oficio'):
            score += 2
        if elementos.get('nombre_titular'):
            score += 1
        if elementos.get('carpeta'):
            score += 2
        if elementos.get('delito'):
            score += 1
        if elementos.get('unidad'):
            score += 1
        if elementos.get('nombres_mencionados'):
            score += 1
        
        # Puntos por palabras clave legales
        palabras_clave = [
            'solicita', 'informa', 'ordena', 'se hace constar',
            'atentamente', 'investigación', 'diligencia', 'actuación'
        ]
        
        texto_lower = texto.lower()
        for palabra in palabras_clave:
            if palabra in texto_lower:
                score += 0.5
        
        return int(score)
    
    def _clasificar_tipo_documento(self, texto: str, elementos: Dict) -> str:
        """Clasifica el tipo de documento basado en el contenido"""
        texto_lower = texto.lower()
        
        if elementos.get('oficio'):
            if 'solicita' in texto_lower or 'solicit' in texto_lower:
                return 'oficio_solicitud'
            elif 'informa' in texto_lower or 'informar' in texto_lower:
                return 'oficio_informativo'
            else:
                return 'oficio_general'
        
        if 'se hace constar' in texto_lower:
            return 'constancia'
        
        if 'atentamente' in texto_lower:
            return 'comunicado_oficial'
        
        if elementos.get('delito'):
            return 'acta_hechos'
        
        if 'investigación' in texto_lower:
            return 'actuacion_ministerial'
        
        return 'documento_general'
    
    def _generar_resumen(self, texto: str, elementos: Dict, max_length: int = 200) -> str:
        """Genera un resumen conciso del párrafo"""
        partes_resumen = []
        
        # Agregar tipo de documento
        if elementos.get('oficio'):
            partes_resumen.append(f"Oficio {elementos['oficio'][0]}")
        
        # Agregar fecha
        if elementos.get('fechas_detalladas'):
            fecha = elementos['fechas_detalladas'][0]
            partes_resumen.append(f"del {fecha['fecha_texto']}")
        
        # Agregar carpeta
        if elementos.get('carpeta'):
            partes_resumen.append(f"Carpeta {elementos['carpeta'][0]}")
        
        # Agregar delito
        if elementos.get('delito'):
            delito = elementos['delito'][0][:50]  # Truncar si es muy largo
            partes_resumen.append(f"Delito: {delito}")
        
        # Si no hay elementos, tomar inicio del texto
        if not partes_resumen:
            # Tomar la primera oración
            primera_oracion = re.split(r'[.!?]', texto)[0]
            return primera_oracion[:max_length].strip() + ('...' if len(primera_oracion) > max_length else '')
        
        resumen = ' - '.join(partes_resumen)
        
        if len(resumen) > max_length:
            resumen = resumen[:max_length-3] + '...'
        
        return resumen


# Instancia global
extractor_parrafos = ExtractorParrafosEstructurados()
