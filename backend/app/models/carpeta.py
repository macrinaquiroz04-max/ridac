# backend/app/models/carpeta.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Carpeta(Base):
    __tablename__ = "carpetas"

    id = Column(Integer, primary_key=True, index=True)
    numero_expediente = Column(String(100), unique=True, nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    ubicacion_fisica = Column(String(255))
    anio = Column(Integer)
    estado = Column(String(50), default='activo')
    usuario_creador_id = Column(Integer, ForeignKey("usuarios.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relaciones
    creador = relationship("Usuario", back_populates="carpetas_creadas", foreign_keys=[usuario_creador_id])
    tomos = relationship("Tomo", back_populates="carpeta", cascade="all, delete-orphan")
    permisos = relationship("PermisoCarpeta", back_populates="carpeta", cascade="all, delete-orphan")
    
    # Relaciones con análisis jurídico - COMENTADAS TEMPORALMENTE PARA EVITAR ERROR DE CONFIGURACIÓN
    # diligencias = relationship("Diligencia", back_populates="carpeta", cascade="all, delete-orphan")
    # personas_identificadas = relationship("PersonaIdentificada", back_populates="carpeta", cascade="all, delete-orphan")
    # lugares_identificados = relationship("LugarIdentificado", back_populates="carpeta", cascade="all, delete-orphan")
    # fechas_importantes = relationship("FechaImportante", back_populates="carpeta", cascade="all, delete-orphan")
    # alertas_mp = relationship("AlertaMP", back_populates="carpeta", cascade="all, delete-orphan")
    # estadisticas = relationship("EstadisticaCarpeta", back_populates="carpeta", uselist=False, cascade="all, delete-orphan")
