# backend/app/models/direccion.py

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class DireccionCorregida(Base):
    """
    Modelo para almacenar direcciones detectadas y corregidas
    con validación SEPOMEX
    """
    __tablename__ = "direcciones_corregidas"
    
    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey('tomos.id'), nullable=False)
    pagina = Column(Integer, nullable=False)
    linea = Column(Integer, default=0)
    
    # Texto original del OCR
    texto_original = Column(Text, nullable=False)
    
    # Componentes de la dirección corregida
    calle = Column(String(200))
    numero = Column(String(20))
    colonia = Column(String(200))
    codigo_postal = Column(String(5))
    alcaldia = Column(String(100))
    
    # Metadatos de validación
    validada_sepomex = Column(Boolean, default=False)
    editada_manualmente = Column(Boolean, default=False)
    ignorada = Column(Boolean, default=False)
    notas = Column(Text)
    
    # Auditoría
    usuario_revision_id = Column(Integer, ForeignKey('usuarios.id'))
    fecha_revision = Column(DateTime, default=datetime.now)
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_modificacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relaciones
    tomo = relationship("Tomo", back_populates="direcciones_corregidas")
    usuario_revision = relationship("Usuario")
    
    def __repr__(self):
        return f"<DireccionCorregida(id={self.id}, calle='{self.calle}', cp='{self.codigo_postal}')>"
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'tomo_id': self.tomo_id,
            'pagina': self.pagina,
            'linea': self.linea,
            'texto_original': self.texto_original,
            'calle': self.calle,
            'numero': self.numero,
            'colonia': self.colonia,
            'codigo_postal': self.codigo_postal,
            'alcaldia': self.alcaldia,
            'validada_sepomex': self.validada_sepomex,
            'editada_manualmente': self.editada_manualmente,
            'ignorada': self.ignorada,
            'notas': self.notas,
            'usuario_revision_id': self.usuario_revision_id,
            'fecha_revision': self.fecha_revision.isoformat() if self.fecha_revision else None,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
