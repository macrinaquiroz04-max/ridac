# 📊 Cómo Abrir Correctamente los Archivos CSV de Auditoría

## 🎯 Formato Mejorado

El sistema ahora exporta archivos CSV optimizados con:
- ✅ **BOM UTF-8**: Reconocimiento automático en Excel
- ✅ **Campos entrecomillados**: Mejor manejo de datos complejos
- ✅ **Headers descriptivos**: Nombres claros en español
- ✅ **User Agent simplificado**: Solo información relevante (Chrome, Firefox, etc.)
- ✅ **Sin saltos de línea**: Descripciones en una sola línea
- ✅ **Valores por defecto**: "-" en lugar de campos vacíos

---

## 📋 Columnas del CSV

| # | Columna | Descripción |
|---|---------|-------------|
| 1 | ID | Identificador único del evento |
| 2 | Fecha y Hora | Timestamp formato YYYY-MM-DD HH:MM:SS |
| 3 | Usuario | Username del usuario |
| 4 | Nombre Completo | Nombre completo del usuario |
| 5 | Acción Realizada | Tipo de acción (LOGIN_EXITOSO, CREAR_CARPETA, etc.) |
| 6 | Tabla Afectada | Tabla de base de datos modificada |
| 7 | ID Registro | ID del registro afectado |
| 8 | Descripción | Descripción legible de la acción |
| 9 | Dirección IP | IP desde donde se realizó la acción |
| 10 | Navegador/Sistema | Navegador simplificado (Chrome, Firefox, etc.) |

---

## 🖥️ Google Sheets (Recomendado)

### Opción 1: Drag & Drop
1. Abrir Google Drive
2. Arrastrar el archivo CSV al navegador
3. Hacer doble clic para abrir
4. ✅ **Se abre perfectamente sin configuración**

### Opción 2: Importar
1. Crear nueva hoja de cálculo
2. Archivo > Importar
3. Seleccionar el CSV
4. Configuración de importación:
   - Tipo de separador: **Detectar automáticamente**
   - Tipo de conversión: **Sí**

**Resultado**: ✅ Perfecto, todos los datos en columnas separadas

---

## 📊 Microsoft Excel

### Excel 2016 o superior (Windows/Mac)

#### Método Recomendado: Abrir Directamente
1. Doble clic en el archivo CSV
2. Excel debería reconocer UTF-8 automáticamente (gracias al BOM)
3. ✅ Los datos se cargan correctamente

#### Si no funciona: Importar Datos
1. Abrir Excel (libro nuevo)
2. **Datos** > **Obtener datos externos** > **Desde texto/CSV**
3. Seleccionar el archivo
4. En el asistente:
   - Origen del archivo: **65001: Unicode (UTF-8)**
   - Delimitador: **Coma**
   - Calificador de texto: **"**
5. Clic en **Cargar**

#### Excel para Mac
1. Abrir Excel
2. Archivo > Importar > Archivo CSV
3. Delimitador: Coma
4. Codificación: UTF-8
5. Importar

---

## 📝 LibreOffice Calc

### Abrir CSV con UTF-8
1. Archivo > Abrir
2. Seleccionar el CSV
3. En el diálogo de importación:
   - **Juego de caracteres**: Unicode (UTF-8)
   - **Separado por**: ☑️ Coma
   - **Separador de texto**: `"`
   - **Opciones de separador**: ☑️ Combinar delimitadores
4. Clic en **OK**

**Resultado**: ✅ Perfecto con acentos y caracteres especiales

---

## 🐍 Python (Análisis)

### pandas - Recomendado

```python
import pandas as pd

# Leer CSV
df = pd.read_csv('auditoria_export_20251114_075608.csv', encoding='utf-8-sig')

# Ver primeras filas
print(df.head())

# Información del DataFrame
print(df.info())

# Estadísticas por acción
print(df['Acción Realizada'].value_counts())

# Filtrar por usuario
eduardo_logs = df[df['Usuario'] == 'eduardo']
print(f"Total de acciones de eduardo: {len(eduardo_logs)}")

# Exportar a Excel con formato
df.to_excel('auditoria_analisis.xlsx', index=False)

# Gráficos
import matplotlib.pyplot as plt

df['Acción Realizada'].value_counts().plot(kind='bar')
plt.title('Distribución de Acciones de Auditoría')
plt.xlabel('Acción')
plt.ylabel('Cantidad')
plt.tight_layout()
plt.savefig('acciones_auditoria.png')
```

### CSV estándar

```python
import csv

with open('auditoria_export_20251114_075608.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f"{row['Fecha y Hora']} - {row['Usuario']}: {row['Acción Realizada']}")
```

---

## 📊 R (Análisis Estadístico)

