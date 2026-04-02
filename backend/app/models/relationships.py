from sqlalchemy.orm import relationship
from app.models.tomo import Tomo
from app.models.extraccion import (
    ExtraccionTomo, DiligenciaTomo, PersonaMencionada,
    Declaracion, AlertaInactividad
)

# Agregar relaciones de extracción al modelo Tomo
Tomo.extracciones = relationship("ExtraccionTomo", back_populates="tomo", cascade="all, delete-orphan", passive_deletes=True)
Tomo.diligencias = relationship("DiligenciaTomo", back_populates="tomo", cascade="all, delete-orphan", passive_deletes=True)
Tomo.personas = relationship("PersonaMencionada", back_populates="tomo", cascade="all, delete-orphan", passive_deletes=True)
Tomo.declaraciones = relationship("Declaracion", back_populates="tomo", cascade="all, delete-orphan", passive_deletes=True)
Tomo.alertas_inactividad = relationship("AlertaInactividad", back_populates="tomo", cascade="all, delete-orphan", passive_deletes=True)