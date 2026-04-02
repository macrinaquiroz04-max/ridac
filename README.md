# RIDAC — Sistema OCR de Análisis Jurídico

Sistema de digitalización, extracción OCR y análisis jurídico de documentos para la
Unidad de Análisis y Contexto (UAyC) — FGJ CDMX.

## Stack

- **Frontend**: Vue 3 + Vite + Pinia
- **Backend**: FastAPI (Python)
- **Base de datos**: PostgreSQL 15 + pgvector + pg_trgm
- **Cola de tareas**: Celery + Redis
- **OCR**: Tesseract · EasyOCR · PaddleOCR (opcional)

## Documentación

Ver carpeta [`documentacion/`](./documentacion/)

- [Instalación](./documentacion/INSTALACION.md)
- [Arquitectura](./documentacion/ARQUITECTURA.md)
- [Guía de uso](./documentacion/GUIA_USO.md)

## Inicio rápido

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend-vue && npm install && npm run dev
```

---

*Desarrollado por Eduardo Lozada Quiroz, ISC — UAyC · FGJ CDMX*
