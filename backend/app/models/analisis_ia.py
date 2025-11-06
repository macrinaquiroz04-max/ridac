from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from app.database import Base

class AnalisisIA(Base):
    __tablename__ = "analisis_ia"

    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha_analisis = Column(DateTime, default=datetime.utcnow, nullable=False)
    resultados_json = Column(Text, nullable=False)  # JSON con todos los resultados
    estado = Column(String(50), default="pendiente")  # pendiente, procesando, completado, error
    tiempo_procesamiento = Column(Integer)  # en segundos
    version_algoritmo = Column(String(20), default="1.0")
    
    # Campos específicos extraídos para consultas rápidas
    total_diligencias = Column(Integer, default=0)
    total_personas = Column(Integer, default=0)
    total_lugares = Column(Integer, default=0)
    total_alertas = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    # tomo = relationship("Tomo", back_populates="analisis_ia")  # Comentado temporalmente
    # usuario = relationship("Usuario", back_populates="analisis_ia")  # Comentado temporalmente
    resultados = relationship("ResultadoAnalisis", back_populates="analisis", cascade="all, delete-orphan")

class ResultadoAnalisis(Base):
    __tablename__ = "resultados_analisis"

    id = Column(Integer, primary_key=True, index=True)
    analisis_id = Column(Integer, ForeignKey("analisis_ia.id"), nullable=False)
    tipo_resultado = Column(String(50), nullable=False)  # diligencia, persona, lugar, alerta
    
    # Campos genéricos que se usan según el tipo
    nombre = Column(String(255))
    descripcion = Column(Text)
    fecha = Column(String(20))
    datos_json = Column(Text)  # JSON con datos específicos del tipo
    
    # Campos específicos por tipo
    # Para diligencias
    tipo_diligencia = Column(String(100))
    responsable = Column(String(255))
    oficio = Column(String(100))
    
    # Para personas
    direccion = Column(Text)
    telefono = Column(String(50))
    num_declaraciones = Column(Integer)
    
    # Para lugares
    tipo_lugar = Column(String(100))
    contexto = Column(String(255))
    frecuencia = Column(Integer)
    
    # Para alertas
    prioridad = Column(String(20))  # baja, media, alta
    dias_transcurridos = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    analisis = relationship("AnalisisIA", back_populates="resultados")

class MetricasAnalisis(Base):
    __tablename__ = "metricas_analisis"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # Métricas de uso
    total_analisis_realizados = Column(Integer, default=0)
    tiempo_promedio_analisis = Column(Integer, default=0)  # en segundos
    tomos_analizados = Column(Integer, default=0)
    
    # Métricas de resultados
    diligencias_encontradas = Column(Integer, default=0)
    personas_identificadas = Column(Integer, default=0)
    lugares_detectados = Column(Integer, default=0)
    alertas_generadas = Column(Integer, default=0)
    
    # Métricas de calidad
    precision_estimada = Column(Integer, default=0)  # porcentaje
    casos_verificados = Column(Integer, default=0)
    casos_correctos = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    usuario = relationship("Usuario")

# Índices para optimizar consultas
from sqlalchemy import Index

# Índices para AnalisisIA
Index('idx_analisis_tomo_fecha', AnalisisIA.tomo_id, AnalisisIA.fecha_analisis)
Index('idx_analisis_usuario_fecha', AnalisisIA.usuario_id, AnalisisIA.fecha_analisis)
Index('idx_analisis_estado', AnalisisIA.estado)

# Índices para ResultadoAnalisis
Index('idx_resultado_analisis_tipo', ResultadoAnalisis.analisis_id, ResultadoAnalisis.tipo_resultado)
Index('idx_resultado_tipo', ResultadoAnalisis.tipo_resultado)
Index('idx_resultado_prioridad', ResultadoAnalisis.prioridad)

# Índices para MetricasAnalisis
Index('idx_metricas_usuario_fecha', MetricasAnalisis.usuario_id, MetricasAnalisis.fecha)