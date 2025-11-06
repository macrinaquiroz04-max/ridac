"""
Rutas para análisis jurídico - Admin
"""

from fastapi import APIRouter
from app.controllers import analisis_admin_controller

router = APIRouter()

# Incluir rutas del controlador
router.include_router(
    analisis_admin_controller.router,
    tags=["Análisis Jurídico - Admin"]
)
