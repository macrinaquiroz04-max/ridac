"""
Controlador para usuarios: consultar análisis jurídico
Dashboard de usuario con diligencias, personas, lugares, estadísticas y alertas
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import Optional, List
from datetime import datetime, date, timedelta
import logging
import re

from app.database import get_db
from app.models.tomo import Tomo
from app.models.carpeta import Carpeta
from app.models.usuario import Usuario
from app.models.permiso import PermisoCarpeta
from app.models.permiso_tomo import PermisoTomo
from app.models.analisis_juridico import (
    Diligencia, PersonaIdentificada, DeclaracionPersona,
    LugarIdentificado, FechaImportante, AlertaMP, EstadisticaCarpeta
)
from app.middlewares.auth_middleware import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def verificar_permiso_carpeta(db: Session, usuario_id: int, carpeta_id: int) -> bool:
    """Verificar si usuario tiene permiso para ver la carpeta"""
    # Verificar si el usuario es admin
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario and usuario.rol and usuario.rol.nombre in ["admin", "Admin", "Administrador", "Director"]:
        return True
    
    # Opción 1: Permiso directo sobre la carpeta
    permiso_carpeta = db.query(PermisoCarpeta).filter(
        PermisoCarpeta.usuario_id == usuario_id,
        PermisoCarpeta.carpeta_id == carpeta_id
    ).first()
    
    if permiso_carpeta is not None:
        return True
    
    # Opción 2: Permiso sobre algún tomo de la carpeta (con puede_ver=True)
    permiso_tomo = db.query(PermisoTomo).join(Tomo).filter(
        PermisoTomo.usuario_id == usuario_id,
        Tomo.carpeta_id == carpeta_id,
        PermisoTomo.puede_ver == True
    ).first()
    
    return permiso_tomo is not None


@router.get("/usuario/carpetas/{carpeta_id}/diligencias")
async def obtener_diligencias(
    carpeta_id: int,
    tipo: Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    orden: str = "cronologico",  # cronologico, fecha_desc, fecha_asc
    limite: int = Query(100, le=200, description="Máximo 200 resultados por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener diligencias de una carpeta de forma ordenada cronológicamente
    OPTIMIZADO: Paginación eficiente, máximo 200 resultados por consulta
    """
    # Verificar permiso
    if not verificar_permiso_carpeta(db, current_user.id, carpeta_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para ver esta carpeta"
        )
    
    # Query base con JOIN para obtener nombres de tomo y carpeta
    query = db.query(
        Diligencia,
        Tomo.nombre_archivo.label('tomo_nombre'),
        Carpeta.nombre.label('carpeta_nombre')
    ).join(
        Tomo, Diligencia.tomo_id == Tomo.id
    ).join(
        Carpeta, Diligencia.carpeta_id == Carpeta.id
    ).filter(Diligencia.carpeta_id == carpeta_id)
    
    # Filtros opcionales
    if tipo:
        query = query.filter(Diligencia.tipo_diligencia.ilike(f"%{tipo}%"))
    
    if fecha_inicio:
        try:
            fecha_obj = date.fromisoformat(fecha_inicio)
            query = query.filter(Diligencia.fecha_diligencia >= fecha_obj)
        except:
            pass
    
    if fecha_fin:
        try:
            fecha_obj = date.fromisoformat(fecha_fin)
            query = query.filter(Diligencia.fecha_diligencia <= fecha_obj)
        except:
            pass
    
    # Ordenamiento
    if orden == "cronologico":
        query = query.order_by(Diligencia.orden_cronologico)
    elif orden == "fecha_desc":
        query = query.order_by(desc(Diligencia.fecha_diligencia))
    elif orden == "fecha_asc":
        query = query.order_by(Diligencia.fecha_diligencia)
    
    # Total
    total = query.count()
    
    # Paginación
    resultados = query.offset(offset).limit(limite).all()
    
    # Formatear respuesta
    resultado = []
    for row in resultados:
        dil = row.Diligencia
        resultado.append({
            "id": dil.id,
            "tipo_diligencia": dil.tipo_diligencia,
            "fecha": dil.fecha_diligencia.isoformat() if dil.fecha_diligencia else None,
            "fecha_texto": dil.fecha_diligencia_texto,
            "responsable": dil.responsable,
            "numero_oficio": dil.numero_oficio,
            "descripcion": dil.descripcion,
            "pagina": dil.numero_pagina,
            "orden": dil.orden_cronologico,
            "verificado": dil.verificado,
            "confianza": round(dil.confianza, 2) if dil.confianza else 0,
            "tomo_nombre": row.tomo_nombre,
            "carpeta_nombre": row.carpeta_nombre
        })
    
    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "pagina_actual": (offset // limite) + 1 if limite > 0 else 1,
        "total_paginas": (total + limite - 1) // limite if limite > 0 else 1,
        "tiene_siguiente": (offset + limite) < total,
        "tiene_anterior": offset > 0,
        "diligencias": resultado
    }


