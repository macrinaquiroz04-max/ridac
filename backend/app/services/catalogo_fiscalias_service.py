"""
Servicio para catálogo de Fiscalías, MPs y Delitos de CDMX
"""
from typing import Dict, List, Optional
from difflib import SequenceMatcher

class CatalogoFiscaliasService:
    """
    Servicio para normalizar fiscalías, agencias del MP y delitos
    """
    
    def __init__(self):
        self.fiscalias = self._cargar_fiscalias()
        self.agencias_mp = self._cargar_agencias_mp()
        self.delitos = self._cargar_delitos()
    
    def _cargar_fiscalias(self) -> Dict:
        """
        Catálogo de Fiscalías de CDMX organizadas por tipo y alcaldía
        """
        return {
            # Fiscalías Centrales
            "CENTRALES": {
                "FCI-DS": {
                    "nombre": "FISCALÍA CENTRAL DE INVESTIGACIÓN DELITOS SEXUALES",
                    "siglas": ["FCI-DS", "FDS", "FISCALIA DELITOS SEXUALES"],
                    "tipo": "Central",
                    "ubicacion": "Ciudad de México"
                },
                "FCI-H": {
                    "nombre": "FISCALÍA CENTRAL DE INVESTIGACIÓN HOMICIDIOS",
                    "siglas": ["FCI-H", "FH", "FISCALIA HOMICIDIOS"],
                    "tipo": "Central"
                },
                "FCI-R": {
                    "nombre": "FISCALÍA CENTRAL DE INVESTIGACIÓN ROBO",
                    "siglas": ["FCI-R", "FR", "FISCALIA ROBO"],
                    "tipo": "Central"
                },
                "FCI-SEC": {
                    "nombre": "FISCALÍA CENTRAL DE INVESTIGACIÓN SECUESTRO",
                    "siglas": ["FCI-SEC", "FSEC", "FISCALIA SECUESTRO"],
                    "tipo": "Central"
                },
                "FCI-EXT": {
                    "nombre": "FISCALÍA CENTRAL DE INVESTIGACIÓN EXTORSIÓN",
                    "siglas": ["FCI-EXT", "FEXT", "FISCALIA EXTORSION"],
                    "tipo": "Central"
                }
            },
            
            # Fiscalías por Alcaldía
            "ALVARO_OBREGON": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN ÁLVARO OBREGÓN",
                "siglas": ["FI-AO", "FISCALIA ALVARO OBREGON"],
                "alcaldia": "Álvaro Obregón"
            },
            "AZCAPOTZALCO": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN AZCAPOTZALCO",
                "siglas": ["FI-AZC", "FISCALIA AZCAPOTZALCO"],
                "alcaldia": "Azcapotzalco"
            },
            "BENITO_JUAREZ": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN BENITO JUÁREZ",
                "siglas": ["FI-BJ", "FISCALIA BENITO JUAREZ"],
                "alcaldia": "Benito Juárez"
            },
            "COYOACAN": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN COYOACÁN",
                "siglas": ["FI-COY", "FISCALIA COYOACAN"],
                "alcaldia": "Coyoacán"
            },
            "CUAJIMALPA": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN CUAJIMALPA",
                "siglas": ["FI-CUA", "FISCALIA CUAJIMALPA"],
                "alcaldia": "Cuajimalpa"
            },
            "CUAUHTEMOC": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN CUAUHTÉMOC",
                "siglas": ["FI-CUH", "FISCALIA CUAUHTEMOC"],
                "alcaldia": "Cuauhtémoc"
            },
            "GUSTAVO_A_MADERO": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN GUSTAVO A. MADERO",
                "siglas": ["FI-GAM", "FISCALIA GUSTAVO A MADERO"],
                "alcaldia": "Gustavo A. Madero"
            },
            "IZTACALCO": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN IZTACALCO",
                "siglas": ["FI-IZC", "FISCALIA IZTACALCO"],
                "alcaldia": "Iztacalco"
            },
            "IZTAPALAPA": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN IZTAPALAPA",
                "siglas": ["FI-IZP", "FISCALIA IZTAPALAPA"],
                "alcaldia": "Iztapalapa"
            },
            "MAGDALENA_CONTRERAS": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN LA MAGDALENA CONTRERAS",
                "siglas": ["FI-MC", "FISCALIA MAGDALENA CONTRERAS"],
                "alcaldia": "La Magdalena Contreras"
            },
            "MIGUEL_HIDALGO": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN MIGUEL HIDALGO",
                "siglas": ["FI-MH", "FISCALIA MIGUEL HIDALGO"],
                "alcaldia": "Miguel Hidalgo"
            },
            "MILPA_ALTA": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN MILPA ALTA",
                "siglas": ["FI-MA", "FISCALIA MILPA ALTA"],
                "alcaldia": "Milpa Alta"
            },
            "TLAHUAC": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN TLÁHUAC",
                "siglas": ["FI-TLA", "FISCALIA TLAHUAC"],
                "alcaldia": "Tláhuac"
            },
            "TLALPAN": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN TLALPAN",
                "siglas": ["FI-TLP", "FISCALIA TLALPAN"],
                "alcaldia": "Tlalpan"
            },
            "VENUSTIANO_CARRANZA": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN VENUSTIANO CARRANZA",
                "siglas": ["FI-VC", "FISCALIA VENUSTIANO CARRANZA"],
                "alcaldia": "Venustiano Carranza"
            },
            "XOCHIMILCO": {
                "nombre": "FISCALÍA DE INVESTIGACIÓN XOCHIMILCO",
                "siglas": ["FI-XOC", "FISCALIA XOCHIMILCO"],
                "alcaldia": "Xochimilco"
            }
        }
    
    def _cargar_agencias_mp(self) -> Dict:
        """
        Catálogo de Agencias del Ministerio Público
        """
        return {
            # Formato: "SIGLA": {"nombre": "...", "fiscalia": "...", "tipo": "..."}
            "FDS-6": {
                "nombre": "AGENCIA INVESTIGADORA DEL M.P. FDS-6",
                "fiscalia": "FISCALÍA DELITOS SEXUALES",
                "tipo": "Delitos Sexuales",
                "numero": "6"
            },
            "FDS-1": {
                "nombre": "AGENCIA INVESTIGADORA DEL M.P. FDS-1",
                "fiscalia": "FISCALÍA DELITOS SEXUALES",
                "tipo": "Delitos Sexuales",
                "numero": "1"
            },
            # Agencias por alcaldía (ejemplos)
            "AO-1": {
                "nombre": "AGENCIA INVESTIGADORA ÁLVARO OBREGÓN 1",
                "alcaldia": "Álvaro Obregón",
                "numero": "1"
            },
            "BJ-2": {
                "nombre": "AGENCIA INVESTIGADORA BENITO JUÁREZ 2",
                "alcaldia": "Benito Juárez",
                "numero": "2"
            }
        }
    
    def _cargar_delitos(self) -> Dict:
        """
        Catálogo de delitos normalizados según Código Penal CDMX
        """
        return {
            # Delitos sexuales
            "ABUSO_SEXUAL": {
                "nombre": "ABUSO SEXUAL",
                "variantes": ["ABUSO SEXUAL", "ABUSO SEXUAl", "ABUSOSEXUAL"],
                "codigo": "181",
                "tipo": "DELITO SEXUAL",
                "agravantes": {
                    "PARENTESCO": "AGRAVADO, POR PARENTESCO",
                    "VIOLENCIA": "AGRAVADO, CON VIOLENCIA",
                    "MENOR": "AGRAVADO, CONTRA MENOR"
                }
            },
            "VIOLACION": {
                "nombre": "VIOLACIÓN",
                "variantes": ["VIOLACION", "VIOLACIÓN", "VIOLAClON"],
                "codigo": "174",
                "tipo": "DELITO SEXUAL",
                "agravantes": {
                    "EQUIPARADA": "VIOLACIÓN EQUIPARADA",
                    "TENTATIVA": "VIOLACIÓN EN GRADO DE TENTATIVA"
                }
            },
            "HOSTIGAMIENTO_SEXUAL": {
                "nombre": "HOSTIGAMIENTO SEXUAL",
                "variantes": ["HOSTIGAMIENTO SEXUAL", "HOSTIGAMIENTO SEXUAl"],
                "codigo": "179",
                "tipo": "DELITO SEXUAL"
            },
            
            # Delitos contra la vida
            "HOMICIDIO": {
                "nombre": "HOMICIDIO",
                "variantes": ["HOMICIDIO", "HOMIClDIO"],
                "codigo": "123",
                "tipo": "DELITO CONTRA LA VIDA",
                "agravantes": {
                    "CALIFICADO": "HOMICIDIO CALIFICADO",
                    "TENTATIVA": "HOMICIDIO EN GRADO DE TENTATIVA"
                }
            },
            "FEMINICIDIO": {
                "nombre": "FEMINICIDIO",
                "variantes": ["FEMINICIDIO", "FEMINIClDIO"],
                "codigo": "148 BIS",
                "tipo": "DELITO CONTRA LA VIDA"
            },
            
            # Delitos patrimoniales
            "ROBO": {
                "nombre": "ROBO",
                "variantes": ["ROBO", "R0BO"],
                "codigo": "220",
                "tipo": "DELITO PATRIMONIAL",
                "agravantes": {
                    "VIOLENCIA": "ROBO CON VIOLENCIA",
                    "CASA_HABITACION": "ROBO A CASA HABITACIÓN",
                    "TRANSEUNTE": "ROBO A TRANSEÚNTE",
                    "VEHICULO": "ROBO DE VEHÍCULO"
                }
            },
            "FRAUDE": {
                "nombre": "FRAUDE",
                "variantes": ["FRAUDE", "FRAU0E"],
                "codigo": "230",
                "tipo": "DELITO PATRIMONIAL"
            },
            
            # Otros delitos
            "SECUESTRO": {
                "nombre": "SECUESTRO",
                "variantes": ["SECUESTRO", "SECUESTRo"],
                "codigo": "163",
                "tipo": "DELITO CONTRA LA LIBERTAD"
            },
            "EXTORSION": {
                "nombre": "EXTORSIÓN",
                "variantes": ["EXTORSION", "EXTORSIÓN", "EXTORSlON"],
                "codigo": "236",
                "tipo": "DELITO PATRIMONIAL"
            }
        }
    
    def normalizar_fiscalia(self, texto: str) -> Optional[Dict]:
        """
        Normaliza el nombre de una fiscalía
        """
        texto_upper = texto.upper().strip()
        
        # Buscar coincidencia exacta
        for categoria in self.fiscalias.values():
            if isinstance(categoria, dict):
                for clave, datos in categoria.items():
                    if isinstance(datos, dict):
                        # Verificar nombre completo
                        if datos.get("nombre", "").upper() in texto_upper:
                            return {
                                "original": texto,
                                "normalizado": datos["nombre"],
                                "encontrado": True,
                                "clave": clave,
                                **datos
                            }
                        
                        # Verificar siglas
                        siglas = datos.get("siglas", [])
                        for sigla in siglas:
                            if sigla.upper() in texto_upper:
                                return {
                                    "original": texto,
                                    "normalizado": datos["nombre"],
                                    "encontrado": True,
                                    "clave": clave,
                                    **datos
                                }
        
        # Búsqueda fuzzy
        mejor_match = None
        mejor_similitud = 0.7
        
        for categoria in self.fiscalias.values():
            if isinstance(categoria, dict):
                for clave, datos in categoria.items():
                    if isinstance(datos, dict):
                        nombre = datos.get("nombre", "")
                        similitud = SequenceMatcher(None, texto_upper, nombre.upper()).ratio()
                        
                        if similitud > mejor_similitud:
                            mejor_similitud = similitud
                            mejor_match = {
                                "original": texto,
                                "normalizado": nombre,
                                "encontrado": True,
                                "similitud": similitud,
                                "clave": clave,
                                **datos
                            }
        
        if mejor_match:
            return mejor_match
        
        return {
            "original": texto,
            "normalizado": texto,
            "encontrado": False,
            "mensaje": "Fiscalía no encontrada en catálogo"
        }
    
    def normalizar_agencia_mp(self, texto: str) -> Optional[Dict]:
        """
        Normaliza el código de agencia del MP
        """
        texto_upper = texto.upper().strip()
        
        # Buscar código directo (ej: "FDS-6")
        for codigo, datos in self.agencias_mp.items():
            if codigo in texto_upper or datos["nombre"].upper() in texto_upper:
                return {
                    "original": texto,
                    "normalizado": datos["nombre"],
                    "codigo": codigo,
                    "encontrado": True,
                    **datos
                }
        
        return {
            "original": texto,
            "normalizado": texto,
            "encontrado": False,
            "mensaje": "Agencia MP no encontrada"
        }
    
    def normalizar_delito(self, texto: str) -> Optional[Dict]:
        """
        Normaliza el nombre del delito
        """
        texto_upper = texto.upper().strip()
        
        # Buscar delito base
        for clave, datos in self.delitos.items():
            nombre = datos["nombre"]
            variantes = datos.get("variantes", [])
            
            # Verificar nombre principal y variantes
            if any(var.upper() in texto_upper for var in [nombre] + variantes):
                resultado = {
                    "original": texto,
                    "normalizado": nombre,
                    "encontrado": True,
                    "clave": clave,
                    **datos
                }
                
                # Verificar agravantes
                agravantes = datos.get("agravantes", {})
                for tipo_agravante, texto_agravante in agravantes.items():
                    if tipo_agravante.upper() in texto_upper or "AGRAVADO" in texto_upper:
                        resultado["normalizado"] = f"{nombre} - {texto_agravante}"
                        resultado["agravante"] = tipo_agravante
                        break
                
                return resultado
        
        # Búsqueda fuzzy
        mejor_match = None
        mejor_similitud = 0.75
        
        for clave, datos in self.delitos.items():
            nombre = datos["nombre"]
            similitud = SequenceMatcher(None, texto_upper, nombre.upper()).ratio()
            
            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_match = {
                    "original": texto,
                    "normalizado": nombre,
                    "encontrado": True,
                    "similitud": similitud,
                    "clave": clave,
                    **datos
                }
        
        if mejor_match:
            return mejor_match
        
        return {
            "original": texto,
            "normalizado": texto,
            "encontrado": False,
            "mensaje": "Delito no encontrado en catálogo"
        }


# Instancia global del servicio
catalogo_fiscalias = CatalogoFiscaliasService()
