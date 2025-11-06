# backend/app/models/tarea_ocr.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class TareaOCR(Base):
    """Tabla para cola de tareas OCR (reemplaza Celery/Redis)"""
    __tablename__ = "tareas_ocr"
    __table_args__ = (
        Index('idx_tareas_estado_prioridad', 'estado', 'prioridad'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"))
    estado = Column(String(50), default='pendiente', index=True)  # pendiente, procesando, completado, error
    pagina_actual = Column(Integer, default=1)
    total_paginas = Column(Integer)
    tiempo_inicio = Column(DateTime(timezone=False))
    tiempo_fin = Column(DateTime(timezone=False))
    error_mensaje = Column(Text)
    progreso_porcentaje = Column(Integer, default=0)
    prioridad = Column(Integer, default=1)
    reintentos = Column(Integer, default=0)
    maximo_reintentos = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now())

    # Relaciones
    tomo = relationship("Tomo", back_populates="tareas_ocr")
