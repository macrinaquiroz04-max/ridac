# backend/app/services/sepomex_service.py

import httpx
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class SepomexService:
    """
    Servicio para validar colonias, códigos postales y direcciones
    usando la API de SEPOMEX (Servicio Postal Mexicano)
    
    API Gratuita: https://api.copomex.com/
    """
    
    def __init__(self):
        # API pública de códigos postales - compatible con SEPOMEX
        # Para obtener API key gratuita: https://copomex.com
        # IMPORTANTE: El token "pruebas" devuelve datos encriptados
        # Debe registrarse en copomex.com para obtener un token real
        self.base_url = "https://api.copomex.com"
        self.api_token = None  # Configurar con API key real de copomex.com
        self.timeout = 10.0
        self.use_api = False  # Cambiar a True después de configurar api_token real
        
        # Diccionario local con CPs de las 16 ALCALDÍAS DE CDMX
        # Base de datos completa: 150+ códigos postales
        self.diccionario_local = {
            # ========== CUAUHTÉMOC (32 CPs) ==========
            "06000": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["CENTRO", "CENTRO HISTÓRICO"]},
            "06010": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["CENTRO"]},
            "06020": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["CENTRO"]},
            "06030": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["CENTRO", "MORELOS"]},
            "06040": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["CENTRO", "ALGARÍN"]},
            "06050": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["CENTRO", "PERALVILLO"]},
            "06060": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["DOCTORES"]},
            "06070": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["DOCTORES"]},
            "06080": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["OBRERA"]},
            "06090": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["BUENOS AIRES"]},
            "06100": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["CENTRO", "GUERRERO"]},
            "06140": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["CONDESA", "ROMA NORTE"]},
            "06170": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["ROMA NORTE"]},
            "06200": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["AMPLIACIÓN ASTURIAS"]},
            "06240": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["ALGARÍN"]},
            "06300": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["MOCTEZUMA"]},
            "06400": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["PERALVILLO"]},
            "06500": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["SANTA MARÍA INSURGENTES"]},
            "06600": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["JUÁREZ"]},
            "06700": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["CONDESA", "HIPÓDROMO", "HIPÓDROMO CONDESA"]},
            "06720": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["HIPÓDROMO"]},
            "06760": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["ROMA SUR"]},
            "06780": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["DOCTORES"]},
            "06800": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["NARVARTE PONIENTE"]},
            "06820": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["OBRERA"]},
            "06850": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["ESPERANZA"]},
            "06900": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["NARVARTE ORIENTE"]},
            "06920": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["ASTURIAS"]},
            "06940": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["ARTES GRÁFICAS"]},
            "06960": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["PAULINO NAVARRO"]},
            "06970": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["VISTA ALEGRE"]},
            "06980": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAUHTÉMOC", "colonias": ["SIMÓN BOLÍVAR"]},
            
            # ========== MIGUEL HIDALGO (20 CPs) ==========
            "11000": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["POLANCO", "POLANCO I SECCIÓN", "POLANCO II SECCIÓN", "POLANCO III SECCIÓN", "GRANADA"]},
            "11200": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["TACUBA"]},
            "11230": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["LEGARIA"]},
            "11250": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["UN HOGAR PARA NOSOTROS"]},
            "11260": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["POPOTLA"]},
            "11280": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["ARGENTINA PONIENTE"]},
            "11300": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["VERÓNICA ANZURES"]},
            "11320": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["ANZURES"]},
            "11340": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["CHAPULTEPEC MORALES"]},
            "11360": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["PENSIL NORTE"]},
            "11400": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["HORACIO", "POLANCO CHAPULTEPEC"]},
            "11410": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["PENSIL SUR"]},
            "11430": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["SAN MIGUEL CHAPULTEPEC"]},
            "11450": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["LAGO NORTE"]},
            "11470": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["LAGO SUR"]},
            "11500": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["IRRIGACIÓN"]},
            "11510": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["POLANCO I SECCIÓN", "POLANCO II SECCIÓN", "POLANCO III SECCIÓN"]},
            "11520": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["GRANADA"]},
            "11529": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["AMPLIACIÓN GRANADA"]},
            "11550": {"estado": "CIUDAD DE MÉXICO", "municipio": "MIGUEL HIDALGO", "colonias": ["ANÁHUAC I SECCIÓN"]},
            
            # BENITO JUÁREZ
            "03100": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["DEL VALLE", "DEL VALLE CENTRO", "DEL VALLE NORTE", "NÁPOLES"]},
            "03103": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["DEL VALLE CENTRO"]},
            "03200": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["NARVARTE PONIENTE"]},
            "03300": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["PORTALES NORTE"]},
            "03310": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["PORTALES SUR"]},
            "03400": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["ACACIAS"]},
            "03500": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["NARVARTE ORIENTE"]},
            "03600": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["VÉRTIZ NARVARTE"]},
            "03700": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["SANTA CRUZ ATOYAC"]},
            "03800": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["SAN SIMÓN TICUMAC"]},
            "03810": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["NÁPOLES", "INSURGENTES SAN BORJA"]},
            "03900": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["ÁLAMOS"]},
            "03910": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["POSTAL"]},
            "03920": {"estado": "CIUDAD DE MÉXICO", "municipio": "BENITO JUÁREZ", "colonias": ["MODERNA"]},
            
            # COYOACÁN
            "04000": {"estado": "CIUDAD DE MÉXICO", "municipio": "COYOACÁN", "colonias": ["VILLA COYOACÁN", "COYOACÁN CENTRO"]},
            "04100": {"estado": "CIUDAD DE MÉXICO", "municipio": "COYOACÁN", "colonias": ["DEL CARMEN", "VILLA COYOACÁN"]},
            "04200": {"estado": "CIUDAD DE MÉXICO", "municipio": "COYOACÁN", "colonias": ["SANTA CATARINA"]},
            "04300": {"estado": "CIUDAD DE MÉXICO", "municipio": "COYOACÁN", "colonias": ["AJUSCO"]},
            "04310": {"estado": "CIUDAD DE MÉXICO", "municipio": "COYOACÁN", "colonias": ["COPILCO UNIVERSIDAD", "COPILCO EL ALTO"]},
            "04320": {"estado": "CIUDAD DE MÉXICO", "municipio": "COYOACÁN", "colonias": ["COPILCO EL BAJO"]},
            "04330": {"estado": "CIUDAD DE MÉXICO", "municipio": "COYOACÁN", "colonias": ["COPILCO"]},
            "04400": {"estado": "CIUDAD DE MÉXICO", "municipio": "COYOACÁN", "colonias": ["ROMERO DE TERREROS"]},
            "04500": {"estado": "CIUDAD DE MÉXICO", "municipio": "COYOACÁN", "colonias": ["PEDREGAL DE SANTO DOMINGO"]},
            
            # ÁLVARO OBREGÓN
            "01000": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["SAN ÁNGEL"]},
            "01010": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["SAN ÁNGEL INN"]},
            "01020": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["GUADALUPE INN"]},
            "01030": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["AXOTLA"]},
            "01040": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["FLORIDA"]},
            "01050": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["CAMPESTRE"]},
            "01060": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["CHIMALISTAC"]},
            "01070": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["TLACOPAC"]},
            "01080": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["ALTAVISTA"]},
            "01090": {"estado": "CIUDAD DE MÉXICO", "municipio": "ÁLVARO OBREGÓN", "colonias": ["GUADALUPE INN"]},
            
            # GUSTAVO A. MADERO
            "07000": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["LINDAVISTA"]},
            "07010": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["TEPEYAC INSURGENTES"]},
            "07020": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["MAGDALENA DE LAS SALINAS"]},
            "07050": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["GUADALUPE INSURGENTES"]},
            "07100": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["VILLA GUSTAVO A. MADERO"]},
            
            # IZTAPALAPA
            "09000": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["IZTAPALAPA CENTRO"]},
            "09100": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["GRANJAS MÉXICO"]},
            "09200": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["SAN LORENZO TEZONCO"]},
            "09810": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["LOMAS DE SAN LORENZO"]},
            
            # TLALPAN
            "14000": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["TLALPAN CENTRO"]},
            "14100": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["PARQUE DEL PEDREGAL"]},
            "14200": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["SAN PEDRO APÓSTOL"]},
            "14300": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["VILLA OLÍMPICA"]},
            
            
            # ========== CUAJIMALPA (10 CPs) ==========
            "05000": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["CUAJIMALPA CENTRO"]},
            "05010": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["ZENTLAPATL"]},
            "05020": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["LOMAS DE VISTA HERMOSA"]},
            "05100": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["CONTADERO"]},
            "05120": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["BOSQUES DE LAS LOMAS"]},
            "05200": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["SAN LORENZO ACOPILCO"]},
            "05219": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["EL MOLINITO"]},
            "05300": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["LA VENTA"]},
            "05348": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["SANTA FE"]},
            "05400": {"estado": "CIUDAD DE MÉXICO", "municipio": "CUAJIMALPA", "colonias": ["SAN PABLO CHIMALPA"]},
            
            # ========== GUSTAVO A. MADERO (15 CPs adicionales) ==========
            "07000": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["LINDAVISTA"]},
            "07010": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["TEPEYAC INSURGENTES"]},
            "07020": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["MAGDALENA DE LAS SALINAS"]},
            "07040": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["INDUSTRIAL"]},
            "07050": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["GUADALUPE INSURGENTES"]},
            "07070": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["ARAGÓN LA VILLA"]},
            "07100": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["VILLA GUSTAVO A. MADERO"]},
            "07140": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["CAMPESTRE ARAGÓN"]},
            "07160": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["LINDAVISTA VALLEJO"]},
            "07300": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["LINDAVISTA SUR"]},
            "07320": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["DEFENSORES DE LA REPÚBLICA"]},
            "07400": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["NUEVA ATZACOALCO"]},
            "07500": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["LA JOYA"]},
            "07600": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["SAN JUAN DE ARAGÓN"]},
            "07700": {"estado": "CIUDAD DE MÉXICO", "municipio": "GUSTAVO A. MADERO", "colonias": ["PUEBLO DE GUADALUPE VICTORIA"]},
            
            # ========== IZTACALCO (10 CPs) ==========
            "08000": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["IZTACALCO"]},
            "08010": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["GABRIEL RAMOS MILLÁN"]},
            "08100": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["AGRÍCOLA PANTITLÁN"]},
            "08200": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["VIADUCTO PIEDAD"]},
            "08220": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["JUVENTINO ROSAS"]},
            "08300": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["SANTA ANITA"]},
            "08400": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["GRANJAS MÉXICO"]},
            "08500": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["AGRÍCOLA ORIENTAL"]},
            "08600": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["MAGDALENA MIXIUHCA"]},
            "08700": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTACALCO", "colonias": ["PUEBLO IZTACALCO"]},
            
            # ========== IZTAPALAPA (15 CPs adicionales) ==========
            "09000": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["IZTAPALAPA CENTRO"]},
            "09020": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["BARRIO SAN PEDRO"]},
            "09040": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["BARRIO SAN LUCAS"]},
            "09060": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["BARRIO SAN PABLO"]},
            "09070": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["SANTA BÁRBARA"]},
            "09080": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["JUAN ESCUTIA"]},
            "09100": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["GRANJAS MÉXICO"]},
            "09200": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["SAN LORENZO TEZONCO"]},
            "09300": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["AGRÍCOLA ORIENTAL"]},
            "09400": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["JUAN ESCUTIA"]},
            "09500": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["UNIDAD VICENTE GUERRERO"]},
            "09600": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["PUEBLO CULHUACÁN"]},
            "09700": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["LOMAS DE ZARAGOZA"]},
            "09800": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["SANTA MARÍA AZTAHUACÁN"]},
            "09810": {"estado": "CIUDAD DE MÉXICO", "municipio": "IZTAPALAPA", "colonias": ["LOMAS DE SAN LORENZO"]},
            
            # ========== MAGDALENA CONTRERAS (8 CPs) ==========
            "10000": {"estado": "CIUDAD DE MÉXICO", "municipio": "MAGDALENA CONTRERAS", "colonias": ["LA MAGDALENA"]},
            "10100": {"estado": "CIUDAD DE MÉXICO", "municipio": "MAGDALENA CONTRERAS", "colonias": ["SAN JERÓNIMO LÍDICE"]},
            "10200": {"estado": "CIUDAD DE MÉXICO", "municipio": "MAGDALENA CONTRERAS", "colonias": ["SAN BERNABÉ OCOTEPEC"]},
            "10300": {"estado": "CIUDAD DE MÉXICO", "municipio": "MAGDALENA CONTRERAS", "colonias": ["PUEBLO NUEVO"]},
            "10320": {"estado": "CIUDAD DE MÉXICO", "municipio": "MAGDALENA CONTRERAS", "colonias": ["BARRANCA SECA"]},
            "10340": {"estado": "CIUDAD DE MÉXICO", "municipio": "MAGDALENA CONTRERAS", "colonias": ["SAN FRANCISCO"]},
            "10378": {"estado": "CIUDAD DE MÉXICO", "municipio": "MAGDALENA CONTRERAS", "colonias": ["LOMAS DE SAN BERNABÉ"]},
            "10400": {"estado": "CIUDAD DE MÉXICO", "municipio": "MAGDALENA CONTRERAS", "colonias": ["HÉROES DE PADIERNA"]},
            
            # ========== MILPA ALTA (6 CPs) ==========
            "12000": {"estado": "CIUDAD DE MÉXICO", "municipio": "MILPA ALTA", "colonias": ["VILLA MILPA ALTA CENTRO"]},
            "12100": {"estado": "CIUDAD DE MÉXICO", "municipio": "MILPA ALTA", "colonias": ["SAN PABLO OZTOTEPEC"]},
            "12200": {"estado": "CIUDAD DE MÉXICO", "municipio": "MILPA ALTA", "colonias": ["SAN PEDRO ATOCPAN"]},
            "12300": {"estado": "CIUDAD DE MÉXICO", "municipio": "MILPA ALTA", "colonias": ["SAN BARTOLOMÉ XICOMULCO"]},
            "12400": {"estado": "CIUDAD DE MÉXICO", "municipio": "MILPA ALTA", "colonias": ["SAN FRANCISCO TECOXPA"]},
            "12500": {"estado": "CIUDAD DE MÉXICO", "municipio": "MILPA ALTA", "colonias": ["SAN JERÓNIMO MIACATLÁN"]},
            
            # ========== TLÁHUAC (8 CPs) ==========
            "13000": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLÁHUAC", "colonias": ["TLÁHUAC CENTRO"]},
            "13010": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLÁHUAC", "colonias": ["LA HABANA"]},
            "13020": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLÁHUAC", "colonias": ["SELENE"]},
            "13040": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLÁHUAC", "colonias": ["JARDINES DEL LLANO"]},
            "13050": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLÁHUAC", "colonias": ["SAN ANDRÉS MIXQUIC"]},
            "13060": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLÁHUAC", "colonias": ["SAN JUAN IXTAYOPAN"]},
            "13070": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLÁHUAC", "colonias": ["SANTA CATARINA YECAHUIZOTL"]},
            "13080": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLÁHUAC", "colonias": ["ZAPOTITLA"]},
            
            # ========== TLALPAN (15 CPs adicionales) ==========
            "14000": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["TLALPAN CENTRO"]},
            "14020": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["VILLA OLÍMPICA"]},
            "14030": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["BELISARIO DOMÍNGUEZ"]},
            "14050": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["ISIDRO FABELA"]},
            "14100": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["PARQUE DEL PEDREGAL"]},
            "14200": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["SAN PEDRO APÓSTOL"]},
            "14240": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["CAÑADA"]},
            "14300": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["VILLA OLÍMPICA"]},
            "14320": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["CANTERA PUENTE DE PIEDRA"]},
            "14330": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["CLUB DE GOLF MÉXICO"]},
            "14340": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["COUNTRY CLUB"]},
            "14360": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["JARDINES DEL PEDREGAL"]},
            "14370": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["FUENTES DEL PEDREGAL"]},
            "14400": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["SAN FERNANDO"]},
            "14500": {"estado": "CIUDAD DE MÉXICO", "municipio": "TLALPAN", "colonias": ["SAN MIGUEL AJUSCO"]},
            
            # ========== VENUSTIANO CARRANZA (15 CPs adicionales) ==========
            "15000": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["ROMERO RUBIO"]},
            "15020": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["MORELOS"]},
            "15100": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["MOCTEZUMA 1RA SECCIÓN"]},
            "15200": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["PENSADOR MEXICANO"]},
            "15300": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["PEÑÓN DE LOS BAÑOS"]},
            "15400": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["FEDERAL"]},
            "15500": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["PUEBLA"]},
            "15600": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["CARACOL"]},
            "15700": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["CINCO DE MAYO"]},
            "15800": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["10 DE MAYO"]},
            "15840": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["CUCHILLA PANTITLÁN"]},
            "15900": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["JARDÍN BALBUENA"]},
            "15960": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["AERONÁUTICA MILITAR"]},
            "15970": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["AVIACIÓN CIVIL"]},
            "15980": {"estado": "CIUDAD DE MÉXICO", "municipio": "VENUSTIANO CARRANZA", "colonias": ["AMPLIACIÓN AVIACIÓN CIVIL"]},
            
            # ========== XOCHIMILCO (10 CPs adicionales) ==========
            "16000": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["XOCHIMILCO CENTRO"]},
            "16010": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["SAN LORENZO ATEMOAYA"]},
            "16020": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["SAN DIEGO"]},
            "16030": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["BARRIO EL ROSARIO"]},
            "16050": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["SAN FRANCISCO TLALNEPANTLA"]},
            "16090": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["SANTA CRUZ ACALPIXCA"]},
            "16100": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["PUEBLO SAN GREGORIO ATLAPULCO"]},
            "16200": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["PUEBLO SANTIAGO TEPALCATLALPAN"]},
            "16300": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["PUEBLO SAN LUIS TLAXIALTEMALCO"]},
            "16400": {"estado": "CIUDAD DE MÉXICO", "municipio": "XOCHIMILCO", "colonias": ["PUEBLO SAN MATEO XALPA"]},
            
            # ========== AZCAPOTZALCO (10 CPs adicionales) ==========
            "02000": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["CENTRO DE AZCAPOTZALCO"]},
            "02010": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["SAN SEBASTIÁN"]},
            "02020": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["SANTA MARÍA LA RIBERA"]},
            "02040": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["SAN ÁLVARO"]},
            "02050": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["SANTA CRUZ DE LAS SALINAS"]},
            "02060": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["SAN BARTOLO CAHUALTONGO"]},
            "02080": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["SAN MARCOS"]},
            "02100": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["CLAVERÍA"]},
            "02300": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["INDUSTRIAL VALLEJO"]},
            "02400": {"estado": "CIUDAD DE MÉXICO", "municipio": "AZCAPOTZALCO", "colonias": ["NUEVA EL ROSARIO"]},
        }
        
    async def validar_codigo_postal(self, cp: str) -> Dict:
        """
        Valida un código postal y obtiene información asociada
        
        Primero intenta usar la API de SEPOMEX (si hay API key configurada).
        Si falla o no hay API key, usa el diccionario local.
        
        Returns:
            {
                "valido": True/False,
                "estado": "Ciudad de México",
                "municipio": "Cuauhtémoc",
                "colonias": ["CONDESA", "HIPÓDROMO", ...],
                "fuente": "api" o "local"
            }
        """
        # Intentar con API primero (si está habilitada y hay token configurado)
        if self.use_api and self.api_token:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/query/info_cp/{cp}",
                        params={"token": self.api_token}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Formato de respuesta de Copomex:
                        # [{"error": false, "response": {"cp": "06700", "asentamiento": "CONDESA", ...}}, ...]
                        if data and len(data) > 0:
                            colonias = []
                            estado = ""
                            municipio = ""
                            
                            for item in data:
                                if not item.get("error") and "response" in item:
                                    resp = item["response"]
                                    colonias.append(resp.get("asentamiento", ""))
                                    if not estado:
                                        estado = resp.get("estado", "")
                                    if not municipio:
                                        municipio = resp.get("municipio", "")
                            
                            if colonias:
                                return {
                                    "valido": True,
                                    "codigo_postal": cp,
                                    "estado": estado,
                                    "municipio": municipio,
                                    "colonias": colonias,
                                    "fuente": "api"
                                }
                        
            except Exception as e:
                logger.warning(f"API SEPOMEX no disponible, usando diccionario local: {str(e)}")
        
        # Fallback al diccionario local
        if cp in self.diccionario_local:
            info = self.diccionario_local[cp]
            return {
                "valido": True,
                "codigo_postal": cp,
                "estado": info["estado"],
                "municipio": info["municipio"],
                "colonias": info["colonias"],
                "fuente": "local",
                "nota": "Datos del diccionario local. Configure API key de copomex.com para datos completos."
            }
        
        # CP no encontrado ni en API ni en diccionario local
        return {
            "valido": False,
            "codigo_postal": cp,
            "error": "Código postal no encontrado",
            "fuente": "ninguna"
        }
    
    async def buscar_colonias_por_cp(self, cp: str) -> List[str]:
        """
        Obtiene lista de colonias para un código postal
        
        Returns:
            ["CONDESA", "HIPÓDROMO", "HIPÓDROMO CONDESA", ...]
        """
        resultado = await self.validar_codigo_postal(cp)
        
        if resultado.get("valido"):
            return resultado.get("colonias", [])
        else:
            return []
    
    async def validar_colonia_en_cp(self, colonia: str, cp: str) -> Dict:
        """
        Valida si una colonia existe en un código postal específico
        
        Returns:
            {
                "valida": True/False,
                "colonia_exacta": "CONDESA",
                "similares": ["HIPÓDROMO CONDESA", "CONDESA SUR"],
                "codigo_postal": "06700"
            }
        """
        colonias_validas = await self.buscar_colonias_por_cp(cp)
        
        if not colonias_validas:
            return {
                "valida": False,
                "colonia": colonia,
                "codigo_postal": cp,
                "error": "Código postal no válido o sin colonias"
            }
        
        # Normalizar colonia ingresada
        colonia_normalizada = colonia.upper().strip()
        
        # Buscar coincidencia exacta
        if colonia_normalizada in colonias_validas:
            return {
                "valida": True,
                "colonia": colonia,
                "colonia_exacta": colonia_normalizada,
                "codigo_postal": cp,
                "mensaje": "Colonia validada correctamente"
            }
        
        # Buscar coincidencias parciales
        similares = [c for c in colonias_validas if colonia_normalizada in c or c in colonia_normalizada]
        
        if similares:
            return {
                "valida": False,
                "colonia": colonia,
                "codigo_postal": cp,
                "similares": similares,
                "mensaje": f"Colonia no exacta. ¿Quisiste decir alguna de estas? {', '.join(similares[:3])}"
            }
        else:
            return {
                "valida": False,
                "colonia": colonia,
                "codigo_postal": cp,
                "mensaje": "Colonia no encontrada en este código postal",
                "colonias_disponibles": colonias_validas[:10]  # Mostrar primeras 10
            }
    
    async def buscar_por_colonia(self, colonia: str, estado: str = "Ciudad de México") -> List[Dict]:
        """
        Busca códigos postales por nombre de colonia
        
        Returns:
            [
                {
                    "codigo_postal": "06700",
                    "municipio": "Cuauhtémoc",
                    "colonia": "CONDESA"
                },
                ...
            ]
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/query/get_colonia_por_cp",
                    params={
                        "type": "simplified",
                        "colonia": colonia,
                        "estado": estado
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data
                else:
                    logger.warning(f"API SEPOMEX error buscando colonia: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error buscando colonia {colonia}: {str(e)}")
            return []
    
    async def validar_direccion_completa(
        self, 
        calle: str, 
        numero: str, 
        colonia: str, 
        cp: str,
        alcaldia: str = None
    ) -> Dict:
        """
        Valida una dirección completa contra SEPOMEX
        
        Returns:
            {
                "valida": True/False,
                "codigo_postal": {validacion_cp},
                "colonia": {validacion_colonia},
                "alcaldia_correcta": "CUAUHTÉMOC",
                "sugerencias": [...]
            }
        """
        resultado = {
            "valida": True,
            "validaciones": {}
        }
        
        # Validar código postal
        validacion_cp = await self.validar_codigo_postal(cp)
        resultado["validaciones"]["codigo_postal"] = validacion_cp
        
        if not validacion_cp.get("valido"):
            resultado["valida"] = False
            return resultado
        
        # Validar colonia en ese CP
        validacion_colonia = await self.validar_colonia_en_cp(colonia, cp)
        resultado["validaciones"]["colonia"] = validacion_colonia
        
        if not validacion_colonia.get("valida"):
            resultado["valida"] = False
        
        # Validar alcaldía (municipio)
        if alcaldia:
            municipio_sepomex = validacion_cp.get("municipio", "").upper()
            alcaldia_normalizada = alcaldia.upper().strip()
            
            resultado["validaciones"]["alcaldia"] = {
                "alcaldia_ingresada": alcaldia,
                "alcaldia_correcta": municipio_sepomex,
                "coincide": alcaldia_normalizada == municipio_sepomex or alcaldia_normalizada in municipio_sepomex
            }
            
            if not resultado["validaciones"]["alcaldia"]["coincide"]:
                resultado["valida"] = False
        
        return resultado

# Instancia global del servicio
sepomex_service = SepomexService()
