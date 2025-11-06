# ✍️ AUTOCORRECTOR LEGAL - Sistema OCR FGJCDMX

## 📋 Resumen Ejecutivo

El **Autocorrector Legal** es un sistema inteligente que corrige automáticamente errores comunes del OCR en documentos jurídicos, específicamente:

1. **Alcaldías de CDMX** (16 alcaldías)
2. **Colonias** (principales colonias de la ciudad)
3. **Términos legales** (ministerio público, averiguación previa, etc.)
4. **Direcciones** (calles, números, nomenclatura)
5. **Detección de duplicados** (entrevistas, declaraciones repetidas)

---

## 🎯 Problemas que Resuelve

### **Problema 1: Errores de OCR en Alcaldías**

**Antes:**
```
❌ Alcaldia Cuauhtemoc
❌ Cuauthemoc
❌ Cuautemock
```

**Después:**
```
✅ CUAUHTÉMOC
```

### **Problema 2: Errores en Colonias**

**Antes:**
```
❌ Cplonia Hina Condesa
❌ Condes
❌ Sta. Maria la Ribera
```

**Después:**
```
✅ CONDESA
✅ SANTA MARÍA LA RIBERA
```

### **Problema 3: Errores en Términos Legales**

**Antes:**
```
❌ Constithcion Politica
❌ Min Publico
❌ Compareciencia
```

**Después:**
```
✅ CONSTITUCIÓN POLÍTICA
✅ MINISTERIO PÚBLICO
✅ COMPARECENCIA
```

### **Problema 4: Direcciones Mal Formateadas**

**Antes:**
```
❌ CALLE GSABRIEL HERNANDEZ PRIMER PISO
❌ CALLE ISAAC OCHOTERENA SIN NUNMERO ENTRE .
❌ calzada de la viga numero 1174
```

**Después:**
```
✅ CALLE GABRIEL HERNANDEZ PRIMER PISO
✅ CALLE ISAAC OCHOTERENA SIN NÚMERO
✅ CALZADA DE LA VIGA NÚMERO 1174
```

### **Problema 5: Duplicados**

**Antes:**
```
❌ Entrevista - MIGUEL SOLARES (repetida 3 veces)
❌ Declaración - Ministerio Público (repetida 3 veces)
❌ Comparecencia (repetida 5 veces)
```

**Después:**
```
✅ Entrevista - MIGUEL SOLARES (única)
✅ Declaración - Ministerio Público (única)
✅ Comparecencia (única)
```

---

## 🔧 Endpoints Disponibles

### **1. Corregir Texto Simple**

```http
POST /api/autocorrector/corregir-texto
```

**Request:**
```json
{
  "texto": "Alcaldia Cuauhtemoc",
  "tipo_correccion": "alcaldia"
}
```

**Response:**
```json
{
  "texto_original": "Alcaldia Cuauhtemoc",
  "texto_corregido": "CUAUHTÉMOC",
  "fue_corregido": true,
  "correcciones": [
    {"tipo": "alcaldia"}
  ],
  "total_correcciones": 1
}
```

**Tipos de corrección disponibles:**
- `"alcaldia"` - Solo alcaldías
- `"colonia"` - Solo colonias
- `"termino_legal"` - Solo términos legales
- `"completo"` - Todos los tipos (default)

---

### **2. Corregir Dirección Completa**

```http
POST /api/autocorrector/corregir-direccion
```

**Request:**
```json
{
  "direccion": "CALLE GSABRIEL HERNANDEZ SIN NUNMERO",
  "colonia": "Cplonia Hina Condesa",
  "alcaldia": "Cuauthemoc"
}
```

**Response:**
```json
{
  "direccion": {
    "original": "CALLE GSABRIEL HERNANDEZ SIN NUNMERO",
    "corregida": "CALLE GABRIEL HERNANDEZ SIN NÚMERO",
    "fue_corregida": true,
    "detalles": {
      "correcciones": ["'gsabriel' → 'gabriel'", "'nunmero' → 'número'"]
    }
  },
  "colonia": {
    "original": "Cplonia Hina Condesa",
    "corregida": "CONDESA",
    "fue_corregida": true
  },
  "alcaldia": {
    "original": "Cuauthemoc",
    "corregida": "CUAUHTÉMOC",
    "fue_corregida": true
  }
}
```

