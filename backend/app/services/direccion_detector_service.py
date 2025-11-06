# backend/app/services/direccion_detector_service.py

import re
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.models.tomo import ContenidoOCR
from app.services.sepomex_service import sepomex_service
from app.utils.logger import logger

class DireccionDetectorService:
    """
    Servicio para detectar y validar direcciones en texto OCR
    Diseñado específicamente para documentos legales de FGJCDMX
    """
    
    def __init__(self):
        # Patrones de detección de direcciones
        self.patterns = {
            # Calles/Avenidas
            'calle': r'(?:calle|c\.|av\.|avenida|privada|calz\.|calzada|andador|blvd\.|boulevard|cerrada|paseo)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+\d*)',
            
            # Números de dirección
            'numero': r'(?:n[úu]m\.?|número|#)\s*(\d+(?:-[A-Z])?(?:\s*int\.?\s*\d+)?)',
            
            # Colonias
            'colonia': r'(?:col\.|colonia)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)',
            
            # Códigos Postales
            'cp': r'(?:c\.?p\.?|código postal)\s*(\d{5})',
            
            # Alcaldías (las 16 de CDMX)
            'alcaldia': r'(?:alc\.|alcaldía|delegación|deleg\.)\s+(cuauhtémoc|miguel\s+hidalgo|benito\s+juárez|coyoacán|iztapalapa|gustavo\s+a\.?\s+madero|álvaro\s+obregón|tlalpan|azcapotzalco|venustiano\s+carranza|iztacalco|xochimilco|tláhuac|magdalena\s+contreras|cuajimalpa|milpa\s+alta)',
            
            # Patrón completo de dirección
            'direccion_completa': r'(?:calle|c\.|av\.|avenida)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+(?:n[úu]m\.?|#)\s*\d+.*?(?:col\.|colonia)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+.*?(?:c\.?p\.?)\s*\d{5}'
        }
        
        # Compilar patrones
        self.compiled_patterns = {
            key: re.compile(pattern, re.IGNORECASE) 
            for key, pattern in self.patterns.items()
        }
    
    async def detectar_direcciones_en_tomo(
        self, 
        db: Session, 
        tomo_id: int
    ) -> Dict[str, Any]:
        """
        Detecta todas las direcciones en un tomo procesado con OCR
        
        Returns:
            {
                'tomo_id': int,
                'total_direcciones': int,
                'direcciones': [
                    {
                        'pagina': int,
                        'linea': int,
                        'texto_original': str,
                        'calle': str,
                        'numero': str,
                        'colonia': str,
                        'cp': str,
                        'alcaldia': str,
                        'validacion': {...}
                    }
                ]
            }
        """
        try:
            # Obtener todo el contenido OCR del tomo
            contenidos = db.query(ContenidoOCR).filter(
                ContenidoOCR.tomo_id == tomo_id
            ).order_by(ContenidoOCR.numero_pagina).all()
            
            if not contenidos:
                return {
                    'tomo_id': tomo_id,
                    'total_direcciones': 0,
                    'direcciones': [],
                    'mensaje': 'No hay contenido OCR procesado'
                }
            
            direcciones_detectadas = []
            
            # Procesar cada página
            for contenido in contenidos:
                if not contenido.texto_extraido:
                    continue
                
                # Detectar direcciones en esta página
                direcciones_pagina = self._detectar_en_texto(
                    contenido.texto_extraido,
                    contenido.numero_pagina
                )
                
                # Validar cada dirección con SEPOMEX
                for dir in direcciones_pagina:
                    validacion = await self._validar_direccion(dir)
                    dir['validacion'] = validacion
                    direcciones_detectadas.append(dir)
            
            logger.info(f"Detectadas {len(direcciones_detectadas)} direcciones en tomo {tomo_id}")
            
            return {
                'tomo_id': tomo_id,
                'total_direcciones': len(direcciones_detectadas),
                'direcciones': direcciones_detectadas,
                'estadisticas': self._generar_estadisticas(direcciones_detectadas)
            }
            
        except Exception as e:
            logger.error(f"Error detectando direcciones en tomo {tomo_id}: {e}")
            raise
    
    def _detectar_en_texto(self, texto: str, numero_pagina: int) -> List[Dict[str, Any]]:
        """
        Detecta direcciones en un texto específico
        """
        direcciones = []
        lineas = texto.split('\n')
        
        for i, linea in enumerate(lineas, 1):
            # Buscar patrón completo de dirección
            match_completo = self.compiled_patterns['direccion_completa'].search(linea)
            
            if match_completo:
                # Extraer componentes
                direccion = {
                    'pagina': numero_pagina,
                    'linea': i,
                    'texto_original': linea.strip(),
                    'calle': self._extraer_componente(linea, 'calle'),
                    'numero': self._extraer_componente(linea, 'numero'),
                    'colonia': self._extraer_componente(linea, 'colonia'),
                    'cp': self._extraer_componente(linea, 'cp'),
                    'alcaldia': self._extraer_componente(linea, 'alcaldia') or ''
                }
                direcciones.append(direccion)
            
            # También detectar direcciones parciales
            elif any([
                self.compiled_patterns['calle'].search(linea),
                self.compiled_patterns['colonia'].search(linea),
                self.compiled_patterns['cp'].search(linea)
            ]):
                # Buscar en contexto (líneas adyacentes)
                contexto = self._obtener_contexto(lineas, i)
                direccion_parcial = self._extraer_de_contexto(contexto, numero_pagina, i)
                if direccion_parcial:
                    direcciones.append(direccion_parcial)
        
        return direcciones
    
    def _extraer_componente(self, texto: str, componente: str) -> Optional[str]:
        """
        Extrae un componente específico de una dirección
        """
        if componente not in self.compiled_patterns:
            return None
        
        match = self.compiled_patterns[componente].search(texto)
        if match:
            return match.group(1).strip().upper()
        return None
    
    def _obtener_contexto(self, lineas: List[str], linea_actual: int, ventana: int = 2) -> str:
        """
        Obtiene el contexto alrededor de una línea
        """
        inicio = max(0, linea_actual - ventana - 1)
        fin = min(len(lineas), linea_actual + ventana)
        return ' '.join(lineas[inicio:fin])
    
    def _extraer_de_contexto(
        self, 
        contexto: str, 
        numero_pagina: int, 
        linea: int
    ) -> Optional[Dict[str, Any]]:
        """
        Intenta extraer una dirección completa del contexto
        """
        calle = self._extraer_componente(contexto, 'calle')
        cp = self._extraer_componente(contexto, 'cp')
        
        # Solo crear dirección si al menos tiene calle o CP
        if calle or cp:
            return {
                'pagina': numero_pagina,
                'linea': linea,
                'texto_original': contexto[:200],  # Limitar longitud
                'calle': calle or '',
                'numero': self._extraer_componente(contexto, 'numero') or '',
                'colonia': self._extraer_componente(contexto, 'colonia') or '',
                'cp': cp or '',
                'alcaldia': self._extraer_componente(contexto, 'alcaldia') or ''
            }
        return None
    
    async def _validar_direccion(self, direccion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida una dirección detectada usando SEPOMEX
        """
        validacion = {
            'valida': False,
            'tiene_errores': False,
            'errores': [],
            'sugerencia': None,
            'mensaje': ''
        }
        
        try:
            # Validar código postal si existe
            if direccion.get('cp'):
                resultado_cp = await sepomex_service.validar_codigo_postal(direccion['cp'])
                
                if not resultado_cp.get('valido'):
                    validacion['tiene_errores'] = True
                    validacion['errores'].append(f"Código postal {direccion['cp']} no es válido")
                else:
                    # Validar colonia si existe
                    if direccion.get('colonia'):
                        resultado_colonia = await sepomex_service.validar_colonia_en_cp(
                            direccion['colonia'],
                            direccion['cp']
                        )
                        
                        if not resultado_colonia.get('valida'):
                            validacion['tiene_errores'] = True
                            validacion['errores'].append(
                                f"Colonia '{direccion['colonia']}' no corresponde al CP {direccion['cp']}"
                            )
                            
                            # Sugerir colonias válidas
                            if resultado_colonia.get('similares'):
                                validacion['sugerencia'] = {
                                    'calle': direccion['calle'],
                                    'numero': direccion['numero'],
                                    'colonia': resultado_colonia['similares'][0],
                                    'cp': direccion['cp'],
                                    'alcaldia': resultado_cp.get('municipio', '')
                                }
                                validacion['mensaje'] = (
                                    f"¿Quisiste decir '{resultado_colonia['similares'][0]}'? "
                                    f"Otras opciones: {', '.join(resultado_colonia['similares'][:3])}"
                                )
                        else:
                            validacion['valida'] = True
                            validacion['mensaje'] = 'Dirección validada correctamente con SEPOMEX'
                    else:
                        validacion['tiene_errores'] = True
                        validacion['errores'].append('Falta especificar la colonia')
            else:
                validacion['tiene_errores'] = True
                validacion['errores'].append('Falta el código postal')
            
            # Validar que tenga componentes mínimos
            if not direccion.get('calle'):
                validacion['tiene_errores'] = True
                validacion['errores'].append('Falta el nombre de la calle')
            
            if not direccion.get('numero'):
                validacion['tiene_errores'] = True
                validacion['errores'].append('Falta el número de dirección')
            
        except Exception as e:
            logger.error(f"Error validando dirección: {e}")
            validacion['errores'].append(f"Error en validación: {str(e)}")
        
        return validacion
    
    def _generar_estadisticas(self, direcciones: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera estadísticas sobre las direcciones detectadas
        """
        total = len(direcciones)
        if total == 0:
            return {}
        
        validas = sum(1 for d in direcciones if d.get('validacion', {}).get('valida'))
        con_errores = sum(1 for d in direcciones if d.get('validacion', {}).get('tiene_errores'))
        
        # Alcaldías más frecuentes
        alcaldias = {}
        for d in direcciones:
            if d.get('alcaldia'):
                alcaldias[d['alcaldia']] = alcaldias.get(d['alcaldia'], 0) + 1
        
        return {
            'total': total,
            'validas': validas,
            'con_errores': con_errores,
            'porcentaje_validas': round((validas / total) * 100, 1) if total > 0 else 0,
            'alcaldias_frecuentes': dict(sorted(alcaldias.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    
    async def guardar_direcciones_corregidas(
        self,
        db: Session,
        tomo_id: int,
        direcciones: List[Dict[str, Any]],
        usuario_id: int
    ) -> Dict[str, Any]:
        """
        Guarda las direcciones corregidas en la base de datos
        """
        try:
            from app.models.direccion import DireccionCorregida
            from datetime import datetime
            
            direcciones_guardadas = 0
            
            for dir_data in direcciones:
                # Solo guardar las que fueron revisadas
                if not dir_data.get('revisada'):
                    continue
                
                # Crear registro de dirección corregida
                direccion = DireccionCorregida(
                    tomo_id=tomo_id,
                    pagina=dir_data['pagina'],
                    linea=dir_data.get('linea', 0),
                    texto_original=dir_data['texto_original'],
                    calle=dir_data.get('texto_corregido', {}).get('calle') or dir_data.get('calle'),
                    numero=dir_data.get('texto_corregido', {}).get('numero') or dir_data.get('numero'),
                    colonia=dir_data.get('texto_corregido', {}).get('colonia') or dir_data.get('colonia'),
                    codigo_postal=dir_data.get('texto_corregido', {}).get('cp') or dir_data.get('cp'),
                    alcaldia=dir_data.get('texto_corregido', {}).get('alcaldia') or dir_data.get('alcaldia'),
                    validada_sepomex=dir_data.get('validacion', {}).get('valida', False),
                    editada_manualmente=dir_data.get('editada_manualmente', False),
                    ignorada=dir_data.get('ignorada', False),
                    notas=dir_data.get('notas'),
                    usuario_revision_id=usuario_id,
                    fecha_revision=datetime.now()
                )
                
                db.add(direccion)
                direcciones_guardadas += 1
            
            db.commit()
            
            logger.info(f"Guardadas {direcciones_guardadas} direcciones corregidas para tomo {tomo_id}")
            
            return {
                'success': True,
                'direcciones_guardadas': direcciones_guardadas,
                'mensaje': f'Se guardaron {direcciones_guardadas} direcciones correctamente'
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error guardando direcciones: {e}")
            raise


# Instancia global
direccion_detector = DireccionDetectorService()
