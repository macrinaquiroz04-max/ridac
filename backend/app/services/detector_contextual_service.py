"""
Detector Contextual para diferenciar Nombres de Personas vs Colonias
Sistema específico para documentos jurídicos FGJCDMX
"""
from typing import Dict, List, Optional, Tuple
import re
from sqlalchemy import create_engine, text
from app.config import settings

class DetectorContextualService:
    """
    Detecta si un texto es nombre de persona o colonia basándose en:
    1. Contexto de palabras cercanas
    2. Patrones de nombres mexicanos
    3. Base de datos SEPOMEX
    4. Posición en el documento
    """
    
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        
        # Palabras que indican que viene un nombre de persona
        self.indicadores_persona = [
            "c.", "ciudadano", "ciudadana", "sr.", "sra.", "señor", "señora",
            "denunciante", "víctima", "victima", "imputado", "indiciado",
            "declaró", "declaro", "manifestó", "manifesto", "compareció",
            "nombre", "apellido", "identidad", "quien dijo llamarse",
            "responde al nombre", "de nombre"
        ]
        
        # Palabras que indican dirección/colonia
        self.indicadores_colonia = [
            "colonia", "col.", "calle", "domicilio", "ubicado en", "ubicada en",
            "residente en", "con domicilio", "avenida", "av.", "calzada",
            "cda.", "cerrada", "privada", "priv.", "número", "num.", "no.",
            "entre", "esquina", "esq.", "código postal", "c.p.", "cp"
        ]
        
        # Nombres propios mexicanos comunes
        self.nombres_comunes_mx = self._cargar_nombres_comunes()
        
        # Apellidos mexicanos comunes
        self.apellidos_comunes_mx = self._cargar_apellidos_comunes()
    
    def _cargar_nombres_comunes(self) -> set:
        """Nombres propios más comunes en México"""
        return {
            # Nombres masculinos
            "JOSÉ", "JUAN", "LUIS", "CARLOS", "MIGUEL", "PEDRO", "JESÚS",
            "ANTONIO", "FRANCISCO", "JAVIER", "RICARDO", "ROBERTO", "MANUEL",
            "RAÚL", "DAVID", "SERGIO", "JORGE", "EDUARDO", "MARIO", "DANIEL",
            "PABLO", "ALEJANDRO", "FERNANDO", "ENRIQUE", "ALBERTO", "ARTURO",
            "HÉCTOR", "OSCAR", "GERARDO", "ARMANDO", "ALFREDO", "JOSÉ LUIS",
            
            # Nombres femeninos
            "MARÍA", "GUADALUPE", "ROSA", "ANA", "LAURA", "PATRICIA", "MARTHA",
            "GABRIELA", "ELIZABETH", "SILVIA", "CARMEN", "LUCÍA", "TERESA",
            "LETICIA", "CLAUDIA", "ANDREA", "MÓNICA", "ALEJANDRA", "MARGARITA",
            "VIRGINIA", "NANCY", "VERÓNICA", "DANIELA", "BRENDA", "JESSICA",
            "MARÍA ELENA", "MARÍA JOSÉ", "ANA MARÍA"
        }
    
    def _cargar_apellidos_comunes(self) -> set:
        """Apellidos más comunes en México"""
        return {
            "GARCÍA", "MARTÍNEZ", "HERNÁNDEZ", "LÓPEZ", "GONZÁLEZ", "RODRÍGUEZ",
            "PÉREZ", "SÁNCHEZ", "RAMÍREZ", "TORRES", "FLORES", "RIVERA",
            "GÓMEZ", "DÍAZ", "CRUZ", "MORALES", "REYES", "GUTIÉRREZ", "ORTIZ",
            "JIMÉNEZ", "MENDOZA", "VÁZQUEZ", "CASTRO", "RAMOS", "MEDINA",
            "GUERRERO", "RUIZ", "ROJAS", "MORENO", "VARGAS", "DOMÍNGUEZ",
            "AGUILAR", "GUZMÁN", "SILVA", "ÁVILA", "MALDONADO", "ESTRADA",
            "SOLARES", "CONTRERAS", "SALAZAR", "CAMPOS", "HERRERA"
        }
    
    def analizar_contexto(self, texto: str, ventana: int = 50) -> Dict:
        """
        Analiza el contexto alrededor de un texto para determinar si es nombre o colonia
        
        Args:
            texto: Texto a analizar
            ventana: Caracteres antes/después a analizar
        
        Returns:
            Dict con la clasificación y confianza
        """
        texto_clean = texto.strip()
        texto_upper = texto_clean.upper()
        
        # Puntuación inicial
        score_persona = 0
        score_colonia = 0
        evidencias = []
        
        # 1. Verificar si está en catálogo SEPOMEX (fuerte indicador de colonia)
        if self._existe_en_sepomex(texto_clean):
            score_colonia += 50
            evidencias.append("Encontrado en catálogo SEPOMEX")
        
        # 2. Analizar composición del texto
        palabras = texto_upper.split()
        
        # 2a. Nombres con un solo token suelen ser colonias
        if len(palabras) == 1:
            if palabras[0] in self.nombres_comunes_mx:
                score_persona += 15
                evidencias.append(f"'{palabras[0]}' es nombre común")
            else:
                score_colonia += 10
                evidencias.append("Una sola palabra (patrón de colonia)")
        
        # 2b. Dos palabras: puede ser nombre+apellido O colonia compuesta
        elif len(palabras) == 2:
            if palabras[0] in self.nombres_comunes_mx:
                score_persona += 20
                evidencias.append(f"Primera palabra '{palabras[0]}' es nombre común")
            if palabras[1] in self.apellidos_comunes_mx:
                score_persona += 20
                evidencias.append(f"Segunda palabra '{palabras[1]}' es apellido común")
            
            # Patrones de colonias de dos palabras
            if any(p in texto_upper for p in ["DEL ", "LA ", "EL ", "LOS ", "LAS ", "SAN ", "SANTA "]):
                score_colonia += 15
                evidencias.append("Contiene artículo/prefijo de colonia")
        
        # 2c. Tres o más palabras: probablemente nombre completo
        else:
            primera = palabras[0]
            if primera in self.nombres_comunes_mx:
                score_persona += 25
                evidencias.append(f"Nombre '{primera}' al inicio")
            
            # Buscar apellidos en las últimas palabras
            for palabra in palabras[-2:]:
                if palabra in self.apellidos_comunes_mx:
                    score_persona += 15
                    evidencias.append(f"Apellido '{palabra}' encontrado")
        
        # 3. Patrones textuales específicos
        
        # 3a. Iniciales seguidas de punto (ej: "M.A.D." o "J. LUIS")
        if re.search(r'\b[A-Z]\.[A-Z]\.', texto_upper):
            score_persona += 20
            evidencias.append("Contiene iniciales con punto")
        
        # 3b. Palabras típicas de colonias
        palabras_colonia = ["NORTE", "SUR", "ORIENTE", "PONIENTE", "CENTRO",
                           "PRIMERA", "SEGUNDA", "TERCERA", "AMPLIACIÓN",
                           "NUEVA", "VIEJA", "INDUSTRIAL"]
        if any(p in texto_upper for p in palabras_colonia):
            score_colonia += 15
            evidencias.append("Contiene término direccional/descriptivo de colonia")
        
        # 3c. Números en el texto (raro en nombres)
        if re.search(r'\d', texto):
            score_colonia += 10
            evidencias.append("Contiene números")
        
        # 3d. Palabras todas en mayúsculas sin espacios extras (típico de colonias en docs oficiales)
        if texto == texto_upper and len(palabras) <= 3:
            score_colonia += 5
            evidencias.append("Formato mayúsculas típico de colonia")
        
        # 4. Determinar clasificación
        confianza = abs(score_persona - score_colonia)
        
        if score_persona > score_colonia:
            clasificacion = "PERSONA"
            certeza = min(confianza / 50 * 100, 100)  # Convertir a porcentaje
        elif score_colonia > score_persona:
            clasificacion = "COLONIA"
            certeza = min(confianza / 50 * 100, 100)
        else:
            clasificacion = "AMBIGUO"
            certeza = 0
        
        return {
            "texto": texto_clean,
            "clasificacion": clasificacion,
            "certeza": round(certeza, 2),
            "score_persona": score_persona,
            "score_colonia": score_colonia,
            "evidencias": evidencias,
            "sugerencia": self._generar_sugerencia(clasificacion, texto_clean, certeza)
        }
    
    def _existe_en_sepomex(self, texto: str) -> bool:
        """Verifica si el texto existe como colonia en SEPOMEX"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT EXISTS(
                        SELECT 1 FROM sepomex_codigos_postales
                        WHERE UPPER(colonia) = UPPER(:texto)
                    )
                """), {"texto": texto})
                return result.scalar()
        except:
            return False
    
    def _generar_sugerencia(self, clasificacion: str, texto: str, certeza: float) -> str:
        """Genera una sugerencia de acción"""
        if certeza >= 80:
            if clasificacion == "PERSONA":
                return f"'{texto}' es muy probablemente un nombre de persona"
            else:
                return f"'{texto}' es muy probablemente una colonia"
        elif certeza >= 50:
            if clasificacion == "PERSONA":
                return f"'{texto}' parece ser un nombre de persona (verificar contexto)"
            else:
                return f"'{texto}' parece ser una colonia (verificar en SEPOMEX)"
        else:
            return f"'{texto}' es ambiguo - revisar contexto del documento"
    
    def procesar_documento_ocr(self, texto_completo: str) -> Dict:
        """
        Procesa un documento completo identificando personas y colonias
        
        Returns:
            Dict con:
            - personas: lista de nombres detectados
            - colonias: lista de colonias detectadas
            - ambiguos: textos que necesitan revisión manual
        """
        personas = []
        colonias = []
        ambiguos = []
        
        # Extraer candidatos usando patrones
        # Patrón 1: Texto después de indicadores de persona
        patron_persona = r'(?:ciudadan[oa]|denunciante|víctima|imputado|de nombre)\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]{3,50})'
        candidatos_persona = re.findall(patron_persona, texto_completo, re.IGNORECASE)
        
        # Patrón 2: Texto después de "colonia"
        patron_colonia = r'(?:colonia|col\.)\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,50})'
        candidatos_colonia = re.findall(patron_colonia, texto_completo, re.IGNORECASE)
        
        # Analizar cada candidato
        for candidato in candidatos_persona:
            resultado = self.analizar_contexto(candidato.strip())
            if resultado["clasificacion"] == "PERSONA":
                personas.append(resultado)
            elif resultado["clasificacion"] == "COLONIA":
                colonias.append(resultado)
            else:
                ambiguos.append(resultado)
        
        for candidato in candidatos_colonia:
            resultado = self.analizar_contexto(candidato.strip())
            if resultado["clasificacion"] == "COLONIA":
                colonias.append(resultado)
            else:
                ambiguos.append(resultado)
        
        return {
            "personas": personas,
            "colonias": colonias,
            "ambiguos": ambiguos,
            "total_personas": len(personas),
            "total_colonias": len(colonias),
            "total_ambiguos": len(ambiguos)
        }


# Instancia global
detector_contextual = DetectorContextualService()
