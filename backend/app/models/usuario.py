# backend/app/models/usuario.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(Text)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())

    # Relaciones
    usuarios = relationship("Usuario", back_populates="rol")

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # Campo password como en la BD
    nombre_completo = Column(String(200))  # nombre_completo como en la BD
    foto_perfil = Column(String(255))  # Ruta de la foto de perfil del usuario
    rol_id = Column(Integer, ForeignKey("roles.id"))
    activo = Column(Boolean, default=True)
    debe_cambiar_password = Column(Boolean, default=False)  # Indica si debe cambiar contraseña
    ultimo_acceso = Column(DateTime(timezone=False))  # Sin timezone como en la BD
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now())

    # Relaciones
    rol = relationship("Rol", back_populates="usuarios")
    permisos_sistema = relationship("PermisoSistema", back_populates="usuario", cascade="all, delete-orphan")
    permisos_carpetas = relationship("PermisoCarpeta", back_populates="usuario", cascade="all, delete-orphan")
    permisos_tomos = relationship("PermisoTomo", back_populates="usuario", cascade="all, delete-orphan")
    carpetas_creadas = relationship("Carpeta", back_populates="creador", foreign_keys="Carpeta.usuario_creador_id")
    tomos_subidos = relationship("Tomo", back_populates="usuario_subida")
    auditorias = relationship("Auditoria", back_populates="usuario")
    tokens_reset = relationship("TokenReset", back_populates="usuario")
    documentos_ocr = relationship("DocumentoOCR", back_populates="usuario")
    # analisis_ia = relationship("AnalisisIA", back_populates="usuario")  # Comentado temporalmente
    # notificaciones = relationship("Notificacion", back_populates="usuario", cascade="all, delete-orphan")
    
    # Propiedad para compatibilidad: permite usar .nombre o .nombre_completo
    @property
    def nombre(self):
        """Alias de nombre_completo para compatibilidad con código admin"""
        return self.nombre_completo
    
    @nombre.setter
    def nombre(self, value):
        """Permite asignar a .nombre y guarda en nombre_completo"""
        self.nombre_completo = value

class TokenReset(Base):
    __tablename__ = "tokens_reset"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    token = Column(String(255), unique=True, nullable=False)
    expiracion = Column(DateTime(timezone=True), nullable=False)
    usado = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    usuario = relationship("Usuario", back_populates="tokens_reset")
