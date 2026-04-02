# backend/app/services/pdf_pagina_service.py

"""
Servicio para extraer números de página REALES de PDFs (no del visor).

Para carpetas judiciales RIDAC que pueden tener numeración interna como:
"Página 196 de 821" donde 196 es el número real y 821 el total.
"""

import fitz  # PyMuPDF
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from app.utils.logger import logger

class PDFPaginaService:
    """Servicio para detectar números de página reales en PDFs"""

    def __init__(self):
        # Patrones para detectar números de página en texto
        # NOTA: Se excluyen números de "TOMO" para no confundir con fojas reales
        self.patrones_pagina = [
            # "Página 196 de 821" o "Foja 196 de 821" (MÁS CONFIABLE)
            r'(?:P[áa]gina|Foja|FOJA|Hoja)\s+(\d+)\s+de\s+(\d+)',
            # "196 de 821" (sin palabra clave)
            r'(?<!TOMO\s)(?<!Tomo\s)(\d+)\s+de\s+(\d+)',
            # "Foja 196" o "FOJA 196"
            r'Foja\s+(\d+)',
            r'FOJA\s+(\d+)',
            # "Hoja 196"
            r'Hoja\s+(\d+)',
            r'HOJA\s+(\d+)',
            # "Pág. 196" o "Pág: 196"
            r'P[áa]g[\.\:]\s*(\d+)',
            # "F. 196" (abreviatura común)
            r'F\.\s*(\d+)',
            # "Fs. 196" (fojas)
            r'Fs\.\s*(\d+)'
        ]
        
        # Ubicaciones comunes donde aparecen números de página
        self.zonas_pagina = {
            'header_right': {'y_inicio': 0, 'y_fin': 0.1, 'x_inicio': 0.7, 'x_fin': 1.0},
            'header_center': {'y_inicio': 0, 'y_fin': 0.1, 'x_inicio': 0.3, 'x_fin': 0.7},
            'footer_right': {'y_inicio': 0.9, 'y_fin': 1.0, 'x_inicio': 0.7, 'x_fin': 1.0},
            'footer_center': {'y_inicio': 0.9, 'y_fin': 1.0, 'x_inicio': 0.3, 'x_fin': 0.7},
            'footer_left': {'y_inicio': 0.9, 'y_fin': 1.0, 'x_inicio': 0.0, 'x_fin': 0.3}
        }

    def extraer_numero_pagina_real(
        self, 
        pdf_path: str, 
        pagina_visor: int,
        forzar_secuencial: bool = True
    ) -> Dict:
        """
        Extrae el número de página REAL del PDF (no el índice del visor).
        
        NOTA: Por defecto usa numeración secuencial (forzar_secuencial=True)
        para evitar confusión con números manuscritos, "TOMO", etc.
        
        Args:
            pdf_path: Ruta al archivo PDF
            pagina_visor: Página mostrada en el visor (0-indexed)
            forzar_secuencial: Si True, usa posición del PDF (recomendado=True)
        
        Returns:
            {
                'pagina_real': 196,           # Número = posición en PDF
                'pagina_visor': 195,          # Índice en el PDF (0-indexed)
                'pagina_visor_display': 196,  # Página del visor (1-indexed)
                'total_paginas_pdf': 821,     # Total de páginas del PDF
                'total_paginas_documento': 821, # Total según numeración interna
                'metodo_deteccion': 'numeracion_secuencial_pdf',
                'confianza': 100,
                'nota': 'Usando posición en PDF (NO números manuscritos)'
            }
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                return {
                    'error': f"Archivo no encontrado: {pdf_path}",
                    'pagina_visor': pagina_visor
                }

            doc = fitz.open(str(pdf_path))
            total_paginas_pdf = len(doc)
            
            # Validar página
            if pagina_visor < 0 or pagina_visor >= total_paginas_pdf:
                doc.close()
                return {
                    'error': f"Página {pagina_visor} fuera de rango (0-{total_paginas_pdf-1})",
                    'total_paginas_pdf': total_paginas_pdf
                }

            doc.close()
            
            # MODO RECOMENDADO: Usar siempre numeración secuencial
            if forzar_secuencial:
                return {
                    'pagina_real': pagina_visor + 1,  # 1-indexed
                    'pagina_visor': pagina_visor,     # 0-indexed
                    'pagina_visor_display': pagina_visor + 1,
                    'total_paginas_pdf': total_paginas_pdf,
                    'total_paginas_documento': total_paginas_pdf,
                    'metodo_deteccion': 'numeracion_secuencial_pdf',
                    'confianza': 100,
                    'nota': 'Usando posición en PDF (ignora números manuscritos/impresos)'
                }
            
            # MODO OPCIONAL: Intentar detectar numeración en el documento
            # (No recomendado para carpetas con tomos)
            else:
                page = doc[pagina_visor]
                resultado = self._detectar_numero_pagina(page, pagina_visor, total_paginas_pdf)
                doc.close()
                return resultado

        except Exception as e:
            logger.error(f"❌ Error extrayendo número de página: {e}")
            return {
                'error': str(e),
                'pagina_visor': pagina_visor
            }

    def _detectar_numero_pagina(
        self, 
        page: fitz.Page, 
        pagina_visor: int,
        total_paginas_pdf: int
    ) -> Dict:
        """
        Detecta el número de página usando múltiples estrategias.
        """
        # Método 1: Buscar en zonas específicas (más preciso)
        resultado_zonas = self._buscar_en_zonas(page, pagina_visor, total_paginas_pdf)
        if resultado_zonas and resultado_zonas.get('confianza', 0) > 80:
            return resultado_zonas

        # Método 2: Buscar en todo el texto
        resultado_texto = self._buscar_en_texto_completo(page, pagina_visor, total_paginas_pdf)
        if resultado_texto and resultado_texto.get('confianza', 0) > 70:
            return resultado_texto

        # Método 3: Asumir numeración secuencial
        return self._asumir_numeracion_secuencial(pagina_visor, total_paginas_pdf)

    def _buscar_en_zonas(
        self, 
        page: fitz.Page, 
        pagina_visor: int,
        total_paginas_pdf: int
    ) -> Optional[Dict]:
        """
        Busca números de página en zonas comunes (header/footer).
        """
        rect = page.rect
        ancho = rect.width
        alto = rect.height

        mejor_resultado = None
        mejor_confianza = 0

        for zona_nombre, zona_coords in self.zonas_pagina.items():
            # Calcular coordenadas absolutas
            x0 = ancho * zona_coords['x_inicio']
            y0 = alto * zona_coords['y_inicio']
            x1 = ancho * zona_coords['x_fin']
            y1 = alto * zona_coords['y_fin']

            zona_rect = fitz.Rect(x0, y0, x1, y1)
            
            # Extraer texto de la zona
            texto_zona = page.get_text("text", clip=zona_rect).strip()

            if not texto_zona:
                continue

            # Buscar patrones
            for patron in self.patrones_pagina:
                match = re.search(patron, texto_zona, re.IGNORECASE | re.MULTILINE)
                if match:
                    grupos = match.groups()
                    
                    if len(grupos) >= 2:
                        # Formato "Página X de Y"
                        pagina_real = int(grupos[0])
                        total_documento = int(grupos[1])
                        confianza = 95
                        metodo = 'patron_pagina_de'
                        
                        # Validación: el número debe ser razonable
                        if pagina_real > 0 and pagina_real <= total_documento:
                            resultado = {
                                'pagina_real': pagina_real,
                                'pagina_visor': pagina_visor,
                                'pagina_visor_display': pagina_visor + 1,
                                'total_paginas_pdf': total_paginas_pdf,
                                'total_paginas_documento': total_documento,
                                'metodo_deteccion': metodo,
                                'confianza': confianza,
                                'texto_encontrado': match.group(0),
                                'zona': zona_nombre
                            }
                            
                            if confianza > mejor_confianza:
                                mejor_resultado = resultado
                                mejor_confianza = confianza
                    
                    elif len(grupos) == 1:
                        # Formato simple "Foja X", "F. X", etc. (CON palabra clave)
                        pagina_real = int(grupos[0])
                        confianza = 85
                        
                        # Validación: debe ser un número razonable
                        # Acepta cualquier número entre 1 y 10000 (carpetas grandes)
                        if 1 <= pagina_real <= 10000:
                            resultado = {
                                'pagina_real': pagina_real,
                                'pagina_visor': pagina_visor,
                                'pagina_visor_display': pagina_visor + 1,
                                'total_paginas_pdf': total_paginas_pdf,
                                'total_paginas_documento': None,
                                'metodo_deteccion': 'patron_foja_explicita',
                                'confianza': confianza,
                                'texto_encontrado': match.group(0),
                                'zona': zona_nombre
                            }
                            
                            if confianza > mejor_confianza:
                                mejor_resultado = resultado
                                mejor_confianza = confianza

        return mejor_resultado

    def _buscar_en_texto_completo(
        self, 
        page: fitz.Page, 
        pagina_visor: int,
        total_paginas_pdf: int
    ) -> Optional[Dict]:
        """
        Busca números de página en todo el texto de la página.
        """
        texto_completo = page.get_text("text")
        
        # Priorizar patrones más específicos
        for i, patron in enumerate(self.patrones_pagina[:5]):  # Primeros 5 patrones son más confiables
            match = re.search(patron, texto_completo, re.IGNORECASE | re.MULTILINE)
            if match:
                grupos = match.groups()
                
                if len(grupos) >= 2:
                    pagina_real = int(grupos[0])
                    total_documento = int(grupos[1])
                    
                    if pagina_real > 0 and pagina_real <= total_documento:
                        return {
                            'pagina_real': pagina_real,
                            'pagina_visor': pagina_visor,
                            'pagina_visor_display': pagina_visor + 1,
                            'total_paginas_pdf': total_paginas_pdf,
                            'total_paginas_documento': total_documento,
                            'metodo_deteccion': 'texto_completo_patron_de',
                            'confianza': 75,
                            'texto_encontrado': match.group(0),
                            'zona': 'texto_completo'
                        }
                
                elif len(grupos) == 1:
                    pagina_real = int(grupos[0])
                    
                    if abs(pagina_real - (pagina_visor + 1)) <= 10:
                        return {
                            'pagina_real': pagina_real,
                            'pagina_visor': pagina_visor,
                            'pagina_visor_display': pagina_visor + 1,
                            'total_paginas_pdf': total_paginas_pdf,
                            'total_paginas_documento': None,
                            'metodo_deteccion': 'texto_completo_foja',
                            'confianza': 70,
                            'texto_encontrado': match.group(0),
                            'zona': 'texto_completo'
                        }

        return None

    def _asumir_numeracion_secuencial(
        self, 
        pagina_visor: int,
        total_paginas_pdf: int
    ) -> Dict:
        """
        Fallback: asumir que la numeración es secuencial (1-indexed).
        """
        return {
            'pagina_real': pagina_visor + 1,  # Convertir a 1-indexed
            'pagina_visor': pagina_visor,
            'pagina_visor_display': pagina_visor + 1,
            'total_paginas_pdf': total_paginas_pdf,
            'total_paginas_documento': total_paginas_pdf,
            'metodo_deteccion': 'asuncion_secuencial',
            'confianza': 50,
            'texto_encontrado': None,
            'zona': None,
            'nota': 'No se encontró numeración explícita, asumiendo secuencial'
        }

    def buscar_pagina_por_contenido(
        self, 
        pdf_path: str, 
        texto_buscado: str,
        case_sensitive: bool = False
    ) -> List[Dict]:
        """
        Busca un texto en el PDF y devuelve las páginas reales donde aparece.
        
        Args:
            pdf_path: Ruta al PDF
            texto_buscado: Texto a buscar
            case_sensitive: Si la búsqueda distingue mayúsculas/minúsculas
        
        Returns:
            Lista de resultados:
            [
                {
                    'pagina_real': 196,
                    'pagina_visor': 195,
                    'coincidencias': 3,
                    'contexto': '...FISCALIA CENTRAL...',
                    'posicion': 1250
                }
            ]
        """
        try:
            doc = fitz.open(str(pdf_path))
            resultados = []

            if not case_sensitive:
                texto_buscado = texto_buscado.lower()

            for pagina_visor in range(len(doc)):
                page = doc[pagina_visor]
                texto_pagina = page.get_text("text")
                
                if not case_sensitive:
                    texto_pagina_busqueda = texto_pagina.lower()
                else:
                    texto_pagina_busqueda = texto_pagina

                if texto_buscado in texto_pagina_busqueda:
                    # Contar coincidencias
                    coincidencias = texto_pagina_busqueda.count(texto_buscado)
                    
                    # Obtener contexto (100 caracteres antes y después)
                    posicion = texto_pagina_busqueda.find(texto_buscado)
                    inicio = max(0, posicion - 100)
                    fin = min(len(texto_pagina), posicion + len(texto_buscado) + 100)
                    contexto = texto_pagina[inicio:fin]

                    # Detectar número de página real
                    info_pagina = self.extraer_numero_pagina_real(pdf_path, pagina_visor)

                    resultados.append({
                        'pagina_real': info_pagina.get('pagina_real', pagina_visor + 1),
                        'pagina_visor': pagina_visor,
                        'pagina_visor_display': pagina_visor + 1,
                        'coincidencias': coincidencias,
                        'contexto': contexto.strip(),
                        'posicion': posicion,
                        'confianza_pagina': info_pagina.get('confianza', 50)
                    })

            doc.close()
            
            return resultados

        except Exception as e:
            logger.error(f"❌ Error buscando en PDF: {e}")
            return []

    def extraer_metadatos_numeracion(self, pdf_path: str) -> Dict:
        """
        Analiza todo el PDF para determinar el esquema de numeración usado.
        
        Útil para carpetas judiciales que pueden tener:
        - Numeración interna (Fojas 1-821)
        - Numeración por sección
        - Saltos en la numeración
        
        Returns:
            {
                'tipo_numeracion': 'secuencial|fojas|mixto',
                'inicio': 1,
                'fin': 821,
                'saltos_detectados': [],
                'zonas_comunes': ['footer_center', 'header_right'],
                'confianza': 85
            }
        """
        try:
            doc = fitz.open(str(pdf_path))
            total_paginas = len(doc)
            
            # Muestrear cada 10 páginas para analizar patrón
            muestra_paginas = range(0, min(total_paginas, 100), 10)
            
            numeros_detectados = []
            zonas_detectadas = []
            
            for pagina_visor in muestra_paginas:
                info = self.extraer_numero_pagina_real(pdf_path, pagina_visor)
                
                if info.get('pagina_real') and info.get('confianza', 0) > 70:
                    numeros_detectados.append({
                        'visor': pagina_visor,
                        'real': info['pagina_real'],
                        'zona': info.get('zona')
                    })
                    
                    if info.get('zona'):
                        zonas_detectadas.append(info['zona'])

            doc.close()

            # Analizar patrón
            if len(numeros_detectados) < 3:
                return {
                    'tipo_numeracion': 'desconocido',
                    'confianza': 20,
                    'nota': 'Muestra insuficiente para determinar patrón'
                }

            # Verificar si es secuencial
            es_secuencial = True
            for i, num in enumerate(numeros_detectados):
                if num['real'] != num['visor'] + 1:
                    es_secuencial = False
                    break

            # Zona más común
            if zonas_detectadas:
                zona_comun = max(set(zonas_detectadas), key=zonas_detectadas.count)
            else:
                zona_comun = None

            return {
                'tipo_numeracion': 'secuencial' if es_secuencial else 'fojas',
                'inicio': numeros_detectados[0]['real'] if numeros_detectados else 1,
                'fin': numeros_detectados[-1]['real'] if numeros_detectados else total_paginas,
                'total_paginas_pdf': total_paginas,
                'zona_comun': zona_comun,
                'muestra_analizada': len(numeros_detectados),
                'confianza': 85 if len(numeros_detectados) >= 5 else 60,
                'ejemplos': numeros_detectados[:5]
            }

        except Exception as e:
            logger.error(f"❌ Error analizando metadatos: {e}")
            return {
                'tipo_numeracion': 'error',
                'error': str(e)
            }


# Instancia global
pdf_pagina_service = PDFPaginaService()
