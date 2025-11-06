"""
Rutas para análisis jurídico - Usuario
"""

from fastapi import APIRouter
from app.controllers import analisis_usuario_controller

router = APIRouter()

# Incluir rutas del controlador
router.include_router(
    analisis_usuario_controller.router,
    tags=["Análisis Jurídico - Usuario"]
)
