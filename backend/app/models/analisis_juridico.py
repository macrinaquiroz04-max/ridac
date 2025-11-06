"""
Modelos para análisis jurídico de documentos OCR
Extracción de diligencias, personas, lugares, fechas y alertas
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Date, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base


class Diligencia(Base):
    """Diligencias extraídas de documentos"""
    __tablename__ = "diligencias"
    
    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"), nullable=False, index=True)
    carpeta_id = Column(Integer, ForeignKey("carpetas.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Información de la diligencia
    tipo_diligencia = Column(String(200), nullable=False, index=True)  # informe pericial, comparecencia, etc.
    fecha_diligencia = Column(Date, nullable=True, index=True)
    fecha_diligencia_texto = Column(String(100))  # Fecha tal como aparece en el texto
    responsable = Column(String(300))  # Nombre de quien realiza la diligencia
    numero_oficio = Column(String(100), index=True)  # Número de oficio si existe
    
    # Contexto
    descripcion = Column(Text)  # Descripción completa de la diligencia
    texto_contexto = Column(Text)  # Fragmento del documento donde se encontró
    numero_pagina = Column(Integer)  # Página donde se encontró
    
    # Párrafo estructurado (nuevo campo)
    parrafo_estructurado = Column(JSONB, nullable=True)  # Información estructurada del párrafo
    
    # Metadatos de extracción
    confianza = Column(Float, default=0.0)  # Confianza de la extracción (0-1)
    verificado = Column(Boolean, default=False)  # Si fue verificado manualmente
    corregido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    # Ordenamiento cronológico
    orden_cronologico = Column(Integer, index=True)  # Orden dentro del expediente
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    tomo = relationship("Tomo")  # back_populates comentado temporalmente
    carpeta = relationship("Carpeta")  # back_populates comentado temporalmente
    corregido_por = relationship("Usuario", foreign_keys=[corregido_por_id])


class PersonaIdentificada(Base):
    """Personas identificadas en los documentos"""
    __tablename__ = "personas_identificadas"
    
    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"), nullable=False, index=True)
    carpeta_id = Column(Integer, ForeignKey("carpetas.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Información personal
    nombre_completo = Column(String(500), nullable=False, index=True)
    nombre_normalizado = Column(String(500), index=True)  # Nombre sin abreviaturas
    alias = Column(String(300))  # Apodos o alias
    
    # Datos de contacto
    direccion = Column(Text)
    colonia = Column(String(200))
    municipio = Column(String(200))
    estado = Column(String(100))
    codigo_postal = Column(String(10))
    telefono = Column(String(100))
    telefono_adicional = Column(String(100))
    
    # Rol en el caso
    rol = Column(String(100), index=True)  # víctima, testigo, imputado, perito, etc.
    
    # Estadísticas
    total_menciones = Column(Integer, default=0)  # Veces que aparece en el expediente
    total_declaraciones = Column(Integer, default=0)  # Número de declaraciones
    
    # Contexto
    primera_mencion_pagina = Column(Integer)
    texto_contexto = Column(Text)
    
    # Metadatos
    confianza = Column(Float, default=0.0)
    verificado = Column(Boolean, default=False)
    corregido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    tomo = relationship("Tomo")  # back_populates comentado temporalmente
    carpeta = relationship("Carpeta")  # back_populates comentado temporalmente
    corregido_por = relationship("Usuario", foreign_keys=[corregido_por_id])
    declaraciones = relationship("DeclaracionPersona", back_populates="persona", cascade="all, delete-orphan")


class DeclaracionPersona(Base):
    """Registro de declaraciones de cada persona"""
    __tablename__ = "declaraciones_personas"
    
    id = Column(Integer, primary_key=True, index=True)
    persona_id = Column(Integer, ForeignKey("personas_identificadas.id", ondelete="CASCADE"), nullable=False, index=True)
    diligencia_id = Column(Integer, ForeignKey("diligencias.id", ondelete="SET NULL"), nullable=True)
    
    fecha_declaracion = Column(Date, index=True)
    tipo_declaracion = Column(String(100))  # inicial, ampliación, ratificación, etc.
    numero_pagina = Column(Integer)
    resumen = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    persona = relationship("PersonaIdentificada", back_populates="declaraciones")
    diligencia = relationship("Diligencia")


class LugarIdentificado(Base):
    """Lugares mencionados en los documentos"""
    __tablename__ = "lugares_identificados"
    
    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"), nullable=False, index=True)
    carpeta_id = Column(Integer, ForeignKey("carpetas.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Información del lugar
    nombre_lugar = Column(Text, nullable=False)
    tipo_lugar = Column(String(100), index=True)  # calle, avenida, colonia, municipio, etc.
    direccion_completa = Column(Text)
    
    # Componentes de dirección
    calle = Column(String(300))
    numero = Column(String(50))
    colonia = Column(String(200))
    municipio = Column(String(200))
    estado = Column(String(100))
    codigo_postal = Column(String(10))
    
    # Contexto
    contexto = Column(Text)  # ¿Por qué es relevante este lugar?
    tipo_relevancia = Column(String(100))  # escena del crimen, domicilio testigo, etc.
    frecuencia_menciones = Column(Integer, default=0)
    numero_pagina = Column(Integer)
    
    # Coordenadas (si se pueden obtener)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    
    # Metadatos
    confianza = Column(Float, default=0.0)
    verificado = Column(Boolean, default=False)
    corregido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    tomo = relationship("Tomo")  # back_populates comentado temporalmente
    carpeta = relationship("Carpeta")  # back_populates comentado temporalmente
    corregido_por = relationship("Usuario", foreign_keys=[corregido_por_id])


class FechaImportante(Base):
    """Fechas relevantes extraídas de narrativas y actuaciones"""
    __tablename__ = "fechas_importantes"
    
    id = Column(Integer, primary_key=True, index=True)
    tomo_id = Column(Integer, ForeignKey("tomos.id", ondelete="CASCADE"), nullable=False, index=True)
    carpeta_id = Column(Integer, ForeignKey("carpetas.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Información de la fecha
    fecha = Column(Date, nullable=False, index=True)
    fecha_texto_original = Column(String(200))  # Fecha tal como aparece
    tipo_fecha = Column(String(100), index=True)  # hechos, actuación MP, audiencia, etc.
    
    # Descripción
    descripcion = Column(Text, nullable=False)  # Qué ocurrió en esta fecha
    texto_contexto = Column(Text)  # Fragmento donde se menciona
    numero_pagina = Column(Integer)
    
    # Clasificación
    es_actuacion_mp = Column(Boolean, default=False, index=True)
    es_fecha_hechos = Column(Boolean, default=False, index=True)
    es_audiencia = Column(Boolean, default=False, index=True)
    
    # Metadatos
    confianza = Column(Float, default=0.0)
    verificado = Column(Boolean, default=False)
    corregido_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    tomo = relationship("Tomo")  # back_populates comentado temporalmente
    carpeta = relationship("Carpeta")  # back_populates comentado temporalmente
    corregido_por = relationship("Usuario", foreign_keys=[corregido_por_id])


class AlertaMP(Base):
    """Alertas de inactividad o irregularidades del Ministerio Público"""
    __tablename__ = "alertas_mp"
    
    id = Column(Integer, primary_key=True, index=True)
    carpeta_id = Column(Integer, ForeignKey("carpetas.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Tipo de alerta
    tipo_alerta = Column(String(100), nullable=False, index=True)  # inactividad, plazo_vencido, etc.
    prioridad = Column(String(20), default='media', index=True)  # baja, media, alta, crítica
    
    # Descripción de la alerta
    titulo = Column(String(300), nullable=False)
    descripcion = Column(Text, nullable=False)
    
    # Datos de la inactividad
    fecha_ultima_actuacion = Column(Date, index=True)
    fecha_siguiente_esperada = Column(Date, nullable=True)
    dias_inactividad = Column(Integer, default=0, index=True)
    
    # Diligencias relacionadas
    ultima_diligencia_id = Column(Integer, ForeignKey("diligencias.id", ondelete="SET NULL"), nullable=True)
    
    # Estado
    estado = Column(String(50), default='activa', index=True)  # activa, resuelta, archivada
    resuelta_fecha = Column(DateTime, nullable=True)
    resuelta_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    notas_resolucion = Column(Text)
    
    # Notificaciones
    notificada = Column(Boolean, default=False)
    fecha_notificacion = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    carpeta = relationship("Carpeta")  # back_populates comentado temporalmente
    ultima_diligencia = relationship("Diligencia", foreign_keys=[ultima_diligencia_id])
    resuelta_por = relationship("Usuario", foreign_keys=[resuelta_por_id])


class EstadisticaCarpeta(Base):
    """Estadísticas generales de una carpeta de investigación"""
    __tablename__ = "estadisticas_carpetas"
    
    id = Column(Integer, primary_key=True, index=True)
    carpeta_id = Column(Integer, ForeignKey("carpetas.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Contadores generales
    total_diligencias = Column(Integer, default=0)
    total_personas = Column(Integer, default=0)
    total_lugares = Column(Integer, default=0)
    total_fechas = Column(Integer, default=0)
    total_alertas_activas = Column(Integer, default=0)
    
    # Estadísticas de tiempo
    fecha_primera_actuacion = Column(Date, nullable=True)
    fecha_ultima_actuacion = Column(Date, nullable=True)
    dias_totales_investigacion = Column(Integer, default=0)
    promedio_dias_entre_actuaciones = Column(Float, default=0.0)
    
    # Contadores por tipo
    total_declaraciones = Column(Integer, default=0)
    total_pericias = Column(Integer, default=0)
    total_comparecencias = Column(Integer, default=0)
    total_oficios = Column(Integer, default=0)
    
    # Calidad de datos
    porcentaje_verificado = Column(Float, default=0.0)  # % de registros verificados
    confianza_promedio = Column(Float, default=0.0)
    
    # Actualización
    ultima_actualizacion = Column(DateTime, default=datetime.utcnow)
    actualizado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    # Relaciones
    carpeta = relationship("Carpeta")  # back_populates comentado temporalmente
    actualizado_por = relationship("Usuario", foreign_keys=[actualizado_por_id])


# Índices compuestos para optimizar consultas
Index('idx_diligencia_carpeta_fecha', Diligencia.carpeta_id, Diligencia.fecha_diligencia)
Index('idx_diligencia_tipo_fecha', Diligencia.tipo_diligencia, Diligencia.fecha_diligencia)
Index('idx_persona_carpeta_nombre', PersonaIdentificada.carpeta_id, PersonaIdentificada.nombre_normalizado)
Index('idx_persona_rol', PersonaIdentificada.carpeta_id, PersonaIdentificada.rol)
Index('idx_lugar_carpeta_tipo', LugarIdentificado.carpeta_id, LugarIdentificado.tipo_lugar)
Index('idx_fecha_carpeta_tipo', FechaImportante.carpeta_id, FechaImportante.fecha, FechaImportante.tipo_fecha)
Index('idx_alerta_carpeta_prioridad', AlertaMP.carpeta_id, AlertaMP.prioridad, AlertaMP.estado)
Index('idx_alerta_estado_fecha', AlertaMP.estado, AlertaMP.created_at)
Index('idx_declaracion_persona_fecha', DeclaracionPersona.persona_id, DeclaracionPersona.fecha_declaracion)
