# app/services/spacy_ner_service.py
# Sistema OCR con Análisis Jurídico
# Extractor de entidades basado en spaCy NER (es_core_news_lg)
# Complementa la extracción regex — especialmente útil en documentos deteriorados

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime

logger = logging.getLogger("ridac_ocr")


# ---------------------------------------------------------------------------
# Carga del modelo de spaCy (singleton por proceso)
# ---------------------------------------------------------------------------

_nlp = None   # es_core_news_lg  (preciso, para producción)
_nlp_sm = None  # es_core_news_sm  (fallback rápido)


def _load_model():
    """Carga el modelo spaCy la primera vez que se necesita."""
    global _nlp, _nlp_sm
    if _nlp is not None:
        return _nlp

    try:
        import spacy
        _nlp = spacy.load("es_core_news_lg")
        # Deshabilitar componentes innecesarios para velocidad
        _nlp.select_pipes(enable=["tok2vec", "ner"])
        logger.info("✅ spaCy es_core_news_lg cargado correctamente")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo cargar es_core_news_lg: {e}. Intentando sm...")
        try:
            import spacy
            _nlp = spacy.load("es_core_news_sm")
            _nlp.select_pipes(enable=["tok2vec", "ner"])
            logger.info("✅ spaCy es_core_news_sm cargado como fallback")
        except Exception as e2:
            logger.error(f"❌ spaCy no disponible: {e2}")
            _nlp = None

    return _nlp


# ---------------------------------------------------------------------------
# Sets de filtrado rápido
# ---------------------------------------------------------------------------

_PALABRAS_EXCLUIR_PERSONA = {
    # Instituciones
    'ministerio', 'procuraduría', 'procuraduria', 'fiscalía', 'fiscalia',
    'secretaría', 'secretaria', 'gobierno', 'presidencia', 'subsecretaría',
    # Documentos
    'código', 'codigo', 'artículo', 'articulo', 'reglamento', 'decreto',
    'acuerdo', 'oficio', 'expediente', 'averiguación',
    # Meses
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
    # Genéricos
    'ciudad', 'estado', 'municipio', 'colonia', 'avenida', 'calle',
    'señor', 'señora', 'ciudadano',
}

_LABELS_PERSONA = {'PER'}
_LABELS_LUGAR  = {'LOC', 'GPE', 'FAC'}  # ORG excluido: son instituciones, no ubicaciones físicas
_LABELS_FECHA  = {'DATE', 'TIME'}

# Palabras que al inicio de un fragmento indican que NO es un lugar geográfico
_PREPOSICIONES_INICIO = frozenset({
    'en', 'se', 'de', 'la', 'el', 'los', 'las', 'lo', 'un', 'una', 'al', 'del',
    'por', 'con', 'para', 'que', 'no', 'ya', 'si', 'ni', 'o', 'y', 'a',
    'su', 'sus', 'mi', 'tu', 'le', 'les', 'nos',
})

# Primera palabra que delata terminología procesal/legal, no un lugar
_PALABRAS_NO_LUGAR_INICIO = frozenset({
    # Terminología procesal
    'materia', 'practicadas', 'emplazamiento', 'fotografía', 'fotografia',
    'forense', 'investigación', 'investigacion', 'criminal', 'delito',
    'fracción', 'fraccion', 'articulo', 'artículo', 'inciso', 'resumen',
    'circular', 'constitución', 'constitucional', 'notificación', 'notificacion',
    'gestión', 'gestion', 'administración', 'administracion',
    'código', 'codigo', 'ley', 'reglamento', 'decreto', 'art', 'previa',
    'actuación', 'actuacion', 'diligencia', 'constancia', 'oficio',
    'coordinación', 'coordinacion', 'laboratorio', 'laboratorios',
    'pericial', 'periciales', 'fotografias', 'fotografías',
    # Pisos/plantas (no son lugares geográficos)
    'piso', 'planta', 'nivel', 'primer', 'primero', 'segundo', 'tercero',
    'tercer', 'cuarto', 'quinto', 'séptimo', 'sexto', 'último',
    # Descriptores genéricos
    'número', 'numero', 'departamento', 'sección', 'seccion', 'turno',
    # Colores (no son lugares)
    'azul', 'negro', 'negra', 'blanco', 'blanca', 'verde', 'rojo', 'roja',
    'amarillo', 'gris', 'café', 'naranja', 'morado', 'dorado', 'obscuro', 'oscuro',
})

# Meses en español → número
_MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
}


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------

