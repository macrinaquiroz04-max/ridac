# ============================================================
# Dockerfile raíz — HuggingFace Spaces (Docker SDK)
# Redirige el build al subdirectorio backend/
# Puerto obligatorio HF Spaces: 7860
# ============================================================

FROM python:3.11-slim

LABEL maintainer="RIDAC"
LABEL description="Sistema OCR RIDAC - Backend FastAPI"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860

# ── Sistema: Tesseract + poppler + libGL (opencv) ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    libglib2.0-0 \
    libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependencias Python (capa cacheada) ──
COPY backend/requirements-production.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-production.txt && \
    pip install --no-cache-dir \
        https://github.com/explosion/spacy-models/releases/download/es_core_news_lg-3.7.0/es_core_news_lg-3.7.0-py3-none-any.whl \
        https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.7.0/es_core_news_sm-3.7.0-py3-none-any.whl

# ── Código fuente del backend ──
COPY backend/ .

# ── Directorios en /tmp (escritura sin permisos root en HF) ──
RUN mkdir -p /tmp/ridac/documentos \
             /tmp/ridac/exportaciones \
             /tmp/ridac/temp \
             /tmp/ridac/logs \
             /tmp/ridac/uploads

# ── Usuario no-root (uid 1000 requerido por HF Spaces) ──
RUN useradd -m -u 1000 ridac && chown -R ridac:ridac /app /tmp/ridac
USER ridac

EXPOSE 7860

CMD ["bash", "start.sh"]