---

### **3. Detectar Duplicados**

```http
POST /api/autocorrector/detectar-duplicados
```

**Request:**
```json
{
  "carpeta_id": 1,
  "tipo_entidad": "diligencias",
  "umbral_similitud": 0.9
}
```

**Response:**
```json
{
  "carpeta_id": 1,
  "tipo_entidad": "diligencias",
  "total_registros": 50,
  "total_duplicados_encontrados": 9,
  "grupos_duplicados": [
    {
      "ids": [1, 2, 3],
      "cantidad": 3,
      "detalles": [
        {
          "id": 1,
          "tipo": "Entrevista",
          "fecha": "2024-01-15",
          "responsable": "MIGUEL SOLARES"
        },
        {
          "id": 2,
          "tipo": "Entrevista",
          "fecha": "2024-01-15",
          "responsable": "MIGUEL SOLARES"
        },
        {
          "id": 3,
          "tipo": "Entrevista",
          "fecha": "2024-01-15",
          "responsable": "MIGUEL SOLARES"
        }
      ]
    }
  ]
}
```

**Tipos de entidad:**
- `"diligencias"` - Entrevistas, declaraciones, comparecencias, etc.
- `"personas"` - Personas identificadas
- `"lugares"` - Lugares mencionados

---

### **4. Corregir Carpeta Completa** 🔒 (Solo Admin)

```http
POST /api/autocorrector/corregir-carpeta
```

**Request:**
```json
{
  "carpeta_id": 1,
  "auto_corregir": false,
  "eliminar_duplicados": false
}
```

**Parámetros:**
- `auto_corregir: false` → Solo reporta correcciones, NO las aplica
- `auto_corregir: true` → Aplica las correcciones en la base de datos
- `eliminar_duplicados: true` → Elimina registros duplicados (mantiene el primero)

**Response:**
```json
{
  "carpeta_id": 1,
  "correcciones": [
    {
      "entidad": "diligencia",
      "id": 5,
      "campo": "tipo_diligencia",
      "original": "Compareciencia",
      "corregido": "COMPARECENCIA"
    },
    {
      "entidad": "persona",
      "id": 12,
      "campo": "colonia",
      "original": "Cplonia Condesa",
      "corregido": "CONDESA"
    },
    {
      "entidad": "lugar",
      "id": 8,
      "campo": "municipio",
      "original": "Cuauthemoc",
      "corregido": "CUAUHTÉMOC"
    }
  ],
  "duplicados_eliminados": [
    {
      "entidad": "diligencia",
      "id_eliminado": 2,
      "id_conservado": 1
    },
    {
      "entidad": "diligencia",
      "id_eliminado": 3,
      "id_conservado": 1
    }
  ],
  "total_correcciones": 3,
  "total_duplicados_eliminados": 2,
  "auto_corregir": false,
  "mensaje": "Correcciones detectadas (no aplicadas)"
}
```

---

## 📚 Diccionarios Incluidos

### **16 Alcaldías de CDMX**

1. ÁLVARO OBREGÓN
2. AZCAPOTZALCO
3. BENITO JUÁREZ
4. COYOACÁN
5. CUAJIMALPA
6. CUAUHTÉMOC
7. GUSTAVO A. MADERO
8. IZTACALCO
9. IZTAPALAPA
10. MAGDALENA CONTRERAS
11. MIGUEL HIDALGO
12. MILPA ALTA
13. TLÁHUAC
14. TLALPAN
15. VENUSTIANO CARRANZA
16. XOCHIMILCO

### **Colonias Principales**

- CONDESA
- ROMA
- POLANCO
- SANTA MARÍA LA RIBERA
- DEL VALLE
- NARVARTE
- DOCTORES
- GUERRERO
- CENTRO
- JUÁREZ
- *(Se pueden agregar más fácilmente)*

### **Términos Legales**

- MINISTERIO PÚBLICO
- AVERIGUACIÓN PREVIA
- CARPETA DE INVESTIGACIÓN
- CONSTITUCIÓN POLÍTICA
- CÓDIGO PENAL
- CÓDIGO PROCESAL PENAL
- DECLARACIÓN
- COMPARECENCIA
- ENTREVISTA
- ACUERDO
- OFICIO
- FISCALÍA
- PROCURADURÍA
- CIUDAD DE MÉXICO

