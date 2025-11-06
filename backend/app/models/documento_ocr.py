from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class DocumentoOCR(Base):
    __tablename__ = "documentos_ocr"
    
    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    nombre = Column(String(255), nullable=False)
    contenido = Column(Text, nullable=False)
    descripcion = Column(Text, nullable=True)
    tipo = Column(String(50), default="ocr_extract")  # ocr_extract, manual_upload, etc.
    
    # Metadatos
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_modificacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    fecha_eliminacion = Column(DateTime, nullable=True)
    activo = Column(Boolean, default=True)
    
    # Relaciones
    tomo = relationship("Tomo", back_populates="documentos_ocr")
    usuario = relationship("Usuario", back_populates="documentos_ocr")
    
    def __repr__(self):
        return f"<DocumentoOCR(id={self.id}, nombre='{self.nombre}', tomo_id={self.tomo_id})>"