@router.get("/usuario/carpetas/{carpeta_id}/personas")
async def obtener_personas(
    carpeta_id: int,
    rol: Optional[str] = None,
    buscar: Optional[str] = None,
    con_declaraciones: Optional[bool] = None,
    limite: int = Query(100, le=200, description="Máximo 200 resultados por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener personas identificadas con sus datos de contacto y estadísticas
    OPTIMIZADO: Paginación eficiente, máximo 200 resultados por consulta
    """
    # Verificar permiso
    if not verificar_permiso_carpeta(db, current_user.id, carpeta_id):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Query base con JOIN para obtener nombres de tomo y carpeta
    query = db.query(
        PersonaIdentificada,
        Tomo.nombre_archivo.label('tomo_nombre'),
        Carpeta.nombre.label('carpeta_nombre')
    ).join(
        Tomo, PersonaIdentificada.tomo_id == Tomo.id
    ).join(
        Carpeta, PersonaIdentificada.carpeta_id == Carpeta.id
    ).filter(
        PersonaIdentificada.carpeta_id == carpeta_id
    )
    
    # Filtros
    if rol:
        query = query.filter(PersonaIdentificada.rol.ilike(f"%{rol}%"))
    
    if buscar:
        query = query.filter(
            or_(
                PersonaIdentificada.nombre_completo.ilike(f"%{buscar}%"),
                PersonaIdentificada.nombre_normalizado.ilike(f"%{buscar}%")
            )
        )
    
    if con_declaraciones is not None:
        if con_declaraciones:
            query = query.filter(PersonaIdentificada.total_declaraciones > 0)
        else:
            query = query.filter(PersonaIdentificada.total_declaraciones == 0)
    
    # Total
    total = query.count()
    
    # Ordenar por menciones
    query = query.order_by(desc(PersonaIdentificada.total_menciones))
    
    # Paginación
    resultados = query.offset(offset).limit(limite).all()
    
    # Formatear respuesta
    resultado = []
    for row in resultados:
        per = row.PersonaIdentificada
        resultado.append({
            "id": per.id,
            "nombre": per.nombre_completo,
            "rol": per.rol,
            "direccion": per.direccion,
            "colonia": per.colonia,
            "municipio": per.municipio,
            "estado": per.estado,
            "telefono": per.telefono,
            "telefono_adicional": per.telefono_adicional,
            "total_menciones": per.total_menciones,
            "total_declaraciones": per.total_declaraciones,
            "pagina_primera_mencion": per.primera_mencion_pagina,
            "verificado": per.verificado,
            "confianza": round(per.confianza, 2) if per.confianza else 0,
            "tomo_nombre": row.tomo_nombre,
            "carpeta_nombre": row.carpeta_nombre
        })
    
    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "pagina_actual": (offset // limite) + 1 if limite > 0 else 1,
        "total_paginas": (total + limite - 1) // limite if limite > 0 else 1,
        "tiene_siguiente": (offset + limite) < total,
        "tiene_anterior": offset > 0,
        "personas": resultado
    }


@router.get("/usuario/personas/{persona_id}/declaraciones")
async def obtener_declaraciones_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener estadística de declaraciones de una persona específica
    """
    # Obtener persona
    persona = db.query(PersonaIdentificada).filter(
        PersonaIdentificada.id == persona_id
    ).first()
    
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    # Verificar permiso
    if not verificar_permiso_carpeta(db, current_user.id, persona.carpeta_id):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Obtener declaraciones
    declaraciones = db.query(DeclaracionPersona).filter(
        DeclaracionPersona.persona_id == persona_id
    ).order_by(DeclaracionPersona.fecha_declaracion).all()
    
    resultado_declaraciones = []
    for decl in declaraciones:
        resultado_declaraciones.append({
            "id": decl.id,
            "fecha": decl.fecha_declaracion.isoformat() if decl.fecha_declaracion else None,
            "tipo": decl.tipo_declaracion,
            "pagina": decl.numero_pagina,
            "resumen": decl.resumen
        })
    
    return {
        "persona": {
            "id": persona.id,
            "nombre": persona.nombre_completo,
            "rol": persona.rol
        },
        "total_declaraciones": len(declaraciones),
        "declaraciones": resultado_declaraciones
    }


@router.get("/usuario/carpetas/{carpeta_id}/lugares")
async def obtener_lugares(
    carpeta_id: int,
    tipo: Optional[str] = None,
    buscar: Optional[str] = None,
    limite: int = Query(100, le=200, description="Máximo 200 resultados por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener lugares mencionados en documentos (direcciones, calles, colonias, etc.)
    OPTIMIZADO: Paginación eficiente, máximo 200 resultados por consulta
    """
    # Verificar permiso
    if not verificar_permiso_carpeta(db, current_user.id, carpeta_id):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Query base con JOIN para obtener nombres de tomo y carpeta
    query = db.query(
        LugarIdentificado,
        Tomo.nombre_archivo.label('tomo_nombre'),
        Carpeta.nombre.label('carpeta_nombre')
    ).join(
        Tomo, LugarIdentificado.tomo_id == Tomo.id
    ).join(
        Carpeta, LugarIdentificado.carpeta_id == Carpeta.id
    ).filter(
        LugarIdentificado.carpeta_id == carpeta_id
    )
    
    # Filtros
    if tipo:
        query = query.filter(LugarIdentificado.tipo_lugar.ilike(f"%{tipo}%"))
    
    if buscar:
        query = query.filter(
            or_(
                LugarIdentificado.nombre_lugar.ilike(f"%{buscar}%"),
                LugarIdentificado.direccion_completa.ilike(f"%{buscar}%"),
                LugarIdentificado.colonia.ilike(f"%{buscar}%"),
                LugarIdentificado.municipio.ilike(f"%{buscar}%")
            )
        )
    
    # Total
    total = query.count()
    
    # Ordenar por frecuencia
    query = query.order_by(desc(LugarIdentificado.frecuencia_menciones))
    
    # Paginación
    resultados = query.offset(offset).limit(limite).all()
    
    # Formatear respuesta
    resultado = []
    for row in resultados:
        lug = row.LugarIdentificado
        resultado.append({
            "id": lug.id,
            "nombre": lug.nombre_lugar,
            "tipo": lug.tipo_lugar,
            "direccion_completa": lug.direccion_completa,
            "calle": lug.calle,
            "numero": lug.numero,
            "colonia": lug.colonia,
            "municipio": lug.municipio,
            "estado": lug.estado,
            "codigo_postal": lug.codigo_postal,
            "relevancia": lug.tipo_relevancia,
            "frecuencia": lug.frecuencia_menciones,
            "pagina": lug.numero_pagina,
            "latitud": lug.latitud,
            "longitud": lug.longitud,
            "verificado": lug.verificado,
            "tomo_nombre": row.tomo_nombre,
            "carpeta_nombre": row.carpeta_nombre
        })
    
    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "pagina_actual": (offset // limite) + 1 if limite > 0 else 1,
        "total_paginas": (total + limite - 1) // limite if limite > 0 else 1,
        "tiene_siguiente": (offset + limite) < total,
        "tiene_anterior": offset > 0,
        "lugares": resultado
    }


@router.get("/usuario/carpetas/{carpeta_id}/fechas")
async def obtener_fechas_importantes(
    carpeta_id: int,
    tipo: Optional[str] = None,  # actuacion_mp, fecha_hechos, audiencia, etc.
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    limite: int = Query(200, le=500, description="Máximo 500 resultados para fechas"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener fechas importantes de narrativas y actuaciones del MP
    OPTIMIZADO: Paginación eficiente con límite máximo de 500
    """
    # Verificar permiso
    if not verificar_permiso_carpeta(db, current_user.id, carpeta_id):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Query base con JOIN para obtener nombres de tomo y carpeta
    query = db.query(
        FechaImportante,
        Tomo.nombre_archivo.label('tomo_nombre'),
        Carpeta.nombre.label('carpeta_nombre')
    ).join(
        Tomo, FechaImportante.tomo_id == Tomo.id
    ).join(
        Carpeta, FechaImportante.carpeta_id == Carpeta.id
    ).filter(
        FechaImportante.carpeta_id == carpeta_id
    )
    
    # Filtros
    if tipo:
        if tipo == "actuacion_mp":
            query = query.filter(FechaImportante.es_actuacion_mp == True)
        elif tipo == "fecha_hechos":
            query = query.filter(FechaImportante.es_fecha_hechos == True)
        elif tipo == "audiencia":
            query = query.filter(FechaImportante.es_audiencia == True)
        else:
            query = query.filter(FechaImportante.tipo_fecha.ilike(f"%{tipo}%"))
    
    if fecha_inicio:
        try:
            fecha_obj = date.fromisoformat(fecha_inicio)
            query = query.filter(FechaImportante.fecha >= fecha_obj)
        except:
            pass
    
    if fecha_fin:
        try:
            fecha_obj = date.fromisoformat(fecha_fin)
            query = query.filter(FechaImportante.fecha <= fecha_obj)
        except:
            pass
    
    # Total
    total = query.count()
    
    # Ordenar por fecha
    query = query.order_by(FechaImportante.fecha)
    
    # Paginación
    resultados = query.offset(offset).limit(limite).all()
    
    # Formatear respuesta
    resultado = []
    for row in resultados:
        fec = row.FechaImportante
        resultado.append({
            "id": fec.id,
            "fecha": fec.fecha.isoformat(),
            "fecha_texto": fec.fecha_texto_original,
            "tipo": fec.tipo_fecha,
            "descripcion": fec.descripcion,
            "es_actuacion_mp": fec.es_actuacion_mp,
            "es_fecha_hechos": fec.es_fecha_hechos,
            "es_audiencia": fec.es_audiencia,
            "pagina": fec.numero_pagina,
            "verificado": fec.verificado,
            "tomo_nombre": row.tomo_nombre,
            "carpeta_nombre": row.carpeta_nombre
        })
    
    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "fechas": resultado
    }


@router.get("/usuario/carpetas/{carpeta_id}/alertas")
async def obtener_alertas_mp(
    carpeta_id: int,
    estado: str = "activa",  # activa, resuelta, archivada
    prioridad: Optional[str] = None,  # baja, media, alta, crítica
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener alertas de inactividad del MP (>6 meses sin actuaciones, etc.)
    """
    # Verificar permiso
    if not verificar_permiso_carpeta(db, current_user.id, carpeta_id):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Query base
    query = db.query(AlertaMP).filter(
        AlertaMP.carpeta_id == carpeta_id,
        AlertaMP.estado == estado
    )
    
    # Filtro de prioridad
    if prioridad:
        query = query.filter(AlertaMP.prioridad == prioridad)
    
    # Ordenar por prioridad y fecha
    prioridad_order = {
        'crítica': 1,
        'alta': 2,
        'media': 3,
        'baja': 4
    }
    
    alertas = query.order_by(AlertaMP.created_at.desc()).all()
    
    # Ordenar por prioridad personalizada
    alertas_ordenadas = sorted(
        alertas,
        key=lambda x: (prioridad_order.get(x.prioridad, 5), -x.dias_inactividad)
    )
    
    # Formatear respuesta
    resultado = []
    for alerta in alertas_ordenadas:
        resultado.append({
            "id": alerta.id,
            "tipo": alerta.tipo_alerta,
            "prioridad": alerta.prioridad,
            "titulo": alerta.titulo,
            "descripcion": alerta.descripcion,
            "dias_inactividad": alerta.dias_inactividad,
            "fecha_ultima_actuacion": alerta.fecha_ultima_actuacion.isoformat() if alerta.fecha_ultima_actuacion else None,
            "estado": alerta.estado,
            "fecha_creacion": alerta.created_at.isoformat(),
            "notificada": alerta.notificada
        })
    
    return {
        "total": len(resultado),
        "carpeta_id": carpeta_id,
        "alertas": resultado
    }


@router.get("/usuario/carpetas/{carpeta_id}/estadisticas")
async def obtener_estadisticas(
    carpeta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener estadísticas generales de la carpeta
    """
    # Verificar permiso
    if not verificar_permiso_carpeta(db, current_user.id, carpeta_id):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Obtener carpeta
    carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()
    if not carpeta:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    
    # Obtener estadísticas
    stats = db.query(EstadisticaCarpeta).filter(
        EstadisticaCarpeta.carpeta_id == carpeta_id
    ).first()
    
    if not stats:
        return {
            "carpeta_id": carpeta_id,
            "carpeta_nombre": carpeta.nombre,
            "mensaje": "No hay estadísticas disponibles. Ejecute el análisis primero."
        }
    
    # Estadísticas por tipo de persona (EXCLUYENDO personas inválidas)
    # Filtrar conceptos legales, lugares y fragmentos OCR
    patrones_invalidos = [
        '%MECANISMO CIUDADANO%', '%MECAITISNO%', '%MECARISMO%', '%MECANISINO%',
        '%ABUSO SEXUAL%', '%VIOLENCIA CONTRA%', '%TRIBUNAL%',
        '%MINISTERIO PUBLICO%', '%SUPREMA CORTE%', '%SALA CIVIL%',
        '%CIUDAD DE%', '%SAN LUIS%', '%ROMA NORTE%',
        '%PRIMER PISO%', '%TERCER PISO%', '%FECHA HORA%',
        '%DICTAMEN PERICIAL%', '%INFORME%', '%NORMAS OFICIALES%',
        '%PERITO OFICIAL%', '%JUSTICIA%', '%DESARROLLO INTEGRAL%',
        '%LIBRE DESA%', '%NORMAL DESARROLLO%', '%ACUERDO MINISTERIAL%'
    ]
    
    query_personas_validas = db.query(PersonaIdentificada).filter(
        PersonaIdentificada.carpeta_id == carpeta_id
    )
    
    # Excluir patrones inválidos
    for patron in patrones_invalidos:
        query_personas_validas = query_personas_validas.filter(
            ~PersonaIdentificada.nombre_completo.ilike(patron)
        )
    
    # Excluir nombres muy cortos (< 6 caracteres)
    query_personas_validas = query_personas_validas.filter(
        func.length(PersonaIdentificada.nombre_completo) >= 6
    )
    
    # Contar total de personas válidas
    total_personas_validas = query_personas_validas.count()
    
    # Personas por rol (solo válidas)
    personas_por_rol = query_personas_validas.with_entities(
        PersonaIdentificada.rol,
        func.count(PersonaIdentificada.id).label('total')
    ).group_by(PersonaIdentificada.rol).all()
    
    # Diligencias por tipo
    diligencias_por_tipo = db.query(
        Diligencia.tipo_diligencia,
        func.count(Diligencia.id).label('total')
    ).filter(
        Diligencia.carpeta_id == carpeta_id
    ).group_by(Diligencia.tipo_diligencia).all()
    
    # Alertas por prioridad
    alertas_por_prioridad = db.query(
        AlertaMP.prioridad,
        func.count(AlertaMP.id).label('total')
    ).filter(
        AlertaMP.carpeta_id == carpeta_id,
        AlertaMP.estado == 'activa'
    ).group_by(AlertaMP.prioridad).all()
    
    return {
        "carpeta_id": carpeta_id,
        "carpeta_nombre": carpeta.nombre,
        "resumen": {
            "total_diligencias": stats.total_diligencias,
            "total_personas": total_personas_validas,  # Usar contador filtrado
            "total_lugares": stats.total_lugares,
            "total_fechas": stats.total_fechas,
            "total_alertas_activas": stats.total_alertas_activas,
            "total_declaraciones": stats.total_declaraciones,
            "total_pericias": stats.total_pericias
        },
        "temporalidad": {
            "fecha_primera_actuacion": stats.fecha_primera_actuacion.isoformat() if stats.fecha_primera_actuacion else None,
            "fecha_ultima_actuacion": stats.fecha_ultima_actuacion.isoformat() if stats.fecha_ultima_actuacion else None,
            "dias_investigacion": stats.dias_totales_investigacion,
            "promedio_dias_entre_actuaciones": round(stats.promedio_dias_entre_actuaciones, 2)
        },
        "personas_por_rol": {
            rol: total for rol, total in personas_por_rol if rol
        },
        "diligencias_por_tipo": {
            tipo: total for tipo, total in diligencias_por_tipo if tipo
        },
        "alertas_por_prioridad": {
            prioridad: total for prioridad, total in alertas_por_prioridad
        },
        "calidad": {
            "porcentaje_verificado": round(stats.porcentaje_verificado, 2),
            "confianza_promedio": round(stats.confianza_promedio, 2)
        },
        "ultima_actualizacion": stats.ultima_actualizacion.isoformat()
    }


@router.get("/usuario/carpetas/{carpeta_id}/linea-tiempo")
async def obtener_linea_tiempo(
    carpeta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener línea de tiempo completa con todas las fechas y diligencias
    """
    # Verificar permiso
    if not verificar_permiso_carpeta(db, current_user.id, carpeta_id):
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Obtener diligencias con fecha
    diligencias = db.query(Diligencia).filter(
        Diligencia.carpeta_id == carpeta_id,
        Diligencia.fecha_diligencia.isnot(None)
    ).order_by(Diligencia.fecha_diligencia).all()
    
    # Convertir a eventos de línea de tiempo
    eventos = []
    for dil in diligencias:
        tipo_evento = _limpiar_texto_evento(dil.tipo_diligencia) or "Diligencia"
        responsable = _limpiar_texto_evento(dil.responsable) or None
        numero_oficio = _limpiar_texto_evento(dil.numero_oficio) or None

        eventos.append({
            "fecha": dil.fecha_diligencia.isoformat(),
            "tipo": "diligencia",
            "categoria": tipo_evento,
            "titulo": _construir_titulo_diligencia(tipo_evento, responsable, numero_oficio),
            "descripcion": _construir_descripcion_diligencia(dil, responsable, numero_oficio),
            "responsable": responsable,
            "oficio": numero_oficio,
            "id": dil.id,
            "pagina": dil.numero_pagina,
            "confianza": float(dil.confianza) if dil.confianza is not None else None
        })
    
    return {
        "carpeta_id": carpeta_id,
        "total_eventos": len(eventos),
        "eventos": eventos
    }


def _limpiar_texto_evento(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None

    texto_limpio = texto.replace("\x0c", " ")
    texto_limpio = re.sub(r"\s+", " ", texto_limpio)
    texto_limpio = texto_limpio.strip(" \t\n\r-:;,")

    return texto_limpio or None


def _construir_titulo_diligencia(tipo: str, responsable: Optional[str], oficio: Optional[str]) -> str:
    if responsable:
        return _truncar_texto(f"{tipo} - {responsable}", 120)

    if oficio:
        return _truncar_texto(f"{tipo} - Oficio {oficio}", 120)

    return _truncar_texto(tipo, 120)


def _construir_descripcion_diligencia(
    diligencia: Diligencia,
    responsable: Optional[str],
    oficio: Optional[str],
    max_len: int = 280
) -> str:
    texto_base = diligencia.descripcion or diligencia.texto_contexto or ""
    texto_base = _limpiar_texto_evento(texto_base) or ""

    frase_relevante = _extraer_frase_relevante(texto_base)
    descripcion = frase_relevante or texto_base

    if not descripcion:
        detalles = []
        if responsable:
            detalles.append(f"Responsable: {responsable}")
        if oficio:
            detalles.append(f"Oficio: {oficio}")
        if diligencia.numero_pagina:
            detalles.append(f"Pag. {diligencia.numero_pagina}")
        descripcion = " | ".join(detalles)

    if not descripcion:
        descripcion = "Detalles no disponibles"

    if (
        diligencia.numero_pagina
        and descripcion
        and f"Pag. {diligencia.numero_pagina}" not in descripcion
        and f"Pagina {diligencia.numero_pagina}" not in descripcion
    ):
        descripcion = f"{descripcion} (Pag. {diligencia.numero_pagina})"

    return _truncar_texto(descripcion, max_len)


def _extraer_frase_relevante(texto: str) -> str:
    if not texto:
        return ""

    frases = re.split(r"(?<=[.!?])\s+", texto)
    for frase in frases:
        frase_limpia = frase.strip()
        if len(frase_limpia) >= 30:
            return frase_limpia

    return frases[0].strip() if frases else ""


def _truncar_texto(texto: str, max_len: int) -> str:
    if len(texto) <= max_len:
        return texto

    return texto[:max_len - 3].rstrip() + "..."


@router.get("/usuario/carpetas")
async def obtener_mis_carpetas_con_analisis(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener carpetas del usuario con resumen de análisis
    """
    # Obtener carpetas con permiso (PermisoCarpeta usa 'tipo', no 'puede_ver')
    permisos = db.query(PermisoCarpeta).filter(
        PermisoCarpeta.usuario_id == current_user.id
    ).all()
    
    carpetas = []
    for permiso in permisos:
        carpeta = permiso.carpeta
        
        # Obtener estadísticas si existen
        stats = db.query(EstadisticaCarpeta).filter(
            EstadisticaCarpeta.carpeta_id == carpeta.id
        ).first()
        
        carpeta_info = {
            "id": carpeta.id,
            "nombre": carpeta.nombre,
            "numero_expediente": carpeta.numero_expediente,
            "estado": carpeta.estado,
            "anio": carpeta.anio
        }
        
        if stats:
            carpeta_info["analisis"] = {
                "total_diligencias": stats.total_diligencias,
                "total_personas": stats.total_personas,
                "total_alertas": stats.total_alertas_activas,
                "dias_investigacion": stats.dias_totales_investigacion,
                "ultima_actuacion": stats.fecha_ultima_actuacion.isoformat() if stats.fecha_ultima_actuacion else None
            }
        else:
            carpeta_info["analisis"] = None
        
        carpetas.append(carpeta_info)
    
    return {
        "total": len(carpetas),
        "carpetas": carpetas
    }


@router.get("/usuario/diligencias/{diligencia_id}")
async def obtener_detalle_diligencia(
    diligencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener detalle completo de una diligencia incluyendo párrafo estructurado
    """
    # Obtener diligencia
    diligencia = db.query(Diligencia).filter(Diligencia.id == diligencia_id).first()
    
    if not diligencia:
        raise HTTPException(status_code=404, detail="Diligencia no encontrada")
    
    # Verificar permisos
    if not verificar_permiso_carpeta(db, current_user.id, diligencia.carpeta_id):
        raise HTTPException(status_code=403, detail="No tiene permiso para ver esta diligencia")
    
    # Construir respuesta
    resultado = {
        "id": diligencia.id,
        "tipo_diligencia": diligencia.tipo_diligencia,
        "fecha_diligencia": diligencia.fecha_diligencia.isoformat() if diligencia.fecha_diligencia else None,
        "fecha_diligencia_texto": diligencia.fecha_diligencia_texto,
        "responsable": diligencia.responsable,
        "numero_oficio": diligencia.numero_oficio,
        "descripcion": diligencia.descripcion,
        "texto_contexto": diligencia.texto_contexto,
        "numero_pagina": diligencia.numero_pagina,
        "confianza": diligencia.confianza,
        "verificado": diligencia.verificado,
        "orden_cronologico": diligencia.orden_cronologico,
        "parrafo_estructurado": diligencia.parrafo_estructurado,  # ← Campo JSON con toda la info estructurada
        "created_at": diligencia.created_at.isoformat() if diligencia.created_at else None
    }
    
    return resultado
