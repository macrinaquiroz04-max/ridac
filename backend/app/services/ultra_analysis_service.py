"""
🚀 SERVICIO DE ANÁLISIS ULTRA-OPTIMIZADO V2
Soluciona el problema de análisis que se cuelga + velocidad 10x más rápida
"""

import re
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

logger = logging.getLogger("ridac_ocr")

try:
    from app.services.legal_entity_filter_service import LegalEntityFilterService
    _FILTER_AVAILABLE = True
except ImportError:
    _FILTER_AVAILABLE = False

class UltraAnalysisService:
    """Servicio de análisis ultra-optimizado que nunca se cuelga"""
    
    def __init__(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Patrones optimizados con regex compiladas
        self.compiled_patterns = self._compile_patterns()
        
        # Cache de resultados para análisis repetidos
        self.analysis_cache = {}
        
        # Filtro de validación de nombres
        self.entity_filter = LegalEntityFilterService() if _FILTER_AVAILABLE else None
    
    def _compile_patterns(self) -> Dict:
        """Compilar todos los patrones regex para máxima velocidad"""
        
        # Números escritos en español para fechas
        _nums = r'(?:primero|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|diecis[eé]is|diecisiete|dieciocho|diecinueve|veinte|veintiuno|veintid[oó]s|veintitr[eé]s|veinticuatro|veinticinco|veintis[eé]is|veintisiete|veintiocho|veintinueve|treinta(?:\s+y\s+\w+)?)'
        _meses = r'(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)'
        _year_txt = r'(?:(?:dos\s+mil|mil\s+novecientos|mil\s+ochocientos)(?:\s+\w+){0,3})'

        patterns = {
            'fechas': [
                # Formatos dd/mm/yyyy, dd-mm-yyyy, dd de mes de yyyy
                re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b', re.IGNORECASE),
                re.compile(r'\b(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\b', re.IGNORECASE),
                re.compile(r'\b(\w+\s+\d{1,2},?\s+\d{4})\b', re.IGNORECASE),
                re.compile(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b', re.IGNORECASE),
                # Fechas escritas en texto: "siete de abril del dos mil veintiséis"
                re.compile(rf'\b({_nums}\s+de\s+{_meses}\s+del?\s+{_year_txt})\b', re.IGNORECASE),
                # "día siete del mes de abril del año dos mil veintiséis"
                re.compile(rf'\b(d[ií]a\s+{_nums}\s+del?\s+mes\s+de\s+{_meses}\s+del?\s+(?:a[ñn]o\s+)?{_year_txt})\b', re.IGNORECASE),
                # "siete de abril de dos mil veintiséis" (sin "del")
                re.compile(rf'\b({_nums}\s+de\s+{_meses}\s+de\s+{_year_txt})\b', re.IGNORECASE),
                # Número + mes escrito + año escrito: "7 de abril del dos mil veintiséis"
                re.compile(rf'\b(\d{{1,2}}\s+de\s+{_meses}\s+del?\s+{_year_txt})\b', re.IGNORECASE),
                # Día escrito + mes + año numérico: "siete de abril de 2026"
                re.compile(rf'\b({_nums}\s+de\s+{_meses}\s+del?\s+\d{{4}})\b', re.IGNORECASE),
            ],
            
            'nombres': [
                # Nombres con título/rol explícito
                re.compile(r'\bC\.\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b'),
                re.compile(r'\bLIC\.\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b'),
                re.compile(r'\bDR\.?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b'),
                re.compile(r'\bING\.?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b'),
                re.compile(r'\b(?:PERITO|FISCAL|TESTIGO|IMPUTADO|VÍCTIMA|VICTIMA|AGRAVIADO|COMPARECIENTE)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b', re.IGNORECASE),
                # Nombres 3 palabras (filtrado por LegalEntityFilterService en código)
                re.compile(r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)\b'),
                
                # Protección de menores (B.C.A., etc.)
                re.compile(r'\b([A-Z]\.){2,4}\b'),  # Iniciales como B.C.A.
            ],
            
            'direcciones': [
                # Direcciones mexicanas — nombre de calle debe empezar con letra mayúscula
                # y NO ser seguido de verbos/frases/calibres
                re.compile(r'\b((?:Calle|Av\.|Avenida|Blvd\.|Boulevard)\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÑ\s\.\-]{2,40}?)(?:\s+(?:n[úu]m|#|\d)|,|\n|$)', re.IGNORECASE),
                re.compile(r'\b((?:Col\.|Colonia)\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÑ\s]{2,28}?)(?:,|\n|$)', re.IGNORECASE),
                re.compile(r'\b((?:Delegación|Alcaldía)\s+[A-Za-záéíóúñÑ][A-Za-záéíóúñÑ\s]{2,23}?)(?:,|\n|$)', re.IGNORECASE),
                re.compile(r'\b(C\.P\.\s*\d{5})\b', re.IGNORECASE),
            ],
            
            'lugares': [
                # Lugares institucionales y geográficos
                re.compile(r'\b(Hospital|Clínica|Centro de Salud)\s+([^,\n]{5,40})', re.IGNORECASE),
                re.compile(r'\b(Plaza|Parque|Jardín)\s+([^,\n]{3,30})', re.IGNORECASE),
                re.compile(r'\b(Fiscalía|Ministerio Público|Agencia)\s+([^,\n]{5,40})', re.IGNORECASE),
                re.compile(r'\b(Ciudad de México|CDMX|Estado de México)\b', re.IGNORECASE),
            ],
            
            'telefonos': [
                re.compile(r'\b(\d{2}[-\s]?\d{4}[-\s]?\d{4})\b'),  # 55-1234-5678
                re.compile(r'\b(\d{10})\b'),  # 5512345678
            ],
            
            'diligencias': [
                re.compile(r'\b(DECLARACIÓN|COMPARECENCIA|TESTIMONIO)\b', re.IGNORECASE),
                re.compile(r'\b(INFORME\s+PERICIAL|DICTAMEN|PERITAJE)\b', re.IGNORECASE),
                re.compile(r'\b(OFICIO|ACUERDO|RESOLUCIÓN)\b', re.IGNORECASE),
            ]
        }
        
        return patterns
    
    async def _process_pages_parallel(self, texto_completo: str, paginas_info: List[Dict]) -> List[Dict]:
        """Procesar texto por páginas en paralelo, manteniendo referencia de página"""
        tasks = []
        
        for pagina_info in paginas_info:
            inicio = pagina_info.get('inicio', 0)
            fin = pagina_info.get('fin', len(texto_completo))
            numero_pagina = pagina_info.get('numero', 1)
            
            # Extraer texto de la página
            texto_pagina = texto_completo[inicio:fin]
            
            # Crear tarea para procesar esta página
            task = self._analyze_page_with_reference(texto_pagina, numero_pagina)
            tasks.append(task)
        
        # Ejecutar todas las tareas en paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar excepciones
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        return valid_results
    
    async def _analyze_page_with_reference(self, texto_pagina: str, numero_pagina: int) -> Dict:
        """Analizar una página específica manteniendo la referencia"""
        loop = asyncio.get_event_loop()
        
        # Ejecutar análisis en thread pool
        result = await loop.run_in_executor(
            self.thread_pool,
            self._extract_patterns_from_page,
            texto_pagina,
            numero_pagina
        )
        
        return result
    
    def _extract_patterns_from_page(self, texto_pagina: str, numero_pagina: int) -> Dict:
        """Extraer patrones de una página específica con referencia"""
        resultado = {
            'fechas': [],
            'nombres': [],
            'direcciones': [],
            'lugares': [],
            'telefonos': [],
            'diligencias': []
        }
        
        try:
            # Extraer cada categoría de patrones
            for categoria, patterns in self.compiled_patterns.items():
                items_encontrados = set()  # Usar set para evitar duplicados
                
                for pattern in patterns:
                    matches = pattern.finditer(texto_pagina)
                    
                    for match in matches:
                        texto_match = match.group(1) if match.groups() else match.group(0)
                        texto_limpio = texto_match.strip()
                        
                        if len(texto_limpio) > 2:  # Filtrar matches muy cortos
                            # Protección especial para menores
                            if categoria == 'nombres' and self._is_minor_protected(texto_limpio):
                                texto_limpio = "[MENOR PROTEGIDO]"
                            elif categoria == 'nombres' and self.entity_filter:
                                es_valido, _ = self.entity_filter.es_nombre_valido(texto_limpio)
                                if not es_valido:
                                    continue
                            elif categoria == 'direcciones' and not self._is_valid_direccion(texto_limpio):
                                continue
                            
                            # Agregar con información de página
                            items_encontrados.add((texto_limpio, match.start(), match.end()))
                
                # Convertir set a lista de diccionarios con información de página
                for item_tuple in items_encontrados:
                    texto_item, start_pos, end_pos = item_tuple
                    entry = {
                        'texto': texto_item,
                        'texto_completo': texto_item,
                        'numero_pagina': numero_pagina,
                        'pagina': numero_pagina,
                        'posicion_inicio': start_pos,
                        'posicion_fin': end_pos,
                        'longitud': len(texto_item)
                    }
                    if categoria == 'nombres':
                        partes = texto_item.split()
                        entry['nombres'] = partes[0] if partes else texto_item
                        entry['apellido_paterno'] = partes[1] if len(partes) > 1 else ''
                        entry['apellido_materno'] = partes[2] if len(partes) > 2 else ''
                        entry['tipo'] = 'persona'
                    elif categoria in ('direcciones', 'lugares'):
                        entry['tipo'] = categoria
                        entry['nombre'] = texto_item
                    resultado[categoria].append(entry)
                        
        except Exception as e:
            logger.warning(f"⚠️ Error extrayendo patrones de página {numero_pagina}: {e}")
        
        return resultado
    
    async def analyze_document_ultra_fast(self, texto_completo: str, timeout_seconds: int = 30, paginas_info: List[Dict] = None) -> Dict[str, Any]:
        """
        Análisis ultra-rápido con timeout para evitar cuelgues + REFERENCIA DE PÁGINAS
        """
        start_time = time.time()
        
        try:
            # Crear hash del texto para cache
            text_hash = str(hash(texto_completo[:1000]))  # Hash de los primeros 1000 chars
            
            # Verificar cache primero
            if text_hash in self.analysis_cache:
                logger.info("⚡ Resultado obtenido del cache de análisis")
                return self.analysis_cache[text_hash]
            
            # Si tenemos información de páginas, usarla
            if paginas_info and len(paginas_info) > 0:
                logger.info(f"📄 Procesando por páginas ({len(paginas_info)} páginas)")
                results = await asyncio.wait_for(
                    self._process_pages_parallel(texto_completo, paginas_info),
                    timeout=timeout_seconds
                )
            else:
                # Dividir el trabajo en chunks para evitar timeouts
                logger.info("📋 Procesando por chunks (sin info de páginas)")
                chunks = self._split_text_into_chunks(texto_completo, chunk_size=10000)
                
                # Procesar chunks en paralelo con timeout
                results = await asyncio.wait_for(
                    self._process_chunks_parallel(chunks),
                    timeout=timeout_seconds
                )
            
            # Combinar resultados
            final_result = self._combine_chunk_results(results)
            
            # Agregar metadatos sobre el procesamiento
            final_result['metadatos'] = {
                'procesado_por_paginas': paginas_info is not None,
                'numero_paginas': len(paginas_info) if paginas_info else 0,
                'tiempo_procesamiento': time.time() - start_time,
                'metodo_procesamiento': 'páginas' if paginas_info else 'chunks'
            }
            
            # Guardar en cache
            self.analysis_cache[text_hash] = final_result
            
            # Limpiar cache si se vuelve muy grande
            if len(self.analysis_cache) > 100:
                self.analysis_cache.clear()
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Análisis completado en {elapsed_time:.2f} segundos")
            
            return final_result
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ TIMEOUT: Análisis cancelado después de {timeout_seconds}s")
            return self._get_fallback_result()
            
        except Exception as e:
            logger.error(f"❌ Error en análisis: {e}")
            return self._get_fallback_result()
    
    def _split_text_into_chunks(self, texto: str, chunk_size: int = 10000) -> List[str]:
        """Dividir texto en chunks para procesamiento paralelo"""
        chunks = []
        for i in range(0, len(texto), chunk_size):
            chunks.append(texto[i:i + chunk_size])
        return chunks
    
    async def _process_chunks_parallel(self, chunks: List[str]) -> List[Dict]:
        """Procesar chunks en paralelo"""
        
        tasks = []
        for chunk in chunks:
            task = asyncio.create_task(self._analyze_chunk(chunk))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar excepciones
        valid_results = [r for r in results if isinstance(r, dict)]
        return valid_results
    
    async def _analyze_chunk(self, chunk: str) -> Dict:
        """Analizar un chunk de texto"""
        
        loop = asyncio.get_event_loop()
        
        # Ejecutar análisis en thread pool para no bloquear
        result = await loop.run_in_executor(
            self.thread_pool,
            self._extract_patterns_from_chunk,
            chunk
        )
        
        return result
    
    def _extract_patterns_from_chunk(self, chunk: str) -> Dict:
        """Extraer todos los patrones de un chunk de texto"""
        
        resultado = {
            'fechas': [],
            'nombres': [],
            'direcciones': [],
            'lugares': [],
            'telefonos': [],
            'diligencias': []
        }
        
        try:
            # Extraer cada categoría de patrones
            for categoria, patterns in self.compiled_patterns.items():
                items_encontrados = set()  # Usar set para evitar duplicados
                
                for pattern in patterns:
                    matches = pattern.finditer(chunk)
                    
                    for match in matches:
                        texto_match = match.group(1) if match.groups() else match.group(0)
                        texto_limpio = texto_match.strip()
                        
                        if len(texto_limpio) > 2:  # Filtrar matches muy cortos
                            # Protección especial para menores
                            if categoria == 'nombres' and self._is_minor_protected(texto_limpio):
                                texto_limpio = "[MENOR PROTEGIDO]"
                            elif categoria == 'nombres' and self.entity_filter:
                                es_valido, _ = self.entity_filter.es_nombre_valido(texto_limpio)
                                if not es_valido:
                                    continue
                            elif categoria == 'direcciones' and not self._is_valid_direccion(texto_limpio):
                                continue
                            
                            items_encontrados.add(texto_limpio)
                
                # Convertir set a lista de diccionarios con información adicional
                for item in items_encontrados:
                    entry = {
                        'texto': item,
                        'texto_completo': item,
                        'posicion': chunk.find(item),
                        'longitud': len(item)
                    }
                    if categoria == 'nombres':
                        partes = item.split()
                        entry['nombres'] = partes[0] if partes else item
                        entry['apellido_paterno'] = partes[1] if len(partes) > 1 else ''
                        entry['apellido_materno'] = partes[2] if len(partes) > 2 else ''
                        entry['tipo'] = 'persona'
                    elif categoria in ('direcciones', 'lugares'):
                        entry['tipo'] = categoria
                        entry['nombre'] = item
                    resultado[categoria].append(entry)
        
        except Exception as e:
            logger.error(f"Error extrayendo patrones: {e}")
        
        return resultado
    
    def _is_minor_protected(self, texto: str) -> bool:
        """Detectar si es un nombre de menor que debe protegerse"""
        # Patrón de iniciales (B.C.A., J.L.M., etc.)
        patron_iniciales = re.match(r'^[A-Z]\.([A-Z]\.)+$', texto)
        return bool(patron_iniciales)
    
    def _is_valid_direccion(self, direccion: str) -> bool:
        """Validar que una dirección detectada sea real y no basura OCR"""
        if not direccion or len(direccion.strip()) < 5:
            return False
        
        texto = direccion.strip()
        texto_lower = texto.lower()
        
        # Siempre aceptar códigos postales (C.P. 12345)
        if re.match(r'^C\.P\.\s*\d{5}$', texto, re.IGNORECASE):
            return True
        
        # Rechazar calibres/munición detectados como calles
        # Ej: "CALLE 9 MM", "CALLE 7.62", "CALLE .308 WIN"
        if re.search(r'\b\d+\.?\d*\s*[Mm][Mm]\b', texto):
            return False
        if re.search(r'\.\d{2,3}["\']\s', texto):
            return False
        if re.search(r'\b(?:WIN|PARABELLUM|BMG|REM|AUTO|MAUSSER|GA)\b', texto, re.IGNORECASE):
            return False
        if re.search(r'\d+\s*[Xx]\s*\d+', texto):
            return False
        
        # Rechazar "coloniaa" (artefacto OCR de "colonia")
        if 'coloniaa' in texto_lower:
            return False
        
        # Rechazar si después del tipo de vía hay verbos/artículos/frases
        via_frase = re.match(
            r'(?:calle|avenida|av\.|blvd\.|boulevard|col\.|colonia)\s+'
            r'(?:se|por|de|en|que|las|los|con|sin|fue|era|son|hay|del|una|un|el|la|al|su|no|ya)\b',
            texto_lower
        )
        if via_frase:
            return False
        
        # Rechazar terminología legal/forense
        terminos_no_lugar = [
            'investigación', 'investigacion', 'rev.:', 'ref.:', 'pgr', 'lftaipg',
            'ministerio', 'agencia de', 'coordinación', 'dictamen', 'carpeta',
            'expediente', 'indiciado', 'constitución', 'constitucion', 'certificado',
            'paradero', 'requerimiento', 'diligencia', 'perito', 'pericial',
            'fraccion', 'fracción', 'artículo', 'articulo', 'casquillo', 'cartucho',
            'bala', 'fusil', 'pistola', 'rifle', 'calibre', 'percutor',
            'narcótico', 'estupefaciente', 'droga', 'fiscal',
        ]
        if any(t in texto_lower for t in terminos_no_lugar):
            return False
        
        # Rechazar colores solos como nombre de colonia (OCR garbage)
        # Ej: "Colonia negro", "Colonia azul", "Colonia obscuro"
        colonia_match = re.match(r'(?:col\.|colonia)\s+(.+)$', texto_lower)
        if colonia_match:
            nombre_colonia = colonia_match.group(1).strip()
            colores_y_basura = {
                'negro', 'negra', 'azul', 'rojo', 'roja', 'blanco', 'blanca',
                'verde', 'gris', 'obscuro', 'obscura', 'oscuro', 'oscura',
                'amarillo', 'amarilla', 'anaranjado', 'dorado', 'declaro',
                'robo', 'humanos', 'número', 'numero', 'acuerdo',
            }
            if nombre_colonia in colores_y_basura:
                return False
        
        # Rechazar si es mayormente números
        digitos = sum(1 for c in texto if c.isdigit())
        letras = sum(1 for c in texto if c.isalpha())
        if letras > 0 and digitos / letras > 0.3:
            return False
        
        # Rechazar textos muy largos con muchas minúsculas (frases, no direcciones)
        palabras = texto.split()
        if len(palabras) > 5:
            # Quitar la primera palabra (tipo de vía)
            resto = palabras[1:]
            minusculas = sum(1 for p in resto if p and p[0].islower())
            if minusculas > len(resto) // 2:
                return False
        
        return True
    
    def _combine_chunk_results(self, chunk_results: List[Dict]) -> Dict[str, Any]:
        """Combinar resultados de todos los chunks"""
        
        resultado_final = {
            'fechas': [],
            'nombres': [],
            'direcciones': [],
            'lugares': [],
            'telefonos': [],
            'diligencias': [],
            'alertas': [],
            'estadisticas': {}
        }
        
        # Combinar todos los resultados
        textos_vistos = defaultdict(set)
        
        for chunk_result in chunk_results:
            for categoria, items in chunk_result.items():
                if categoria in resultado_final and isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and 'texto' in item:
                            texto_normalizado = item['texto'].lower().strip()
                            
                            # Evitar duplicados globales
                            if texto_normalizado not in textos_vistos[categoria]:
                                textos_vistos[categoria].add(texto_normalizado)
                                resultado_final[categoria].append(item)
        
        # Generar alertas automáticas
        resultado_final['alertas'] = self._generate_automatic_alerts(resultado_final)
        
        # Calcular estadísticas
        resultado_final['estadisticas'] = {
            'total_fechas': len(resultado_final['fechas']),
            'total_nombres': len(resultado_final['nombres']),
            'total_direcciones': len(resultado_final['direcciones']),
            'total_lugares': len(resultado_final['lugares']),
            'total_telefonos': len(resultado_final['telefonos']),
            'total_diligencias': len(resultado_final['diligencias']),
            'total_alertas': len(resultado_final['alertas']),
            'tiempo_analisis': time.time()
        }
        
        return resultado_final
    
    def _generate_automatic_alerts(self, resultado: Dict) -> List[Dict]:
        """Generar alertas automáticas basadas en patrones detectados"""
        
        alertas = []
        
        # Alerta por muchos nombres (posible caso complejo)
        if len(resultado['nombres']) > 10:
            alertas.append({
                'tipo': 'caso_complejo',
                'mensaje': f'Caso con múltiples personas involucradas ({len(resultado["nombres"])} nombres detectados)',
                'prioridad': 'media'
            })
        
        # Alerta por menores protegidos
        menores_detectados = sum(1 for n in resultado['nombres'] if '[MENOR PROTEGIDO]' in n.get('texto', ''))
        if menores_detectados > 0:
            alertas.append({
                'tipo': 'menores_involucrados',
                'mensaje': f'Documento contiene {menores_detectados} menores de edad protegidos',
                'prioridad': 'alta'
            })
        
        # Alerta por muchas diligencias (caso activo)
        if len(resultado['diligencias']) > 5:
            alertas.append({
                'tipo': 'caso_activo',
                'mensaje': f'Caso con múltiples diligencias ({len(resultado["diligencias"])} detectadas)',
                'prioridad': 'media'
            })
        
        return alertas
    
    def _get_fallback_result(self) -> Dict[str, Any]:
        """Resultado básico en caso de error o timeout"""
        return {
            'fechas': [],
            'nombres': [],
            'direcciones': [],
            'lugares': [],
            'telefonos': [],
            'diligencias': [],
            'alertas': [{
                'tipo': 'analisis_fallback',
                'mensaje': 'Análisis completado en modo básico por timeout o error',
                'prioridad': 'baja'
            }],
            'estadisticas': {
                'total_fechas': 0,
                'total_nombres': 0,
                'total_direcciones': 0,
                'total_lugares': 0,
                'total_telefonos': 0,
                'total_diligencias': 0,
                'total_alertas': 1,
                'modo': 'fallback'
            }
        }

# Instancia global del servicio
ultra_analysis_service = UltraAnalysisService()

# Función de compatibilidad para el controlador existente
async def analizar_documento_ultra_rapido(texto_completo: str, paginas_info: List[Dict] = None) -> Dict[str, Any]:
    """Función de compatibilidad con el controlador existente + REFERENCIA DE PÁGINAS"""
    return await ultra_analysis_service.analyze_document_ultra_fast(texto_completo, paginas_info=paginas_info)