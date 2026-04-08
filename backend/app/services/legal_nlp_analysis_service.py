"""
Servicio de análisis NLP para documentos legales mexicanos
Extrae: diligencias, personas, lugares, fechas y genera alertas
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from dateutil import parser as date_parser
import unicodedata

# Importar el extractor de párrafos estructurados
from app.services.extractor_parrafos_estructurados import extractor_parrafos

logger = logging.getLogger(__name__)


class LegalNLPAnalysisService:
    """Servicio de análisis NLP para documentos jurídicos"""
    
    # Patrones para tipos de diligencias
    TIPOS_DILIGENCIAS = {
        'informe_pericial': [
            r'informe\s+pericial',
            r'peritaje',
            r'dictamen\s+pericial',
            r'opinión\s+técnica'
        ],
        'declaración': [
            r'declaración',
            r'declara',
            r'declaró',
            r'manifestó',
            r'manifestación'
        ],
        'inspección': [
            r'inspección',
            r'fe\s+ministerial',
            r'inspección\s+ocular'
        ],
        'entrevista': [
            r'entrevista',
            r'se\s+entrevistó'
        ],
        'solicitud': [
            r'solicitud',
            r'se\s+solicita',
            r'oficio\s+de\s+petición'
        ],
        'orden': [
            r'orden\s+de',
            r'se\s+ordena',
            r'orden\s+ministerial'
        ],
        'citatorio': [
            r'citatorio',
            r'se\s+cita',
            r'comparecencia\s+citada'
        ],
        'acuerdo': [
            r'acuerdo',
            r'se\s+acuerda',
            r'acuerdo\s+ministerial'
        ],
        'oficio': [
            r'oficio\s+n[úu]m',
            r'oficio\s+número'
        ]
    }
    
    # Patrones para roles de personas
    ROLES_PERSONAS = {
        'víctima': [r'víctima', r'ofendid[ao]', r'afectad[ao]'],
        'testigo': [r'testigo', r'declarante'],
        'imputado': [r'imputad[ao]', r'acusad[ao]', r'indiciado', r'presunto responsable'],
        'perito': [r'perito', r'experto', r'especialista'],
        'ministerio_publico': [r'ministerio público', r'MP', r'agente', r'fiscal'],
        'defensor': [r'defensor', r'abogado defensor'],
        'policia': [r'policía', r'agente policial', r'elemento'],
        'familiar': [r'familiar', r'hermano', r'hermana', r'padre', r'madre', r'hijo', r'hija', r'esposo', r'esposa']
    }
    
    # Palabras comunes en direcciones mexicanas
    PALABRAS_DIRECCION = [
        'avenida', 'calle', 'calzada', 'boulevard', 'privada', 'andador',
        'cerrada', 'callejón', 'paseo', 'viaducto', 'periférico', 'diagonal',
        'colonia', 'fraccionamiento', 'unidad', 'conjunto', 'residencial',
        'municipio', 'delegación', 'estado', 'ciudad'
    ]
    
    # Meses en español
    MESES = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    def __init__(self):
        """Inicializar servicio de análisis"""
        pass
    
    def analizar_documento_completo(
        self,
        texto: str,
        numero_pagina: int = 1,
        contexto_carpeta: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Análisis completo de un documento
        
        Args:
            texto: Texto del documento
            numero_pagina: Número de página
            contexto_carpeta: Contexto adicional de la carpeta
            
        Returns:
            Dict con todos los elementos extraídos
        """
        resultado = {
            "diligencias": [],
            "personas": [],
            "lugares": [],
            "fechas": [],
            "oficios": [],
            "telefonos": [],
            "errores": []
        }
        
        try:
            # Extraer diligencias
            resultado["diligencias"] = self.extraer_diligencias(texto, numero_pagina)
            
            # Extraer personas
            resultado["personas"] = self.extraer_personas(texto, numero_pagina)
            
            # Extraer lugares y direcciones
            resultado["lugares"] = self.extraer_lugares(texto, numero_pagina)
            
            # Extraer fechas
            resultado["fechas"] = self.extraer_fechas(texto, numero_pagina)
            
            # Extraer números de oficio
            resultado["oficios"] = self.extraer_oficios(texto)
            
            # Extraer teléfonos
            resultado["telefonos"] = self.extraer_telefonos(texto)

            # Enriquecer resultados con validaciones adicionales
            self._postprocesar_resultado(texto, resultado)
        
        except Exception as e:
            logger.error(f"Error en análisis completo: {str(e)}")
            resultado["errores"].append(str(e))
        
        return resultado

    def _postprocesar_resultado(self, texto: str, resultado: Dict[str, any]) -> None:
        """Ajusta y depura las entidades extraídas para mejorar calidad."""
        resultado["diligencias"] = self._enriquecer_diligencias(
            resultado.get("diligencias", []),
            texto,
            resultado.get("oficios", [])
        )

        resultado["telefonos"] = self._deduplicar_telefonos(resultado.get("telefonos", []))

        resultado["personas"] = self._enriquecer_personas(
            resultado.get("personas", []),
            resultado.get("telefonos", [])
        )

        resultado["lugares"] = self._deduplicar_lugares(resultado.get("lugares", []))

        resultado["fechas"] = self._enriquecer_fechas(resultado.get("fechas", []))
    
    def _enriquecer_diligencias(self, diligencias: List[Dict], texto: str, oficios: List[str]) -> List[Dict]:
        oficios_usados = set()
        resultado = []

        for diligencia in diligencias:
            datos = diligencia.copy()

            if not datos.get("tipo"):
                datos["tipo"] = "Diligencia"

            if not datos.get("responsable"):
                responsable = self._buscar_responsable_ampliado(datos.get("contexto", ""))
                if not responsable:
                    responsable = self._buscar_responsable_ampliado(texto)
                if responsable:
                    datos["responsable"] = responsable

            if not datos.get("oficio") and oficios:
                contexto = datos.get("contexto", "")
                for oficio in oficios:
                    if oficio in oficios_usados:
                        continue
                    if oficio in contexto:
                        datos["oficio"] = oficio
                        oficios_usados.add(oficio)
                        break
                else:
                    for oficio in oficios:
                        if oficio not in oficios_usados:
                            datos["oficio"] = oficio
                            oficios_usados.add(oficio)
                            break

            if not datos.get("fecha"):
                datos["fecha"] = self._extraer_fecha_de_texto(datos.get("contexto", ""))

            resultado.append(datos)

        return resultado

    def _deduplicar_telefonos(self, telefonos: List[str]) -> List[str]:
        normalizados = []
        vistos = set()

        for telefono in telefonos:
            limpio = self._normalizar_telefono(telefono)
            if limpio and limpio not in vistos:
                vistos.add(limpio)
                normalizados.append(limpio)

        return normalizados

    def _clave_similar_existe(self, clave_nueva: str, claves_existentes: set, umbral: float = 0.88) -> bool:
        """Detectar si ya existe un nombre muy similar (variantes OCR) usando similitud de cadenas."""
        from difflib import SequenceMatcher
        for clave in claves_existentes:
            ratio = SequenceMatcher(None, clave_nueva, clave).ratio()
            if ratio >= umbral:
                return True
        return False

    def _enriquecer_personas(self, personas: List[Dict], telefonos_globales: List[str]) -> List[Dict]:
        resultado = []
        nombres_vistos = set()
        telefonos_usados = set()

        for persona in personas:
            nombre_original = persona.get("nombre", "").strip()
            if not nombre_original:
                continue

            nombre_limpio = self._limpiar_nombre_display(nombre_original)
            if not nombre_limpio:
                continue

            clave = self._clave_nombre(nombre_limpio)
            if clave in nombres_vistos:
                continue
            # Deduplicación fuzzy: rechazar nombres que son variantes OCR de uno ya visto
            # (ej: "Ferando Santiago" ≈ "Fernando Santiago", "Salva Reza" ≈ "Salvador Reza")
            if self._clave_similar_existe(clave, nombres_vistos):
                continue

            datos = persona.copy()
            datos["nombre"] = nombre_limpio
            if not datos.get("rol"):
                datos["rol"] = "Desconocido"

            datos["telefono"] = self._normalizar_telefono(datos.get("telefono"))
            if not datos["telefono"] and telefonos_globales:
                for telefono in telefonos_globales:
                    if telefono not in telefonos_usados:
                        datos["telefono"] = telefono
                        telefonos_usados.add(telefono)
                        break

            if datos.get("direccion"):
                datos["direccion"] = self._normalizar_espacios(datos["direccion"])

            resultado.append(datos)
            nombres_vistos.add(clave)

        return resultado

    def _deduplicar_lugares(self, lugares: List[Dict]) -> List[Dict]:
        resultado = []
        vistos = set()

        for lugar in lugares:
            direccion = lugar.get("direccion_completa", "")
            if not direccion:
                continue

            clave = self._normalizar_espacios(direccion).lower()
            if clave in vistos:
                continue

            datos = lugar.copy()
            datos["direccion_completa"] = self._normalizar_espacios(direccion)
            resultado.append(datos)
            vistos.add(clave)

        return resultado

    def _enriquecer_fechas(self, fechas: List[Dict]) -> List[Dict]:
        resultado = []
        fechas_vistas = set()

        for fecha in fechas:
            valor = fecha.get("fecha")
            if not valor:
                continue

            if valor in fechas_vistas:
                continue

            datos = fecha.copy()
            if not datos.get("tipo"):
                datos["tipo"] = self._clasificar_fecha(datos.get("contexto", ""))

            resultado.append(datos)
            fechas_vistas.add(valor)

        return resultado

    def extraer_diligencias(self, texto: str, numero_pagina: int) -> List[Dict]:
        """
        Extraer diligencias del texto usando extractor de párrafos estructurados
        
        Este método ahora usa el ExtractorParrafosEstructurados que:
        - Identifica párrafos relevantes con elementos legales
        - Extrae información estructurada (fechas, oficios, nombres, etc.)
        - Clasifica el tipo de documento
        - Genera resúmenes automáticos
        """
        diligencias = []
        
        # Usar el extractor de párrafos estructurados
        parrafos_estructurados = extractor_parrafos.extraer_parrafos_estructurados(
            texto=texto,
            numero_pagina=numero_pagina,
            min_longitud=100,
            max_longitud=3000
        )
        
        # Convertir cada párrafo estructurado en una diligencia
        for parrafo_struct in parrafos_estructurados:
            # Determinar tipo de diligencia basado en el tipo de documento
            tipo_documento = parrafo_struct.get('tipo_documento', 'documento_general')
            tipo_diligencia = self._mapear_tipo_documento_a_diligencia(tipo_documento)
            
            # Extraer fecha principal
            fecha_principal = None
            elementos = parrafo_struct.get('elementos', {})
            
            if elementos.get('fechas_detalladas'):
                # Usar la primera fecha encontrada
                primera_fecha = elementos['fechas_detalladas'][0]
                fecha_principal = self._convertir_fecha_detallada(primera_fecha)
            
            # Extraer responsable
            responsable = None
            if elementos.get('nombre_titular'):
                responsable = elementos['nombre_titular'][0]
            elif elementos.get('nombres_mencionados'):
                responsable = elementos['nombres_mencionados'][0]
            
            # Extraer oficio
            oficio = None
            if elementos.get('oficio'):
                oficio = elementos['oficio'][0]
            
            # Calcular confianza
            relevancia = parrafo_struct.get('relevancia', 0)
            confianza = min(1.0, relevancia / 10.0)  # Normalizar a 0-1
            
            diligencia = {
                "tipo": tipo_diligencia,
                "fecha": fecha_principal,
                "responsable": responsable,
                "oficio": oficio,
                "descripcion": parrafo_struct.get('resumen', '')[:500],
                "contexto": parrafo_struct.get('texto_completo', ''),
                "pagina": numero_pagina,
                "confianza": confianza,
                "parrafo_estructurado": parrafo_struct  # ¡NUEVO! Guardar toda la info estructurada
            }
            
            diligencias.append(diligencia)
        
        return diligencias
    
    def _mapear_tipo_documento_a_diligencia(self, tipo_documento: str) -> str:
        """Mapea el tipo de documento detectado a un tipo de diligencia"""
        mapeo = {
            'oficio_solicitud': 'Solicitud',
            'oficio_informativo': 'Informe',
            'oficio_general': 'Oficio',
            'constancia': 'Fe Ministerial',
            'comunicado_oficial': 'Comunicado',
            'acta_hechos': 'Acta De Hechos',
            'actuacion_ministerial': 'Actuación Ministerial',
            'documento_general': 'Diligencia General'
        }
        return mapeo.get(tipo_documento, 'Diligencia General')
    
    def _convertir_fecha_detallada(self, fecha_det: Dict) -> Optional[str]:
        """
        Convierte una fecha detallada a formato ISO
        
        Args:
            fecha_det: Dict con keys 'dia', 'mes', 'anio'
            
        Returns:
            Fecha en formato ISO (YYYY-MM-DD) o None si es inválida
        """
        try:
            mes_num = self.MESES.get(fecha_det['mes'].lower())
            if not mes_num:
                return None
            
            fecha_obj = date(
                year=fecha_det['anio'],
                month=mes_num,
                day=fecha_det['dia']
            )
            
            # Validar que la fecha esté en rango válido
            if self._es_fecha_valida(fecha_obj):
                return fecha_obj.isoformat()
            
            return None
        except (ValueError, KeyError):
            return None
    
    def extraer_personas(self, texto: str, numero_pagina: int) -> List[Dict]:
        """Extraer personas mencionadas"""
        personas = []
        nombres_encontrados = set()
        
        # Patrón para nombres (mayúsculas seguidas)
        patron_nombre = r'\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,4})\b'
        
        matches = re.finditer(patron_nombre, texto)
        
        for match in matches:
            nombre = match.group(1).strip()
            
            # Filtrar palabras comunes que no son nombres
            if self._es_nombre_valido(nombre) and nombre not in nombres_encontrados:
                nombres_encontrados.add(nombre)
                
                # Extraer contexto alrededor del nombre
                inicio = max(0, match.start() - 100)
                fin = min(len(texto), match.end() + 100)
                contexto = texto[inicio:fin]
                
                # Determinar rol
                rol = self._determinar_rol(contexto)
                
                # Buscar dirección cerca del nombre
                direccion = self._extraer_direccion_cerca(texto, match.start())
                
                # Buscar teléfono cerca del nombre
                telefono = self._extraer_telefono_cerca(texto, match.start())
                
                persona = {
                    "nombre": nombre,
                    "rol": rol,
                    "direccion": direccion,
                    "telefono": telefono,
                    "contexto": contexto,
                    "pagina": numero_pagina,
                    "confianza": 0.7
                }
                
                personas.append(persona)
        
        return personas
    
    # Palabras que indican que lo que sigue a CALLE/AVENIDA NO es un nombre de calle sino basura OCR
    _PALABRAS_NO_NOMBRE_CALLE = re.compile(
        r'^(?:se\b|en\b|de\b|los\b|las\b|fue|fueron|son|ha|han|esta|están|está|que|por\b|para\b|con\b|del\b|al\b)',
        re.IGNORECASE
    )

    def extraer_lugares(self, texto: str, numero_pagina: int) -> List[Dict]:
        """Extraer lugares y direcciones"""
        lugares = []
        
        # Patrones para direcciones — el nombre debe empezar con letra mayúscula (nombre propio)
        # [^,\n]{5,100} reemplazado por [A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ][^,\n;]{3,60} para evitar basura OCR
        patrones_direccion = [
            r'((?:avenida|av\.?|calle|calzada|blvd\.?|boulevard|privada|andador|cerrada)\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ][^,\n;]{3,60})',
            r'(colonia\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ][^,\n;]{2,50})',
            r'(municipio\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ][^,\n;]{2,50})',
            r'(fraccionamiento\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ][^,\n;]{2,50})'
        ]
        
        for patron in patrones_direccion:
            matches = re.finditer(patron, texto, re.IGNORECASE)
            
            for match in matches:
                direccion = match.group(1).strip()
                
                # Extraer la parte del nombre (después del keyword de vía)
                # Si el texto después del keyword empieza con preposición/artículo común → basura OCR
                keyword_match = re.match(
                    r'^(?:avenida|av\.?|calle|calzada|blvd\.?|boulevard|privada|andador|cerrada|colonia|municipio|fraccionamiento)\s+',
                    direccion, re.IGNORECASE
                )
                if keyword_match:
                    resto = direccion[keyword_match.end():]
                    if self._PALABRAS_NO_NOMBRE_CALLE.match(resto):
                        continue  # Basura OCR — omitir
                    # Rechazar si el "nombre" tiene más de 3 palabras en MAYÚSCULAS seguidas
                    # (indicativo de texto institucional/OCR), a menos que sea una institución real
                    if re.search(r'[A-Z]{3,}\s+[A-Z]{3,}\s+[A-Z]{3,}\s+[A-Z]{3,}', resto):
                        continue
                
                # Rechazar direcciones que contienen números de expediente / código de barras
                if re.search(r'\b(?:PGR|FGR|AP|A\.P\.|SEIDO|UEIDO|REV|FO-FF|IT-FF)\b', direccion):
                    continue
                
                # Extraer componentes
                componentes = self._parsear_direccion(direccion)
                
                # Extraer contexto
                inicio = max(0, match.start() - 50)
                fin = min(len(texto), match.end() + 50)
                contexto = texto[inicio:fin]
                
                lugar = {
                    "direccion_completa": direccion,
                    "componentes": componentes,
                    "tipo": componentes.get("tipo", "dirección"),
                    "contexto": contexto,
                    "pagina": numero_pagina,
                    "confianza": 0.75
                }
                
                lugares.append(lugar)
        
        return lugares
    
    def extraer_fechas(self, texto: str, numero_pagina: int) -> List[Dict]:
        """Extraer fechas mencionadas"""
        fechas = []
        
        # Patrones de fechas en español
        _meses_alt = '|'.join(self.MESES.keys())
        patrones_fecha = [
            # "5 de enero de 2023" / "5 de enero del 2023"
            r'(\d{1,2})\s+de\s+(' + _meses_alt + r')\s+del?\s+(\d{4})',
            # "a 15 de enero de/del 2023" (con preposición inicial)
            r'a\s+(\d{1,2})\s+de\s+(' + _meses_alt + r')\s+del?\s+(\d{4})',
            # "05/01/2023" o "5-1-2023"
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
            # "enero 5, 2023"
            r'(' + _meses_alt + r')\s+(\d{1,2}),?\s+(\d{4})',
            # Solo mes + año: "enero de 2014", "enero del 2014"
            r'\b(' + _meses_alt + r')\s+del?\s+(\d{4})\b',
        ]
        
        for patron in patrones_fecha:
            matches = re.finditer(patron, texto, re.IGNORECASE)
            
            for match in matches:
                fecha_texto = match.group(0)
                
                # Intentar parsear la fecha
                fecha_obj = self._parsear_fecha(fecha_texto)
                
                if fecha_obj:
                    # Extraer contexto
                    inicio = max(0, match.start() - 100)
                    fin = min(len(texto), match.end() + 100)
                    contexto = texto[inicio:fin]
                    
                    # Clasificar tipo de fecha
                    tipo_fecha = self._clasificar_fecha(contexto)
                    
                    fecha_info = {
                        "fecha": fecha_obj.isoformat(),
                        "fecha_texto": fecha_texto,
                        "tipo": tipo_fecha,
                        "contexto": contexto,
                        "pagina": numero_pagina,
                        "confianza": 0.85
                    }
                    
                    fechas.append(fecha_info)
        
        return fechas
    
    def extraer_oficios(self, texto: str) -> List[str]:
        """Extraer números de oficio"""
        oficios = []
        
        # Patrones para oficios
        patrones = [
            r'oficio\s+n[úu]m(?:ero)?\s*[.:]?\s*([A-Z0-9/-]+)',
            r'oficio\s+([A-Z0-9/-]{5,})',
            r'n[úu]m(?:ero)?\s+de\s+oficio\s*[.:]?\s*([A-Z0-9/-]+)'
        ]
        
        for patron in patrones:
            matches = re.finditer(patron, texto, re.IGNORECASE)
            for match in matches:
                oficio = match.group(1).strip()
                if oficio not in oficios:
                    oficios.append(oficio)
        
        return oficios
    
    def extraer_telefonos(self, texto: str) -> List[str]:
        """Extraer números telefónicos"""
        telefonos = []
        
        # Patrones para teléfonos mexicanos
        patrones = [
            r'\b(\d{3})[- ]?(\d{3})[- ]?(\d{4})\b',  # 555-123-4567
            r'\b(\d{2})[- ]?(\d{4})[- ]?(\d{4})\b',  # 55-1234-5678
            r'\b(\(\d{3}\))[- ]?(\d{3})[- ]?(\d{4})\b',  # (555) 123-4567
        ]
        
        for patron in patrones:
            matches = re.finditer(patron, texto)
            for match in matches:
                telefono = ''.join(match.groups()).replace('(', '').replace(')', '')
                if telefono not in telefonos and len(telefono) == 10:
                    telefonos.append(telefono)
        
        return telefonos
    
    def generar_alertas_inactividad(
        self,
        diligencias: List[Dict],
        umbral_dias: int = 180
    ) -> List[Dict]:
        """
        Generar alertas de inactividad del MP
        
        Args:
            diligencias: Lista de diligencias ordenadas cronológicamente
            umbral_dias: Días de inactividad para generar alerta
            
        Returns:
            Lista de alertas
        """
        alertas = []
        
        if not diligencias or len(diligencias) < 2:
            return alertas
        
        # Ordenar diligencias por fecha
        diligencias_ordenadas = sorted(
            [d for d in diligencias if d.get('fecha')],
            key=lambda x: x['fecha']
        )
        
        for i in range(len(diligencias_ordenadas) - 1):
            diligencia_actual = diligencias_ordenadas[i]
            diligencia_siguiente = diligencias_ordenadas[i + 1]
            
            try:
                fecha_actual = date_parser.parse(diligencia_actual['fecha']).date()
                fecha_siguiente = date_parser.parse(diligencia_siguiente['fecha']).date()

                # 🔍 VALIDACIÓN ESTRICTA: Solo fechas plausibles
                if not (self._es_fecha_valida(fecha_actual) and self._es_fecha_valida(fecha_siguiente)):
                    logger.debug(
                        f"⚠️ Fechas descartadas en alerta - Actual: {fecha_actual}, Siguiente: {fecha_siguiente}"
                    )
                    continue
                
                dias_diferencia = (fecha_siguiente - fecha_actual).days

                # No generar alertas con días negativos o cero
                if dias_diferencia <= 0:
                    continue
                
                # Validar que la diferencia no sea absurda (> 5 años)
                if dias_diferencia > 1825:  # 5 años
                    logger.debug(
                        f"⚠️ Diferencia absurda descartada: {dias_diferencia} días entre {fecha_actual} y {fecha_siguiente}"
                    )
                    continue
                
                if dias_diferencia >= umbral_dias:
                    # Determinar prioridad
                    if dias_diferencia >= 365:
                        prioridad = 'crítica'
                    elif dias_diferencia >= 270:
                        prioridad = 'alta'
                    elif dias_diferencia >= 180:
                        prioridad = 'media'
                    else:
                        prioridad = 'baja'
                    
                    alerta = {
                        "tipo": "inactividad_mp",
                        "prioridad": prioridad,
                        "dias_inactividad": dias_diferencia,
                        "fecha_ultima_actuacion": diligencia_actual['fecha'],
                        "fecha_siguiente_actuacion": diligencia_siguiente['fecha'],
                        "ultima_diligencia": diligencia_actual,
                        "descripcion": f"Inactividad de {dias_diferencia} días entre actuaciones del MP"
                    }
                    
                    alertas.append(alerta)
            
            except Exception as e:
                logger.error(f"Error calculando diferencia de fechas: {str(e)}")
        
        return alertas
    
    # Métodos auxiliares privados
    
    def _buscar_responsable_ampliado(self, texto: str) -> Optional[str]:
        if not texto:
            return None

        patrones = [
            r'responsable\s*[:\-]\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ\.\s]{2,80})',
            r'(?:lic\.?|dra\.?|dr\.?|ing\.?|c\.?|ciudadan[ao])\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ]+){1,3})',
            r'(?:agente|fiscal|ministerio\s+público)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑ]+){1,3})'
        ]

        for patron in patrones:
            coincidencia = re.search(patron, texto, re.IGNORECASE)
            if coincidencia:
                nombre = coincidencia.group(1).strip()
                nombre = re.sub(r'\s+(?:del|de|la|el)\s+ministerio.*$', '', nombre, flags=re.IGNORECASE)
                nombre = re.sub(r'\s+(?:agente|fiscal|mp)$', '', nombre, flags=re.IGNORECASE)
                nombre = self._normalizar_espacios(nombre)
                if self._es_nombre_valido(nombre):
                    return nombre

        return None

    def _normalizar_telefono(self, telefono: Optional[str]) -> Optional[str]:
        if not telefono:
            return None

        digitos = re.sub(r'\D', '', telefono)
        if len(digitos) == 10:
            return digitos
        return None

    def _normalizar_espacios(self, texto: str) -> str:
        return re.sub(r'\s+', ' ', texto.strip())

    def _limpiar_nombre_display(self, nombre: str) -> Optional[str]:
        if not nombre:
            return None

        texto = self._normalizar_espacios(nombre)
        texto = texto.strip(',.;:')
        texto = re.sub(r'^(lic\.?|dr\.?|dra\.?|ing\.?|c\.?|ciudadan[ao])\s+', '', texto, flags=re.IGNORECASE)
        texto = re.sub(r'\s+(del\s+ministerio\s+público|agente\s+del\s+mp|fiscal)$', '', texto, flags=re.IGNORECASE)
        texto = self._normalizar_espacios(texto)
        return texto if len(texto.split()) >= 2 else None

    def _clave_nombre(self, nombre: str) -> str:
        texto = unicodedata.normalize('NFKD', nombre)
        texto = ''.join(c for c in texto if not unicodedata.category(c).startswith('Mn'))
        texto = re.sub(r'[^A-Za-z\s]', '', texto)
        texto = self._normalizar_espacios(texto)
        return texto.upper()

    def _extraer_fecha_de_texto(self, texto: str) -> Optional[str]:
        """Extraer primera fecha encontrada en el texto"""
        patron = r'(\d{1,2})\s+de\s+(' + '|'.join(self.MESES.keys()) + r')\s+de\s+(\d{4})'
        match = re.search(patron, texto, re.IGNORECASE)
        
        if match:
            dia = int(match.group(1))
            mes = self.MESES[match.group(2).lower()]
            anio = int(match.group(3))
            
            try:
                fecha = date(anio, mes, dia)
                if self._es_fecha_valida(fecha):
                    return fecha.isoformat()
                return None
            except:
                return None
        
        return None
    
    def _extraer_responsable(self, texto: str) -> Optional[str]:
        """Extraer nombre del responsable de la diligencia"""
        # Buscar después de palabras clave
        patrones = [
            r'realiz[oóa]\s+(?:por|el)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
            r'(?:licenciado|doctor|ingeniero)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})',
            r'agente\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})'
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extraer_oficio_de_texto(self, texto: str) -> Optional[str]:
        """Extraer número de oficio del texto"""
        patron = r'oficio\s+n[úu]m(?:ero)?\s*[.:]?\s*([A-Z0-9/-]+)'
        match = re.search(patron, texto, re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        return None
    
    def _es_nombre_valido(self, nombre: str) -> bool:
        """Verificar si un string es un nombre válido"""
        # Filtrar palabras comunes que no son nombres
        palabras_excluir = {
            'Ministerio Público', 'Fiscalía', 'Estado', 'México', 'Ciudad',
            'Código', 'Artículo', 'Fracción', 'Penal', 'Civil', 'Carpeta',
            'Investigación', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo',
            'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        }
        
        if nombre in palabras_excluir:
            return False
        
        # Debe tener al menos 2 palabras
        palabras = nombre.split()
        if len(palabras) < 2:
            return False
        
        # No debe ser muy largo
        if len(palabras) > 5:
            return False
        
        return True
    
    def _determinar_rol(self, contexto: str) -> Optional[str]:
        """Determinar el rol de una persona basado en el contexto"""
        for rol, patrones in self.ROLES_PERSONAS.items():
            for patron in patrones:
                if re.search(patron, contexto, re.IGNORECASE):
                    return rol.replace('_', ' ').title()
        
        return None
    
    def _extraer_direccion_cerca(self, texto: str, posicion: int, radio: int = 300) -> Optional[str]:
        """Extraer dirección cerca de una posición"""
        inicio = max(0, posicion - radio)
        fin = min(len(texto), posicion + radio)
        fragmento = texto[inicio:fin]
        
        patron = r'((?:avenida|av\.?|calle|calzada|boulevard)\s+[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ][^,\n;]{3,60})'
        match = re.search(patron, fragmento, re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extraer_telefono_cerca(self, texto: str, posicion: int, radio: int = 200) -> Optional[str]:
        """Extraer teléfono cerca de una posición"""
        inicio = max(0, posicion - radio)
        fin = min(len(texto), posicion + radio)
        fragmento = texto[inicio:fin]
        
        patron = r'\b(\d{3})[- ]?(\d{3})[- ]?(\d{4})\b'
        match = re.search(patron, fragmento)
        
        if match:
            return ''.join(match.groups())
        
        return None
    
    def _parsear_direccion(self, direccion: str) -> Dict[str, str]:
        """Parsear componentes de una dirección"""
        componentes = {}
        
        # Tipo de vía
        for tipo_via in ['avenida', 'calle', 'calzada', 'boulevard', 'privada']:
            if tipo_via in direccion.lower():
                componentes['tipo'] = tipo_via
                break
        
        # Colonia
        match_colonia = re.search(r'colonia\s+([^,\n]+)', direccion, re.IGNORECASE)
        if match_colonia:
            componentes['colonia'] = match_colonia.group(1).strip()
        
        # Municipio
        match_municipio = re.search(r'municipio\s+([^,\n]+)', direccion, re.IGNORECASE)
        if match_municipio:
            componentes['municipio'] = match_municipio.group(1).strip()
        
        return componentes
    
    def _parsear_fecha(self, fecha_texto: str) -> Optional[date]:
        """Parsear texto de fecha a objeto date"""
        try:
            # Intentar con dateutil
            fecha = date_parser.parse(fecha_texto, dayfirst=True).date()
            if self._es_fecha_valida(fecha):
                return fecha
            return None
        except:
            # Intentar manualmente — soporta "de YYYY" y "del YYYY"
            patron = r'(\d{1,2})\s+de\s+(\w+)\s+del?\s+(\d{4})'
            match = re.search(patron, fecha_texto, re.IGNORECASE)
            
            if match:
                dia = int(match.group(1))
                mes_nombre = match.group(2).lower()
                anio = int(match.group(3))

                if mes_nombre in self.MESES:
                    mes = self.MESES[mes_nombre]
                    try:
                        fecha = date(anio, mes, dia)
                        if self._es_fecha_valida(fecha):
                            return fecha
                    except:
                        pass
            
            # Sobrescribir: solo mes + año ("enero del 2014")
            patron_mes_anio = r'^(' + '|'.join(self.MESES.keys()) + r')\s+del?\s+(\d{4})$'
            match2 = re.search(patron_mes_anio, fecha_texto.strip(), re.IGNORECASE)
            if match2:
                mes_nombre = match2.group(1).lower()
                anio = int(match2.group(2))
                if mes_nombre in self.MESES and 1990 <= anio <= datetime.now().year + 1:
                    # Devolver el 1° del mes como placeholder
                    try:
                        return date(anio, self.MESES[mes_nombre], 1)
                    except:
                        pass
            
            return None
    
    def _clasificar_fecha(self, contexto: str) -> str:
        """Clasificar el tipo de fecha basado en el contexto"""
        contexto_lower = contexto.lower()
        
        if any(palabra in contexto_lower for palabra in ['hechos', 'ocurrieron', 'sucedió']):
            return 'fecha_hechos'
        elif any(palabra in contexto_lower for palabra in ['actuación', 'diligencia', 'ministerio']):
            return 'actuacion_mp'
        elif any(palabra in contexto_lower for palabra in ['audiencia', 'comparecencia']):
            return 'audiencia'
        elif any(palabra in contexto_lower for palabra in ['declaración', 'manifestó']):
            return 'declaracion'
        else:
            return 'fecha_general'

    def _es_fecha_valida(self, fecha: date) -> bool:
        """
        Validar que una fecha sea plausible para expedientes de fiscalía
        - No acepta fechas muy antiguas (antes de 2015)
        - No acepta fechas futuras más allá de 1 año
        """
        current_date = datetime.now().date()
        current_year = current_date.year
        
        # Rango plausible: documentos históricos (desde 1990) hasta 1 año en el futuro
        # Nota: expedientes PGR/FGJ pueden tener fechas desde los años 90
        fecha_minima = date(1990, 1, 1)
        fecha_maxima = date(current_year + 1, 12, 31)
        
        return fecha_minima <= fecha <= fecha_maxima


# Instancia global del servicio
legal_nlp_service = LegalNLPAnalysisService()
