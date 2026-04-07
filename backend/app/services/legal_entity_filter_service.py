"""
Servicio de filtrado inteligente para análisis jurídico
Descarta entidades no válidas detectadas por error del NLP/OCR
"""

import re
from typing import Dict, List, Optional, Tuple


class LegalEntityFilterService:
    """Filtra entidades jurídicas inválidas detectadas por error"""
    
    # ============================================
    # LISTAS POSITIVAS - Nombres/apellidos reales
    # ============================================
    
    NOMBRES_COMUNES = {
        # Nombres masculinos
        'juan', 'josé', 'jose', 'carlos', 'luis', 'miguel', 'francisco', 'javier',
        'antonio', 'manuel', 'fernando', 'jorge', 'ricardo', 'roberto', 'alejandro',
        'pedro', 'daniel', 'david', 'sergio', 'eduardo', 'alberto', 'arturo',
        'rafael', 'raúl', 'raul', 'enrique', 'victor', 'víctor', 'jesus', 'jesús',
        'diego', 'angel', 'ángel', 'pablo', 'marco', 'marcos', 'gabriel', 'gerardo',
        'oscar', 'óscar', 'rodrigo', 'andres', 'andrés', 'felipe', 'guillermo',
        'gustavo', 'hector', 'héctor', 'hugo', 'ignacio', 'jaime', 'julio',
        'mauricio', 'mario', 'ramon', 'ramón', 'ruben', 'rubén', 'salvador',
        'samuel', 'santiago', 'omar', 'isaac', 'ismael', 'abraham', 'cesar', 'césar',
        'adrian', 'adrián', 'armando', 'bernardo', 'orlando', 'emilio', 'ernesto',
        
        # Nombres femeninos
        'maria', 'maría', 'guadalupe', 'rosa', 'ana', 'martha', 'margarita',
        'elizabeth', 'isabel', 'patricia', 'elena', 'laura', 'carmen', 'silvia',
        'teresa', 'claudia', 'sandra', 'gabriela', 'andrea', 'mónica', 'monica',
        'alejandra', 'verónica', 'veronica', 'beatriz', 'norma', 'adriana',
        'liliana', 'carolina', 'diana', 'julia', 'karla', 'leticia', 'lorena',
        'lucia', 'lucía', 'magdalena', 'marcela', 'marisol', 'nancy', 'olga',
        'paola', 'raquel', 'rocio', 'rocío', 'sara', 'sofía', 'sofia', 'susana',
        'yolanda', 'ximena', 'jessica', 'daniela', 'fernanda', 'pamela', 'carolina',
        'valentina', 'camila', 'natalia', 'victoria', 'emilia', 'mariana', 'dulce',
        'lourdes', 'irma', 'cristina', 'gloria', 'eva', 'dalia', 'lidia', 'alma',
        'angelica', 'angélica', 'barbara', 'bárbara', 'cecilia', 'consuelo'
    }
    
    APELLIDOS_COMUNES = {
        'garcia', 'garcía', 'hernandez', 'hernández', 'martinez', 'martínez',
        'lopez', 'lópez', 'gonzalez', 'gonzález', 'rodriguez', 'rodríguez',
        'perez', 'pérez', 'sanchez', 'sánchez', 'ramirez', 'ramírez', 'torres',
        'flores', 'rivera', 'gomez', 'gómez', 'diaz', 'díaz', 'cruz', 'morales',
        'reyes', 'gutierrez', 'gutiérrez', 'ortiz', 'chavez', 'chávez', 'ruiz',
        'jimenez', 'jiménez', 'mendoza', 'alvarez', 'álvarez', 'castillo',
        'moreno', 'romero', 'herrera', 'medina', 'aguilar', 'vargas', 'contreras',
        'santiago', 'guerrero', 'estrada', 'cortes', 'cortés', 'mendez', 'méndez',
        'soto', 'guzman', 'guzmán', 'rojas', 'castro', 'bautista', 'ortega',
        'campos', 'cervantes', 'suarez', 'suárez', 'vazquez', 'vázquez', 'rios',
        'ríos', 'salazar', 'ramos', 'mejia', 'mejía', 'leon', 'león', 'sandoval',
        'carrillo', 'dominguez', 'domínguez', 'maldonado', 'calderon', 'calderón',
        'vega', 'navarro', 'pena', 'peña', 'delgado', 'luna', 'serrano', 'ibarra',
        'duran', 'durán', 'espinoza', 'solis', 'solís', 'ochoa', 'lara', 'camacho',
        'avila', 'ávila', 'fuentes', 'villa', 'trejo', 'escobedo', 'molina',
        'velazquez', 'velázquez', 'miranda', 'cabrera', 'montoya', 'cervantes',
        'alvarado', 'villarreal', 'benitez', 'benítez', 'salas', 'montes', 'orozco',
        'marin', 'marín', 'juarez', 'juárez', 'lozano', 'parra', 'gallegos',
        'escobar', 'leon', 'garza', 'barrera', 'munoz', 'muñoz', 'estrada',
        'albarran', 'albarrán', 'cavazos', 'saldivar', 'saldívar', 'macias'
    }
    
    # ============================================
    # LISTAS NEGRAS - NO son personas reales
    # ============================================
    
    TITULOS_NO_PERSONAS = {
        # Instituciones
        'ministerio publico', 'ministerio público', 'min publico', 'ministario publico',
        'procuraduria general', 'procuraduría general', 'fiscalia', 'fiscalía',
        'agencia investigadora', 'representacion social', 'representación social',
        'visitaduria ministerial', 'visitaduría ministerial',
        'contraloria interna', 'contraloría interna',
        'direccion general', 'dirección general',
        'fiscalia central', 'fiscalía central', 'fiscalla central',
        'fiscalizacion superior', 'fiscalización superior',
        
        # Documentos legales
        'constitucion politica', 'constitución política',
        'codigo nacional', 'código nacional', 'codigo nac',
        'codigo penal', 'código penal',
        'codigo civil', 'código civil',
        'ley general', 'ley federal', 'ley organica', 'ley orgánica', 'ley genera', 'ley carisi', 'lay cirverai',
        'codigo procesal', 'código procesal',
        'procedimientos penales', 'procedigiientos penales',
        'procedimientos civiles',
        'averiguaciones previas', 'averiguación previa', 'averiguaciones coarirras',
        'protocolo nacional', 'guia nacional', 'guía nacional',
        
        # Lugares/Entidades geográficas
        'estados unidos mexicanos', 'estados unidos', 'estado unidos', 'entaos levss menmanos', 'estaris unidos', 'unidos mexicanos',
        'distrito federal', 'ciudad de mexico', 'ciudad de méxico', 'distnto federal', 'distrita fadrra', 'distrito pevra', 'mnto fedecal', 'drsumo foderal',
        'delegacion cuauhtemoc', 'delegación cuauhtémoc', 'alcaldia cuauhtemoc', 'del cuautumoc', 'del cunitemoc', 'dorta del cuentemor',
        'mexico distrito federal', 'méxico distrito federal',
        'general gabriel hernandez', 'general gabriel hemandez', 'gatrrel hamady', 'sral gabriel femaod',
        'doctor andrade', 'colonia doctores', 'colonia dintaros',
        'calle general gabriel hernandez',
        
        # Conceptos abstractos
        'datos personales', 'derechos humanos', 'seguridad publica', 'seguridad pública', 'dotos penonajo',
        'servidores publicos', 'servidores públicos',
        'delitos cometidos', 'delitos sexuales', 'delitos sexuale', 'dolitos saany',
        'abuso sexual', 'abuso sexuale', 'violencia familiar', 'violencia intrafamiliar',
        'mecanismo ciudadano', 'mecanismos ciudadanos',
        'informacion publica', 'información pública', 'infornacion publica', 'informacion escobr', 'informecion escolar',
        'administracion publica', 'administración pública',
        'fundamento legal', 'primer apellido', 'segundo apellido',
        'numero numero', 'número número',
        'planta baja', 'edificio principal',
        'poder judicial', 'organos jurisdiccionales', 'órganos jurisdiccionales',
        'procesos jurisdiccionales', 'procedimiento administrativo',
        'auditoria superior', 'auditoría superior', 'fuucanion supervor',
        'registro nacional', 'sistema nacional', 'sislejha integral', 'jerxrirado sistena',
        'comision nacional', 'comisión nacional',
        'diario oficial', 'diatio ufcral',
        'segundo turno', 'actuacion primer', 'asunto terminado',
        'el ciudadano', 'ciudadano de',
        
        # Referencias bibliográficas y personajes históricos/ficticios
        'sigmund freud', 'carl jung', 'jacques lacan', 'melanie klein',
        'anna freud', 'alfred adler', 'erik erikson',
        'diccionario larousse', 'diccionario enciclopedico', 'diccionario enciclopédico',
        'enciclopedia britanica', 'enciclopedia británica',
        'segunda guerra mundial', 'primera guerra mundial', 'guerra mundial',
        'revolucion mexicana', 'revolución mexicana',
        'constitucion de', 'constitución de',
        'suprema corte', 'corte suprema',
        'nueva york', 'los angeles', 'washington',
        
        # Juzgados y tribunales
        'juzgado', 'tribunal colegiado', 'tribunal', 'circuito',
        'materia penal', 'materia civil', 'amparo penal',
        'semanario judicial', 'tesis jurisprudencia',
        
        # Documentos y conceptos legales adicionales
        'acta constitutiva', 'representante legal',
        'desarrollo integral', 'personas violadas',
        'armonización legislativa', 'mejores prácticas',
        'sociedad civil', 'publicación diario',
        
        # Calles y lugares
        'periférico', 'avenida', 'boulevard', 'calzada',
        'colonia', 'fraccionamiento',
        
        # Roles/Puestos (no nombres específicos)
        'asesor juridico', 'asesor jurídico', 'asesores juridicos',
        'procurador general', 'ciudadano procurador',
        'coordinador general', 'servicios periciales',
        'medica cirujana', 'miedica cirujana',
        
        # Basura OCR común detectada en tu lista
        'age nisteris', 'ae cr', 'ne mbuios', 'te canelifueion foviica',
        'liy cirverai', 'caianumecas jor', 'ey futam de mratessas',
        'ce se', 'hara teenda', 'tanena moeg', 'aiemacn estalar',
        'lay carisi', 'etacion euparos', 'caumbla tabarai',
        'pratecoa xe camos', 'trc mtiva', 'ea sa ae taay',
        'fa cobemamental', 'fadedades progies', 'ea nombre',
        'constucion folines', 'ta constitucion yoliñes',
        'pobiss lzolerr', 'ditos personales', 'tacal lomala', 'tai lo', 'dar cel',
        'fivcurdura sonura', 'avenguaciones provias centrans', 'suzuates agens',
        'procuraduria gerural', 'prucuraduda gon',
        'yaretir dueñas andrade', 'jarastzar su', 'daniela sglead anaya cast',
        'maria fernand', 'isabel campuzano estrada',
        'manuel horacio cavazos lopez', 'barbara cavazos albarran', 'estela salas febrero',
        
        # Basura OCR común general
        'unidad firma', 'hora motivo', 'fecha hora motivo', 'clase responsable',
        'estimados señores', 'estimados padres',
        'de la', 'el licenciado', 'la licenciada',
        'en derecho', 'en degecho', 'de erio', 'del min',
        'acuerdo institucional', 'ehecrotino ed', 'investigacion número'
    }
    
    # Patrones de basura OCR en responsables
    PATRONES_BASURA_RESPONSABLE = [
        r'^en\s+de[rg]echo$',  # "en derecho", "en degecho"
        r'^de\s+\w{1,4}$',  # "de erio", "del min"
        r'^del\s+\w{1,4}$',
        r'^\w{1,3}$',  # Una o dos letras solas
        r'^-+$',  # Solo guiones
        r'^\s*$',  # Vacío
        r'[A-Z]{10,}',  # Muchas mayúsculas seguidas (basura OCR)
        r'^\d+$',  # Solo números
        r'^del\s+minister',  # "DEL MINISTERIO..." (genérico)
        r'^de\s+minister',  # "DE MINISTERIO..." (genérico)
        r'^de\s+la\s+policia',  # "DE LA POLICIA DE" (genérico)
        r'sin\s+estar$',  # "sin estar" (basura)
        r'^porque\s+no',  # "PORQUE NO ESTABA TAN" (basura)
        r'rapport\s+para',  # "rapport para favorecer la" (descripción, no nombre)
        r'encuadre\s+terapeutico',  # "encuadre terapeutico con la" (descripción)
        r'^en\s+pedagogia$',  # "en Pedagogia" (carrera, no nombre)
        r'\s+se$',  # Termina en " SE" (truncado)
        r'^\w+\s+j[l]as\s',  # "Cesar Ivan Jlas" (OCR error)
    ]
    
    # Responsables genéricos que NO son nombres específicos
    RESPONSABLES_GENERICOS = {
        'del ministerio público',
        'del ministerio publico',
        'de ministerio público',
        'de ministerio publico',
        'del ministerio público adscrito',
        'del ministerio publico considere',
        'del ministerio público procuraduríaede',
        'del ministerio público fecha',
        'del ministerio público eñ',
        'del ministerio público para',
        'del ministerio público en',
        'del ministeryo publico licentrociado',
        'del ministhrrd publico',
        'del ministerdo publico',
        'del ministerio publicq',
        'del maspter',
        'de la policia de',
        'sin estar',
        'porque no estaba tan',
        'siguiente registro de actuacion',
        'rapport para favorecer la',
        'encuadre terapeutico con la',
        'en pedagogia',
    }
    
    # ============================================
    # ESTADOS Y MUNICIPIOS MEXICANOS (no son apellidos cuando son 2a palabra sola)
    # ============================================
    
    ESTADOS_MEXICO = {
        'guerrero', 'oaxaca', 'morelos', 'puebla', 'hidalgo', 'tlaxcala',
        'michoacan', 'michoacán', 'jalisco', 'sinaloa', 'sonora', 'chihuahua',
        'coahuila', 'veracruz', 'tabasco', 'campeche', 'yucatan', 'yucatán',
        'chiapas', 'nayarit', 'colima', 'aguascalientes', 'zacatecas', 'durango',
        'guanajuato', 'queretaro', 'querétaro', 'tamaulipas', 'baja california',
    }
    
    # ============================================
    # VALIDACIONES
    # ============================================
    
    def es_nombre_valido(self, nombre: str) -> Tuple[bool, Optional[str]]:
        """
        Validar si un nombre es una persona real
        Returns: (es_valido, razon_invalido)
        """
        # Validar que nombre no sea None
        if nombre is None:
            return False, "Nombre es None"
        
        if not nombre or len(nombre.strip()) < 3:
            return False, "Nombre muy corto"
        
        nombre_lower = nombre.lower().strip()
        
        # 1. Verificar lista negra exacta
        if nombre_lower in self.TITULOS_NO_PERSONAS:
            return False, "Es un título/institución, no una persona"
        
        # 2. Verificar lista negra parcial (contiene) - MÁS AGRESIVO
        for titulo_invalido in self.TITULOS_NO_PERSONAS:
            if titulo_invalido in nombre_lower and len(titulo_invalido) > 5:  # Reducido de 8 a 5
                return False, f"Contiene término institucional"
        
        # 3. Palabras clave institucionales adicionales
        keywords_invalidos = [
            'codigo', 'código', 'ley ', 'estados unidos', 'estado unidos',
            'distrito', 'constitucion', 'constitución', 'fiscal', 'protocolo',
            'guia', 'guía', 'nacional', 'federal', 'general', 'publica', 'pública',
            'delitos', 'informacion', 'información', 'administracion', 'administración',
            'servidores', 'derechos', 'datos personales', 'sistema ', 'servicio',
            'coordinador', 'asunto', 'turno', 'investigacion', 'investigación',
            'ciudadano de', 'alcaldia', 'alcaldía', 'colonia ', 'calle ', 'avenida',
            'doctor andrade', 'gabriel hernandez', 'doctores',
            'universidad', 'autonoma', 'autónoma', 'escolar',
            'periciales', 'juridicos', 'jurídicos', 'asesor', 'asesores',
            'segundoturn', 'actuacion', 'terminado'
        ]
        
        for keyword in keywords_invalidos:
            if keyword in nombre_lower:
                return False, f"Keyword institucional"
        
        # 4. Debe tener al menos 2 palabras (nombre + apellido)
        palabras = nombre.split()
        if len(palabras) < 2:
            return False, "Falta apellido"
        
        # 5. Cada palabra debe tener longitud mínima (evitar "A B C", "Abc Def")
        for palabra in palabras:
            if len(palabra) < 2:
                return False, "Palabras muy cortas"
        
        # 5b. Al menos una palabra debe tener 4+ caracteres (nombres reales: Juan, María, etc)
        palabras_largas = [p for p in palabras if len(p) >= 4]
        if len(palabras_largas) == 0:
            return False, "Todas las palabras son muy cortas"
        
        # 6. Primera palabra debe ser un nombre razonable
        primera_palabra = palabras[0].lower()
        if len(primera_palabra) < 3:
            return False, "Primer nombre muy corto"
        
        # 7. No puede tener solo mayúsculas sin sentido
        if len(nombre) > 30 and nombre.isupper():
            palabras_largas = [p for p in palabras if len(p) > 15]
            if len(palabras_largas) > 0:
                return False, "Mayúsculas sospechosas"
        
        # 8. No puede tener caracteres extraños
        if re.search(r'[^a-zA-ZáéíóúñÑÁÉÍÓÚ\s\.\-]', nombre):
            return False, "Caracteres inválidos"
        
        # 9. Debe tener al menos 2 vocales (nombres reales tienen vocales)
        vocales_count = len(re.findall(r'[aeiouáéíóúAEIOUÁÉÍÓÚ]', nombre))
        if vocales_count < 2:
            return False, "Pocas vocales - OCR error"
        
        # 10. Si tiene números, rechazar
        if re.search(r'\d', nombre):
            return False, "Contiene números"
        
        # 11. Rechazar consonantes excesivas seguidas (OCR error)
        # Más de 4 consonantes seguidas es muy sospechoso (ej: "Phcratit")
        if re.search(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{4,}', nombre):
            return False, "OCR error - consonantes excesivas"
        
        # 12. Debe empezar con mayúscula
        if not nombre[0].isupper():
            return False, "No empieza con mayúscula"
        
        # 13. Detectar palabras comunes que NO son nombres de personas
        palabras_sospechosas = [
            'tomo', 'juzgado', 'tribunal', 'circuito', 'materia', 'penal', 'civil',
            'semanario', 'judicial', 'colegiado', 'amparo', 'secretari', 'periférico',
            'desarrollo', 'integral', 'violadas', 'legal', 'acta', 'constitutiva',
            'armonización', 'legislativa', 'prácticas', 'sociedad', 'publicación'
        ]
        
        nombre_lower_palabras = nombre.lower().split()
        for palabra_sospechosa in palabras_sospechosas:
            # Si la primera o segunda palabra contiene un término sospechoso, rechazar
            if len(nombre_lower_palabras) >= 1 and palabra_sospechosa in nombre_lower_palabras[0]:
                return False, "Contiene término institucional/conceptual"
            if len(nombre_lower_palabras) >= 2 and palabra_sospechosa in nombre_lower_palabras[1]:
                return False, "Contiene término institucional/conceptual"
        
        # 14. Detectar basura OCR: palabras con patrón extraño (ej: "Dai Sacos", "Cds Waco")
        # Nombres reales no tienen mayúsculas en medio: "CdS", "WaCo", etc.
        for palabra in palabras:
            if len(palabra) > 2:
                # Contar transiciones mayúscula-minúscula-mayúscula (patrón extraño)
                transiciones = 0
                for i in range(len(palabra)-1):
                    if palabra[i].isupper() and palabra[i+1].islower() or palabra[i].islower() and palabra[i+1].isupper():
                        transiciones += 1
                if transiciones >= 2:  # "CdS", "WaCo" tienen 2+ transiciones
                    return False, "Patrón de capitalización sospechoso (OCR error)"
        
        # 15. VALIDACIÓN FINAL: Al menos una palabra debe ser un nombre o apellido conocido
        # Esto filtra basura OCR que pasa todas las reglas anteriores
        tiene_nombre_apellido_conocido = False
        palabras_lower = [p.lower() for p in palabras]
        
        for palabra_lower in palabras_lower:
            if palabra_lower in self.NOMBRES_COMUNES or palabra_lower in self.APELLIDOS_COMUNES:
                tiene_nombre_apellido_conocido = True
                break
        
        if not tiene_nombre_apellido_conocido:
            return False, "No contiene ningún nombre o apellido conocido (posible OCR error)"
        
        # 16. Detectar combinaciones ciudad+estado: "Iguala Guerrero", "Ayotzinapa Guerrero"
        # Si tiene exactamente 2 palabras, la 2ª es un estado mexicano, y la 1ª no es un nombre conocido
        if len(palabras) == 2 and palabras_lower[1] in self.ESTADOS_MEXICO:
            if palabras_lower[0] not in self.NOMBRES_COMUNES:
                return False, "Parece ciudad+estado, no nombre de persona"
        
        return True, None
    
    def es_responsable_valido(self, responsable: str) -> Tuple[bool, Optional[str]]:
        """
        Validar si un responsable es válido
        Returns: (es_valido, razon_invalido)
        """
        # Validar que responsable no sea None
        if responsable is None:
            return False, "Responsable es None"
        
        if not responsable or len(responsable.strip()) < 3:
            return False, "Responsable muy corto"
        
        responsable_lower = responsable.lower().strip()
        
        # 1. Verificar lista de responsables genéricos
        if responsable_lower in self.RESPONSABLES_GENERICOS:
            return False, "Responsable genérico (no nombre específico)"
        
        # 2. Patrones de basura OCR
        for patron in self.PATRONES_BASURA_RESPONSABLE:
            if re.search(patron, responsable_lower):
                return False, f"Patrón de basura OCR"
        
        # 3. Si empieza con "del ministerio" y no tiene nombre propio, rechazar
        if responsable_lower.startswith('del ministerio'):
            # Debe tener un nombre propio después (con mayúsculas)
            # Ejemplo válido: "DEL MINISTERIO PÚBLICO SANDRA FLORES"
            # Ejemplo inválido: "DEL MINISTERIO PÚBLICO EN"
            palabras = responsable.split()
            tiene_nombre_propio = any(palabra[0].isupper() and len(palabra) > 3 and palabra.lower() not in ['ministerio', 'público', 'publico', 'para', 'adscrito', 'considere'] for palabra in palabras if len(palabra) > 0)
            if not tiene_nombre_propio:
                return False, "Ministerio Público sin nombre específico"
        
        # 4. Verificar que no sea un título institucional genérico
        if responsable_lower in self.TITULOS_NO_PERSONAS:
            return False, "Es institución, no persona específica"
        
        # 5. Debe tener al menos un nombre y apellido (2 palabras con mayúsculas)
        palabras_mayusculas = [p for p in responsable.split() if p and p[0].isupper() and len(p) > 2]
        if len(palabras_mayusculas) < 2:
            return False, "No tiene nombre completo (mínimo nombre + apellido)"
        
        return True, None
    
    def es_diligencia_valida(self, diligencia: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validar si una diligencia tiene datos mínimos válidos
        Returns: (es_valida, razon_invalida)
        """
        # Manejar valores None de forma segura
        tipo = diligencia.get('tipo', '') or ''
        fecha = diligencia.get('fecha', '') or ''
        responsable = diligencia.get('responsable', '') or ''
        
        tipo = tipo.strip() if isinstance(tipo, str) else ''
        fecha = fecha.strip() if isinstance(fecha, str) else ''
        responsable = responsable.strip() if isinstance(responsable, str) else ''
        
        # 1. Debe tener tipo
        if not tipo or len(tipo) < 3:
            return False, "Sin tipo de diligencia"
        
        # 2. Si no tiene fecha NI responsable, probablemente sea basura
        if not fecha and not responsable:
            return False, "Sin fecha ni responsable (probablemente basura)"
        
        # 3. Si tiene responsable, validarlo
        if responsable:
            es_valido, razon = self.es_responsable_valido(responsable)
            if not es_valido:
                # Si el responsable es inválido pero tiene fecha, aún puede ser útil
                if not fecha or fecha.lower() == 'sin fecha':
                    return False, f"Responsable inválido y sin fecha: {razon}"
        
        return True, None
    
    def filtrar_personas(self, personas: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filtrar personas, separando válidas de inválidas
        Returns: (personas_validas, personas_rechazadas)
        """
        validas = []
        rechazadas = []
        
        for persona in personas:
            # Manejar None de forma segura
            nombre = persona.get('nombre', '') or ''
            nombre = nombre.strip() if isinstance(nombre, str) else ''
            
            es_valido, razon = self.es_nombre_valido(nombre)
            
            if es_valido:
                validas.append(persona)
            else:
                persona_rechazada = persona.copy()
                persona_rechazada['razon_rechazo'] = razon
                rechazadas.append(persona_rechazada)
        
        return validas, rechazadas
    
    def filtrar_diligencias(self, diligencias: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filtrar diligencias, separando válidas de inválidas
        Returns: (diligencias_validas, diligencias_rechazadas)
        """
        validas = []
        rechazadas = []
        
        for diligencia in diligencias:
            es_valida, razon = self.es_diligencia_valida(diligencia)
            
            if es_valida:
                validas.append(diligencia)
            else:
                diligencia_rechazada = diligencia.copy()
                diligencia_rechazada['razon_rechazo'] = razon
                rechazadas.append(diligencia_rechazada)
        
        return validas, rechazadas
    
    def limpiar_direccion_lugar(self, direccion: str) -> Tuple[str, bool]:
        """
        Limpiar dirección de un lugar
        Returns: (direccion_limpia, es_valida)
        """
        # Validar que direccion no sea None
        if direccion is None:
            return '', False
        
        if not direccion or len(direccion.strip()) < 5:
            return direccion, False
        
        direccion_lower = direccion.lower().strip()
        
        # Si es un concepto legal, no es una dirección real
        if direccion_lower in self.TITULOS_NO_PERSONAS:
            return direccion, False
        
        # Debe contener palabras clave de direcciones
        palabras_clave_direccion = ['calle', 'avenida', 'av.', 'calzada', 'privada', 
                                     'colonia', 'numero', 'número', '#']
        
        tiene_palabra_clave = any(palabra in direccion_lower for palabra in palabras_clave_direccion)
        
        if not tiene_palabra_clave:
            # Podría ser solo un nombre de lugar sin dirección completa
            # Lo aceptamos si tiene al menos 2 palabras
            if len(direccion.split()) < 2:
                return direccion, False
        
        return direccion, True


# Instancia global del filtro
legal_entity_filter = LegalEntityFilterService()
