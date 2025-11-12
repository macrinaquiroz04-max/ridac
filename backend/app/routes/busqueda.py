# backend/app/routes/busqueda.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from app.database import get_db
from app.models.tomo import Tomo, ContenidoOCR
from app.models.carpeta import Carpeta
from app.models.usuario import Usuario
from app.models.permiso import PermisoCarpeta
from app.middlewares.auth_middleware import get_current_active_user
from app.middlewares.permission_middleware import check_folder_access
from app.services.cache_service import cache_service
from app.utils.auditoria_utils import registrar_auditoria
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/busqueda",
    tags=["Búsqueda"]
)


# Schemas
class BusquedaSimple(BaseModel):
    termino: str
    carpeta_id: Optional[int] = None
    solo_titulos: bool = False


class BusquedaAvanzada(BaseModel):
    terminos: Optional[List[str]] = None
    carpeta_ids: Optional[List[int]] = None
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    procesado: Optional[bool] = None
    motor_ocr: Optional[str] = None
    confianza_minima: Optional[float] = None


class ResultadoBusqueda(BaseModel):
    tomo_id: int
    tomo_nombre: str
    carpeta_id: int
    carpeta_nombre: str
    pagina: Optional[int]
    fragmento: str
    confianza: Optional[float]
    relevancia: float

    class Config:
        from_attributes = True


# ==================== BÚSQUEDA SIMPLE ====================

