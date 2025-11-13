# backend/app/models/auditoria.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base

class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        Index('idx_auditoria_usuario_fecha', 'usuario_id', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    accion = Column(String(100), nullable=False)
    tabla_afectada = Column(String(50))  # Nombre real de la columna en la DB
    registro_id = Column(Integer)        # Nombre real de la columna en la DB
    descripcion = Column(Text)           # Descripción legible de la acción
    valores_anteriores = Column(JSONB)   # Valores antes del cambio
    valores_nuevos = Column(JSONB)       # Valores después del cambio
    ip_address = Column(String(50))      # Dirección IP
    user_agent = Column(Text)            # User agent del navegador
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relaciones
    usuario = relationship("Usuario", back_populates="auditorias")