### **Errores OCR Comunes**

| Error OCR | Corrección |
|-----------|-----------|
| `cplonia` | `colonia` |
| `hina` | *(eliminado - ruido)* |
| `constithcion` | `constitución` |
| `ciudadanop` | `ciudadano` |
| `alcaldia` | `alcaldía` |
| `nunmero` / `sunmero` | `número` |
| `gsabriel` | `gabriel` |
| `sin nunmero` | `sin número` |

---

## 💡 Casos de Uso

### **Caso 1: Usuario Normal - Revisar Texto al Copiar**

1. Usuario selecciona texto del documento OCR
2. Click en botón "Revisar Ortografía Legal"
3. Sistema muestra correcciones sugeridas
4. Usuario acepta/rechaza cada corrección

### **Caso 2: Administrador - Corregir Carpeta Completa**

1. Admin entra al análisis jurídico de una carpeta
2. Click en "Corregir Errores OCR"
3. Sistema muestra reporte de correcciones detectadas
4. Admin revisa y confirma
5. Sistema aplica todas las correcciones

### **Caso 3: Procesamiento Automático al hacer OCR**

1. Se procesa un nuevo documento con OCR
2. Al guardar diligencias/personas/lugares:
   - Sistema autocorrige alcaldías
   - Sistema autocorrige colonias
   - Sistema normaliza términos legales
3. Datos se guardan ya corregidos

---

## 🔍 Algoritmo de Detección

### **Similitud de Texto (Levenshtein)**

```python
similitud("Cuauthemoc", "CUAUHTÉMOC") = 0.91  # ✅ Match
similitud("Cplonia Condesa", "CONDESA") = 0.76  # ✅ Match
similitud("Compareciencia", "COMPARECENCIA") = 0.93  # ✅ Match
```

**Umbrales:**
- Alcaldías: >= 0.80
- Colonias: >= 0.75
- Términos legales: >= 0.80
- Duplicados: >= 0.90 (configurable)

---

## 🚀 Integración Frontend

### **Ejemplo: Botón de Corrección**

```html
<button onclick="corregirTexto()">
  ✍️ Revisar Ortografía Legal
</button>

<script>
async function corregirTexto() {
  const texto = document.getElementById('texto-extraido').value;
  
  const response = await fetch('/api/autocorrector/corregir-texto', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      texto: texto,
      tipo_correccion: 'completo'
    })
  });
  
  const resultado = await response.json();
  
  if (resultado.fue_corregido) {
    // Mostrar correcciones al usuario
    mostrarCorrecciones(resultado.correcciones);
    
    // Opcionalmente aplicar automáticamente
    document.getElementById('texto-extraido').value = resultado.texto_corregido;
  } else {
    alert('✅ No se encontraron errores');
  }
}
</script>
```

---

## 📊 Estadísticas y Reportes

### **Reporte de Correcciones**

```json
{
  "carpeta_id": 1,
  "fecha_analisis": "2025-10-12T15:30:00",
  "estadisticas": {
    "total_diligencias": 50,
    "diligencias_corregidas": 12,
    "total_personas": 30,
    "personas_corregidas": 8,
    "total_lugares": 20,
    "lugares_corregidos": 15,
    "duplicados_encontrados": 9,
    "duplicados_eliminados": 9
  },
  "tipos_correcciones": {
    "alcaldias": 15,
    "colonias": 8,
    "terminos_legales": 12,
    "direcciones": 20,
    "errores_ocr": 35
  }
}
```

---

## 🔐 Permisos

| Endpoint | Roles Permitidos |
|----------|-----------------|
| `/corregir-texto` | Todos los usuarios autenticados |
| `/corregir-direccion` | Todos los usuarios autenticados |
| `/detectar-duplicados` | Todos los usuarios autenticados |
| `/corregir-carpeta` | **Solo Admin** |

---

## 🎯 Próximas Mejoras

### **Fase 2: API SEPOMEX** (Opcional)

