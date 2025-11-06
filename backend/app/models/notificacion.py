from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    titulo = Column(String(255), nullable=False)
    mensaje = Column(Text, nullable=False)
    tipo = Column(String(50), default='info')  # info, warning, error, success, TOMO_ELIMINADO, CARPETA_ELIMINADA, etc.
    leida = Column(Boolean, default=False, index=True)
    url_accion = Column(String(500))  # URL para acción relacionada
    datos_extra = Column(JSONB)  # JSON con información adicional (no datos_adicionales)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), index=True)
    leida_at = Column(DateTime(timezone=False))  # Fecha cuando se marcó como leída

    # Relaciones
    # usuario = relationship("Usuario", back_populates="notificaciones")