# 📘 Manual de Usuario - Autocorrector Legal

## Índice
1. [Introducción](#introducción)
2. [Acceso al Sistema](#acceso-al-sistema)
3. [Funciones Principales](#funciones-principales)
4. [Guía de Uso](#guía-de-uso)
5. [Validación SEPOMEX](#validación-sepomex)
6. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## Introducción

El **Autocorrector Legal** es una herramienta especializada que corrige automáticamente errores comunes en textos jurídicos extraídos mediante OCR, incluyendo:

- ✅ Nombres de alcaldías de la CDMX
- ✅ Nombres de colonias
- ✅ Términos legales específicos
- ✅ Validación contra catálogo oficial SEPOMEX
- ✅ Detección de duplicados en bases de datos

### ¿Por qué es necesario?

El OCR (reconocimiento óptico de caracteres) puede introducir errores al escanear documentos:
- "Cuauhtémoc" → "Cuauthemoc", "Cuauhtemoc"
- "Colonia" → "Cplonia", "Colpnia"
- "Sentencia" → "Senrencia"

El autocorrector detecta y corrige estos errores automáticamente.

---

## Acceso al Sistema

1. Inicie sesión en el sistema con sus credenciales
2. En el menú principal, haga clic en **"✍️ Autocorrector Legal"**
3. Se abrirá la página con 4 pestañas disponibles

**URL directa:**
```
http://192.168.1.132:8000/autocorrector-legal.html
```

---

## Funciones Principales

### 1. ✏️ Corregir Texto

**Uso:** Corrección rápida de fragmentos de texto.

**Cómo usar:**
1. Pegue o escriba el texto con posibles errores
2. Seleccione el tipo de corrección:
   - **completa**: Corrige alcaldías, colonias y términos legales
   - **alcaldia**: Solo nombres de alcaldías
   - **colonia**: Solo nombres de colonias
   - **termino**: Solo términos legales
3. Haga clic en **"Corregir Texto"**

**Ejemplo:**

**Entrada:**
```
Alcaldia Cuauthemoc, Cplonia Condesa, senrencia definitiva
```

**Salida:**
```
✅ Correcciones realizadas: 3

alcaldia: "Cuauthemoc" → "CUAUHTÉMOC"
colonia: "Cplonia Condesa" → "CONDESA"
termino: "senrencia" → "SENTENCIA"
```

---

### 2. 🏠 Corregir Dirección

**Uso:** Corrección completa de direcciones con validación oficial.

**Cómo usar:**
1. Ingrese los componentes de la dirección:
   - **Dirección**: Calle y número
   - **Colonia**: Nombre de la colonia
   - **Alcaldía**: Delegación o municipio
   - **Código Postal** (opcional pero recomendado)
2. Haga clic en **"Corregir Dirección"**

**Validación SEPOMEX:**
- Si proporciona el código postal, el sistema valida contra el catálogo oficial del Servicio Postal Mexicano
- Muestra si la colonia existe en ese código postal
- Sugiere colonias similares si hay errores

**Ejemplo:**

**Entrada:**
```
Dirección: CALLE GABRIEL HERNANDEZ 56
Colonia: Condeza
Alcaldía: Cuauthemoc
Código Postal: 06700
```

**Salida:**
```
✅ Dirección corregida: CALLE GABRIEL HERNANDEZ 56
✅ Colonia corregida: CONDESA
✅ Alcaldía corregida: CUAUHTÉMOC

📍 Validación SEPOMEX:
✅ Colonia validada en el catálogo oficial
   Código Postal: 06700
   Estado: CIUDAD DE MÉXICO
   Municipio: CUAUHTÉMOC
```

---

### 3. 🔍 Detectar Duplicados

**Uso:** Identificar registros duplicados en carpetas para limpiar la base de datos.

**Cómo usar:**
1. Seleccione una **carpeta** de la lista
2. Seleccione el **tipo de entidad** a revisar:
   - **demandante**: Personas que demandan
   - **demandado**: Personas demandadas
   - **testigo**: Testigos
   - **perito**: Peritos
   - **todos**: Todas las entidades
3. Haga clic en **"Detectar Duplicados"**

**Interpretación de resultados:**

El sistema agrupa entidades similares y muestra:
- **Registros en el grupo**: Cuántos duplicados encontró
- **Se conservará**: El primer registro (ID más bajo)
- **Se eliminarían**: Los duplicados detectados

**Ejemplo:**

```
📊 Estadísticas de Duplicados
Total de duplicados: 5 registros
Grupos de duplicados: 2 grupos

Grupo 1 - Juan Pérez García
├─ ID: 123 ✅ (Se conservará)
├─ ID: 145 ❌ (Duplicado)
└─ ID: 167 ❌ (Duplicado)

Grupo 2 - María López
├─ ID: 234 ✅ (Se conservará)
└─ ID: 256 ❌ (Duplicado)
```

---

### 4. 📁 Corregir Carpeta Completa

**⚠️ SOLO ADMINISTRADORES**

**Uso:** Aplicar correcciones masivas a todos los textos de una carpeta.

**Cómo usar:**
1. Seleccione una **carpeta**
2. Elija el modo:
   - ☑️ **Solo reportar** (recomendado primero): Muestra qué se corregiría sin aplicar cambios
   - ✅ **Aplicar correcciones**: Guarda los cambios en la base de datos
3. Haga clic en **"Iniciar Corrección"**

**Recomendación:**
1. Primero ejecute en modo "Solo reportar"
2. Revise el reporte cuidadosamente
3. Si está conforme, ejecute nuevamente con "Aplicar correcciones"

**Ejemplo de reporte:**

```
📊 Reporte de Corrección Masiva
Carpeta: Juicio 123/2024

Total de correcciones: 45
├─ alcaldia: 15 correcciones
├─ colonia: 20 correcciones
└─ termino: 10 correcciones

Total de duplicados: 3 grupos
├─ demandante: 1 grupo (2 registros)
├─ demandado: 1 grupo (2 registros)
└─ testigo: 1 grupo (3 registros)

Documentos procesados: 12
Tiempo de procesamiento: 2.3 segundos
```

---

## Validación SEPOMEX

### ¿Qué es SEPOMEX?

**SEPOMEX** (Servicio Postal Mexicano) es el catálogo oficial de códigos postales de México. Nuestro sistema se integra con su API para validar que las colonias y códigos postales sean correctos.

### ¿Cómo funciona?

1. **Validación exacta:**
   - Si la colonia existe en el código postal: ✅ "Colonia validada"
   
2. **Sugerencias inteligentes:**
   - Si hay errores ortográficos: muestra colonias similares
   - Ejemplo: "Condeza" → Sugiere "CONDESA"

3. **Información adicional:**
   - Estado
   - Municipio/Alcaldía
   - Todas las colonias válidas en ese CP

### Ejemplo de uso

**Caso 1: Colonia válida**
```
Input: Colonia "CONDESA", CP "06700"
✅ Validación: Colonia validada correctamente
```

**Caso 2: Error ortográfico**
```
Input: Colonia "Condeza", CP "06700"
⚠️ Validación: Colonia no encontrada
💡 Sugerencias:
   - CONDESA
   - CONDESA HIPÓDROMO
```

**Caso 3: Colonia en CP incorrecto**
```
Input: Colonia "POLANCO", CP "06700"
⚠️ Validación: Colonia no existe en este código postal
💡 Colonias válidas en 06700:
   - CONDESA
   - HIPÓDROMO
   - HIPÓDROMO CONDESA
```

### Códigos postales de ejemplo para pruebas

| Código Postal | Alcaldía | Colonias de ejemplo |
|---------------|----------|---------------------|
| 06700 | CUAUHTÉMOC | CONDESA, HIPÓDROMO |
| 11000 | MIGUEL HIDALGO | POLANCO, GRANADA |
| 03100 | BENITO JUÁREZ | DEL VALLE, NÁPOLES |
| 04100 | COYOACÁN | DEL CARMEN, VILLA COYOACÁN |

---

## Preguntas Frecuentes

### ¿Puedo deshacer las correcciones?

**Solo en modo "Solo reportar":** No se aplican cambios, solo se muestra el reporte.

**En modo "Aplicar correcciones":** Los cambios se guardan en la base de datos. Se recomienda hacer una copia de seguridad antes de correcciones masivas.

### ¿Cuánto tarda una corrección masiva?

Depende del tamaño de la carpeta:
- Carpeta pequeña (1-10 documentos): 1-3 segundos
- Carpeta mediana (10-50 documentos): 3-10 segundos
- Carpeta grande (50+ documentos): 10-30 segundos

### ¿Qué pasa si la API de SEPOMEX no responde?

El sistema funciona normalmente pero sin validación SEPOMEX:
- Se aplican correcciones ortográficas estándar
- No se valida contra el catálogo oficial
- Se muestra un mensaje informativo

### ¿Puedo agregar nuevas palabras al diccionario?

Los diccionarios están en el backend:
- `backend/app/services/legal_autocorrector_service.py`

Un administrador puede agregar nuevas entradas a:
- `self.diccionario_alcaldias`
- `self.diccionario_colonias`
- `self.diccionario_terminos_legales`

### ¿El sistema aprende de las correcciones?

Actualmente no. El sistema usa diccionarios predefinidos. En futuras versiones se podría implementar aprendizaje automático.

### ¿Puedo exportar los reportes?

Los reportes se muestran en pantalla. Puede:
1. Copiar el texto del reporte (Ctrl+C)
2. Guardar la página completa (Ctrl+S)
3. Tomar captura de pantalla (Win+Shift+S)

---

## Soporte

Para reportar errores o solicitar nuevas funciones:
- Contacte al administrador del sistema
- Indique la función que estaba usando
- Proporcione el texto de entrada y el error recibido

---

**Versión del manual:** 1.0  
**Última actualización:** Enero 2025  
**Sistema:** Análisis Jurídico FJ1
