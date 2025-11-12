# 🔍 BÚSQUEDA SEMÁNTICA - SISTEMA OCR

## ¿Qué es la búsqueda semántica?

La búsqueda semántica utiliza inteligencia artificial para encontrar documentos relacionados **conceptualmente**, no solo por palabras exactas. Esto significa que puede encontrar documentos relevantes incluso si no contienen las palabras exactas de su búsqueda.

## 🚀 Configuración inicial

### 1. Instalar dependencias

```bash
cd backend
pip install sentence-transformers scikit-learn
```

### 2. Ejecutar migración de base de datos

```bash
python migrations/add_embeddings_column.py
```

### 3. Generar embeddings para documentos existentes

```bash
python scripts/generar_embeddings.py
```

## 📖 Cómo usar la búsqueda semántica

### Interfaz web
- Acceder a: `http://localhost:8000/busqueda-semantica.html`
- Escribir consulta en lenguaje natural
- Ajustar similitud mínima según necesidades
- Los resultados se ordenan por relevancia semántica

### API Endpoints

#### Búsqueda semántica
```http
POST /api/busqueda/semantica
Content-Type: application/json
Authorization: Bearer {token}

{
    "query": "homicidio en la colonia del valle",
    "similitud_minima": 0.5,
    "limit": 50,
    "carpeta_id": 123  // opcional
}
```

#### Actualizar embeddings
```http
POST /api/busqueda/actualizar-embeddings
Authorization: Bearer {token}

{
    "tomo_id": 456  // opcional, si no se especifica actualiza todos
}
```

## 💡 Ejemplos de consultas

### Búsquedas tradicionales vs semánticas

**Búsqueda tradicional:** `"robo de vehiculo"`
- Solo encuentra documentos con esas palabras exactas

**Búsqueda semántica:** `"robo de vehiculo"`
- Encuentra documentos sobre:
  - "hurto de automóvil"
  - "apropiación indebida de vehículo"
  - "sustracción de auto"
  - "delito patrimonial vehicular"

### Ejemplos prácticos

```javascript
// Búsqueda de violencia doméstica
{
    "query": "violencia doméstica",
    "similitud_minima": 0.6
}
// Encuentra: "agresión familiar", "maltrato conyugal", "violencia intrafamiliar"

// Búsqueda de drogas
{
    "query": "narcóticos",
    "similitud_minima": 0.5
}
// Encuentra: "estupefacientes", "sustancias psicotrópicas", "drogas"

// Búsqueda geográfica
{
    "query": "centro de la ciudad",
    "similitud_minima": 0.4
}
// Encuentra: "zócalo", "downtown", "área metropolitana"
```

## ⚙️ Configuración de similitud

- **0.3 - 0.4:** Muy flexible, más resultados pero menos precisos
- **0.5 - 0.6:** Balanceado, buena relación precisión/cobertura
- **0.7 - 0.8:** Estricto, pocos resultados pero muy relevantes
- **0.9+:** Muy estricto, solo documentos casi idénticos

## 🔧 Funcionalidades técnicas

### Modelo de embeddings
- **Modelo:** `paraphrase-multilingual-MiniLM-L12-v2`
- **Idiomas:** Español, inglés y otros idiomas
- **Dimensiones:** 384 dimensiones vectoriales
- **Rendimiento:** Optimizado para velocidad y precisión

### Almacenamiento
- **Base de datos:** PostgreSQL con JSONB
- **Índices:** GIN para búsquedas eficientes
- **Generación:** Automática al procesar nuevos documentos

### Procesamiento automático
Los embeddings se generan automáticamente cuando:
- Se procesa un nuevo documento OCR
- Se ejecuta el procesamiento por lotes
- Se ejecuta manualmente el script de actualización

## 📊 Métricas y análisis

### Estadísticas disponibles
- Total de documentos encontrados
- Puntuación de similitud por resultado
- Tiempo de procesamiento
- Cobertura de embeddings en la base de datos

### Monitoreo
```python
# Verificar estado de embeddings
GET /api/busqueda/estadisticas-embeddings

# Respuesta
{
    "total_documentos": 1500,
    "con_embeddings": 1200,
    "sin_embeddings": 300,
    "cobertura_porcentaje": 80.0
}
```

## 🚨 Troubleshooting

### Error: "sentence-transformers no está instalado"
```bash
pip install sentence-transformers
```

### Error: "No se pudo generar embedding"
- Verificar que el texto no esté vacío
- Verificar memoria disponible
- Reiniciar el servicio si es necesario

### Búsquedas lentas
- Verificar que exista el índice GIN
- Considerar reducir el límite de resultados
- Verificar recursos del servidor

### No se encuentran resultados
- Reducir la similitud mínima
- Verificar que los documentos tengan embeddings
- Probar consultas más generales

## 🔄 Mantenimiento

### Actualización periódica
Ejecutar semanalmente para documentos nuevos:
```bash
python scripts/generar_embeddings.py
```

### Reindexación completa
Para regenerar todos los embeddings:
```sql
UPDATE contenido_ocr SET embeddings = NULL;
```
```bash
python scripts/generar_embeddings.py
```

## 🎯 Mejores prácticas

1. **Consultas efectivas:**
   - Usar frases descriptivas en lugar de palabras sueltas
   - Incluir contexto en las consultas
   - Probar diferentes niveles de similitud

2. **Rendimiento:**
   - Procesar embeddings en horarios de bajo tráfico
   - Monitorear uso de memoria durante generación
   - Configurar límites apropiados por consulta

3. **Precisión:**
   - Ajustar similitud según el caso de uso
   - Combinar con búsqueda tradicional cuando sea necesario
   - Validar resultados con usuarios finales

## 📈 Roadmap futuro

- [ ] Soporte para múltiples modelos de embedding
- [ ] Búsqueda híbrida (semántica + tradicional)
- [ ] Clustering automático de documentos similares
- [ ] Métricas de relevancia por usuario
- [ ] Exportación de resultados semánticos
- [ ] Integración con análisis de sentimientos