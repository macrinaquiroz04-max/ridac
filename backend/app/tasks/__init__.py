# app/tasks/__init__.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Año: 2025

from .celery_app import celery_app

__all__ = ['celery_app']
