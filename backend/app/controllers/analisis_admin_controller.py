"""
Controlador de administración para extracción OCR y análisis de documentos legales
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, Dict, List
from datetime import datetime, date
from pydantic import BaseModel
import logging
import asyncio
import json
import os

from app.database import get_db
from app.models.tomo import Tomo, ContenidoOCR
from app.models.carpeta import Carpeta
from app.models.usuario import Usuario
from app.models.documento_ocr import DocumentoOCR
from app.models.analisis_juridico import (
    Diligencia, PersonaIdentificada, DeclaracionPersona,
    LugarIdentificado, FechaImportante, AlertaMP, EstadisticaCarpeta
)
from app.middlewares.auth_middleware import get_current_user
from app.middlewares.permission_middleware import require_admin
from app.services.legal_ocr_service import legal_ocr_service
from app.services.legal_nlp_analysis_service import legal_nlp_service
from app.services.ocr_worker_pool import ocr_worker_pool
from app.utils.auditoria_utils import registrar_auditoria

router = APIRouter()
logger = logging.getLogger(__name__)


# Estado de procesamiento (en memoria para esta versión)
procesamiento_estado = {}

# Timestamp para health check - actualizado durante procesamiento largo
ultimo_heartbeat = {"timestamp": datetime.now()}


def es_fecha_plausible(fecha: date) -> bool:
    """
    Valida que la fecha esté en un rango razonable para expedientes de fiscalía.
    - Acepta fechas desde 1990 (expedientes históricos PGR/FGJ incluyen años 90-2000)
    - No acepta fechas futuras más allá de 1 año
    """
    ano_actual = datetime.now().year
    fecha_minima = date(1990, 1, 1)
    fecha_maxima = date(ano_actual + 1, 12, 31)
    return fecha_minima <= fecha <= fecha_maxima


@router.post("/admin/tomos/{tomo_id}/extract-ocr")
async def iniciar_extraccion_ocr(
    tomo_id: int,
    background_tasks: BackgroundTasks,
    expandir_abreviaturas: bool = True,
    pagina_inicio: Optional[int] = 1,
    pagina_fin: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Iniciar extracción OCR de un tomo (proceso en background)
    Solo para administradores
    """
    # Verificar rol de admin
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden iniciar extracción OCR"
        )
    
    # Verificar que el tomo existe
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(status_code=404, detail="Tomo no encontrado")

    # Verificar que el archivo existe
    if not tomo.ruta_archivo or not os.path.exists(tomo.ruta_archivo):
        # El PDF desapareció (reinicio de contenedor en HF Spaces limpió /tmp).
        # Resetear a 'pendiente' para que el usuario sepa que debe volver a subir el archivo.
        tomo.estado = "pendiente"
        db.commit()
        raise HTTPException(
            status_code=404,
            detail=(
                "El archivo PDF no está disponible en el servidor. "
                "Esto ocurre cuando el servidor se reinicia (los archivos en /tmp son temporales). "
                "Por favor vuelve a subir el PDF para poder procesarlo."
            )
        )
    
    # Inicializar estado de procesamiento con tiempo
    estado_key = f"ocr_{tomo_id}"
    inicio_timestamp = datetime.now()
    procesamiento_estado[estado_key] = {
        "estado": "iniciando",
        "progreso": 0,
        "pagina_actual": 0,
        "total_paginas": tomo.numero_paginas or 0,
        "inicio": inicio_timestamp.isoformat(),
        "inicio_timestamp": inicio_timestamp.timestamp(),
        "tiempo_transcurrido": 0,
        "tiempo_estimado": 0,
        "velocidad": 0,
        "personas_encontradas": 0,
        "errores": []
    }
    
    # Actualizar estado del tomo
    tomo.estado = 'procesando'
    db.commit()
    
    # Agregar tarea en background
    background_tasks.add_task(
        procesar_ocr_tomo,
        tomo_id,
        tomo.ruta_archivo,
        expandir_abreviaturas,
        pagina_inicio,
        pagina_fin,
        current_user.id
    )
    
    return {
        "success": True,
        "message": "Extracción OCR iniciada",
        "tomo_id": tomo_id,
    "estado": procesamiento_estado[estado_key]
    }


@router.get("/admin/tomos/{tomo_id}/ocr-status")
async def obtener_estado_ocr(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener estado actual de la extracción OCR"""
    # Verificar rol
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Obtener tomo
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(status_code=404, detail="Tomo no encontrado")
    
    # Obtener estado de procesamiento
    estado_key = f"ocr_{tomo_id}"
    estado = procesamiento_estado.get(estado_key, {
        "estado": tomo.estado,
        "progreso": 0,
        "mensaje": "No hay proceso activo"
    })
    
    # Contar documentos OCR generados
    total_documentos = db.query(DocumentoOCR).filter(
        DocumentoOCR.tomo_id == tomo_id,
        DocumentoOCR.activo == True
    ).count()
    
    return {
        "tomo_id": tomo_id,
        "estado_tomo": tomo.estado,
        "procesamiento": estado,
        "documentos_generados": total_documentos
    }


@router.get("/admin/estado-procesamiento")
async def obtener_todos_los_procesamientos(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener estado de todos los procesamientos activos
    Útil para monitoreo y detectar si el sistema se está "apendejeando"
    """
    from datetime import datetime, timedelta
    
    # Verificar rol
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Información de heartbeat
    tiempo_desde_heartbeat = (datetime.now() - ultimo_heartbeat["timestamp"]).total_seconds()
    
    # Filtrar solo procesos activos
    procesos_activos = {
        k: v for k, v in procesamiento_estado.items()
        if v.get("estado") in ["iniciando", "procesando"]
    }
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "sistema_activo": tiempo_desde_heartbeat < 120,
        "ultimo_heartbeat_segundos": int(tiempo_desde_heartbeat),
        "total_procesos": len(procesamiento_estado),
        "procesos_activos": len(procesos_activos),
        "procesos": procesos_activos,
        "nota": "Si ultimo_heartbeat_segundos > 120 y hay procesos activos, revisar logs"
    }


