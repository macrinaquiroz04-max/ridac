# backend/app/services/autocorrector_integrado_service.py

"""
Servicio de autocorrección integrado que combina:
- Corrección de texto básica
- Validación SEPOMEX (colonias, CPs, alcaldías)
- Normalización de fiscalías
- Normalización de delitos
- Detección de entidades (personas, lugares)
"""

from typing import Dict, List, Optional
from app.utils.logger import logger


class AutocorrectorIntegradoService:
    """Servicio de autocorrección integrado para OCR"""

    def __init__(self):
        self.sepomex_service = None
        self.catalogo_fiscalias = None
        self.detector_contextual = None
        self.text_correction_service = None
        self._init_services()

    def _init_services(self):
        """Inicializar servicios de forma lazy"""
        try:
            from app.services.sepomex_service_postgresql import sepomex_service_postgresql
            self.sepomex_service = sepomex_service_postgresql
            logger.info("✓ Servicio SEPOMEX PostgreSQL cargado")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar SEPOMEX: {e}")

        try:
            from app.services.catalogo_fiscalias_service import catalogo_fiscalias
            self.catalogo_fiscalias = catalogo_fiscalias
            logger.info("✓ Catálogo de fiscalías cargado")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar catálogo fiscalías: {e}")

        try:
            from app.services.detector_contextual_service import detector_contextual
            self.detector_contextual = detector_contextual
            logger.info("✓ Detector contextual cargado")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar detector contextual: {e}")

        try:
            from app.services.text_correction_service import TextCorrectionService
            self.text_correction_service = TextCorrectionService()
            logger.info("✓ Corrector de texto cargado")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar corrector de texto: {e}")

    def corregir_texto_completo(
        self,
        texto: str,
        aplicar_sepomex: bool = True,
        detectar_entidades: bool = True
    ) -> Dict:
        """
        Corrige un texto completo aplicando todas las correcciones disponibles.

        Returns:
            {
                'texto_corregido': str,
                'correcciones_aplicadas': int,
                'entidades_detectadas': {...},
                'estadisticas': {...}
            }
        """
        resultado = {
            'texto_original': texto,
            'texto_corregido': texto,
            'correcciones_aplicadas': 0,
            'entidades_detectadas': {},
            'estadisticas': {
                'colonias_corregidas': 0,
                'alcaldias_corregidas': 0,
                'fiscalias_detectadas': 0,
                'delitos_detectados': 0,
                'personas_detectadas': 0,
                'colonias_detectadas': 0
            }
        }

        try:
            # 1. Corrección básica de texto
            if self.text_correction_service:
                texto = self.text_correction_service.corregir_texto(texto, "legal")
                resultado['correcciones_aplicadas'] += 1

            # 2. Detectar y corregir colonias con SEPOMEX
            if aplicar_sepomex and self.sepomex_service:
                texto, stats_sepomex = self._corregir_con_sepomex(texto)
                resultado['estadisticas'].update(stats_sepomex)
                resultado['correcciones_aplicadas'] += stats_sepomex.get('total_correcciones', 0)

            # 3. Detectar entidades legales
            if detectar_entidades:
                entidades = self._detectar_entidades(texto)
                resultado['entidades_detectadas'] = entidades
                resultado['estadisticas'].update({
                    'fiscalias_detectadas': len(entidades.get('fiscalias', [])),
                    'delitos_detectados': len(entidades.get('delitos', [])),
                    'personas_detectadas': len(entidades.get('personas', [])),
                    'colonias_detectadas': len(entidades.get('colonias', []))
                })

            resultado['texto_corregido'] = texto

        except Exception as e:
            logger.error(f"❌ Error en corrección integrada: {e}")
            resultado['error'] = str(e)

        return resultado

    def _corregir_con_sepomex(self, texto: str) -> tuple:
        """Corrige SOLO alcaldías (RÁPIDO - regex) - SEPOMEX desactivado temporalmente"""
        stats = {
            'colonias_corregidas': 0,
            'alcaldias_corregidas': 0,
            'total_correcciones': 0
        }

        try:
            import re
            
            # Alcaldías comunes con errores OCR (MUY RÁPIDO - solo regex)
            alcaldias_map = {
                'ALVARO OBREGON': 'ÁLVARO OBREGÓN',
                'GUSTAVO A MADERO': 'GUSTAVO A. MADERO',
                'BENITO JUAREZ': 'BENITO JUÁREZ',
                'COYOACAN': 'COYOACÁN',
                'TLAHUAC': 'TLÁHUAC',
                'CUAUHTEMOC': 'CUAUHTÉMOC',
                'MAGDALENA CONTRERAS': 'LA MAGDALENA CONTRERAS',
                'CUAJIMALPA': 'CUAJIMALPA DE MORELOS'
            }

            for alcaldia_error, alcaldia_correcta in alcaldias_map.items():
                if alcaldia_error in texto.upper():
                    texto = re.sub(alcaldia_error, alcaldia_correcta, texto, flags=re.IGNORECASE)
                    stats['alcaldias_corregidas'] += 1
                    stats['total_correcciones'] += 1
            
            # DESACTIVADO: Búsqueda SEPOMEX (es async y causa problemas)
            # Se puede habilitar después arreglando el async/await
            # Colonias: Solo si hay palabras clave
            # texto_lower = texto.lower()
            # palabras_clave = ['colonia', 'col.', 'col ', 'domicilio']
            
            # tiene_colonias = any(palabra in texto_lower for palabra in palabras_clave)
            
            # if tiene_colonias and self.sepomex_service:
            #     # Buscar colonias en TODO el texto pero limitar consultas
            #     patrones_colonia = [
            #         r'colonia[:\s]+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]{3,40})(?:[,\.]|$)',
            #         r'col[.:\s]+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]{3,40})(?:[,\.]|$)',
            #     ]

            #     colonias_vistas = set()  # Evitar duplicados
            #     max_consultas = 3  # Máximo 3 consultas SEPOMEX por página
                
            #     for patron in patrones_colonia:
            #         matches = re.finditer(patron, texto, re.IGNORECASE)
            #         for match in matches:
            #             if stats['colonias_corregidas'] >= max_consultas:
            #                 break
                            
            #             colonia_original = match.group(1).strip()
                        
            #             # Limpiar y validar
            #             if len(colonia_original) < 4 or colonia_original.lower() in colonias_vistas:
            #                 continue
            #             colonias_vistas.add(colonia_original.lower())
                        
            #             # Buscar sugerencia en SEPOMEX
            #             try:
            #                 sugerencias = self.sepomex_service.buscar_colonias_por_texto(colonia_original)
                            
            #                 if sugerencias and len(sugerencias) > 0:
            #                     sugerencia = sugerencias[0]
            #                     if sugerencia['similitud'] > 0.80:  # 80% de similitud
            #                         colonia_correcta = sugerencia['colonia']
            #                         if colonia_correcta != colonia_original:
            #                             texto = texto.replace(colonia_original, colonia_correcta)
            #                             stats['colonias_corregidas'] += 1
            #                             stats['total_correcciones'] += 1
            #             except Exception:
            #                 continue  # Si falla una consulta, seguir con las demás

            # Alcaldías comunes con errores OCR
            alcaldias_map = {
                'ALVARO OBREGON': 'ÁLVARO OBREGÓN',
                'GUSTAVO A MADERO': 'GUSTAVO A. MADERO',
                'BENITO JUAREZ': 'BENITO JUÁREZ',
                'COYOACAN': 'COYOACÁN',
                'TLAHUAC': 'TLÁHUAC',
                'TLALPAN': 'TLALPAN',
                'MIGUEL HIDALGO': 'MIGUEL HIDALGO',
                'CUAUHTEMOC': 'CUAUHTÉMOC',
                'VENUSTIANO CARRANZA': 'VENUSTIANO CARRANZA',
                'IZTACALCO': 'IZTACALCO',
                'IZTAPALAPA': 'IZTAPALAPA',
                'MAGDALENA CONTRERAS': 'LA MAGDALENA CONTRERAS',
                'MILPA ALTA': 'MILPA ALTA',
                'CUAJIMALPA': 'CUAJIMALPA DE MORELOS',
                'XOCHIMILCO': 'XOCHIMILCO',
                'AZCAPOTZALCO': 'AZCAPOTZALCO'
            }

            for alcaldia_error, alcaldia_correcta in alcaldias_map.items():
                if alcaldia_error in texto.upper():
                    # Reemplazar manteniendo el case
                    texto = re.sub(
                        alcaldia_error,
                        alcaldia_correcta,
                        texto,
                        flags=re.IGNORECASE
                    )
                    stats['alcaldias_corregidas'] += 1
                    stats['total_correcciones'] += 1

        except Exception as e:
            logger.error(f"❌ Error en corrección SEPOMEX: {e}")

        return texto, stats

    def _detectar_entidades(self, texto: str) -> Dict:
        """Detecta entidades legales (OPTIMIZADO - solo en primera página)"""
        entidades = {
            'fiscalias': [],
            'delitos': [],
            'agencias_mp': [],
            'personas': [],
            'colonias': []
        }

        try:
            # OPTIMIZACIÓN: Limitar análisis a primeras 500 palabras
            texto_inicio = ' '.join(texto.split()[:500])
            lineas_inicio = texto_inicio.split('\n')[:50]

            # Detectar fiscalías (primeras 50 líneas)
            if self.catalogo_fiscalias:
                for linea in lineas_inicio:
                    if 'fiscal' in linea.lower():
                        resultado = self.catalogo_fiscalias.normalizar_fiscalia(linea)
                        if resultado['encontrado']:
                            entidades['fiscalias'].append(resultado)
                            break  # Solo la primera

            # Detectar delitos (primeras 50 líneas) - REDUCIDO de 100
            if self.catalogo_fiscalias:
                palabras_clave = ['ABUSO', 'VIOLACION', 'HOMICIDIO', 'ROBO', 'FRAUDE',
                                  'SECUESTRO', 'EXTORSION', 'FEMINICIDIO']
                
                for linea in lineas_inicio:
                    linea_upper = linea.upper()
                    if any(palabra in linea_upper for palabra in palabras_clave):
                        resultado = self.catalogo_fiscalias.normalizar_delito(linea)
                        if resultado['encontrado']:
                            entidades['delitos'].append(resultado)
                            break  # Solo el primero

            # Detectar agencias MP (primeras 30 líneas) - REDUCIDO de 50
            if self.catalogo_fiscalias:
                import re
                patron_agencia = r'(?:FDS|AO|BJ)-\d+'  # Solo los más comunes
                
                texto_compacto = '\n'.join(lineas_inicio[:30])
                matches = re.findall(patron_agencia, texto_compacto)
                
                if matches:
                    # Solo procesar el primero encontrado
                    resultado = self.catalogo_fiscalias.normalizar_agencia_mp(matches[0])
                    if resultado['encontrado']:
                        entidades['agencias_mp'].append(resultado)

            # DESACTIVAR detector contextual (muy lento) - Se puede habilitar después
            # if self.detector_contextual:
            #     resultado_detector = self.detector_contextual.procesar_documento_ocr(texto_inicio)
            #     entidades['personas'] = resultado_detector.get('personas', [])[:10]  # Max 10
            #     entidades['colonias'] = resultado_detector.get('colonias', [])[:10]  # Max 10

        except Exception as e:
            logger.error(f"❌ Error detectando entidades: {e}")

        return entidades


# Instancia global
autocorrector_integrado = AutocorrectorIntegradoService()
