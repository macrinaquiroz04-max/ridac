# backend/app/models/tomo.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class Tomo(Base):
    __tablename__ = "tomos"
    __table_args__ = (
        UniqueConstraint('carpeta_id', 'numero_tomo', name='uq_carpeta_tomo'),
    )

    id = Column(Integer, primary_key=True, index=True)
    carpeta_id = Column(Integer, ForeignKey("carpetas.id", ondelete="CASCADE"), index=True)
    numero_tomo = Column(Integer, nullable=False)
    nombre_archivo = Column(String(255), nullable=False)
    ruta_archivo = Column(Text, nullable=False)
    tamanio_bytes = Column(Integer)
    numero_paginas = Column(Integer)
    hash_sha256 = Column(String(64), index=True)  # Hash del archivo para verificar integridad
    estado = Column(String(50), default='pendiente', index=True)  # pendiente, procesando, completado, error
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now())
    fecha_procesamiento = Column(DateTime(timezone=True))
    usuario_subida_id = Column(Integer, ForeignKey("usuarios.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    carpeta = relationship("Carpeta", back_populates="tomos")
    usuario_subida = relationship("Usuario", back_populates="tomos_subidos")
    contenido_ocr = relationship("ContenidoOCR", back_populates="tomo", cascade="all, delete-orphan")
    tareas_ocr = relationship("TareaOCR", back_populates="tomo", cascade="all, delete-orphan")
    permisos_tomos = relationship("PermisoTomo", back_populates="tomo", cascade="all, delete-orphan", passive_deletes=True)
    documentos_ocr = relationship("DocumentoOCR", back_populates="tomo", cascade="all, delete-orphan", passive_deletes=True)
    # analisis_ia = relationship("AnalisisIA", back_populates="tomo", cascade="all, delete-orphan")  # Comentado temporalmente
    
    # Relaciones con análisis jurídico - COMENTADAS TEMPORALMENTE PARA EVITAR ERROR DE CONFIGURACIÓN
    # diligencias = relationship("Diligencia", back_populates="tomo", cascade="all, delete-orphan")
    # personas_identificadas = relationship("PersonaIdentificada", back_populates="tomo", cascade="all, delete-orphan")
    # lugares_identificados = relationship("LugarIdentificado", back_populates="tomo", cascade="all, delete-orphan")
    # fechas_importantes = relationship("FechaImportante", back_populates="tomo", cascade="all, delete-orphan")


class ContenidoOCR(Base):
    __tablename__ = "contenido_ocr"
    __table_args__ = (
        UniqueConstraint('tomo_id', 'numero_pagina', name='uq_tomo_pagina'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"), index=True)
    numero_pagina = Column(Integer, nullable=False)
    texto_extraido = Column(Text)
    confianza = Column(Numeric(5, 2))
    embeddings = Column(JSONB)  # Embeddings vectoriales para búsqueda semántica
    datos_adicionales = Column(JSONB)
    created_at = Column(DateTime(timezone=False), server_default=func.now())
    updated_at = Column(DateTime(timezone=False), server_default=func.now())

    # Relación
    tomo = relationship("Tomo", back_populates="contenido_ocr")

    # Relaciones
    tomo = relationship("Tomo", back_populates="contenido_ocr")
