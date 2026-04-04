# backend/app/services/entity_correction_service.py
# Corrección post-OCR especializada en Fechas, Nombres y Ubicaciones
# Para documentos legales escaneados de baja calidad (copias de copias)
# Desarrollador: Eduardo Lozada Quiroz, ISC

import re
from difflib import SequenceMatcher
from typing import List, Tuple, Optional, Dict
from app.utils.logger import logger


# ── Catálogos cerrados ─────────────────────────────────────────────────────────

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

MESES_INDEX = {m: i + 1 for i, m in enumerate(MESES_ES)}

# Variantes OCR de meses (copia-de-copia confunde letras)
_MESES_VARIANTES: Dict[str, str] = {
    # enero
    "enerö": "enero", "ener0": "enero", "en3ro": "enero",
    # febrero
    "febreo": "febrero", "febr3ro": "febrero", "febrro": "febrero",
    # marzo
    "marz0": "marzo", "marze": "marzo",
    # abril
    "abnil": "abril", "abri1": "abril",
    # mayo
    "may0": "mayo",
    # junio
    "juni0": "junio", "junlo": "junio",
    # julio
    "juli0": "julio", "julío": "julio",
    # agosto
    "ag0sto": "agosto", "agooto": "agosto", "agost0": "agosto",
    # septiembre
    "septienbre": "septiembre", "sept1embre": "septiembre",
    "septiernbre": "septiembre", "septiembe": "septiembre",
    "sep1iembre": "septiembre", "septembre": "septiembre",
    # octubre
    "0ctubre": "octubre", "octnbre": "octubre", "octuber": "octubre",
    # noviembre
    "novienbre": "noviembre", "noviernbre": "noviembre",
    "novierbre": "noviembre", "novlembre": "noviembre",
    # diciembre
    "dicienbre": "diciembre", "dic1embre": "diciembre",
    "diciernbre": "diciembre", "diclerbre": "diciembre",
}

# Estados de la República Mexicana (para validación de ubicaciones)
ESTADOS_MEXICO = [
    "aguascalientes", "baja california", "baja california sur",
    "campeche", "chiapas", "chihuahua", "ciudad de méxico", "cdmx",
    "coahuila", "colima", "durango", "guanajuato", "guerrero",
    "hidalgo", "jalisco", "estado de méxico", "michoacán", "morelos",
    "nayarit", "nuevo león", "oaxaca", "puebla", "querétaro",
    "quintana roo", "san luis potosí", "sinaloa", "sonora", "tabasco",
    "tamaulipas", "tlaxcala", "veracruz", "yucatán", "zacatecas",
    # Alias comunes
    "distrito federal", "d.f.", "d. f.", "mexico", "méxico",
]

# Prefijos de nombre comunes en documentos legales
_PREFIJOS_NOMBRE = {
    "ciudadano", "ciudadana", "c.", "señor", "señora", "sr.", "sra.",
    "licenciado", "licenciada", "lic.", "ingeniero", "ing.", "doctor",
    "dr.", "dra.", "general", "coronel", "teniente", "comandante",
    "subprocurador", "agente", "ministerio público", "fiscal",
    # Identificadores de rol
    "víctima", "ofendido", "ofendida", "imputado", "imputada",
    "testigo", "declarante", "denunciante", "querellante",
}

# ── Correcciones OCR de dígitos en contexto de fecha ──────────────────────────

_DIG_SUBS = str.maketrans({
    "l": "1", "I": "1", "O": "0", "o": "0",
    "S": "5", "s": "5", "Z": "2", "B": "8",
    "G": "6", "q": "9", "g": "9",
})


