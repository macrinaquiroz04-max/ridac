# backend/app/models/permiso.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class PermisoCarpeta(Base):
    __tablename__ = "permisos_carpeta"
    __table_args__ = (
        UniqueConstraint('usuario_id', 'carpeta_id', name='uq_usuario_carpeta'),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    carpeta_id = Column(Integer, ForeignKey("carpetas.id", ondelete="CASCADE"), index=True)
    puede_leer = Column(Boolean, default=True)
    puede_escribir = Column(Boolean, default=False)
    puede_eliminar = Column(Boolean, default=False)
    puede_compartir = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())

    # Relaciones
    usuario = relationship("Usuario", back_populates="permisos_carpetas")
    carpeta = relationship("Carpeta", back_populates="permisos")

class PermisoSistema(Base):
    __tablename__ = "permisos_sistema"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    gestionar_usuarios = Column(Boolean, default=False)
    gestionar_roles = Column(Boolean, default=False)
    gestionar_carpetas = Column(Boolean, default=False)
    procesar_ocr = Column(Boolean, default=False)
    ver_auditoria = Column(Boolean, default=False)
    configurar_sistema = Column(Boolean, default=False)
    exportar_datos = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relaciones
    usuario = relationship("Usuario", back_populates="permisos_sistema")

    __table_args__ = (
        UniqueConstraint('usuario_id', name='uq_usuario_permisos'),
    )