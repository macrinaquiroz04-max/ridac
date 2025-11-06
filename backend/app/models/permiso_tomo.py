# backend/app/models/permiso_tomo.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class PermisoTomo(Base):
    """Permisos específicos de usuarios sobre tomos individuales"""
    __tablename__ = "permisos_tomo"
    __table_args__ = (
        UniqueConstraint('usuario_id', 'tomo_id', name='uq_usuario_tomo'),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"), index=True)
    puede_ver = Column(Boolean, default=True)  # Ver vista previa del tomo
    puede_buscar = Column(Boolean, default=False)  # Buscar en contenido OCR
    puede_ver_sellos = Column(Boolean, default=False)  # Ver sellos en vista previa
    puede_extraer_texto = Column(Boolean, default=False)  # Extraer texto específico
    busqueda_cronologica = Column(Boolean, default=False)  # Realizar búsqueda cronológica
    fecha_inicio_acceso = Column(DateTime(timezone=True), nullable=True)  # Periodo de acceso
    fecha_fin_acceso = Column(DateTime(timezone=True), nullable=True)  # Periodo de acceso
    puede_exportar = Column(Boolean, default=False)  # Solo para administradores
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    usuario = relationship("Usuario", back_populates="permisos_tomos")
    tomo = relationship("Tomo", back_populates="permisos_tomos")