def _ratio_similitud(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ── Fecha ──────────────────────────────────────────────────────────────────────

def _normalizar_mes(token: str) -> Optional[str]:
    """
    Intenta convertir un token (posiblemente garbled) en un nombre de mes limpio.
    Usa: variantes exactas → fuzzy Levenshtein 0.80+
    """
    t = token.lower().strip(" .,;")
    # Variante exacta conocida
    if t in _MESES_VARIANTES:
        return _MESES_VARIANTES[t]
    # Coincidencia exacta
    if t in MESES_ES:
        return t
    # Fuzzy — solo candidatos de longitud similar (±3 chars)
    mejor, best_ratio = None, 0.0
    for mes in MESES_ES:
        if abs(len(mes) - len(t)) > 4:
            continue
        r = _ratio_similitud(t, mes)
        if r > best_ratio:
            best_ratio, mejor = r, mes
    return mejor if best_ratio >= 0.78 else None


def _reparar_digitos_fecha(s: str) -> str:
    """Corrige errores l→1, O→0, etc. dentro de un fragmento que representa un número."""
    return s.translate(_DIG_SUBS)


def _validar_dia(d: int) -> bool:
    return 1 <= d <= 31


def _validar_mes(m: int) -> bool:
    return 1 <= m <= 12


def _validar_anio(a: int) -> bool:
    return 1900 <= a <= 2099


def corregir_fechas(texto: str) -> str:
    """
    Revisa el texto línea por línea y repara fechas mal reconocidas.

    Casos atendidos:
    1.  "15 de naizo de 2024" → "15 de marzo de 2024"   (mes garbled)
    2.  "l5 de marzo de 2024" → "15 de marzo de 2024"   (día con l→1)
    3.  "15 de marzo de 2O24" → "15 de marzo de 2024"   (año con O→0)
    4.  "15/O3/2024"         → "15/03/2024"             (separador numérico)
    5.  "15-O3-2O24"         → "15-03-2024"             (guion numérico)
    """

    # ── Patrón 1: "DD de MES de YYYY" o "DD de MES del YYYY" ────────────────
    PAT_TEXTO = re.compile(
        r'\b(\d{1,2}[lIoO\d]*)'          # día (posiblemente con l/I/O)
        r'\s+de\s+'
        r'([A-Za-záéíóúüñÁÉÍÓÚÜÑ]{3,13})'  # mes (posiblemente garbled)
        r'\s+de[l]?\s+'
        r'(\d{1,4}[lIoO\d]*)',            # año (posiblemente con l/I/O)
        re.IGNORECASE,
    )

    def _fix_texto(m: re.Match) -> str:
        dia_raw, mes_raw, anio_raw = m.group(1), m.group(2), m.group(3)
        dia_str   = _reparar_digitos_fecha(dia_raw)
        anio_str  = _reparar_digitos_fecha(anio_raw)
        mes_clean = _normalizar_mes(mes_raw)

        try:
            dia  = int(dia_str)
            anio = int(anio_str)
        except ValueError:
            return m.group(0)  # no se pudo reparar, dejar igual

        if mes_clean is None or not _validar_dia(dia) or not _validar_anio(anio):
            return m.group(0)

        # Preservar "del" si estaba antes
        de_del = "del" if "del" in m.group(0).lower()[m.group(0).lower().index("de ") + 3:] else "de"
        return f"{dia} de {mes_clean} {de_del} {anio}"

    texto = PAT_TEXTO.sub(_fix_texto, texto)

    # ── Patrón 2: "DD/MM/YYYY" o "DD-MM-YYYY" con caracteres OCR-falseados ──
    PAT_NUM = re.compile(
        r'\b(\d{1,2}[lIoOSsZBGqg\d]*)'
        r'([/\-\.])'
        r'(\d{1,2}[lIoOSsZBGqg\d]*)'
        r'\2'                               # mismo separador
        r'(\d{2,4}[lIoOSsZBGqg\d]*)',
    )

    def _fix_num(m: re.Match) -> str:
        d_raw, sep, mo_raw, y_raw = m.group(1), m.group(2), m.group(3), m.group(4)
        try:
            d  = int(_reparar_digitos_fecha(d_raw))
            mo = int(_reparar_digitos_fecha(mo_raw))
            y  = int(_reparar_digitos_fecha(y_raw))
        except ValueError:
            return m.group(0)
        if _validar_dia(d) and _validar_mes(mo) and _validar_anio(y):
            return f"{d:02d}{sep}{mo:02d}{sep}{y}"
        return m.group(0)

    texto = PAT_NUM.sub(_fix_num, texto)

    return texto


# ── Nombres ────────────────────────────────────────────────────────────────────

# Artefactos OCR comunes dentro de nombres (no dígitos)
_NOMBRE_SUBS = [
    (re.compile(r'0(?=[A-ZÁÉÍÓÚÑ])',  re.UNICODE), 'O'),   # 0CAMPO → OCAMPO
    (re.compile(r'(?<=[A-ZÁÉÍÓÚÑ])0', re.UNICODE), 'O'),   # CAMINÚ0 → CAMINÚO – raro
    (re.compile(r'1(?=[A-ZÁÉÍÓÚÑ])',  re.UNICODE), 'I'),   # 1GNACIO → IGNACIO
    (re.compile(r'(?<=[A-ZÁÉÍÓÚÑ])1', re.UNICODE), 'I'),
    (re.compile(r'\b([A-ZÁÉÍÓÚÑ])\s([A-ZÁÉÍÓÚÑ])\s([A-ZÁÉÍÓÚÑ])\b'), r'\1\2\3'),  # G A R → GAR
    # Espacios extras dentro de nombres por tipo (ej. "GARCI A" → "GARCIA")
    (re.compile(r'([A-ZÁÉÍÓÚÑ]{2,})\s([A-ZÁÉÍÓÚÑ])(?=\s|$)'), r'\1\2'),
]

# Artículos/preposiciones en apellidos compuestos (NO se capitalizan)
_PARTICULAS = {"de", "del", "la", "las", "los", "y", "e", "van", "von", "da", "das", "do"}


def _capitalizar_nombre(nombre: str) -> str:
    """
    Capitaliza correctamente un nombre completo.
    Ejemplo: "JUAN de LA ROSA MARTINEZ" → "Juan de la Rosa Martinez"
    """
    partes = nombre.strip().split()
    resultado = []
    for p in partes:
        pl = p.lower()
        if pl in _PARTICULAS and resultado:   # partícula en medio → minúscula
            resultado.append(pl)
        else:
            resultado.append(p.capitalize())
    return " ".join(resultado)


def corregir_nombres(texto: str) -> str:
    """
    Aplica correcciones OCR a nombres detectados en el texto:
    - Reemplaza 0/1 por O/I dentro de secuencias de letras mayúsculas
    - Colapsa letras sueltas separadas por espacio (G A R → GAR)
    - NO modifica dígitos en contextos que claramente no son nombres
    """
    # ── Corregir artefactos dentro de bloques de MAYÚSCULAS (probable nombre) ─
    # Primero identificar candidatos a nombre: 2+ palabras en mayúsculas seguidas
    NOMBRE_BLOQUE = re.compile(
        r'\b([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9]{1,19}(?:\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9]{1,19}){1,4})\b'
    )

    def _fix_bloque(m: re.Match) -> str:
        bloque = m.group(0)
        # Aplicar sustituciones de artefactos OCR
        for patron, reemplazo in _NOMBRE_SUBS:
            bloque = patron.sub(reemplazo, bloque)
        return bloque

    texto = NOMBRE_BLOQUE.sub(_fix_bloque, texto)
    return texto


# ── Ubicaciones ───────────────────────────────────────────────────────────────

def _estado_mas_cercano(token: str) -> Optional[str]:
    """Devuelve el nombre de estado más parecido si similaridad >= 0.80."""
    t = token.lower().strip()
    mejor, best_ratio = None, 0.0
    for estado in ESTADOS_MEXICO:
        if abs(len(estado) - len(t)) > 5:
            continue
        r = _ratio_similitud(t, estado)
        if r > best_ratio:
            best_ratio, mejor = r, estado
    return mejor if best_ratio >= 0.80 else None


def corregir_ubicaciones(texto: str) -> str:
    """
    Valida y corrige nombres de estados/ubicaciones garbled en el texto.
    Ejemplo: "Ciodad de Mexlco" → "Ciudad de México"
             "Chihualua"        → "Chihuahua"
    """
    # CDMX y D.F. tienen variantes comunes
    texto = re.sub(r'\bCiudad\s+de\s+Mexl?c[o0]\b', 'Ciudad de México', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\bD\.\s*F\.\b', 'Ciudad de México', texto)
    texto = re.sub(r'\bCDMX\b', 'CDMX', texto)

    # Corregir "Nuev[o0] Le[o0]n"
    texto = re.sub(r'\bNuev[o0]\s*Le[o0]n\b', 'Nuevo León', texto, flags=re.IGNORECASE)

    # Reparar nombres de estados con artefactos dígito-letra
    PAT_ESTADO = re.compile(
        r'\b((?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ0-9]{2,15}\s*){1,4})\b'
    )

    def _fix_estado(m: re.Match) -> str:
        fragmento = m.group(0).strip()
        corregido = _estado_mas_cercano(fragmento)
        if corregido:
            # Capitalizar para presentación
            return " ".join(w.capitalize() for w in corregido.split())
        return fragmento

    # Solo aplicar en frases cortas que podrían ser estados (máx 4 palabras)
    partes = texto.split(",")
    partes_corregidas = []
    for parte in partes:
        parte_strip = parte.strip()
        num_palabras = len(parte_strip.split())
        if 1 <= num_palabras <= 4:
            candidate = _fix_estado(re.match(r'.+', parte_strip) or re.Match)
            partes_corregidas.append(" " + candidate if parte.startswith(" ") else candidate)
        else:
            partes_corregidas.append(parte)

    return ",".join(partes_corregidas)


# ── Clase principal del servicio ───────────────────────────────────────────────

class EntityCorrectionService:
    """
    Servicio de corrección post-OCR para entidades críticas:
    - Fechas    → reconstruye días/meses/años garbled
    - Nombres   → corrige artefactos 0/1 en secuencias de mayúsculas
    - Ubicaciones → valida contra catálogo de estados mexicanos

    Se llama DESPUÉS del OCR y ANTES de guardar en BD.
    """

    def corregir_todo(self, texto: str) -> str:
        """Aplica todas las correcciones en orden seguro."""
        if not texto:
            return texto
        try:
            texto = corregir_fechas(texto)
        except Exception as e:
            logger.warning(f"entity_correction fechas: {e}")

        try:
            texto = corregir_nombres(texto)
        except Exception as e:
            logger.warning(f"entity_correction nombres: {e}")

        # Ubicaciones: más experimental, solo si hay marcadores claros
        try:
            texto = self._corregir_ubicaciones_en_contexto(texto)
        except Exception as e:
            logger.warning(f"entity_correction ubicaciones: {e}")

        return texto

    def _corregir_ubicaciones_en_contexto(self, texto: str) -> str:
        """
        Aplica corrección de ubicaciones solo en líneas que contienen
        indicadores geográficos (ciudad, estado, municipio, etc.).
        Más conservador que corregir_ubicaciones() para todo el texto.
        """
        indicadores = re.compile(
            r'\b(ciudad|estado|municipio|alcaldía|delegación|colonia|col\.|'
            r'domicilio|calle|avenida|av\.|carretera|federal)\b',
            re.IGNORECASE,
        )
        lineas = texto.splitlines()
        resultado = []
        for linea in lineas:
            if indicadores.search(linea):
                linea = corregir_ubicaciones(linea)
            resultado.append(linea)
        return "\n".join(resultado)

    def extraer_fechas_validadas(self, texto: str) -> List[str]:
        """
        Extrae y devuelve fechas ya corregidas del texto.
        Útil para diagnóstico o para guardar en metadatos.
        """
        texto_corregido = corregir_fechas(texto)
        pat = re.compile(
            r'\b\d{1,2}\s+de\s+(?:' + '|'.join(MESES_ES) + r')\s+del?\s+\d{4}\b'
            r'|\b\d{2}/\d{2}/\d{4}\b'
            r'|\b\d{2}-\d{2}-\d{4}\b',
            re.IGNORECASE,
        )
        return pat.findall(texto_corregido)

    def extraer_nombres_normalizados(self, texto: str) -> List[str]:
        """
        Extrae nombres en mayúsculas (patrón común en documentos legales mexicanos)
        y los devuelve normalizados.
        """
        texto_corregido = corregir_nombres(texto)
        # Patrón: 2-4 palabras en mayúsculas
        PAT = re.compile(
            r'\b([A-ZÁÉÍÓÚÑ]{2,20}(?:\s+[A-ZÁÉÍÓÚÑ]{2,20}){1,3})\b'
        )
        nombres = []
        for m in PAT.finditer(texto_corregido):
            nombre = m.group(0)
            # Filtrar palabras que son claramente no-nombres (siglas institucionales cortas, etc.)
            if len(nombre) > 6 and not _es_sigla_institucional(nombre):
                nombres.append(_capitalizar_nombre(nombre))
        return list(dict.fromkeys(nombres))  # deduplicar preservando orden


def _es_sigla_institucional(texto: str) -> bool:
    """Detecta si el token es una sigla conocida (no un nombre de persona)."""
    SIGLAS = {
        "CDMX", "PGR", "FGR", "FGJ", "PGJDF", "SSP", "SEDENA", "SEMAR",
        "SAT", "IMSS", "ISSSTE", "INE", "CURP", "RFC", "SEP", "SRE",
        "CNDH", "INAI", "CJF", "SCJN", "TSJ", "MP", "AMP", "CI",
    }
    return texto.strip().upper() in SIGLAS


# Instancia global (importar desde otros módulos)
entity_correction = EntityCorrectionService()