```r
library(readr)
library(dplyr)
library(ggplot2)

# Leer CSV
auditoria <- read_csv('auditoria_export_20251114_075608.csv', 
                      locale = locale(encoding = "UTF-8"))

# Ver estructura
str(auditoria)

# Resumen por acción
summary_acciones <- auditoria %>%
  group_by(`Acción Realizada`) %>%
  summarise(
    total = n(),
    usuarios_unicos = n_distinct(Usuario)
  ) %>%
  arrange(desc(total))

print(summary_acciones)

# Gráfico de acciones
ggplot(summary_acciones, aes(x = reorder(`Acción Realizada`, total), y = total)) +
  geom_bar(stat = "identity", fill = "steelblue") +
  coord_flip() +
  labs(title = "Distribución de Acciones de Auditoría",
       x = "Acción",
       y = "Cantidad") +
  theme_minimal()

ggsave("acciones_auditoria.png", width = 10, height = 6)
```

---

## 🔍 Solución de Problemas Comunes

### ❌ Problema: "Caracteres raros" o símbolos extraños

**Causa**: Codificación incorrecta (no UTF-8)

**Solución**:
- **Excel**: Usar "Datos > Desde texto" y seleccionar UTF-8
- **LibreOffice**: Abrir con "Juego de caracteres: Unicode (UTF-8)"
- **Bloc de notas**: Guardar como > Codificación: UTF-8

### ❌ Problema: Todo en una sola columna

**Causa**: Delimitador incorrecto

**Solución**:
- Verificar que el delimitador sea **coma (,)**
- En Excel: Datos > Texto en columnas > Delimitado > Coma
- En LibreOffice: Editar > Texto en columnas

### ❌ Problema: Datos JSON/diccionarios se ven mal

**Causa**: Los valores anteriores/nuevos están en el formato viejo

**Solución**:
- La versión nueva del exportador ya no incluye estos campos
- Si necesitas estos datos, usar el script Python o consulta SQL directa

---

## 📌 Mejores Prácticas

### Para Análisis Rápido
✅ **Usar Google Sheets**: Reconocimiento perfecto, sin configuración

### Para Análisis Avanzado
✅ **Usar Python/pandas**: Potente para filtrado y análisis estadístico

### Para Reportes
✅ **Importar a Excel**: Aplicar formato, crear tablas dinámicas

### Para Respaldo
✅ **Guardar como está**: El CSV es texto plano, fácil de respaldar

---

## 🎨 Tips de Formato en Excel/Sheets

### Formato Condicional por Acción

**En Excel/Sheets:**
1. Seleccionar columna "Acción Realizada"
2. Formato condicional > Nueva regla
3. Aplicar colores por tipo:
   - 🟢 `LOGIN_EXITOSO` → Verde
   - 🔴 `LOGIN_FALLIDO` → Rojo
   - 🔵 `CREAR_*` → Azul
   - 🟡 `MODIFICAR_*` → Amarillo
   - 🟠 `ELIMINAR_*` → Naranja

### Filtros Automáticos
1. Seleccionar fila de encabezados
2. Datos > Crear filtro
3. Usar flechitas para filtrar por:
   - Usuario específico
   - Rango de fechas
   - Tipo de acción

### Congelar Encabezados
1. Seleccionar fila 2
2. Ver > Congelar filas > 1 fila
3. Ahora puedes hacer scroll y ver siempre los headers

---

## 📊 Plantilla de Análisis Excel

```
Hoja 1: Datos Brutos (CSV importado)
Hoja 2: Resumen por Usuario (Tabla Dinámica)
Hoja 3: Resumen por Acción (Tabla Dinámica)
Hoja 4: Timeline de Eventos (Gráfico)
Hoja 5: IPs Más Activas (Top 10)
```

---

## 🚀 Automatización

### Script Bash - Convertir a Excel

```bash
#!/bin/bash
# Convertir CSV a Excel usando LibreOffice en servidor

INPUT_CSV="auditoria_export_20251114_075608.csv"
OUTPUT_XLSX="auditoria_analisis.xlsx"

libreoffice --headless --convert-to xlsx:"Calc MS Excel 2007 XML" \
  --infilter="csv:44,34,76" \
  "$INPUT_CSV"

echo "✅ Convertido a $OUTPUT_XLSX"
```

### Python - Conversión Automática

```python
import pandas as pd

# Leer CSV
df = pd.read_csv('auditoria_export_20251114_075608.csv', encoding='utf-8-sig')

# Crear Excel con formato
with pd.ExcelWriter('auditoria_formateada.xlsx', engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='Auditoría', index=False)
    
    # Obtener workbook y worksheet
    workbook = writer.book
    worksheet = writer.sheets['Auditoría']
    
    # Formato de encabezados
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#1a365d',
        'font_color': 'white',
        'border': 1
    })
    
    # Aplicar formato
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(col_num, col_num, 20)  # Ancho automático

print("✅ Excel formateado creado")
```

---

## 📞 Soporte

Si tienes problemas para abrir el CSV:
1. Verificar que el archivo no esté corrupto
2. Intentar con Google Sheets primero (más compatible)
3. Usar el script de Python para conversión
4. Consultar logs del backend si hay errores en la exportación

---

**Sistema OCR FGJCDMX**  
**Desarrollado por**: Eduardo Lozada Quiroz, ISC  
**Organización**: UAyC  
**Año**: 2025