@router.post("/simple", response_model=List[ResultadoBusqueda])
async def busqueda_simple(
    busqueda: BusquedaSimple,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),  # Reducido de 500 a 100 para mejor rendimiento
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    POST /busqueda/simple
    Búsqueda simple por término en títulos y contenido OCR.
    ⚡ OPTIMIZADO: Usa caché Redis para búsquedas frecuentes
    """
    if not busqueda.termino or len(busqueda.termino.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El término de búsqueda debe tener al menos 2 caracteres"
        )

    termino = busqueda.termino.strip()
    
    # Crear clave de caché basada en el término y parámetros
    cache_key = f"busqueda:simple:{termino}:{busqueda.carpeta_id}:{busqueda.solo_titulos}:{current_user.id}:{skip}:{limit}"
    
    # Intentar obtener desde caché
    cached_data = cache_service.get(cache_key)
    if cached_data:
        logger.info(f"✅ Búsqueda '{termino}' obtenida desde caché")
        return cached_data
    
    search_pattern = f"%{termino}%"

    resultados = []

    # Obtener carpetas con acceso
    carpetas_accesibles = []
    if current_user.rol.nombre in ["admin", "administrador"]:
        carpetas_query = db.query(Carpeta.id)
    else:
        carpetas_query = db.query(PermisoCarpeta.carpeta_id).filter(
            PermisoCarpeta.usuario_id == current_user.id
        )

    if busqueda.carpeta_id:
        # Verificar acceso a la carpeta específica
        has_access = await check_folder_access(
            carpeta_id=busqueda.carpeta_id,
            user=current_user,
            db=db,
            required_permission="lectura"
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a esta carpeta"
            )

        carpetas_accesibles = [busqueda.carpeta_id]
    else:
        carpetas_accesibles = [c[0] for c in carpetas_query.all()]

    # Buscar en títulos de tomos
    tomos_query = db.query(Tomo).filter(
        Tomo.carpeta_id.in_(carpetas_accesibles),
        or_(
            Tomo.nombre.ilike(search_pattern),
            Tomo.descripcion.ilike(search_pattern)
        )
    )

    tomos = tomos_query.all()

    for tomo in tomos:
        resultados.append(ResultadoBusqueda(
            tomo_id=tomo.id,
            tomo_nombre=tomo.nombre,
            carpeta_id=tomo.carpeta_id,
            carpeta_nombre=tomo.carpeta.nombre,
            pagina=None,
            fragmento=tomo.descripcion or tomo.nombre,
            confianza=None,
            relevancia=1.0  # Mayor relevancia para coincidencias en título
        ))

    # Si no es solo títulos, buscar en contenido OCR
    if not busqueda.solo_titulos:
        contenido_query = db.query(ContenidoOCR).join(Tomo).filter(
            Tomo.carpeta_id.in_(carpetas_accesibles),
            ContenidoOCR.texto_ocr.ilike(search_pattern)
        )

        contenidos = contenido_query.all()

        for contenido in contenidos:
            # Extraer fragmento con contexto
            texto = contenido.texto_ocr
            indice = texto.lower().find(termino.lower())

            if indice != -1:
                inicio = max(0, indice - 100)
                fin = min(len(texto), indice + len(termino) + 100)
                fragmento = texto[inicio:fin]

                if inicio > 0:
                    fragmento = "..." + fragmento
                if fin < len(texto):
                    fragmento = fragmento + "..."
            else:
                fragmento = texto[:200]

            resultados.append(ResultadoBusqueda(
                tomo_id=contenido.tomo_id,
                tomo_nombre=contenido.tomo.nombre,
                carpeta_id=contenido.tomo.carpeta_id,
                carpeta_nombre=contenido.tomo.carpeta.nombre,
                pagina=contenido.numero_pagina,
                fragmento=fragmento,
                confianza=contenido.confianza,
                relevancia=0.8  # Menor relevancia para contenido OCR
            ))

    # Ordenar por relevancia
    resultados.sort(key=lambda x: x.relevancia, reverse=True)

    # Aplicar paginación
    result = resultados[skip:skip + limit]
    
    # Registrar auditoría
    registrar_auditoria(
        db=db,
        usuario_id=current_user.id,
        accion="BUSQUEDA_SIMPLE",
        tabla_afectada="contenido_ocr",
        valores_nuevos={
            "termino": termino,
            "carpeta_id": busqueda.carpeta_id,
            "solo_titulos": busqueda.solo_titulos,
            "total_resultados": len(resultados),
            "resultados_devueltos": len(result)
        }
    )
    
    # Guardar en caché por 10 minutos (convertir a dict para serialización)
    result_dict = [r.model_dump() for r in result]
    cache_service.set(cache_key, result_dict, ttl=600)
    logger.info(f"💾 Búsqueda '{termino}' guardada en caché ({len(result)} resultados)")
    
    return result


# ==================== BÚSQUEDA AVANZADA ====================

@router.post("/avanzada", response_model=List[ResultadoBusqueda])
async def busqueda_avanzada(
    busqueda: BusquedaAvanzada,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),  # Reducido de 500 a 100 para mejor rendimiento
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    POST /busqueda/avanzada
    Búsqueda avanzada con múltiples filtros.
    """
    resultados = []

    # Obtener carpetas con acceso
    carpetas_accesibles = []
    if current_user.rol.nombre == "Administrador":
        carpetas_query = db.query(Carpeta.id)
    else:
        carpetas_query = db.query(PermisoCarpeta.carpeta_id).filter(
            PermisoCarpeta.usuario_id == current_user.id
        )

    if busqueda.carpeta_ids:
        # Verificar acceso a cada carpeta
        for carpeta_id in busqueda.carpeta_ids:
            has_access = await check_folder_access(
                carpeta_id=carpeta_id,
                user=current_user,
                db=db,
                required_permission="lectura"
            )

            if has_access:
                carpetas_accesibles.append(carpeta_id)
    else:
        carpetas_accesibles = [c[0] for c in carpetas_query.all()]

    if not carpetas_accesibles:
        return []

    # Construir query base
    query = db.query(ContenidoOCR).join(Tomo).filter(
        Tomo.carpeta_id.in_(carpetas_accesibles)
    )

    # Filtrar por términos de búsqueda
    if busqueda.terminos:
        terminos_filters = []
        for termino in busqueda.terminos:
            if termino.strip():
                pattern = f"%{termino.strip()}%"
                terminos_filters.append(ContenidoOCR.texto_ocr.ilike(pattern))

        if terminos_filters:
            query = query.filter(or_(*terminos_filters))

    # Filtrar por fecha
    if busqueda.fecha_desde:
        fecha_desde_dt = datetime.combine(busqueda.fecha_desde, datetime.min.time())
        query = query.filter(Tomo.creado_en >= fecha_desde_dt)

    if busqueda.fecha_hasta:
        fecha_hasta_dt = datetime.combine(busqueda.fecha_hasta, datetime.max.time())
        query = query.filter(Tomo.creado_en <= fecha_hasta_dt)

    # Filtrar por estado de procesamiento
    if busqueda.procesado is not None:
        query = query.filter(Tomo.procesado == busqueda.procesado)

    # Filtrar por motor OCR
    if busqueda.motor_ocr:
        query = query.filter(ContenidoOCR.motor_ocr == busqueda.motor_ocr)

    # Filtrar por confianza mínima
    if busqueda.confianza_minima is not None:
        query = query.filter(
            ContenidoOCR.confianza >= busqueda.confianza_minima
        )

    # Ejecutar query
    contenidos = query.all()

    for contenido in contenidos:
        # Calcular relevancia basada en varios factores
        relevancia = 0.5

        # Aumentar relevancia si hay términos específicos
        if busqueda.terminos:
            texto_lower = contenido.texto_ocr.lower()
            terminos_encontrados = sum(
                1 for t in busqueda.terminos
                if t.lower() in texto_lower
            )
            relevancia += (terminos_encontrados / len(busqueda.terminos)) * 0.3

        # Aumentar relevancia por confianza
        if contenido.confianza:
            relevancia += (contenido.confianza / 100) * 0.2

        # Extraer fragmento
        texto = contenido.texto_ocr
        if busqueda.terminos and busqueda.terminos[0]:
            primer_termino = busqueda.terminos[0]
            indice = texto.lower().find(primer_termino.lower())

            if indice != -1:
                inicio = max(0, indice - 100)
                fin = min(len(texto), indice + len(primer_termino) + 100)
                fragmento = texto[inicio:fin]

                if inicio > 0:
                    fragmento = "..." + fragmento
                if fin < len(texto):
                    fragmento = fragmento + "..."
            else:
                fragmento = texto[:200]
        else:
            fragmento = texto[:200]

        resultados.append(ResultadoBusqueda(
            tomo_id=contenido.tomo_id,
            tomo_nombre=contenido.tomo.nombre,
            carpeta_id=contenido.tomo.carpeta_id,
            carpeta_nombre=contenido.tomo.carpeta.nombre,
            pagina=contenido.numero_pagina,
            fragmento=fragmento,
            confianza=contenido.confianza,
            relevancia=relevancia
        ))

    # Ordenar por relevancia
    resultados.sort(key=lambda x: x.relevancia, reverse=True)

    # Aplicar paginación
    resultados_paginados = resultados[skip:skip + limit]
    
    # Registrar auditoría
    registrar_auditoria(
        db=db,
        usuario_id=current_user.id,
        accion="BUSQUEDA_AVANZADA",
        tabla_afectada="contenido_ocr",
        valores_nuevos={
            "terminos": busqueda.terminos,
            "carpeta_ids": busqueda.carpeta_ids,
            "fecha_desde": busqueda.fecha_desde.isoformat() if busqueda.fecha_desde else None,
            "fecha_hasta": busqueda.fecha_hasta.isoformat() if busqueda.fecha_hasta else None,
            "total_resultados": len(resultados),
            "resultados_devueltos": len(resultados_paginados)
        }
    )
    
    return resultados_paginados