class SpacyNERService:
    """
    Extractor de entidades usando spaCy es_core_news_lg.

    Especialidades vs. regex:
    - Detecta nombres incluso cuando parte del nombre fue corrupto por OCR
      (usa vectores de palabra, no patrones exactos)
    - Detecta ubicaciones geográficas por contexto, no solo por lista
    - Detecta fechas escritas en lenguaje natural
    - No requiere palabras clave previas al nombre (Lic., C., etc.)
    """

    def __init__(self):
        # Cargar modelo (puede tardar 2-3 s la primera vez)
        _load_model()

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------

    def extraer_entidades(
        self,
        texto: str,
        numero_pagina: int,
        max_chars: int = 100_000
    ) -> Dict[str, List[Dict]]:
        """
        Extrae personas, lugares y fechas del texto con spaCy NER.

        Returns:
            {
              "personas": [ {"nombre": ..., "pagina": ..., "confianza": ...} ],
              "lugares":  [ {"direccion_completa": ..., "pagina": ..., ...} ],
              "fechas":   [ {"fecha": ISO, "fecha_texto": ..., "pagina": ..., ...} ],
            }
        """
        resultado = {"personas": [], "lugares": [], "fechas": []}

        nlp = _load_model()
        if nlp is None or not texto:
            return resultado

        # Truncar si el texto es muy largo (evitar timeout)
        if len(texto) > max_chars:
            texto = texto[:max_chars]

        try:
            doc = nlp(texto)
        except Exception as e:
            logger.warning(f"spaCy error en página {numero_pagina}: {e}")
            return resultado

        nombres_vistos: set = set()
        lugares_vistos: set = set()
        fechas_vistas: set = set()

        for ent in doc.ents:
            texto_ent = ent.text.strip()

            # ── PERSONAS ────────────────────────────────────────────
            if ent.label_ in _LABELS_PERSONA:
                nombre = self._limpiar_nombre(texto_ent)
                if nombre and self._es_nombre_valido(nombre):
                    clave = self._normalizar_clave(nombre)
                    if clave not in nombres_vistos:
                        nombres_vistos.add(clave)
                        # Extraer contexto (±80 chars)
                        start = max(0, ent.start_char - 80)
                        end = min(len(texto), ent.end_char + 80)
                        contexto = texto[start:end]
                        resultado["personas"].append({
                            "nombre": nombre,
                            "rol": self._detectar_rol(contexto),
                            "pagina": numero_pagina,
                            "contexto": contexto,
                            "confianza": 0.80,
                            "fuente": "spacy_ner",
                        })

            # ── LUGARES ─────────────────────────────────────────────
            elif ent.label_ in _LABELS_LUGAR:
                lugar = self._limpiar_lugar(texto_ent)
                if lugar and len(lugar) >= 4:
                    clave = lugar.lower().strip()
                    if (
                        clave not in lugares_vistos
                        and not self._es_artefacto_ocr(lugar)
                        and self._es_lugar_geografico_valido(lugar)
                    ):
                        lugares_vistos.add(clave)
                        start = max(0, ent.start_char - 50)
                        end = min(len(texto), ent.end_char + 50)
                        contexto = texto[start:end]
                        resultado["lugares"].append({
                            "direccion_completa": lugar,
                            "nombre_lugar": lugar,
                            "tipo": self._tipo_lugar(ent.label_),
                            "pagina": numero_pagina,
                            "contexto": contexto,
                            "confianza": 0.75,
                            "fuente": "spacy_ner",
                        })

            # ── FECHAS ──────────────────────────────────────────────
            elif ent.label_ in _LABELS_FECHA:
                fecha_iso = self._parsear_fecha_spacy(texto_ent)
                if fecha_iso:
                    clave = fecha_iso
                    if clave not in fechas_vistas:
                        fechas_vistas.add(clave)
                        start = max(0, ent.start_char - 100)
                        end = min(len(texto), ent.end_char + 100)
                        contexto = texto[start:end]
                        resultado["fechas"].append({
                            "fecha": fecha_iso,
                            "fecha_texto": texto_ent,
                            "tipo": self._clasificar_fecha(contexto),
                            "pagina": numero_pagina,
                            "contexto": contexto,
                            "confianza": 0.85,
                            "fuente": "spacy_ner",
                        })

        return resultado

    # ------------------------------------------------------------------
    # Métodos auxiliares
    # ------------------------------------------------------------------

    def _limpiar_nombre(self, texto: str) -> Optional[str]:
        """Normaliza un nombre detectado por NER."""
        # Quitar puntuación sobrante
        texto = re.sub(r'^[,;:\.\-\s]+|[,;:\.\-\s]+$', '', texto)
        # Normalizar espacios
        texto = re.sub(r'\s+', ' ', texto).strip()
        # Capitalizar correctamente
        if texto.isupper() and len(texto) > 3:
            texto = texto.title()
        return texto if len(texto) >= 4 else None

    def _es_nombre_valido(self, nombre: str) -> bool:
        """Filtra nombres que no son personas reales."""
        nombre_lower = nombre.lower()

        # Mínimo 2 palabras
        palabras = nombre.split()
        if len(palabras) < 2:
            return False

        # Máximo 6 palabras
        if len(palabras) > 6:
            return False

        # No contiene palabras institucionales
        for palabra in palabras:
            if palabra.lower() in _PALABRAS_EXCLUIR_PERSONA:
                return False

        # No solo números
        if re.match(r'^[\d\s\-/]+$', nombre):
            return False

        # Al menos 2 vocales
        vocales = len(re.findall(r'[aeiouáéíóúAEIOUÁÉÍÓÚ]', nombre))
        if vocales < 2:
            return False

        # No tiene caracteres raros de OCR
        if re.search(r'[0-9@#$%&*\[\]{}]', nombre):
            return False

        return True

    def _detectar_rol(self, contexto: str) -> str:
        """Detecta el rol de la persona en el contexto."""
        ctx = contexto.lower()
        if re.search(r'v[ií]ctima|ofendid[oa]|agraviado', ctx):
            return 'Víctima'
        if re.search(r'imputad[oa]|acusad[oa]|indiciado|procesad[oa]', ctx):
            return 'Imputado'
        if re.search(r'testigo|declarante', ctx):
            return 'Testigo'
        if re.search(r'perito|experto|especialista', ctx):
            return 'Perito'
        if re.search(r'ministerio p[úu]blico|fiscal\b|agente del mp', ctx):
            return 'Ministerio Público'
        if re.search(r'defensor|abogado', ctx):
            return 'Defensor'
        if re.search(r'polic[ií]a|elemento|agente\s+\w+\s+polic', ctx):
            return 'Policía'
        return 'Desconocido'

    def _limpiar_lugar(self, texto: str) -> Optional[str]:
        """Normaliza un lugar detectado por NER."""
        texto = re.sub(r'^[,;:\.\-\s]+|[,;:\.\-\s]+$', '', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto if len(texto) >= 3 else None

    def _es_lugar_geografico_valido(self, texto: str) -> bool:
        """
        Validación semántica específica para entidades LOC de spaCy:
        rechaza fragmentos procesales, de cabecera OCR, preposicionales
        y artefactos que spaCy clasifica erróneamente como lugar.
        """
        if not texto:
            return False
        palabras = texto.split()
        if not palabras:
            return False

        primera = palabras[0].lower()

        # 1. Empieza con preposición / artículo / conjunción
        if primera in _PREPOSICIONES_INICIO:
            return False

        # 2. Empieza con dígito (p. ej. "18 Emplazamiento", "2do Piso")
        if primera and primera[0].isdigit():
            return False

        # 3. Primera palabra es terminología procesal (no un nombre de lugar)
        if primera in _PALABRAS_NO_LUGAR_INICIO:
            return False

        # 4. Tres o más palabras ≥4 chars completamente en MAYÚSCULAS
        #    → encabezado institucional OCR ("DEJA REPURIKA ... INMENCIORGANIZADA")
        palabras_allcaps = [
            p for p in palabras
            if len(p) >= 4 and p.isalpha() and p.isupper()
        ]
        if len(palabras_allcaps) >= 3:
            return False

        # 5. Debe tener al menos UNA palabra en Title Case real
        #    (mayúscula inicial + alguna minúscula) → nombre propio, no header OCR
        tiene_nombre_propio = any(
            len(p) >= 3 and p[0].isupper() and len(p) > 1 and p[1].islower()
            for p in palabras
        )
        if not tiene_nombre_propio:
            return False

        return True

    # Colores y descriptores genéricos que no son nombres de lugares
    _COLORES_Y_DESCRIPTORES = {
        'negro', 'negra', 'azul', 'blanco', 'blanca', 'verde', 'rojo', 'roja',
        'amarillo', 'amarilla', 'café', 'gris', 'naranja', 'morado', 'morada',
        'rosa', 'dorado', 'dorada', 'plateado', 'plateada', 'obscuro', 'oscuro',
        'claro', 'marino', 'anaranjado', 'anaranjada', 'traslucido', 'traslúcido',
        'número', 'numero', 'regular', 'buen', 'bueno', 'mal', 'malo', 'infantil',
    }

    def _es_artefacto_ocr(self, texto: str) -> bool:
        """Detecta si el texto es ruido OCR, no un lugar real."""
        # Demasiados bloques de mayúsculas (cabecera institucional)
        bloques = re.findall(r'[A-ZÁÉÍÓÚÑ]{3,}', texto)
        if len(bloques) >= 5:
            return True
        # Contiene códigos de expediente / referencias institucionales
        if re.search(
            r'\b(?:PGR|FGR|SEIDO|UEIDO|A\.P\.|REV\.|FO-FF|LFTAIP[A-Z]*|LETAIP[A-Z]*|UEIDMS?)\b',
            texto, re.IGNORECASE
        ):
            return True
        # Longitud excesiva con pocas letras (basura)
        if len(texto) > 80 and len(re.findall(r'[a-záéíóúAÁEÉIÍOÓUÚ]', texto)) < 20:
            return True
        # "coloniaa" es artefacto OCR (doble 'a' por error de escaneo)
        if re.search(r'coloniaa\b', texto, re.IGNORECASE):
            return True
        # Si todas las palabras son colores o descriptores genéricos → no es un lugar real
        palabras = [p.lower().strip('.,;:"()') for p in texto.split() if p.strip('.,;:()')]
        if palabras and all(p in self._COLORES_Y_DESCRIPTORES for p in palabras):
            return True
        return False

    def _tipo_lugar(self, label: str) -> str:
        return {
            'LOC': 'localización',
            'GPE': 'entidad_geopolítica',
            'FAC': 'instalación',
            'ORG': 'organización',
        }.get(label, 'lugar')

    def _parsear_fecha_spacy(self, texto: str) -> Optional[str]:
        """
        Convierte el texto de fecha detectado por spaCy a formato ISO.
        Maneja formatos como:
          '15 de enero de 2014', '15/01/2014', '2014-01-15',
          'enero de 2014', '15 de enero del 2014'
        """
        texto = texto.strip().lower()
        texto = re.sub(r'\s+', ' ', texto)

        # dd/mm/yyyy o dd-mm-yyyy
        m = re.match(r'^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$', texto)
        if m:
            return self._validar_fecha(int(m.group(3)), int(m.group(2)), int(m.group(1)))

        # yyyy-mm-dd (ISO)
        m = re.match(r'^(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})$', texto)
        if m:
            return self._validar_fecha(int(m.group(1)), int(m.group(2)), int(m.group(3)))

        # "15 de enero de/del 2014"
        m = re.search(r'(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+del?\s+(\d{4})', texto)
        if m:
            mes = _MESES.get(m.group(2))
            if mes:
                return self._validar_fecha(int(m.group(3)), mes, int(m.group(1)))

        # "enero de/del 2014" (solo mes + año)
        m = re.search(r'^([a-záéíóúñ]+)\s+del?\s+(\d{4})$', texto)
        if m:
            mes = _MESES.get(m.group(1))
            if mes:
                return self._validar_fecha(int(m.group(2)), mes, 1)

        # Intentar con dateutil como último recurso
        try:
            from dateutil import parser as dparser
            dt = dparser.parse(texto, dayfirst=True, fuzzy=True)
            return self._validar_fecha(dt.year, dt.month, dt.day)
        except Exception:
            pass

        return None

    def _validar_fecha(self, año: int, mes: int, dia: int) -> Optional[str]:
        """Devuelve ISO si la fecha es válida y plausible para expedientes."""
        try:
            if not (1 <= mes <= 12 and 1 <= dia <= 31 and 1990 <= año <= datetime.now().year + 1):
                return None
            f = date(año, mes, dia)
            return f.isoformat()
        except Exception:
            return None

    def _clasificar_fecha(self, contexto: str) -> str:
        ctx = contexto.lower()
        if any(p in ctx for p in ['hechos', 'ocurrieron', 'sucedió', 'pasaron']):
            return 'fecha_hechos'
        if any(p in ctx for p in ['actuación', 'diligencia', 'ministerio']):
            return 'actuacion_mp'
        if any(p in ctx for p in ['audiencia', 'comparecencia']):
            return 'audiencia'
        if any(p in ctx for p in ['declaración', 'manifestó', 'declaró']):
            return 'declaracion'
        return 'fecha_general'

    def _normalizar_clave(self, nombre: str) -> str:
        """Genera clave normalizada para deduplicación."""
        import unicodedata
        texto = unicodedata.normalize('NFKD', nombre)
        texto = ''.join(c for c in texto if not unicodedata.category(c).startswith('Mn'))
        texto = re.sub(r'[^A-Za-z\s]', '', texto)
        return re.sub(r'\s+', ' ', texto).upper().strip()


# Instancia global (carga el modelo una sola vez)
spacy_ner_service = SpacyNERService()