@router.post("/admin/tomos/{tomo_id}/analyze")
async def iniciar_analisis_juridico(
    tomo_id: int,
    background_tasks: BackgroundTasks,
    generar_alertas: bool = True,
    umbral_inactividad_dias: int = 180,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Iniciar análisis jurídico de un tomo (extraer diligencias, personas, lugares, etc.)
    """
    # Verificar rol
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Verificar tomo
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(status_code=404, detail="Tomo no encontrado")
    
    # Verificar que existe contenido OCR (tanto en la tabla nueva como en la original)
    hay_paginas_ocr = db.query(ContenidoOCR.id).filter(ContenidoOCR.tomo_id == tomo_id).first()
    documento_ocr = db.query(DocumentoOCR).filter(
        DocumentoOCR.tomo_id == tomo_id,
        DocumentoOCR.activo == True
    ).first()

    if not hay_paginas_ocr and not documento_ocr:
        raise HTTPException(
            status_code=400,
            detail="Debes ejecutar el OCR del tomo antes de lanzar el análisis jurídico"
        )
    
    # Inicializar estado
    estado_key = f"analisis_{tomo_id}"
    procesamiento_estado[estado_key] = {
        "estado": "iniciando",
        "progreso": 0,
        "fase": "preparación",
        "inicio": datetime.now().isoformat()
    }
    
    # Agregar tarea en background
    background_tasks.add_task(
        procesar_analisis_juridico,
        tomo_id,
        tomo.carpeta_id,
        generar_alertas,
        umbral_inactividad_dias,
        current_user.id
    )
    
    return {
        "success": True,
        "message": "Análisis jurídico iniciado",
        "tomo_id": tomo_id,
        "estado": procesamiento_estado[estado_key]
    }


@router.get("/admin/tomos/{tomo_id}/analysis-status")
async def obtener_estado_analisis(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener estado del análisis jurídico"""
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    estado_key = f"analisis_{tomo_id}"
    estado = procesamiento_estado.get(estado_key, {
        "estado": "no_iniciado",
        "mensaje": "No hay análisis activo"
    })
    
    # Contar elementos extraídos
    total_diligencias = db.query(Diligencia).filter(Diligencia.tomo_id == tomo_id).count()
    total_personas = db.query(PersonaIdentificada).filter(PersonaIdentificada.tomo_id == tomo_id).count()
    total_lugares = db.query(LugarIdentificado).filter(LugarIdentificado.tomo_id == tomo_id).count()
    total_fechas = db.query(FechaImportante).filter(FechaImportante.tomo_id == tomo_id).count()
    
    return {
        "tomo_id": tomo_id,
        "procesamiento": estado,
        "elementos_extraidos": {
            "diligencias": total_diligencias,
            "personas": total_personas,
            "lugares": total_lugares,
            "fechas": total_fechas
        }
    }


@router.get("/admin/documentos/{documento_id}")
async def obtener_documento_ocr_admin(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener documento OCR completo para edición"""
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    documento = db.query(DocumentoOCR).filter(
        DocumentoOCR.id == documento_id,
        DocumentoOCR.activo == True
    ).first()
    
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    return {
        "id": documento.id,
        "tomo_id": documento.tomo_id,
        "nombre": documento.nombre,
        "contenido": documento.contenido,
        "descripcion": documento.descripcion,
        "tipo": documento.tipo,
        "fecha_creacion": documento.fecha_creacion.isoformat(),
        "fecha_modificacion": documento.fecha_modificacion.isoformat() if documento.fecha_modificacion else None,
        "tomo": {
            "id": documento.tomo.id,
            "nombre_archivo": documento.tomo.nombre_archivo,
            "carpeta": documento.tomo.carpeta.nombre
        }
    }


@router.put("/admin/documentos/{documento_id}/correct")
async def corregir_documento_ocr(
    documento_id: int,
    contenido_corregido: str,
    notas_correccion: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Corregir texto extraído por OCR"""
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    documento = db.query(DocumentoOCR).filter(
        DocumentoOCR.id == documento_id,
        DocumentoOCR.activo == True
    ).first()
    
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Guardar contenido anterior como respaldo (opcional)
    contenido_anterior = documento.contenido
    
    # Actualizar documento
    documento.contenido = contenido_corregido
    documento.fecha_modificacion = datetime.now()
    documento.usuario_id = current_user.id
    
    if notas_correccion:
        if documento.descripcion:
            documento.descripcion += f"\n\nCorrección: {notas_correccion}"
        else:
            documento.descripcion = f"Corrección: {notas_correccion}"
    
    db.commit()
    db.refresh(documento)
    
    return {
        "success": True,
        "message": "Documento corregido exitosamente",
        "documento_id": documento.id,
        "caracteres_anteriores": len(contenido_anterior),
        "caracteres_nuevos": len(contenido_corregido)
    }


@router.get("/admin/carpetas/{carpeta_id}/estadisticas")
async def obtener_estadisticas_carpeta(
    carpeta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener estadísticas completas de una carpeta"""
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()
    if not carpeta:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    
    # Obtener o crear estadísticas
    stats = db.query(EstadisticaCarpeta).filter(
        EstadisticaCarpeta.carpeta_id == carpeta_id
    ).first()
    
    if not stats:
        # Generar estadísticas por primera vez
        stats = generar_estadisticas_carpeta(db, carpeta_id)
    
    return {
        "carpeta_id": carpeta_id,
        "carpeta_nombre": carpeta.nombre,
        "estadisticas": {
            "total_diligencias": stats.total_diligencias,
            "total_personas": stats.total_personas,
            "total_lugares": stats.total_lugares,
            "total_fechas": stats.total_fechas,
            "total_alertas_activas": stats.total_alertas_activas,
            "fecha_primera_actuacion": stats.fecha_primera_actuacion.isoformat() if stats.fecha_primera_actuacion else None,
            "fecha_ultima_actuacion": stats.fecha_ultima_actuacion.isoformat() if stats.fecha_ultima_actuacion else None,
            "dias_investigacion": stats.dias_totales_investigacion,
            "promedio_dias_entre_actuaciones": round(stats.promedio_dias_entre_actuaciones, 2),
            "total_declaraciones": stats.total_declaraciones,
            "total_pericias": stats.total_pericias,
            "porcentaje_verificado": round(stats.porcentaje_verificado, 2),
            "ultima_actualizacion": stats.ultima_actualizacion.isoformat()
        }
    }


@router.post("/admin/carpetas/{carpeta_id}/recalcular-estadisticas")
async def recalcular_estadisticas(
    carpeta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Recalcular estadísticas de una carpeta"""
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()
    if not carpeta:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    
    try:
        stats = generar_estadisticas_carpeta(db, carpeta_id, actualizar=True)
        
        return {
            "success": True,
            "message": "Estadísticas recalculadas",
            "estadisticas": {
                "total_diligencias": stats.total_diligencias,
                "total_personas": stats.total_personas,
                "total_alertas_activas": stats.total_alertas_activas
            }
        }
    except Exception as e:
        logger.error(f"Error recalculando estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# === Funciones auxiliares ===

async def procesar_ocr_tomo(
    tomo_id: int,
    ruta_pdf: str,
    expandir_abreviaturas: bool,
    pagina_inicio: int,
    pagina_fin: Optional[int],
    usuario_id: int
):
    """Procesar OCR de un tomo (función background)"""
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        logger.info(f"Iniciando procesamiento OCR del tomo {tomo_id}")
        
        estado_key = f"ocr_{tomo_id}"

        # Actualizar estado
        procesamiento_estado[estado_key]["estado"] = "procesando"
        inicio_timestamp = procesamiento_estado[estado_key].get("inicio_timestamp", datetime.now().timestamp())
        
        # Callback para actualizar progreso
        async def actualizar_progreso(pagina, total, porcentaje, texto=None):
            # Actualizar heartbeat para health check
            ultimo_heartbeat["timestamp"] = datetime.now()
            
            ahora = datetime.now().timestamp()
            tiempo_transcurrido = ahora - inicio_timestamp
            
            # Calcular velocidad (páginas por minuto)
            velocidad = (pagina / tiempo_transcurrido * 60) if tiempo_transcurrido > 0 else 0
            
            # Calcular tiempo estimado
            paginas_restantes = total - pagina
            tiempo_estimado = (paginas_restantes / velocidad * 60) if velocidad > 0 else 0
            
            procesamiento_estado[estado_key]["progreso"] = porcentaje
            procesamiento_estado[estado_key]["pagina_actual"] = pagina
            procesamiento_estado[estado_key]["total_paginas"] = total
            procesamiento_estado[estado_key]["tiempo_transcurrido"] = int(tiempo_transcurrido)
            procesamiento_estado[estado_key]["tiempo_estimado"] = int(tiempo_estimado)
            procesamiento_estado[estado_key]["velocidad"] = round(velocidad, 2)
            procesamiento_estado[estado_key]["mensaje"] = f"Procesando página {pagina} de {total}"
            
            logger.info(f"Tomo {tomo_id}: {porcentaje:.1f}% - Página {pagina}/{total} - Vel: {velocidad:.1f} pág/min")
        
        # Extraer texto
        resultado = await legal_ocr_service.extraer_texto_pdf(
            ruta_pdf,
            pagina_inicio,
            pagina_fin,
            actualizar_progreso
        )
        
        if resultado["success"]:
            # Consolidar todo el texto
            texto_completo = "\n\n".join([
                f"=== Página {pag} ===\n{texto}"
                for pag, texto in sorted(resultado["paginas"].items())
            ])
            
            # Crear documento OCR
            documento = DocumentoOCR(
                tomo_id=tomo_id,
                usuario_id=usuario_id,
                nombre=f"Extracción OCR Completa - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                contenido=texto_completo,
                descripcion=f"Método: {resultado['metodo']}, Total páginas: {resultado['total_paginas']}",
                tipo="ocr_complete",
                fecha_creacion=datetime.now(),
                activo=True
            )
            
            db.add(documento)
            db.flush()  # Para obtener el ID
            
            # ========================================
            # NUEVO: Procesar entidades legales automáticamente
            # ========================================
            logger.info(f"📊 Procesando entidades legales del tomo {tomo_id}...")
            
            try:
                from app.services.detector_contextual_service import detector_contextual
                from app.services.catalogo_fiscalias_service import catalogo_fiscalias
                
                # Procesar documento completo
                entidades = detector_contextual.procesar_documento_ocr(texto_completo)
                
                # Buscar fiscalías
                fiscalias_detectadas = []
                for linea in texto_completo.split('\n')[:50]:  # Primeras 50 líneas
                    if 'fiscal' in linea.lower():
                        resultado_fiscalia = catalogo_fiscalias.normalizar_fiscalia(linea)
                        if resultado_fiscalia['encontrado']:
                            fiscalias_detectadas.append(resultado_fiscalia)
                
                # Buscar delitos
                delitos_detectados = []
                for linea in texto_completo.split('\n')[:100]:  # Primeras 100 líneas
                    if any(palabra in linea.upper() for palabra in ['ABUSO', 'VIOLACION', 'HOMICIDIO', 'ROBO', 'FRAUDE', 'DELITO']):
                        resultado_delito = catalogo_fiscalias.normalizar_delito(linea)
                        if resultado_delito['encontrado']:
                            delitos_detectados.append(resultado_delito)
                
                # Guardar estadísticas en la descripción
                stats = f"\n\n📊 ENTIDADES DETECTADAS:\n"
                stats += f"• Personas: {len(entidades['personas'])}\n"
                stats += f"• Colonias: {len(entidades['colonias'])}\n"
                stats += f"• Fiscalías: {len(fiscalias_detectadas)}\n"
                stats += f"• Delitos: {len(delitos_detectados)}\n"
                
                if fiscalias_detectadas:
                    stats += f"\n🏛️  Fiscalía principal: {fiscalias_detectadas[0]['normalizado']}\n"
                
                if delitos_detectados:
                    stats += f"⚖️  Delito principal: {delitos_detectados[0]['normalizado']}\n"
                
                documento.descripcion += stats
                
                logger.info(f"✅ Entidades procesadas: {len(entidades['personas'])} personas, {len(entidades['colonias'])} colonias")
                
            except Exception as e:
                logger.warning(f"⚠️  Error procesando entidades (OCR continúa): {e}")
            
            # ========================================
            
            # Actualizar tomo
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
            if tomo:
                tomo.estado = 'completado'
                tomo.fecha_procesamiento = datetime.now()
            
            db.commit()
            
            # Actualizar estado final
            procesamiento_estado[estado_key]["estado"] = "completado"
            procesamiento_estado[estado_key]["progreso"] = 100
            procesamiento_estado[estado_key]["documento_id"] = documento.id
            procesamiento_estado[estado_key]["fin"] = datetime.now().isoformat()
            
            logger.info(f"OCR completado para tomo {tomo_id}")
        
        else:
            # Error en la extracción
            procesamiento_estado[estado_key]["estado"] = "error"
            procesamiento_estado[estado_key]["errores"] = resultado["errores"]
            procesamiento_estado[estado_key]["mensaje"] = \
                "; ".join(resultado["errores"]) if resultado["errores"] else "Error en extracción OCR"
            
            # Actualizar tomo
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
            if tomo:
                tomo.estado = 'error'
            
            db.commit()
            
            logger.error(f"Error en OCR del tomo {tomo_id}: {resultado['errores']}")
    
    except Exception as e:
        logger.error(f"Excepción en procesamiento OCR del tomo {tomo_id}: {str(e)}")
        procesamiento_estado[estado_key]["estado"] = "error"
        procesamiento_estado[estado_key]["errores"] = [str(e)]
        procesamiento_estado[estado_key]["mensaje"] = str(e)

        # Actualizar tomo
        try:
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
            if tomo:
                tomo.estado = 'error'
            db.commit()
        except Exception:
            pass
    
    finally:
        db.close()


async def procesar_analisis_juridico(
    tomo_id: int,
    carpeta_id: int,
    generar_alertas: bool,
    umbral_inactividad_dias: int,
    usuario_id: int
):
    """Procesar análisis jurídico de un tomo (función background)"""
    from app.database import SessionLocal
    db = SessionLocal()
    
    estado_key = f"analisis_{tomo_id}"
    
    try:
        logger.info(f"Iniciando análisis jurídico del tomo {tomo_id}")
        
        # Inicializar estado si no existe
        if estado_key not in procesamiento_estado:
            procesamiento_estado[estado_key] = {
                "estado": "procesando",
                "progreso": 0,
                "fase": "iniciando"
            }
        else:
            procesamiento_estado[estado_key]["estado"] = "procesando"
            procesamiento_estado[estado_key]["progreso"] = 0
            procesamiento_estado[estado_key]["fase"] = "iniciando"
            procesamiento_estado[estado_key]["inicio"] = datetime.now().isoformat()
            procesamiento_estado[estado_key]["mensaje"] = "Preparando análisis jurídico"
        
        # Obtener contenido OCR página por página
        from app.models.tomo import ContenidoOCR
        
        paginas_ocr = db.query(ContenidoOCR).filter(
            ContenidoOCR.tomo_id == tomo_id
        ).order_by(ContenidoOCR.numero_pagina).all()
        
        if not paginas_ocr:
            raise Exception(f"No se encontró contenido OCR para el tomo {tomo_id}")
        
        procesamiento_estado[estado_key]["total_paginas"] = len(paginas_ocr)
        procesamiento_estado[estado_key]["mensaje"] = f"Analizando {len(paginas_ocr)} páginas extraídas por OCR"
        
        logger.info(f"Texto OCR obtenido: {len(paginas_ocr)} páginas")
        
        # 🧹 LIMPIAR ANÁLISIS PREVIO (evitar duplicados al re-analizar)
        logger.info(f"🧹 Eliminando análisis previo del tomo {tomo_id}...")
        
        # Contar registros antes de eliminar
        count_diligencias = db.query(Diligencia).filter(Diligencia.tomo_id == tomo_id).count()
        count_personas = db.query(PersonaIdentificada).filter(PersonaIdentificada.tomo_id == tomo_id).count()
        count_lugares = db.query(LugarIdentificado).filter(LugarIdentificado.tomo_id == tomo_id).count()
        count_fechas = db.query(FechaImportante).filter(FechaImportante.tomo_id == tomo_id).count()
        
        logger.info(f"📊 Registros previos: {count_diligencias} diligencias, {count_personas} personas, {count_lugares} lugares, {count_fechas} fechas")
        
        # Eliminar análisis previo del TOMO específico
        db.query(Diligencia).filter(Diligencia.tomo_id == tomo_id).delete()
        db.query(PersonaIdentificada).filter(PersonaIdentificada.tomo_id == tomo_id).delete()
        db.query(LugarIdentificado).filter(LugarIdentificado.tomo_id == tomo_id).delete()
        db.query(FechaImportante).filter(FechaImportante.tomo_id == tomo_id).delete()
        
        # Las alertas son por CARPETA, no por tomo, así que las dejamos
        # (se regenerarán al final con los nuevos datos de todos los tomos)
        
        db.commit()
        logger.info(f"✅ Análisis previo eliminado correctamente")
        
        # Fase 1: Análisis página por página (para mantener número de página correcto)
        procesamiento_estado[estado_key]["fase"] = "analizando_texto"
        procesamiento_estado[estado_key]["progreso"] = 10
        procesamiento_estado[estado_key]["mensaje"] = "Analizando texto página por página con modelos NLP + spaCy NER"

        # ── Cargar spaCy NER (ya instalado, complementa extracción regex) ──
        try:
            from app.services.spacy_ner_service import spacy_ner_service
            _spacy_disponible = True
            logger.info("🧠 spaCy NER activado para complementar extracción regex")
        except Exception as _e_spacy:
            _spacy_disponible = False
            logger.warning(f"⚠️ spaCy NER no disponible: {_e_spacy}")

        # Analizar cada página individualmente
        resultado_analisis = {
            "diligencias": [],
            "personas": [],
            "lugares": [],
            "fechas": [],
            "oficios": [],
            "telefonos": [],
            "errores": []
        }

        # ── Ventana con overlap: cola de 300 chars de la página anterior ──
        # Captura entidades que quedaron cortadas entre dos páginas escaneadas
        _cola_pagina_anterior = ""

        for idx, pagina_ocr in enumerate(paginas_ocr):
            # Actualizar progreso
            progreso_actual = 10 + (idx / len(paginas_ocr)) * 15  # 10-25% del progreso total
            procesamiento_estado[estado_key]["progreso"] = int(progreso_actual)
            procesamiento_estado[estado_key]["mensaje"] = f"Analizando página {pagina_ocr.numero_pagina}/{len(paginas_ocr)}"

            texto_pagina = pagina_ocr.texto_extraido or ""

            # Texto con overlap de la página anterior (para entidades en bordes)
            texto_con_overlap = (_cola_pagina_anterior + " " + texto_pagina).strip()

            # ── Motor 1: regex / NLP existente ──────────────────────────
            resultado_pagina = legal_nlp_service.analizar_documento_completo(
                texto_con_overlap,
                numero_pagina=pagina_ocr.numero_pagina
            )

            resultado_analisis["diligencias"].extend(resultado_pagina["diligencias"])
            resultado_analisis["personas"].extend(resultado_pagina["personas"])
            resultado_analisis["lugares"].extend(resultado_pagina["lugares"])
            resultado_analisis["fechas"].extend(resultado_pagina["fechas"])
            resultado_analisis["oficios"].extend(resultado_pagina["oficios"])
            resultado_analisis["telefonos"].extend(resultado_pagina["telefonos"])

            # ── Motor 2: spaCy NER (captura lo que regex no detectó) ────
            if _spacy_disponible and texto_pagina.strip():
                try:
                    ner_resultado = spacy_ner_service.extraer_entidades(
                        texto_con_overlap,
                        numero_pagina=pagina_ocr.numero_pagina
                    )
                    resultado_analisis["personas"].extend(ner_resultado.get("personas", []))
                    resultado_analisis["lugares"].extend(ner_resultado.get("lugares", []))
                    resultado_analisis["fechas"].extend(ner_resultado.get("fechas", []))
                    logger.debug(
                        f"   🧠 spaCy pág {pagina_ocr.numero_pagina}: "
                        f"{len(ner_resultado.get('personas',[]))} personas, "
                        f"{len(ner_resultado.get('lugares',[]))} lugares, "
                        f"{len(ner_resultado.get('fechas',[]))} fechas"
                    )
                except Exception as _e_ner:
                    logger.warning(f"⚠️ Error spaCy NER pág {pagina_ocr.numero_pagina}: {_e_ner}")

            # Guardar los últimos 300 caracteres como overlap para la siguiente página
            _cola_pagina_anterior = texto_pagina[-300:] if len(texto_pagina) > 300 else texto_pagina

        logger.info(
            f"📄 Análisis completado (regex + spaCy NER): "
            f"{len(resultado_analisis['diligencias'])} diligencias, "
            f"{len(resultado_analisis['personas'])} personas (antes de filtro)"
        )
        
        # Importar servicios de limpieza
        from app.services.legal_autocorrector_service import legal_autocorrector
        from app.services.legal_entity_filter_service import legal_entity_filter
        
        # 🔍 FILTRAR entidades inválidas detectadas por error
        logger.info(f"🔍 Filtrando entidades inválidas...")
        logger.info(f"   Antes del filtro: {len(resultado_analisis['diligencias'])} diligencias, {len(resultado_analisis['personas'])} personas")
        
        diligencias_validas, diligencias_rechazadas = legal_entity_filter.filtrar_diligencias(resultado_analisis["diligencias"])
        personas_validas, personas_rechazadas = legal_entity_filter.filtrar_personas(resultado_analisis["personas"])
        
        logger.info(f"   Después del filtro: {len(diligencias_validas)} diligencias válidas ({len(diligencias_rechazadas)} rechazadas)")
        logger.info(f"   Después del filtro: {len(personas_validas)} personas válidas ({len(personas_rechazadas)} rechazadas)")
        
        # Reemplazar con las listas filtradas
        resultado_analisis["diligencias"] = diligencias_validas
        resultado_analisis["personas"] = personas_validas
        
        # Fase 2: Guardar diligencias
        procesamiento_estado[estado_key]["fase"] = "guardando_diligencias"
        procesamiento_estado[estado_key]["progreso"] = 30
        procesamiento_estado[estado_key]["mensaje"] = "Guardando diligencias detectadas"
        
        for idx, dil in enumerate(resultado_analisis["diligencias"]):
            # ✍️ AUTOCORRECCIÓN: Limpiar tipo de diligencia
            tipo_corregido = dil["tipo"]
            if tipo_corregido:
                tipo_corregido, _ = legal_autocorrector.corregir_termino_legal(tipo_corregido)
            
            # ✍️ AUTOCORRECCIÓN: Limpiar responsable
            responsable_corregido = dil.get("responsable")
            if responsable_corregido:
                resultado_resp = legal_autocorrector.corregir_texto_completo(responsable_corregido)
                responsable_corregido = resultado_resp['texto_corregido']
            
            diligencia = Diligencia(
                tomo_id=tomo_id,
                carpeta_id=carpeta_id,
                tipo_diligencia=tipo_corregido,  # ← Corregido
                fecha_diligencia_texto=dil.get("fecha"),
                responsable=responsable_corregido,  # ← Corregido
                numero_oficio=dil.get("oficio"),
                descripcion=dil.get("descripcion"),
                texto_contexto=dil.get("contexto"),
                numero_pagina=dil.get("pagina"),
                confianza=dil.get("confianza", 0.7),
                orden_cronologico=idx + 1,
                parrafo_estructurado=dil.get("parrafo_estructurado")  # ← NUEVO
            )
            
            # Parsear fecha si existe
            if dil.get("fecha"):
                try:
                    from dateutil import parser as date_parser
                    fecha_parseada = date_parser.parse(dil["fecha"]).date()
                    if es_fecha_plausible(fecha_parseada):
                        diligencia.fecha_diligencia = fecha_parseada
                    else:
                        logger.debug(
                            "Fecha descartada por no plausible en diligencia: %s", dil.get("fecha")
                        )
                except Exception as ex:
                    logger.debug("No se pudo parsear fecha de diligencia: %s", ex)
            
            db.add(diligencia)
        
        # Fase 3: Guardar personas
        procesamiento_estado[estado_key]["fase"] = "guardando_personas"
        procesamiento_estado[estado_key]["progreso"] = 50
        procesamiento_estado[estado_key]["mensaje"] = "Guardando personas identificadas"
        
        personas_guardadas = 0
        personas_rechazadas = 0
        
        for per in resultado_analisis["personas"]:
            nombre = per.get("nombre", "").strip()
            
            # 🔍 VALIDACIÓN: Verificar que sea un nombre de persona real
            es_valido, razon_invalido = legal_entity_filter.es_nombre_valido(nombre)
            
            if not es_valido:
                logger.debug(f"   ⚠️ Persona rechazada: '{nombre}' - Razón: {razon_invalido}")
                personas_rechazadas += 1
                continue  # No guardar esta persona
            
            # ✍️ AUTOCORRECCIÓN: Limpiar dirección
            direccion_corregida = per.get("direccion")
            if direccion_corregida:
                direccion_corregida, _, _ = legal_autocorrector.corregir_direccion(direccion_corregida)
            
            persona = PersonaIdentificada(
                tomo_id=tomo_id,
                carpeta_id=carpeta_id,
                nombre_completo=nombre,
                nombre_normalizado=nombre.upper(),
                rol=per.get("rol"),
                direccion=direccion_corregida,  # ← Corregida
                telefono=per.get("telefono"),
                texto_contexto=per.get("contexto"),
                primera_mencion_pagina=per.get("pagina"),
                total_menciones=1,
                confianza=per.get("confianza", 0.7)
            )
            db.add(persona)
            personas_guardadas += 1
        
        logger.info(f"   ✅ Personas guardadas: {personas_guardadas} de {len(resultado_analisis['personas'])} (rechazadas: {personas_rechazadas})")
        procesamiento_estado[estado_key]["mensaje"] = f"Personas válidas almacenadas: {personas_guardadas}"
        
        # Actualizar contador de personas en el estado de progreso
        ocr_estado_key = f"ocr_{tomo_id}"
        if ocr_estado_key in procesamiento_estado:
            procesamiento_estado[ocr_estado_key]["personas_encontradas"] = personas_guardadas
        
        # Fase 4: Guardar lugares
        procesamiento_estado[estado_key]["fase"] = "guardando_lugares"
        procesamiento_estado[estado_key]["progreso"] = 70
        procesamiento_estado[estado_key]["mensaje"] = "Guardando lugares relevantes"
        
        lugares_guardados = 0
        for lug in resultado_analisis["lugares"]:
            # ✍️ AUTOCORRECCIÓN: Limpiar dirección del lugar
            direccion_lugar_corregida = lug["direccion_completa"]
            if direccion_lugar_corregida:
                direccion_lugar_corregida, _, _ = legal_autocorrector.corregir_direccion(direccion_lugar_corregida)
                
                # 🔍 FILTRAR: Validar que sea una dirección real
                direccion_limpia, es_valida = legal_entity_filter.limpiar_direccion_lugar(direccion_lugar_corregida)
                
                if not es_valida:
                    logger.debug(f"   ⚠️ Lugar rechazado (no es dirección válida): {direccion_lugar_corregida}")
                    continue  # No guardar este lugar
                
                direccion_lugar_corregida = direccion_limpia
            
            lugar = LugarIdentificado(
                tomo_id=tomo_id,
                carpeta_id=carpeta_id,
                nombre_lugar=direccion_lugar_corregida,  # ← Corregido y validado
                direccion_completa=direccion_lugar_corregida,  # ← Corregido y validado
                tipo_lugar=lug.get("tipo"),
                contexto=lug.get("contexto"),
                numero_pagina=lug.get("pagina"),
                confianza=lug.get("confianza", 0.7)
            )
            db.add(lugar)
            lugares_guardados += 1
        
        logger.info(f"   ✅ Lugares guardados: {lugares_guardados} de {len(resultado_analisis['lugares'])}")
        procesamiento_estado[estado_key]["mensaje"] = f"Lugares almacenados: {lugares_guardados}"
        
        # Fase 5: Guardar fechas
        procesamiento_estado[estado_key]["fase"] = "guardando_fechas"
        procesamiento_estado[estado_key]["progreso"] = 85
        procesamiento_estado[estado_key]["mensaje"] = "Registrando fechas importantes"
        
        for fec in resultado_analisis["fechas"]:
            try:
                from dateutil import parser as date_parser
                fecha_obj = date_parser.parse(fec["fecha"]).date()
                if not es_fecha_plausible(fecha_obj):
                    logger.debug("Fecha importante descartada por no plausible: %s", fec.get("fecha"))
                    continue
                
                fecha_imp = FechaImportante(
                    tomo_id=tomo_id,
                    carpeta_id=carpeta_id,
                    fecha=fecha_obj,
                    fecha_texto_original=fec.get("fecha_texto"),
                    tipo_fecha=fec.get("tipo", "fecha_general"),
                    descripcion=fec.get("contexto", ""),
                    texto_contexto=fec.get("contexto"),
                    numero_pagina=fec.get("pagina"),
                    es_actuacion_mp='actuacion_mp' in fec.get("tipo", ""),
                    es_fecha_hechos='hechos' in fec.get("tipo", ""),
                    confianza=fec.get("confianza", 0.8)
                )
                db.add(fecha_imp)
            except:
                continue
        
        db.commit()
        
        # Fase 6: Generar alertas si se solicita
        if generar_alertas:
            procesamiento_estado[estado_key]["fase"] = "generando_alertas"
            procesamiento_estado[estado_key]["progreso"] = 95
            procesamiento_estado[estado_key]["mensaje"] = "Generando alertas de inactividad"
            
            # 🧹 Limpiar alertas previas de la carpeta (se regeneran con los nuevos datos)
            logger.info(f"🧹 Eliminando alertas previas de la carpeta {carpeta_id}...")
            db.query(AlertaMP).filter(AlertaMP.carpeta_id == carpeta_id).delete()
            db.commit()
            
            # Obtener todas las diligencias de la carpeta
            diligencias = db.query(Diligencia).filter(
                Diligencia.carpeta_id == carpeta_id,
                Diligencia.fecha_diligencia.isnot(None)
            ).order_by(Diligencia.fecha_diligencia).all()
            
            # Convertir a formato para análisis
            diligencias_data = [
                {
                    "fecha": d.fecha_diligencia.isoformat(),
                    "tipo": d.tipo_diligencia,
                    "id": d.id
                }
                for d in diligencias
            ]
            
            alertas = legal_nlp_service.generar_alertas_inactividad(
                diligencias_data,
                umbral_inactividad_dias
            )
            
            # Guardar alertas
            for alerta in alertas:
                alerta_mp = AlertaMP(
                    carpeta_id=carpeta_id,
                    tipo_alerta=alerta["tipo"],
                    prioridad=alerta["prioridad"],
                    titulo=f"Inactividad de {alerta['dias_inactividad']} días",
                    descripcion=alerta["descripcion"],
                    dias_inactividad=alerta["dias_inactividad"],
                    fecha_ultima_actuacion=date.fromisoformat(alerta["fecha_ultima_actuacion"]),
                    estado='activa'
                )
                db.add(alerta_mp)
            
            db.commit()
        
        # Fase 7: Actualizar estadísticas
        procesamiento_estado[estado_key]["fase"] = "actualizando_estadisticas"
        procesamiento_estado[estado_key]["progreso"] = 98
        procesamiento_estado[estado_key]["mensaje"] = "Actualizando estadísticas de carpeta"
        
        generar_estadisticas_carpeta(db, carpeta_id, actualizar=True)
        
        # Finalizado
        procesamiento_estado[estado_key]["estado"] = "completado"
        procesamiento_estado[estado_key]["progreso"] = 100
        procesamiento_estado[estado_key]["fin"] = datetime.now().isoformat()
        procesamiento_estado[estado_key]["mensaje"] = "Análisis jurídico completado"
        
        logger.info(f"Análisis jurídico completado para tomo {tomo_id}")
    
    except Exception as e:
        logger.error(f"Error en análisis jurídico del tomo {tomo_id}: {str(e)}")
        procesamiento_estado[estado_key]["estado"] = "error"
        procesamiento_estado[estado_key]["error"] = str(e)
        procesamiento_estado[estado_key]["mensaje"] = str(e)
    
    finally:
        db.close()


def generar_estadisticas_carpeta(
    db: Session,
    carpeta_id: int,
    actualizar: bool = False
) -> EstadisticaCarpeta:
    """Generar o actualizar estadísticas de una carpeta"""
    
    # Buscar estadísticas existentes
    stats = db.query(EstadisticaCarpeta).filter(
        EstadisticaCarpeta.carpeta_id == carpeta_id
    ).first()
    
    if not stats:
        stats = EstadisticaCarpeta(carpeta_id=carpeta_id)
        db.add(stats)
    
    # Contar elementos
    stats.total_diligencias = db.query(Diligencia).filter(
        Diligencia.carpeta_id == carpeta_id
    ).count()
    
    stats.total_personas = db.query(PersonaIdentificada).filter(
        PersonaIdentificada.carpeta_id == carpeta_id
    ).count()
    
    stats.total_lugares = db.query(LugarIdentificado).filter(
        LugarIdentificado.carpeta_id == carpeta_id
    ).count()
    
    stats.total_fechas = db.query(FechaImportante).filter(
        FechaImportante.carpeta_id == carpeta_id
    ).count()
    
    stats.total_alertas_activas = db.query(AlertaMP).filter(
        AlertaMP.carpeta_id == carpeta_id,
        AlertaMP.estado == 'activa'
    ).count()
    
    # Fechas de actuaciones
    diligencias = db.query(Diligencia).filter(
        Diligencia.carpeta_id == carpeta_id,
        Diligencia.fecha_diligencia.isnot(None)
    ).order_by(Diligencia.fecha_diligencia).all()
    
    if diligencias:
        stats.fecha_primera_actuacion = diligencias[0].fecha_diligencia
        stats.fecha_ultima_actuacion = diligencias[-1].fecha_diligencia
        
        if len(diligencias) > 1:
            delta = stats.fecha_ultima_actuacion - stats.fecha_primera_actuacion
            stats.dias_totales_investigacion = delta.days
            stats.promedio_dias_entre_actuaciones = delta.days / (len(diligencias) - 1)
    
    # Contar por tipo
    stats.total_declaraciones = db.query(Diligencia).filter(
        Diligencia.carpeta_id == carpeta_id,
        Diligencia.tipo_diligencia.ilike('%declaración%')
    ).count()
    
    stats.total_pericias = db.query(Diligencia).filter(
        Diligencia.carpeta_id == carpeta_id,
        Diligencia.tipo_diligencia.ilike('%pericial%')
    ).count()
    
    # Actualizar timestamp
    stats.ultima_actualizacion = datetime.now()
    
    db.commit()
    db.refresh(stats)
    
    return stats


import os


@router.get("/admin/carpetas-analisis")
async def listar_carpetas_analisis(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener lista de carpetas con información de análisis para admin
    """
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    try:
        # Obtener todas las carpetas con sus tomos
        carpetas = db.query(Carpeta).all()
        
        resultado = []
        for carpeta in carpetas:
            # Contar tomos
            total_tomos = db.query(Tomo).filter(Tomo.carpeta_id == carpeta.id).count()
            
            # Obtener estadísticas si existen
            stats = db.query(EstadisticaCarpeta).filter(
                EstadisticaCarpeta.carpeta_id == carpeta.id
            ).first()
            
            # Determinar estado del análisis
            estado_analisis = "pendiente"
            progreso = 0
            
            if stats and stats.total_diligencias > 0:
                estado_analisis = "completado"
                progreso = 100
            
            # Verificar si hay análisis en proceso
            estado_key = f"analisis_carpeta_{carpeta.id}"
            if estado_key in procesamiento_estado:
                estado_proc = procesamiento_estado[estado_key]
                if estado_proc["estado"] == "procesando":
                    estado_analisis = "procesando"
                    progreso = estado_proc.get("progreso", 0)
                elif estado_proc["estado"] == "error":
                    estado_analisis = "error"
            
            carpeta_info = {
                "id": carpeta.id,
                "nombre": carpeta.nombre,
                "numero_expediente": carpeta.numero_expediente,
                "descripcion": carpeta.descripcion,
                "total_tomos": total_tomos,
                "estado_analisis": estado_analisis,
                "progreso": progreso,
                "estadisticas": None
            }
            
            if stats:
                carpeta_info["estadisticas"] = {
                    "total_diligencias": stats.total_diligencias,
                    "total_personas": stats.total_personas,
                    "total_lugares": stats.total_lugares,
                    "total_fechas": stats.total_fechas,
                    "total_alertas_activas": stats.total_alertas_activas
                }
            
            resultado.append(carpeta_info)
        
        return resultado
    
    except Exception as e:
        logger.error(f"Error al listar carpetas para análisis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class AnalisisRequest(BaseModel):
    tomo_ids: Optional[List[int]] = None
    generar_alertas: bool = True
    umbral_inactividad_dias: int = 60

@router.post("/admin/carpetas/{carpeta_id}/iniciar-analisis")
async def iniciar_analisis_carpeta(
    carpeta_id: int,
    request: AnalisisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Iniciar análisis jurídico de tomos seleccionados o TODOS los tomos de una carpeta
    Si se envía tomo_ids, analiza solo esos tomos. Si no, analiza todos.
    """
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    # Verificar carpeta
    carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()
    if not carpeta:
        raise HTTPException(status_code=404, detail="Carpeta no encontrada")
    
    # Obtener tomos con OCR completado
    query = db.query(Tomo).filter(
        Tomo.carpeta_id == carpeta_id,
        Tomo.estado == 'completado'
    )
    
    # Si se especificaron tomos, filtrar solo esos
    if request.tomo_ids:
        query = query.filter(Tomo.id.in_(request.tomo_ids))
    
    tomos = query.all()
    
    if not tomos:
        raise HTTPException(
            status_code=400,
            detail="No hay tomos con OCR completado en esta carpeta"
        )
    
    # Inicializar estado individual de cada tomo para que el monitor reciba actualizaciones inmediatas
    for tomo in tomos:
        estado_tomo_key = f"analisis_{tomo.id}"
        procesamiento_estado[estado_tomo_key] = {
            "estado": "en_cola",
            "progreso": 0,
            "fase": "en_cola",
            "inicio": datetime.now().isoformat(),
            "mensaje": "Análisis jurídico en cola",
            "total_paginas": tomo.numero_paginas or 0,
            "errores": []
        }
    
    # Verificar que existe contenido OCR (tabla ContenidoOCR página por página)
    from app.models.tomo import ContenidoOCR
    
    paginas_ocr = db.query(ContenidoOCR).filter(
        ContenidoOCR.tomo_id.in_([t.id for t in tomos])
    ).count()
    
    if paginas_ocr == 0:
        raise HTTPException(
            status_code=400,
            detail="No hay contenido OCR disponible para analizar. Ejecuta primero la extracción OCR."
        )
    
    # Inicializar estado
    estado_key = f"analisis_carpeta_{carpeta_id}"
    procesamiento_estado[estado_key] = {
        "estado": "procesando",
        "progreso": 0,
        "fase": "preparación",
        "total_tomos": len(tomos),
        "tomos_procesados": 0,
        "inicio": datetime.now().isoformat(),
        "mensaje": "Preparando tomos para análisis jurídico"
    }
    
    # Agregar tarea en background
    background_tasks.add_task(
        procesar_analisis_carpeta_completa,
        carpeta_id,
        [t.id for t in tomos],
        request.generar_alertas,
        request.umbral_inactividad_dias,
        current_user.id
    )
    
    # Mensaje personalizado según selección
    if request.tomo_ids:
        mensaje = f"Análisis iniciado para {len(tomos)} tomo(s) seleccionado(s)"
    else:
        mensaje = f"Análisis iniciado para todos los tomos ({len(tomos)})"
    
    return {
        "success": True,
        "mensaje": mensaje,
        "carpeta_id": carpeta_id,
        "total_tomos": len(tomos),
        "tomos_seleccionados": request.tomo_ids,
        "estado": procesamiento_estado[estado_key]
    }


async def procesar_analisis_carpeta_completa(
    carpeta_id: int,
    tomo_ids: List[int],
    generar_alertas: bool,
    umbral_inactividad_dias: int,
    usuario_id: int
):
    """Procesar análisis de todos los tomos de una carpeta"""
    from app.database import SessionLocal
    db = SessionLocal()
    
    estado_key = f"analisis_carpeta_{carpeta_id}"
    total_tomos = len(tomo_ids)
    
    try:
        logger.info(f"Iniciando análisis de carpeta {carpeta_id} con {total_tomos} tomos")
        
        for idx, tomo_id in enumerate(tomo_ids):
            # Actualizar progreso
            tomos_procesados = idx
            progreso = int((tomos_procesados / total_tomos) * 100)
            
            procesamiento_estado[estado_key]["tomos_procesados"] = tomos_procesados
            procesamiento_estado[estado_key]["progreso"] = progreso
            procesamiento_estado[estado_key]["tomo_actual"] = tomo_id
            
            # Procesar este tomo
            await procesar_analisis_juridico(
                tomo_id,
                carpeta_id,
                False,  # No generar alertas por tomo individual
                umbral_inactividad_dias,
                usuario_id
            )
            
            logger.info(f"Tomo {tomo_id} procesado ({idx+1}/{total_tomos})")
        
        # Una vez procesados todos los tomos, generar alertas globales
        if generar_alertas:
            procesamiento_estado[estado_key]["fase"] = "generando_alertas"
            procesamiento_estado[estado_key]["progreso"] = 95
            
            # Obtener todas las diligencias
            diligencias = db.query(Diligencia).filter(
                Diligencia.carpeta_id == carpeta_id,
                Diligencia.fecha_diligencia.isnot(None)
            ).order_by(Diligencia.fecha_diligencia).all()
            
            if diligencias:
                diligencias_data = [
                    {
                        "fecha": d.fecha_diligencia.isoformat(),
                        "tipo": d.tipo_diligencia,
                        "id": d.id
                    }
                    for d in diligencias
                    if d.fecha_diligencia and es_fecha_plausible(d.fecha_diligencia)
                ]
                
                alertas = legal_nlp_service.generar_alertas_inactividad(
                    diligencias_data,
                    umbral_inactividad_dias
                )
                
                # Limpiar alertas anteriores
                db.query(AlertaMP).filter(
                    AlertaMP.carpeta_id == carpeta_id
                ).delete()
                
                # Guardar nuevas alertas
                for alerta in alertas:
                    alerta_mp = AlertaMP(
                        carpeta_id=carpeta_id,
                        tipo_alerta=alerta["tipo"],
                        prioridad=alerta["prioridad"],
                        titulo=f"Inactividad de {alerta['dias_inactividad']} días",
                        descripcion=alerta["descripcion"],
                        dias_inactividad=alerta["dias_inactividad"],
                        fecha_ultima_actuacion=date.fromisoformat(alerta["fecha_ultima_actuacion"]),
                        estado='activa'
                    )
                    db.add(alerta_mp)
                
                db.commit()
        
        # Actualizar estadísticas
        procesamiento_estado[estado_key]["fase"] = "actualizando_estadisticas"
        procesamiento_estado[estado_key]["progreso"] = 98
        
        generar_estadisticas_carpeta(db, carpeta_id, actualizar=True)
        
        # Finalizado
        procesamiento_estado[estado_key]["estado"] = "completado"
        procesamiento_estado[estado_key]["progreso"] = 100
        procesamiento_estado[estado_key]["tomos_procesados"] = total_tomos
        procesamiento_estado[estado_key]["fin"] = datetime.now().isoformat()
        
        logger.info(f"Análisis de carpeta {carpeta_id} completado exitosamente")
    
    except Exception as e:
        logger.error(f"Error en análisis de carpeta {carpeta_id}: {str(e)}")
        procesamiento_estado[estado_key]["estado"] = "error"
        procesamiento_estado[estado_key]["error"] = str(e)
    
    finally:
        db.close()


# ========================================
# NUEVO ENDPOINT: Reprocesar entidades legales
# ========================================

@router.post("/reprocesar-entidades/{documento_id}")
async def reprocesar_entidades_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Reprocesa un documento OCR existente para extraer entidades legales:
    - Personas
    - Colonias
    - Fiscalías
    - Delitos
    - Agencias MP
    
    Actualiza la descripción del documento con las estadísticas.
    """
    try:
        # Obtener documento
        documento = db.query(DocumentoOCR).filter(
            DocumentoOCR.id == documento_id,
            DocumentoOCR.activo == True
        ).first()
        
        if not documento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento {documento_id} no encontrado"
            )
        
        logger.info(f"📊 Reprocesando entidades del documento {documento_id}...")
        
        # Importar servicios
        from app.services.detector_contextual_service import detector_contextual
        from app.services.catalogo_fiscalias_service import catalogo_fiscalias
        
        texto_completo = documento.contenido
        
        # 1. Procesar personas y colonias
        entidades = detector_contextual.procesar_documento_ocr(texto_completo)
        
        # 2. Detectar fiscalías (primeras 50 líneas)
        fiscalias_detectadas = []
        for linea in texto_completo.split('\n')[:50]:
            if 'fiscal' in linea.lower():
                resultado = catalogo_fiscalias.normalizar_fiscalia(linea)
                if resultado['encontrado'] and resultado not in fiscalias_detectadas:
                    fiscalias_detectadas.append(resultado)
        
        # 3. Detectar delitos (primeras 100 líneas)
        delitos_detectados = []
        palabras_clave = ['ABUSO', 'VIOLACION', 'HOMICIDIO', 'ROBO', 'FRAUDE', 'DELITO', 
                          'SECUESTRO', 'EXTORSION', 'FEMINICIDIO', 'HOSTIGAMIENTO']
        
        for linea in texto_completo.split('\n')[:100]:
            if any(palabra in linea.upper() for palabra in palabras_clave):
                resultado = catalogo_fiscalias.normalizar_delito(linea)
                if resultado['encontrado'] and resultado not in delitos_detectados:
                    delitos_detectados.append(resultado)
        
        # 4. Detectar agencias MP
        agencias_detectadas = []
        import re
        patron_agencia = r'(?:FDS|AO|BJ|COY|IZT|CUAU|GAM|MH|VC|XOC|TLALP|TAH|CUAJ|MILAL|MCONTR|AZC|IZTAP)-\d+'
        
        for linea in texto_completo.split('\n')[:50]:
            matches = re.findall(patron_agencia, linea)
            for codigo in matches:
                resultado = catalogo_fiscalias.normalizar_agencia_mp(codigo)
                if resultado['encontrado'] and resultado not in agencias_detectadas:
                    agencias_detectadas.append(resultado)
        
        # 5. Actualizar descripción del documento
        descripcion_base = documento.descripcion.split('\n\n📊 ENTIDADES DETECTADAS:')[0]
        
        stats = f"\n\n📊 ENTIDADES DETECTADAS (Reprocesado {datetime.now().strftime('%Y-%m-%d %H:%M')}):\n"
        stats += f"• Personas: {len(entidades['personas'])}\n"
        stats += f"• Colonias: {len(entidades['colonias'])}\n"
        stats += f"• Fiscalías: {len(fiscalias_detectadas)}\n"
        stats += f"• Delitos: {len(delitos_detectados)}\n"
        stats += f"• Agencias MP: {len(agencias_detectadas)}\n"
        stats += f"• Ambiguos: {len(entidades['ambiguos'])}\n"
        
        if fiscalias_detectadas:
            stats += f"\n🏛️  Fiscalía: {fiscalias_detectadas[0]['normalizado'][:60]}...\n"
        
        if delitos_detectados:
            stats += f"⚖️  Delito: {delitos_detectados[0]['normalizado']}\n"
            if delitos_detectados[0].get('agravante_detectado'):
                stats += f"   Agravante: {delitos_detectados[0]['agravante_tipo']}\n"
        
        if agencias_detectadas:
            stats += f"🏢 Agencia: {agencias_detectadas[0]['normalizado']}\n"
        
        # Agregar ejemplos
        if entidades['personas']:
            stats += f"\n👤 Ejemplos de personas:\n"
            for persona in entidades['personas'][:3]:
                stats += f"   • {persona['texto']} (certeza: {persona['certeza']:.0f}%)\n"
        
        if entidades['colonias']:
            stats += f"\n🏘️  Ejemplos de colonias:\n"
            for colonia in entidades['colonias'][:3]:
                stats += f"   • {colonia['texto']} (certeza: {colonia['certeza']:.0f}%)\n"
        
        documento.descripcion = descripcion_base + stats
        db.commit()
        
        logger.info(f"✅ Documento {documento_id} reprocesado exitosamente")
        
        return {
            "success": True,
            "documento_id": documento_id,
            "entidades": {
                "personas": len(entidades['personas']),
                "colonias": len(entidades['colonias']),
                "fiscalias": len(fiscalias_detectadas),
                "delitos": len(delitos_detectados),
                "agencias_mp": len(agencias_detectadas),
                "ambiguos": len(entidades['ambiguos'])
            },
            "detalle": {
                "personas": entidades['personas'][:5],
                "colonias": entidades['colonias'][:5],
                "fiscalias": fiscalias_detectadas,
                "delitos": delitos_detectados,
                "agencias_mp": agencias_detectadas
            },
            "mensaje": "Entidades reprocesadas y guardadas en la descripción del documento"
        }
    
    except Exception as e:
        logger.error(f"❌ Error reprocesando entidades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reprocesando entidades: {str(e)}"
        )


@router.post("/reprocesar-tomo-completo/{tomo_id}")
async def reprocesar_tomo_completo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Reprocesa todos los documentos OCR de un tomo para extraer entidades legales.
    """
    try:
        # Obtener todos los documentos del tomo
        documentos = db.query(DocumentoOCR).filter(
            DocumentoOCR.tomo_id == tomo_id,
            DocumentoOCR.activo == True
        ).all()
        
        if not documentos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontraron documentos OCR para el tomo {tomo_id}"
            )
        
        logger.info(f"📊 Reprocesando {len(documentos)} documentos del tomo {tomo_id}...")
        
        resultados = []
        
        for documento in documentos:
            try:
                # Reprocesar cada documento
                resultado = await reprocesar_entidades_documento(
                    documento.id,
                    db,
                    current_user
                )
                resultados.append({
                    "documento_id": documento.id,
                    "success": True,
                    "entidades": resultado["entidades"]
                })
            except Exception as e:
                logger.error(f"❌ Error en documento {documento.id}: {e}")
                resultados.append({
                    "documento_id": documento.id,
                    "success": False,
                    "error": str(e)
                })
        
        exitosos = sum(1 for r in resultados if r["success"])
        
        return {
            "success": True,
            "tomo_id": tomo_id,
            "total_documentos": len(documentos),
            "procesados_exitosamente": exitosos,
            "resultados": resultados,
            "mensaje": f"Reprocesados {exitosos}/{len(documentos)} documentos del tomo {tomo_id}"
        }
    
    except Exception as e:
        logger.error(f"❌ Error reprocesando tomo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reprocesando tomo: {str(e)}"
        )


# ==========================================
# ENDPOINTS CON MULTITHREADING (WORKER POOL)
# ==========================================

@router.post("/admin/tomos/{tomo_id}/procesar-ocr-completo")
async def procesar_ocr_completo_multithreading(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Procesar OCR completo de un tomo usando worker pool (MULTITHREADING)
    
    NO BLOQUEA el servidor - usa ThreadPoolExecutor para verdadero paralelismo.
    Múltiples usuarios pueden procesar tomos simultáneamente.
    
    Args:
        tomo_id: ID del tomo a procesar
        
    Returns:
        Información de la tarea iniciada
        
    Raises:
        404: Tomo no encontrado
        409: Tomo ya está siendo procesado
        503: Todos los workers están ocupados
    """
    # Verificar rol de admin
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden iniciar extracción OCR"
        )
    
    # Validar que el tomo existe
    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
    if not tomo:
        raise HTTPException(status_code=404, detail="Tomo no encontrado")
    
    # Verificar que el archivo existe
    if not tomo.ruta_archivo or not os.path.exists(tomo.ruta_archivo):
        tomo.estado = "pendiente"
        db.commit()
        raise HTTPException(
            status_code=404,
            detail=(
                "El archivo PDF no está disponible en el servidor. "
                "Esto ocurre cuando el servidor se reinicia (los archivos en /tmp son temporales). "
                "Por favor vuelve a subir el PDF para poder procesarlo."
            )
        )

    # Verificar si ya está en proceso
    task_id = f"ocr_tomo_{tomo_id}"
    if ocr_worker_pool.is_task_active(task_id):
        raise HTTPException(
            status_code=409,
            detail="Este tomo ya está siendo procesado. Por favor espera a que termine."
        )
    
    # Verificar disponibilidad de workers
    if ocr_worker_pool.get_available_workers() == 0:
        raise HTTPException(
            status_code=503,
            detail=f"Todos los workers están ocupados procesando otros tomos. Intenta más tarde. (Máximo: {ocr_worker_pool.max_workers} tomos simultáneos)"
        )
    
    # Construir URL de BD usando variables de entorno (para workers en threads)
    # Usar los nombres de variables que están en docker-compose.yml
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "sistema_ocr")
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    logger.info(f"🔗 DB URL para worker: postgresql://{db_user}:****@{db_host}:{db_port}/{db_name}")
    
    # Enviar tarea al worker pool (NO BLOQUEANTE)
    try:
        ocr_worker_pool.submit_ocr_task(
            task_id=task_id,
            ocr_function=_procesar_ocr_tomo_sync,
            tomo_id=tomo_id,
            ruta_archivo=tomo.ruta_archivo,
            db_url=db_url,
            usuario_id=current_user.id
        )
        
        # Actualizar estado del tomo
        tomo.estado = 'procesando'
        db.commit()
        
        logger.info(f"✅ OCR de tomo {tomo_id} enviado al worker pool")
        
        return {
            "success": True,
            "mensaje": f"Procesamiento OCR iniciado para tomo {tomo_id}",
            "tomo_id": tomo_id,
            "task_id": task_id,
            "workers_disponibles": ocr_worker_pool.get_available_workers(),
            "workers_totales": ocr_worker_pool.max_workers,
            "info": "El procesamiento se ejecuta en segundo plano. Usa /api/progress/ocr/{tomo_id} para monitorear."
        }
        
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error enviando tarea al worker pool: {str(e)}")
        raise HTTPException(status_code=500, detail="Error iniciando procesamiento")


@router.get("/admin/workers/estado")
async def obtener_estado_workers(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener estado del worker pool
    
    Muestra cuántos workers están ocupados y cuántos disponibles,
    así como información de las tareas activas.
    
    Returns:
        Estado completo del worker pool
    """
    # Verificar rol de admin
    if current_user.rol.nombre not in ["admin", "Admin", "Administrador", "SuperAdmin"]:
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden ver el estado de los workers"
        )
    
    tareas_activas = ocr_worker_pool.get_active_tasks()
    
    return {
        "workers_totales": ocr_worker_pool.max_workers,
        "workers_disponibles": ocr_worker_pool.get_available_workers(),
        "workers_ocupados": len(tareas_activas),
        "tareas_activas": [
            {
                "task_id": task_id,
                "tomo_id": int(task_id.split("_")[-1]) if "_" in task_id else None,
                "inicio": info["inicio"].isoformat(),
                "estado": info["estado"],
                "thread": info["thread_id"],
                "tiempo_transcurrido_segundos": int((datetime.now() - info["inicio"]).total_seconds())
            }
            for task_id, info in tareas_activas.items()
        ],
        "info": f"Puedes procesar hasta {ocr_worker_pool.max_workers} tomos simultáneamente"
    }


def _procesar_ocr_tomo_sync(tomo_id: int, ruta_archivo: str, db_url: str, usuario_id: int):
    """
    Función SÍNCRONA que procesa el OCR en un thread separado
    
    Crea su propia sesión de BD para evitar conflictos entre threads.
    Esta función se ejecuta en un worker del ThreadPoolExecutor.
    
    Args:
        tomo_id: ID del tomo a procesar
        ruta_archivo: Ruta al archivo PDF
        db_url: URL de conexión a la base de datos
        usuario_id: ID del usuario que inició el proceso
        
    Returns:
        Resultado del procesamiento OCR
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os
    
    # Crear engine y sesión propios para este thread
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Obtener tomo
        tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
        if not tomo:
            raise ValueError(f"Tomo {tomo_id} no encontrado")
        
        logger.info(f"🚀 Iniciando procesamiento OCR COMPLETO (Thread): {ruta_archivo}")
        logger.info(f"📄 Total de páginas: {tomo.numero_paginas}")
        
        # Inicializar estado de procesamiento (alias para SSE y worker pool)
        task_id = f"ocr_tomo_{tomo_id}"
        estado_key = f"ocr_{tomo_id}"
        inicio_timestamp = datetime.now()
        
        procesamiento_estado[estado_key] = {
            "tomo_id": tomo_id,
            "task_id": task_id,
            "estado": "procesando",
            "progreso": 0,
            "pagina_actual": 0,
            "total_paginas": tomo.numero_paginas or 0,
            "inicio": inicio_timestamp.isoformat(),
            "inicio_timestamp": inicio_timestamp.timestamp(),
            "tiempo_transcurrido": 0,
            "tiempo_estimado": 0,
            "velocidad": 0,
            "personas_encontradas": 0,
            "errores": []
        }
        
        # ── Detectar páginas ya procesadas para poder reanudar ───────────────
        paginas_existentes = {
            p.numero_pagina
            for p in db.query(ContenidoOCR.numero_pagina).filter(
                ContenidoOCR.tomo_id == tomo_id,
                ContenidoOCR.texto_extraido.isnot(None)
            ).all()
        }
        total_paginas_tomo = tomo.numero_paginas or 0
        primera_pagina_faltante = 1
        if paginas_existentes and total_paginas_tomo:
            todas_esperadas = set(range(1, total_paginas_tomo + 1))
            faltantes = sorted(todas_esperadas - paginas_existentes)
            if faltantes:
                primera_pagina_faltante = faltantes[0]
                logger.info(
                    f"⏭️ Reanudando OCR del tomo {tomo_id} desde página {primera_pagina_faltante} "
                    f"({len(paginas_existentes)} páginas ya guardadas)"
                )
            else:
                logger.info(f"✅ OCR del tomo {tomo_id} ya completo, saltando extracción")
                primera_pagina_faltante = None  # Marca para saltar
        
        # Callback para actualizar progreso y guardar checkpoint en BD
        def actualizar_progreso_sync(pagina, total, porcentaje, texto=None):
            global ultimo_heartbeat
            ultimo_heartbeat["timestamp"] = datetime.now()

            # Calcular tiempos
            ahora = datetime.now()
            tiempo_transcurrido = (ahora - inicio_timestamp).total_seconds()
            velocidad = pagina / tiempo_transcurrido if tiempo_transcurrido > 0 else 0
            tiempo_estimado = ((total - pagina) / velocidad) if velocidad > 0 else 0

            procesamiento_estado[estado_key].update({
                "estado": "procesando",
                "progreso": porcentaje,
                "pagina_actual": pagina,
                "total_paginas": total,
                "tiempo_transcurrido": int(tiempo_transcurrido),
                "tiempo_estimado": int(tiempo_estimado),
                "velocidad": round(velocidad, 2)
            })

            # ━ Checkpoint: guardar página en BD inmediatamente ━━━━━━━━━━━━━
            if texto is not None:
                try:
                    existing = db.query(ContenidoOCR).filter(
                        and_(
                            ContenidoOCR.tomo_id == tomo_id,
                            ContenidoOCR.numero_pagina == pagina
                        )
                    ).first()
                    if existing:
                        existing.texto_extraido = texto
                        existing.updated_at = datetime.now()
                    else:
                        db.add(ContenidoOCR(
                            tomo_id=tomo_id,
                            numero_pagina=pagina,
                            texto_extraido=texto
                        ))
                    db.commit()
                except Exception as e_chk:
                    logger.warning(f"⚠️ Checkpoint pág {pagina} falló: {e_chk}")
                    db.rollback()

            if pagina % 10 == 0:
                logger.info(f"📄 OCR Tomo {tomo_id}: {pagina}/{total} ({porcentaje}%) - {round(velocidad, 2)} pág/s")

        # Procesar con legal_ocr_service usando asyncio.run() para ejecutar función async
        logger.info(f"🔄 Ejecutando extracción OCR (async en thread)...")

        import asyncio
        if primera_pagina_faltante is None:
            # Ya estaba completo, construir resultado dummy a partir de BD
            paginas_bd = db.query(ContenidoOCR).filter(
                ContenidoOCR.tomo_id == tomo_id
            ).order_by(ContenidoOCR.numero_pagina).all()
            resultado = {
                "success": True,
                "paginas": {p.numero_pagina: p.texto_extraido or "" for p in paginas_bd},
                "total_paginas": len(paginas_bd),
                "metodo": "cache",
                "errores": []
            }
        else:
            resultado = asyncio.run(legal_ocr_service.extraer_texto_pdf(
                ruta_pdf=ruta_archivo,
                pagina_inicio=primera_pagina_faltante,
                pagina_fin=None,
                callback_progreso=actualizar_progreso_sync
            ))
        
        logger.info(f"💾 Guardando resultados OCR del tomo {tomo_id} en BD...")
        
        # Guardar páginas procesadas
        # resultado["paginas"] es un dict: {numero_pagina: texto, ...}
        personas_encontradas = 0  # Conteo real se llena durante el análisis jurídico posterior
        for numero_pagina, texto in resultado.get("paginas", {}).items():
            contenido = db.query(ContenidoOCR).filter(
                and_(
                    ContenidoOCR.tomo_id == tomo_id,
                    ContenidoOCR.numero_pagina == numero_pagina
                )
            ).first()

            if contenido:
                contenido.texto_extraido = texto
                contenido.updated_at = datetime.now()
            else:
                contenido = ContenidoOCR(
                    tomo_id=tomo_id,
                    numero_pagina=numero_pagina,
                    texto_extraido=texto
                )
                db.add(contenido)
        
        # Commit de todas las páginas
        db.commit()
        
        # Actualizar estado del tomo
        tomo.estado = 'completado'
        tomo.fecha_procesamiento = datetime.now()
        db.commit()
        
        # Actualizar estado final
        procesamiento_estado[estado_key].update({
            "estado": "completado",
            "progreso": 100,
            "fin": datetime.now().isoformat(),
            "personas_encontradas": personas_encontradas,
            "resultado": {
                "paginas_procesadas": len(resultado.get("paginas", [])),
                "texto_total_caracteres": len(resultado.get("texto_completo", "")),
                "personas_encontradas": personas_encontradas
            }
        })
        
        logger.info(f"✅ OCR Tomo {tomo_id} completado exitosamente - {personas_encontradas} personas encontradas")
        
        # 📝 Registrar auditoría del procesamiento OCR
        try:
            tiempo_total = (datetime.now() - inicio_timestamp).total_seconds()
            registrar_auditoria(
                usuario_id=usuario_id,
                accion="PROCESAR_OCR",
                request=None,  # No tenemos Request en worker thread
                tabla_afectada="tomos",
                registro_id=tomo_id,
                valores_nuevos={
                    "nombre_archivo": tomo.nombre_archivo,
                    "numero_paginas": tomo.numero_paginas,
                    "paginas_procesadas": len(resultado.get("paginas", [])),
                    "personas_encontradas": personas_encontradas,
                    "tiempo_total": round(tiempo_total, 2),
                    "velocidad": round(len(resultado.get("paginas", [])) / tiempo_total if tiempo_total > 0 else 0, 2),
                    "tipo_proceso": "ocr_worker_pool"
                }
            )
            logger.info(f"📝 Auditoría registrada para OCR del tomo {tomo_id}")
        except Exception as e:
            logger.error(f"Error registrando auditoría de OCR: {e}")
        
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Error procesando OCR tomo {tomo_id}: {str(e)}", exc_info=True)
        
        # Actualizar estado de error
        estado_key = f"ocr_{tomo_id}"
        if estado_key in procesamiento_estado:
            procesamiento_estado[estado_key].update({
                "estado": "error",
                "errores": [str(e)],
                "error": str(e),
                "mensaje": str(e),
                "fin": datetime.now().isoformat()
            })
        
        # Actualizar tomo en BD
        try:
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
            if tomo:
                tomo.estado = 'error'
                db.commit()
        except:
            pass
        
        raise
        
    finally:
        # Cerrar sesión de BD
        db.close()
        engine.dispose()