# ==================== ESTADÍSTICAS DE BÚSQUEDA ====================

@router.get("/estadisticas")
async def obtener_estadisticas(
    carpeta_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /busqueda/estadisticas
    Obtener estadísticas de contenido disponible para búsqueda.
    """
    # Obtener carpetas con acceso
    if current_user.rol.nombre in ["admin", "administrador"]:
        if carpeta_id:
            carpetas_accesibles = [carpeta_id]
        else:
            carpetas_query = db.query(Carpeta.id).all()
            carpetas_accesibles = [c[0] for c in carpetas_query]
    else:
        permisos_query = db.query(PermisoCarpeta.carpeta_id).filter(
            PermisoCarpeta.usuario_id == current_user.id
        )

        if carpeta_id:
            # Verificar acceso
            has_access = await check_folder_access(
                carpeta_id=carpeta_id,
                user=current_user,
                db=db,
                required_permission="lectura"
            )

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene acceso a esta carpeta"
                )

            carpetas_accesibles = [carpeta_id]
        else:
            carpetas_accesibles = [p[0] for p in permisos_query.all()]

    # Contar tomos
    total_tomos = db.query(func.count(Tomo.id)).filter(
        Tomo.carpeta_id.in_(carpetas_accesibles)
    ).scalar()

    # Contar tomos procesados
    tomos_procesados = db.query(func.count(Tomo.id)).filter(
        Tomo.carpeta_id.in_(carpetas_accesibles),
        Tomo.procesado == True
    ).scalar()

    # Contar páginas procesadas
    paginas_procesadas = db.query(func.count(ContenidoOCR.id)).join(Tomo).filter(
        Tomo.carpeta_id.in_(carpetas_accesibles)
    ).scalar()

    # Obtener motores OCR utilizados
    motores_ocr = db.query(
        ContenidoOCR.motor_ocr,
        func.count(ContenidoOCR.id).label('cantidad')
    ).join(Tomo).filter(
        Tomo.carpeta_id.in_(carpetas_accesibles)
    ).group_by(ContenidoOCR.motor_ocr).all()

    # Calcular confianza promedio
    confianza_promedio = db.query(
        func.avg(ContenidoOCR.confianza)
    ).join(Tomo).filter(
        Tomo.carpeta_id.in_(carpetas_accesibles),
        ContenidoOCR.confianza.isnot(None)
    ).scalar()

    return {
        "carpetas_accesibles": len(carpetas_accesibles),
        "total_tomos": total_tomos,
        "tomos_procesados": tomos_procesados,
        "tomos_pendientes": total_tomos - tomos_procesados,
        "paginas_procesadas": paginas_procesadas,
        "motores_ocr": [
            {"motor": m[0], "cantidad": m[1]}
            for m in motores_ocr
        ],
        "confianza_promedio": round(confianza_promedio, 2) if confianza_promedio else None
    }


# ==================== SUGERENCIAS ====================

@router.get("/sugerencias")
async def obtener_sugerencias(
    termino: str = Query(..., min_length=2),
    limite: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /busqueda/sugerencias
    Obtener sugerencias de autocompletado basadas en nombres de tomos.
    """
    # Obtener carpetas con acceso
    if current_user.rol.nombre in ["admin", "administrador"]:
        carpetas_query = db.query(Carpeta.id).all()
        carpetas_accesibles = [c[0] for c in carpetas_query]
    else:
        permisos_query = db.query(PermisoCarpeta.carpeta_id).filter(
            PermisoCarpeta.usuario_id == current_user.id
        ).all()
        carpetas_accesibles = [p[0] for p in permisos_query]

    # Buscar tomos que coincidan
    search_pattern = f"%{termino}%"

    tomos = db.query(Tomo.nombre, Tomo.id).filter(
        Tomo.carpeta_id.in_(carpetas_accesibles),
        Tomo.nombre.ilike(search_pattern)
    ).limit(limite).all()

    sugerencias = [
        {
            "id": t[1],
            "texto": t[0]
        }
        for t in tomos
    ]

    return sugerencias


# ==================== TÉRMINOS FRECUENTES ====================

@router.get("/terminos-frecuentes")
async def obtener_terminos_frecuentes(
    carpeta_id: Optional[int] = None,
    limite: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /busqueda/terminos-frecuentes
    Obtener términos más frecuentes en el contenido OCR.
    (Implementación simplificada - para producción usar full-text search)
    """
    # Obtener carpetas con acceso
    if current_user.rol.nombre in ["admin", "administrador"]:
        if carpeta_id:
            carpetas_accesibles = [carpeta_id]
        else:
            carpetas_query = db.query(Carpeta.id).all()
            carpetas_accesibles = [c[0] for c in carpetas_query]
    else:
        permisos_query = db.query(PermisoCarpeta.carpeta_id).filter(
            PermisoCarpeta.usuario_id == current_user.id
        )

        if carpeta_id:
            has_access = await check_folder_access(
                carpeta_id=carpeta_id,
                user=current_user,
                db=db,
                required_permission="lectura"
            )

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene acceso a esta carpeta"
                )

            carpetas_accesibles = [carpeta_id]
        else:
            carpetas_accesibles = [p[0] for p in permisos_query.all()]

    # Esta es una implementación simplificada
    # En producción, usar PostgreSQL full-text search o Elasticsearch
    return {
        "message": "Función en desarrollo",
        "info": "Usar PostgreSQL ts_vector o Elasticsearch para análisis de términos frecuentes"
    }


# Schemas para búsqueda semántica
class BusquedaSemantica(BaseModel):
    query: str
    carpeta_id: Optional[int] = None
    tomo_id: Optional[int] = None
    similitud_minima: float = 0.5
    limit: int = 50


@router.get("/test-semantica")
async def test_busqueda_semantica():
    """
    Endpoint de prueba para verificar que la búsqueda semántica esté disponible
    """
    try:
        # Verificar dependencias básicas
        deps = {
            "controller": True,
            "sentence_transformers": False,
            "sklearn": False
        }
        
        try:
            import sentence_transformers
            deps["sentence_transformers"] = True
        except ImportError:
            pass
            
        try:
            import sklearn
            deps["sklearn"] = True
        except ImportError:
            pass
        
        return {
            "success": True,
            "message": "Endpoint de búsqueda semántica disponible",
            "dependencies": deps,
            "ready": deps["sentence_transformers"] and deps["sklearn"]
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error verificando estado: {str(e)}",
            "ready": False
        }


@router.post("/semantica", response_model=Dict[str, Any])
async def busqueda_semantica(
    busqueda: BusquedaSemantica,
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Búsqueda semántica usando embeddings vectoriales
    
    La búsqueda semántica encuentra documentos relacionados conceptualmente,
    no solo por palabras exactas.
    
    - **query**: Texto de búsqueda (mínimo 3 caracteres)
    - **carpeta_id**: Filtrar por carpeta específica (opcional)
    - **tomo_id**: Filtrar por tomo específico (opcional)
    - **similitud_minima**: Umbral de similitud (0.0 a 1.0, default: 0.5)
    - **limit**: Número máximo de resultados (default: 50)
    """
    try:
        # Validar parámetros básicos
        if len(busqueda.query) < 3:
            return {
                "success": False,
                "message": "La consulta debe tener al menos 3 caracteres",
                "total": 0,
                "resultados": []
            }
        
        if not (0.0 <= busqueda.similitud_minima <= 1.0):
            return {
                "success": False,
                "message": "La similitud mínima debe estar entre 0.0 y 1.0",
                "total": 0,
                "resultados": []
            }
        
        # Verificar si hay embeddings en la base de datos
        from app.models.tomo import ContenidoOCR
        
        contenidos_con_embeddings = db.query(ContenidoOCR).filter(
            ContenidoOCR.embeddings.isnot(None),
            ContenidoOCR.embeddings != {}
        ).limit(1).all()
        
        if not contenidos_con_embeddings:
            return {
                "success": False,
                "message": "No hay documentos con embeddings generados. Ejecute primero: python scripts/generar_embeddings.py",
                "total": 0,
                "resultados": [],
                "parametros": {
                    "query": busqueda.query,
                    "similitud_minima": busqueda.similitud_minima,
                    "tipo_busqueda": "semantica"
                }
            }
        
        # Intentar cargar el controlador de búsqueda semántica
        try:
            from app.controllers.busqueda_controller import busqueda_controller
            
            # Realizar búsqueda semántica
            resultado = busqueda_controller.busqueda_semantica(
                db=db,
                query=busqueda.query,
                carpeta_id=busqueda.carpeta_id,
                tomo_id=busqueda.tomo_id,
                similitud_minima=busqueda.similitud_minima,
                skip=skip,
                limit=busqueda.limit,
                current_user_id=current_user.id
            )
            
            # Registrar auditoría
            registrar_auditoria(
                db=db,
                usuario_id=current_user.id,
                accion="BUSQUEDA_SEMANTICA",
                tabla_afectada="contenido_ocr",
                valores_nuevos={
                    "query": busqueda.query,
                    "carpeta_id": busqueda.carpeta_id,
                    "tomo_id": busqueda.tomo_id,
                    "similitud_minima": busqueda.similitud_minima,
                    "total_resultados": resultado.get("total", 0),
                    "tipo_busqueda": "semantica"
                }
            )
            
            return resultado
            
        except ImportError as import_error:
            # Si faltan dependencias de ML, hacer búsqueda tradicional como fallback
            logger.warning(f"Dependencias de ML no disponibles: {import_error}")
            
            # Fallback a búsqueda tradicional
            from app.models.carpeta import Carpeta
            from app.models.permiso import PermisoCarpeta, PermisoSistema
            
            # Obtener carpetas permitidas para el usuario
            carpetas_permitidas = []
            permisos_sistema = db.query(PermisoSistema).filter(
                PermisoSistema.usuario_id == current_user.id
            ).first()

            es_admin = permisos_sistema and permisos_sistema.ver_auditoria

            if not es_admin:
                permisos_carpetas = db.query(PermisoCarpeta.carpeta_id).filter(
                    PermisoCarpeta.usuario_id == current_user.id
                ).all()
                carpetas_permitidas = [p[0] for p in permisos_carpetas]

            # Búsqueda tradicional como fallback
            base_query = db.query(ContenidoOCR).join(
                db.query(ContenidoOCR.tomo_id).join(
                    db.query(ContenidoOCR.tomo_id, ContenidoOCR.numero_pagina).subquery()
                ).subquery()
            )
            
            if carpetas_permitidas:
                from app.models.tomo import Tomo
                base_query = base_query.join(Tomo).join(Carpeta).filter(
                    Carpeta.id.in_(carpetas_permitidas)
                )
            
            if busqueda.carpeta_id:
                if carpetas_permitidas and busqueda.carpeta_id not in carpetas_permitidas:
                    return {
                        "success": False,
                        "message": "No tiene permisos para buscar en esta carpeta",
                        "total": 0,
                        "resultados": []
                    }
                base_query = base_query.filter(Carpeta.id == busqueda.carpeta_id)
            
            # Búsqueda por texto (fallback)
            resultados = base_query.filter(
                ContenidoOCR.texto_extraido.ilike(f"%{busqueda.query}%")
            ).limit(busqueda.limit).all()
            
            # Formatear resultados
            resultados_list = []
            for contenido in resultados:
                if hasattr(contenido, 'tomo') and hasattr(contenido.tomo, 'carpeta'):
                    tomo = contenido.tomo
                    carpeta = tomo.carpeta
                    
                    contexto = contenido.texto_extraido[:300] if contenido.texto_extraido else ""
                    
                    resultados_list.append({
                        "carpeta_id": carpeta.id,
                        "carpeta_nombre": carpeta.nombre_completo,
                        "tomo_id": tomo.id,
                        "numero_tomo": tomo.numero_tomo,
                        "nombre_archivo": tomo.nombre_archivo,
                        "pagina": contenido.numero_pagina,
                        "contexto": contexto,
                        "similitud": 0.8,  # Similitud fija para fallback
                        "confianza_porcentaje": float(contenido.confianza) if contenido.confianza else None,
                        "motor_usado": "fallback-tradicional"
                    })
            
            resultado_fallback = {
                "success": True,
                "message": "Búsqueda realizada con método tradicional (dependencias de IA no disponibles)",
                "total": len(resultados_list),
                "resultados": resultados_list,
                "parametros": {
                    "query": busqueda.query,
                    "similitud_minima": busqueda.similitud_minima,
                    "tipo_busqueda": "tradicional-fallback"
                }
            }
            
            # Registrar auditoría
            registrar_auditoria(
                db=db,
                usuario_id=current_user.id,
                accion="BUSQUEDA_SEMANTICA",
                tabla_afectada="contenido_ocr",
                valores_nuevos={
                    "query": busqueda.query,
                    "carpeta_id": busqueda.carpeta_id,
                    "tomo_id": busqueda.tomo_id,
                    "similitud_minima": busqueda.similitud_minima,
                    "total_resultados": len(resultados_list),
                    "tipo_busqueda": "tradicional-fallback"
                }
            )
            
            return resultado_fallback
        
    except Exception as e:
        logger.error(f"Error en búsqueda semántica: {str(e)}")
        return {
            "success": False,
            "message": f"Error interno: {str(e)}",
            "total": 0,
            "resultados": []
        }


@router.post("/actualizar-embeddings")
async def actualizar_embeddings(
    tomo_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    Actualizar embeddings para contenido OCR (solo administradores)
    
    Genera vectores embeddings para documentos que no los tienen.
    Este proceso puede tomar tiempo dependiendo de la cantidad de documentos.
    
    - **tomo_id**: ID del tomo específico (opcional, si no se especifica actualiza todos)
    """
    from app.controllers.busqueda_controller import busqueda_controller
    
    # Verificar permisos de administrador
    if not current_user.es_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden actualizar embeddings"
        )
    
    # Actualizar embeddings
    resultado = busqueda_controller.actualizar_embeddings_contenido(
        db=db,
        tomo_id=tomo_id
    )
    
    if not resultado["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=resultado["message"]
        )
    
    # Registrar auditoría
    registrar_auditoria(
        db=db,
        usuario_id=current_user.id,
        accion="ACTUALIZAR_EMBEDDINGS",
        tabla_afectada="contenido_ocr",
        valores_nuevos={
            "tomo_id": tomo_id,
            "total_actualizado": resultado["total_actualizado"]
        }
    )
    
    return {
        "message": "Embeddings actualizados correctamente",
        "total_actualizado": resultado["total_actualizado"]
    }
