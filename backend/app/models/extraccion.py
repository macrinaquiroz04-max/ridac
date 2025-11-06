from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class ExtraccionTomo(Base):
    """Almacena información estructurada extraída de los tomos"""
    __tablename__ = "extracciones_tomo"

    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"), index=True)
    pagina = Column(Integer)
    tipo_extraccion = Column(String(50))  # diligencia, fecha, lugar, persona, etc.
    contenido = Column(JSONB)  # Almacena la información estructurada
    fecha_documento = Column(DateTime(timezone=True))
    fecha_extraccion = Column(DateTime(timezone=True), server_default='now()')
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')

    # Relaciones
    tomo = relationship("Tomo", back_populates="extracciones")

class DiligenciaTomo(Base):
    """Almacena información específica de diligencias"""
    __tablename__ = "diligencias_tomo"

    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"), index=True)
    pagina = Column(Integer)
    tipo_diligencia = Column(String(100))  # informe pericial, comparecencia, etc.
    fecha = Column(DateTime(timezone=True))
    responsable = Column(String(200))
    numero_oficio = Column(String(100), nullable=True)
    contenido = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')

    # Relaciones
    tomo = relationship("Tomo", back_populates="diligencias")

class PersonaMencionada(Base):
    """Almacena información sobre personas mencionadas en los tomos"""
    __tablename__ = "personas_mencionadas"

    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"), index=True)
    nombre = Column(String(200))
    tipo = Column(String(50))  # testigo, perito, MP, etc.
    direccion = Column(Text, nullable=True)
    telefono = Column(String(50), nullable=True)
    lat = Column(Float, nullable=True)  # Para geolocalización
    lon = Column(Float, nullable=True)  # Para geolocalización
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')

    # Relaciones
    tomo = relationship("Tomo", back_populates="personas")
    declaraciones = relationship("Declaracion", back_populates="persona")

class Declaracion(Base):
    """Almacena información sobre declaraciones de personas"""
    __tablename__ = "declaraciones"

    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("personas_mencionadas.id", ondelete="CASCADE"))
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"))
    fecha = Column(DateTime(timezone=True))
    tipo = Column(String(50))  # inicial, ampliación, etc.
    contenido = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')

    # Relaciones
    persona = relationship("PersonaMencionada", back_populates="declaraciones")
    tomo = relationship("Tomo", back_populates="declaraciones")

class AlertaInactividad(Base):
    """Almacena alertas por inactividad en las carpetas"""
    __tablename__ = "alertas_inactividad"

    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"))
    ultima_diligencia = Column(DateTime(timezone=True))
    dias_inactividad = Column(Integer)
    estado = Column(String(20))  # activa, resuelta, etc.
    created_at = Column(DateTime(timezone=True), server_default='now()')
    updated_at = Column(DateTime(timezone=True), server_default='now()', onupdate='now()')

    # Relaciones
    tomo = relationship("Tomo", back_populates="alertas_inactividad")