# Dockerfile - Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Cliente: Unidad de Análisis y Contexto (UAyC)
# Año: 2025 - Propiedad Intelectual Protegida
# Contacto: aduardolozada1958@gmail.com

FROM python:3.11-slim

# Establecer zona horaria
ENV TZ=America/Mexico_City
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    gcc \
    g++ \
    curl \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Crear directorios necesarios
RUN mkdir -p /FGJCDMX/documentos \
    /FGJCDMX/exportaciones \
    /FGJCDMX/temp \
    /FGJCDMX/logs \
    /app/uploads

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt requirements.txt

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear usuario no-root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /FGJCDMX

# Cambiar a usuario no-root
USER appuser

# Exponer puertos
EXPOSE 8000 8443

# Script de inicio
COPY docker-entrypoint.sh /docker-entrypoint.sh
USER root
RUN chmod +x /docker-entrypoint.sh
USER appuser

# Comando de inicio
ENTRYPOINT ["/docker-entrypoint.sh"]