```python
async def validar_colonia_sepomex(colonia: str, cp: str) -> bool:
    """
    Validar que la colonia existe en el catálogo SEPOMEX
    """
    url = f"https://api.copomex.com/query/get_colonia_por_cp/{cp}"
    response = await http_client.get(url)
    colonias_validas = response.json()
    return colonia in colonias_validas
```

### **Fase 3: Machine Learning**

- Aprender de correcciones manuales
- Mejorar precisión con el tiempo
- Detectar patrones específicos del OCR usado

### **Fase 4: Sugerencias Contextuales**

```
Usuario escribe: "Alcaldia Cuaute"
Sistema sugiere: "¿Quisiste decir CUAUHTÉMOC?"
```

---

## 📝 Logs y Auditoría

Todas las correcciones quedan registradas:

```python
{
  "timestamp": "2025-10-12T15:30:00",
  "usuario_id": 5,
  "accion": "correccion_automatica",
  "carpeta_id": 1,
  "entidad": "diligencia",
  "entidad_id": 12,
  "campo": "tipo_diligencia",
  "valor_anterior": "Compareciencia",
  "valor_nuevo": "COMPARECENCIA",
  "confianza": 0.93
}
```

---

## ✅ Checklist de Implementación

- [x] Servicio de corrección (`legal_autocorrector_service.py`)
- [x] Controlador con endpoints (`autocorrector_controller.py`)
- [x] Integración en `main.py`
- [x] Diccionarios de alcaldías (16)
- [x] Diccionarios de colonias (10 principales)
- [x] Diccionarios de términos legales (14)
- [x] Detección de duplicados
- [x] **Frontend** - Botón "Revisar Ortografía" ✅
- [x] **Frontend** - Panel de correcciones sugeridas ✅
- [x] **Frontend** - Reporte de correcciones masivas ✅
- [x] **Integración con SEPOMEX** ✅ **CATÁLOGO OFICIAL COMPLETO - PostgreSQL**
  - [x] Validación de códigos postales ✅
  - [x] Validación de colonias ✅
  - [x] Sugerencias de colonias similares (fuzzy search) ✅
  - [x] **1,110 códigos postales** de CDMX ✅
  - [x] **1,381 colonias únicas** (76% catálogo oficial) ✅
  - [x] **16 alcaldías completas** ✅
  - [x] **PostgreSQL con pg_trgm** (búsqueda fuzzy activada) ✅
  - [x] **Autocorrección automática de errores OCR** ✅
  - [x] **Autocompletado inteligente** ✅
  - [x] **6 tipos de asentamiento** (Colonia, Barrio, Pueblo, etc.) ✅
  - [x] Tasa de éxito: 100% en pruebas ✅
  - [ ] API externa opcional (requiere token de copomex.com)
- [x] **Tests realizados** ✅
  - [x] Test básico (6 pruebas, 100% éxito)
  - [x] Test ampliado (14 CPs, 100% validación)
  - [ ] Tests unitarios automáticos (pendiente)
- [x] **Documentación completa** ✅
  - [x] Manual de usuario
  - [x] Guía de configuración SEPOMEX
  - [x] Estado de implementación
  - [x] Scripts de prueba

---

## 🚀 ¿Cómo Empezar?

### **1. Probar en Swagger**

```
http://localhost:8000/docs#/✍️%20Autocorrector%20Legal
```

### **2. Ejemplo Rápido**

```bash
curl -X POST "http://localhost:8000/api/autocorrector/corregir-texto" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "texto": "Alcaldia Cuauthemoc, Cplonia Condesa",
    "tipo_correccion": "completo"
  }'
```

### **3. Corregir Carpeta de Prueba**

```bash
curl -X POST "http://localhost:8000/api/autocorrector/corregir-carpeta" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "carpeta_id": 1,
    "auto_corregir": false,
    "eliminar_duplicados": false
  }'
```

---

## 📞 Soporte

**Documentación:**
- Este archivo: `AUTOCORRECTOR_LEGAL.md`
- Código fuente: `backend/app/services/legal_autocorrector_service.py`
- Controlador: `backend/app/controllers/autocorrector_controller.py`

**API Docs:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

*Sistema Autocorrector Legal - FGJCDMX*  
*Versión 1.0 - 12 de octubre de 2025*
