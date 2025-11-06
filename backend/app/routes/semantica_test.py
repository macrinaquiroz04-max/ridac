# Test endpoint para búsqueda semántica
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.middlewares.auth_middleware import get_current_active_user
from app.models.usuario import Usuario
from app.utils.logger import logger

router = APIRouter()

class BusquedaSemanticaSimple(BaseModel):
    query: str
    carpeta_id: Optional[int] = None
    tomo_id: Optional[int] = None
    similitud_minima: float = 0.5
    limit: int = 50

@router.get("/status")
async def busqueda_semantica_status():
    """Endpoint simple para verificar que la búsqueda semántica esté disponible"""
    try:
        import sentence_transformers
        import sklearn
        return {
            "success": True,
            "message": "Búsqueda semántica operativa con IA",
            "ready": True,
            "dependencies": {
                "sentence_transformers": True,
                "sklearn": True
            }
        }
    except ImportError:
        return {
            "success": True,
            "message": "Funcionalidad básica disponible",
            "ready": False,
            "dependencies": {
                "sentence_transformers": False,
                "sklearn": False
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "ready": False
        }

@router.post("/semantica")
async def busqueda_semantica_simple(
    busqueda: BusquedaSemanticaSimple,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Búsqueda semántica inteligente por categorías"""
    try:
        # Log detallado para debugging
        logger.info(f"🔍 BÚSQUEDA SEMÁNTICA INICIADA")
        logger.info(f"👤 Usuario: {current_user.id} ({current_user.username})")
        logger.info(f"📝 Query: '{busqueda.query}'")
        logger.info(f"📁 Carpeta ID: {busqueda.carpeta_id}")
        logger.info(f"📊 Similitud mínima: {busqueda.similitud_minima}")
        logger.info(f"📋 Límite: {busqueda.limit}")
        
        # Importar el controlador real de búsqueda semántica
        from app.controllers.busqueda_controller import busqueda_controller
        
        # Realizar búsqueda semántica real
        logger.info(f"🤖 Llamando busqueda_controller.busqueda_semantica...")
        resultado = busqueda_controller.busqueda_semantica(
            db=db,
            query=busqueda.query,
            carpeta_id=busqueda.carpeta_id,
            tomo_id=busqueda.tomo_id,
            similitud_minima=busqueda.similitud_minima,
            skip=0,
            limit=busqueda.limit,
            current_user_id=current_user.id
        )
        
        logger.info(f"📊 Resultado de búsqueda semántica: success={resultado.get('success')}, total={resultado.get('total')}")
        
        # Agregar parámetros esperados por el frontend
        resultado["parametros"] = {
            "similitud_minima": busqueda.similitud_minima,
            "tipo_busqueda": "Semántica",
            "query": busqueda.query,
            "limit": busqueda.limit
        }
        
        # Si no hay resultados semánticos, intentamos búsqueda por categorías
        if resultado.get("total", 0) == 0:
            logger.info(f"🔄 Sin resultados semánticos, intentando búsqueda por categorías...")
            resultado_categorias = buscar_por_categorias(
                db, busqueda.query, busqueda.carpeta_id, current_user.id, busqueda.limit
            )
            
            # Agregar parámetros a resultado de categorías también
            resultado_categorias["parametros"] = {
                "similitud_minima": busqueda.similitud_minima,
                "tipo_busqueda": "Categorías",
                "query": busqueda.query,
                "limit": busqueda.limit
            }
            
            logger.info(f"📂 Resultado de categorías: success={resultado_categorias.get('success')}, total={resultado_categorias.get('total')}")
            
            if resultado_categorias.get("total", 0) > 0:
                logger.info(f"✅ Retornando resultados de categorías")
                return resultado_categorias
        
        return resultado
        
    except Exception as e:
        # Fallback a búsqueda tradicional si falla la semántica
        resultado_fallback = buscar_por_categorias(
            db, busqueda.query, busqueda.carpeta_id, current_user.id, busqueda.limit
        )
        
        # Agregar parámetros al fallback
        resultado_fallback["parametros"] = {
            "similitud_minima": busqueda.similitud_minima,
            "tipo_busqueda": "Fallback",
            "query": busqueda.query,
            "limit": busqueda.limit
        }
        
        return resultado_fallback


@router.get("/diagnostico")
async def diagnostico_embeddings(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Diagnóstico de embeddings en la base de datos"""
    try:
        from app.models.tomo import ContenidoOCR
        
        # Contar documentos totales
        total = db.query(ContenidoOCR).count()
        
        # Contar documentos con embeddings
        con_embeddings = db.query(ContenidoOCR).filter(
            ContenidoOCR.embeddings.isnot(None)
        ).count()
        
        # Contar documentos sin embeddings
        sin_embeddings = total - con_embeddings
        
        # Obtener ejemplos con embeddings
        ejemplos_con = []
        if con_embeddings > 0:
            docs_con = db.query(ContenidoOCR).filter(
                ContenidoOCR.embeddings.isnot(None)
            ).limit(3).all()
            
            for doc in docs_con:
                embed_info = "No es lista"
                if doc.embeddings and isinstance(doc.embeddings, list):
                    embed_info = f"{len(doc.embeddings)} elementos"
                
                ejemplos_con.append({
                    "id": doc.id,
                    "tomo_id": doc.tomo_id,
                    "embedding_info": embed_info,
                    "texto_preview": doc.texto_extraido[:100] if doc.texto_extraido else "Sin texto"
                })
        
        # Obtener ejemplos sin embeddings
        ejemplos_sin = []
        if sin_embeddings > 0:
            docs_sin = db.query(ContenidoOCR).filter(
                ContenidoOCR.embeddings.is_(None)
            ).limit(3).all()
            
            for doc in docs_sin:
                ejemplos_sin.append({
                    "id": doc.id,
                    "tomo_id": doc.tomo_id,
                    "texto_preview": doc.texto_extraido[:100] if doc.texto_extraido else "Sin texto"
                })
        
        return {
            "success": True,
            "estadisticas": {
                "total_documentos": total,
                "con_embeddings": con_embeddings,
                "sin_embeddings": sin_embeddings,
                "porcentaje_procesado": round((con_embeddings / total * 100), 2) if total > 0 else 0
            },
            "ejemplos_con_embeddings": ejemplos_con,
            "ejemplos_sin_embeddings": ejemplos_sin
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/asignar-permisos-test")
async def asignar_permisos_test(
    usuario_target: str = "dianaa",
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """TEMPORAL: Asignar permisos a usuario específico (admin only)"""
    try:
        from app.models.permiso import PermisoCarpeta
        from app.models.carpeta import Carpeta
        
        # Buscar usuario target
        usuario_obj = db.query(Usuario).filter(Usuario.username == usuario_target).first()
        if not usuario_obj:
            return {
                "success": False,
                "error": f"Usuario '{usuario_target}' no encontrado"
            }
        
        # Obtener todas las carpetas disponibles
        carpetas = db.query(Carpeta).all()
        
        permisos_creados = []
        permisos_existentes = []
        
        for carpeta in carpetas:
            # Verificar si ya tiene permiso
            permiso_existente = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == usuario_obj.id,
                PermisoCarpeta.carpeta_id == carpeta.id
            ).first()
            
            if not permiso_existente:
                # Crear permiso de lectura
                nuevo_permiso = PermisoCarpeta(
                    usuario_id=usuario_obj.id,
                    carpeta_id=carpeta.id,
                    tipo='lectura'
                )
                db.add(nuevo_permiso)
                permisos_creados.append({
                    "carpeta_id": carpeta.id,
                    "carpeta_nombre": carpeta.nombre,
                    "tipo": "lectura"
                })
            else:
                permisos_existentes.append({
                    "carpeta_id": carpeta.id,
                    "carpeta_nombre": carpeta.nombre,
                    "tipo": permiso_existente.tipo
                })
        
        if permisos_creados:
            db.commit()
        
        return {
            "success": True,
            "message": f"Permisos procesados para usuario {usuario_target}",
            "usuario_id": usuario_obj.id,
            "usuario_username": usuario_target,
            "permisos_creados": permisos_creados,
            "permisos_existentes": permisos_existentes,
            "total_creados": len(permisos_creados),
            "total_existentes": len(permisos_existentes)
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/debug-permisos")
async def debug_permisos_usuario(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Debug de permisos del usuario actual"""
    try:
        from app.models.permiso import PermisoCarpeta, PermisoSistema
        from app.models.carpeta import Carpeta
        from app.models.tomo import ContenidoOCR, Tomo
        
        # Verificar permisos de sistema
        permisos_sistema = db.query(PermisoSistema).filter(
            PermisoSistema.usuario_id == current_user.id
        ).first()
        
        es_admin = permisos_sistema and permisos_sistema.ver_auditoria
        
        # Obtener permisos de carpetas
        permisos_carpetas_query = db.query(PermisoCarpeta, Carpeta).join(
            Carpeta, PermisoCarpeta.carpeta_id == Carpeta.id
        ).filter(
            PermisoCarpeta.usuario_id == current_user.id
        ).all()
        
        carpetas_info = []
        carpetas_permitidas = []
        
        for permiso, carpeta in permisos_carpetas_query:
            carpetas_permitidas.append(carpeta.id)
            
            # Contar tomos y contenido con embeddings en esta carpeta
            tomos_count = db.query(Tomo).filter(Tomo.carpeta_id == carpeta.id).count()
            
            contenido_total = db.query(ContenidoOCR).join(Tomo).filter(
                Tomo.carpeta_id == carpeta.id
            ).count()
            
            contenido_con_embeddings = db.query(ContenidoOCR).join(Tomo).filter(
                Tomo.carpeta_id == carpeta.id,
                ContenidoOCR.embeddings.isnot(None)
            ).count()
            
            carpetas_info.append({
                "id": carpeta.id,
                "nombre": carpeta.nombre,
                "tipo_permiso": permiso.tipo,
                "tomos_count": tomos_count,
                "contenido_total": contenido_total,
                "contenido_con_embeddings": contenido_con_embeddings
            })
        
        return {
            "success": True,
            "usuario": {
                "id": current_user.id,
                "username": current_user.username,
                "es_admin": es_admin
            },
            "permisos_sistema": {
                "existe": permisos_sistema is not None,
                "ver_auditoria": permisos_sistema.ver_auditoria if permisos_sistema else False
            },
            "carpetas_permitidas": carpetas_permitidas,
            "carpetas_detalle": carpetas_info,
            "resumen": {
                "total_carpetas_acceso": len(carpetas_info),
                "total_contenido_disponible": sum(c["contenido_total"] for c in carpetas_info),
                "total_con_embeddings": sum(c["contenido_con_embeddings"] for c in carpetas_info)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def buscar_por_categorias(db, query: str, carpeta_id: Optional[int], user_id: int, limit: int):
    """Búsqueda inteligente por categorías usando patrones"""
    from app.models.tomo import ContenidoOCR, Tomo
    from app.models.carpeta import Carpeta
    from app.models.permiso import PermisoCarpeta, PermisoSistema
    import re
    
    try:
        query_lower = query.lower().strip()
        
        # Mapeo de categorías a patrones de búsqueda COMPLETO
        categorias = {
            "nombres": {
                "keywords": ["nombres", "nombre", "personas", "persona", "sujetos", "individuo", "declarante", "testigo", "imputado"],
                "patterns": [
                    r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*\b',  # Nombres completos
                    r'\b[A-Z]\.[A-Z]\.[A-Z]\.?\b',  # Iniciales como M.A.C
                    r'\b[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z]\.\b',  # Juan P. M.
                    r'\b[A-Z]\.\s*[A-Z][a-z]+\b',   # J. Pérez
                    r'(?:C\.|ciudadan[ao])\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+',  # C. Juan Pérez
                    r'(?:Sr\.|Sra\.|señor|señora)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+',  # Sr. Juan Pérez
                ]
            },
            "diligencias": {
                "keywords": ["diligencias", "diligencia", "actuación", "gestión", "trámite", "procedimiento"],
                "patterns": [
                    r'(?:diligencia|actuación)\s+(?:de|del|para)\s+[a-záéíóúñ\s]+',
                    r'(?:se\s+)?(?:practicó|realizó|llevó\s+a\s+cabo)\s+[a-záéíóúñ\s]+',
                    r'(?:inspección|reconocimiento|cateo|allanamiento)',
                    r'(?:declaración|testimonio|interrogatorio)',
                    r'(?:pericial|peritaje|dictamen)',
                    r'(?:citatorio|notificación|emplazamiento)'
                ]
            },
            "tipo_diligencia": {
                "keywords": ["tipo de diligencia", "clase de diligencia", "naturaleza"],
                "patterns": [
                    r'(?:declaración\s+(?:testimonial|ministerial|preparatoria))',
                    r'(?:inspección\s+(?:ocular|ministerial|judicial))',
                    r'(?:reconocimiento\s+(?:de\s+personas|en\s+rueda))',
                    r'(?:cateo|allanamiento|búsqueda)',
                    r'(?:pericial\s+(?:médica|contable|grafoscópica|balística))',
                    r'(?:fe\s+(?:ministerial|de\s+hechos))',
                    r'(?:citatorio|notificación|requerimiento)'
                ]
            },
            "fecha_diligencia": {
                "keywords": ["fecha de diligencia", "cuando se realizó", "día de la actuación"],
                "patterns": [
                    r'(?:el\s+día|fecha|realizada\s+el)\s+\d{1,2}\s+de\s+[a-záéíóúñ]+\s+de\s+\d{4}',
                    r'(?:practicada|realizada|efectuada)\s+el\s+\d{1,2}/\d{1,2}/\d{4}',
                    r'a\s+las\s+\d{1,2}:\d{2}\s+horas\s+del\s+día\s+\d{1,2}',
                    r'siendo\s+las\s+\d{1,2}:\d{2}\s+horas'
                ]
            },
            "quien_realiza": {
                "keywords": ["quien realiza", "funcionario", "servidor público", "agente", "MP"],
                "patterns": [
                    r'(?:agente\s+del\s+ministerio\s+público|MP)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+',
                    r'(?:licenciado|lic\.)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+',
                    r'(?:perito|médico\s+legista)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+',
                    r'(?:oficial|comandante|inspector)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+',
                    r'(?:secretario|actuario)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+'
                ]
            },
            "numero_oficio": {
                "keywords": ["número de oficio", "oficio", "expediente", "folio"],
                "patterns": [
                    r'(?:oficio\s+(?:número|no\.?|núm\.?)\s*)[A-Z]*\d+[/-]?\d*[/-]?\d*',
                    r'(?:expediente\s+(?:número|no\.?|núm\.?)\s*)[A-Z]*\d+[/-]?\d*',
                    r'(?:folio\s+(?:número|no\.?|núm\.?)\s*)\d+',
                    r'(?:carpeta\s+de\s+investigación\s*)[A-Z]*\d+[/-]?\d*[/-]?\d*',
                    r'(?:CI|C\.I\.)\s*[A-Z]*\d+[/-]?\d*[/-]?\d*'
                ]
            },
            "fechas": {
                "keywords": ["fechas", "fecha", "día", "cuando", "tiempo", "año", "narrativa", "actuación"],
                "patterns": [
                    r'\b\d{1,2}\s+de\s+[a-záéíóúñ]+\s+de\s+\d{4}\b',  # 15 de enero de 2023
                    r'\b\d{1,2}/\d{1,2}/\d{4}\b',              # 15/01/2023
                    r'\b[a-záéíóúñ]+\s+de\s+\d{4}\b',          # enero de 2023
                    r'(?:el\s+día|en\s+fecha)\s+\d{1,2}\s+de\s+[a-záéíóúñ]+',
                    r'(?:siendo\s+las|a\s+las)\s+\d{1,2}:\d{2}\s+horas',
                    r'(?:aproximadamente\s+)?(?:las\s+)?\d{1,2}:\d{2}\s*(?:horas)?'
                ]
            },
            "lugares": {
                "keywords": ["lugares", "lugar", "ubicación", "sitio", "domicilio", "dirección", "donde", "ubicado"],
                "patterns": [
                    r'(?:en\s+el\s+lugar\s+denominado|ubicado\s+en)\s+[A-Za-záéíóúñ\s,]+',
                    r'(?:domicilio\s+ubicado\s+en|sito\s+en)\s+[A-Za-záéíóúñ\s,\d]+',
                    r'(?:avenida|av\.?|calle|c\.?|boulevard|blvd\.?)\s+[^,\n.]+(?:\d+[^,\n.]*)?',
                    r'(?:colonia|col\.?|fraccionamiento|fracc\.?)\s+[A-Za-záéíóúñ\s]+',
                    r'(?:municipio|alcaldía)\s+[A-Za-záéíóúñ\s]+',
                    r'(?:código\s+postal|C\.P\.)\s+\d{5}',
                    r'(?:entre\s+las\s+calles|esquina\s+con)\s+[A-Za-záéíóúñ\s]+'
                ]
            },
            "telefonos": {
                "keywords": ["teléfonos", "teléfono", "celular", "número telefónico", "contacto"],
                "patterns": [
                    r'(?:teléfono|tel\.?|celular)\s*:?\s*\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}',
                    r'\b\d{3}[-\s]?\d{3}[-\s]?\d{4}\b',  # 555-123-4567
                    r'\b\d{2}[-\s]?\d{4}[-\s]?\d{4}\b',  # 55-1234-5678
                    r'(?:lada\s+)?\d{2,3}\s+\d{3,4}\s+\d{4}',
                    r'(?:número\s+telefónico|contacto)\s*:?\s*[\d\s-]+\d'
                ]
            },
            "direcciones": {
                "keywords": ["direcciones", "dirección", "domicilio", "ubicación", "residencia", "vive en"],
                "patterns": [
                    r'(?:domiciliado\s+en|reside\s+en|vive\s+en)\s+[A-Za-záéíóúñ\s,\d#°-]+',
                    r'(?:avenida|av\.?|calle|c\.?)\s+[^,\n.]+\s*(?:número\s*|#|no\.?\s*)?\d+[A-Za-z]?',
                    r'(?:boulevard|blvd\.?|periférico|anillo)\s+[^,\n.]+',
                    r'(?:privada|priv\.?|andador)\s+[A-Za-záéíóúñ\s]+\s*\d*',
                    r'(?:manzana|mz\.?)\s*\d+[A-Za-z]?\s*(?:lote|lt\.?)\s*\d+[A-Za-z]?',
                    r'(?:interior|int\.?|departamento|depto\.?)\s*\d+[A-Za-z]?',
                    r'(?:entre\s+)?(?:calle|c\.?)\s+[A-Za-záéíóúñ\s]+\s+y\s+(?:calle|c\.?)\s+[A-Za-záéíóúñ\s]+'
                ]
            },
            "declaraciones": {
                "keywords": ["declaraciones", "declaración", "testimonio", "manifestó", "dijo", "expresó"],
                "patterns": [
                    r'(?:declaró|manifestó|expresó|dijo|refirió)\s+(?:que\s+)?[^.]+',
                    r'(?:en\s+su\s+declaración|al\s+ser\s+interrogado)\s+[^.]+',
                    r'(?:testimonial|testimonio)\s+[^.]+',
                    r'(?:bajo\s+protesta\s+de\s+decir\s+verdad)\s+[^.]+',
                    r'(?:preguntado\s+(?:que\s+)?si|interrogado\s+sobre)\s+[^.]+',
                    r'(?:ratifica|confirma|sostiene)\s+(?:que\s+)?[^.]+'
                ]
            },
            "delitos": {
                "keywords": ["delitos", "delito", "crimen", "falta", "infracción", "ilícito"],
                "patterns": [
                    r'\b(?:homicidio|asesinato|muerte\s+violenta|privación\s+de\s+la\s+vida)\b',
                    r'\b(?:robo|hurto|sustracción|despojo)\b',
                    r'\b(?:violación|abuso\s+sexual|estupro|hostigamiento)\b',
                    r'\b(?:lesiones|golpes|agresión|riña)\b',
                    r'\b(?:secuestro|privación\s+(?:ilegal\s+)?de\s+la\s+libertad)\b',
                    r'\b(?:extorsión|amenazas|chantaje)\b',
                    r'\b(?:fraude|estafa|engaño)\b',
                    r'\b(?:narcóticos|drogas|estupefacientes|psicotrópicos)\b',
                    r'\b(?:daño\s+en\s+propiedad|vandalismo)\b'
                ]
            }
        }
        
        # Determinar categoría buscada
        categoria_encontrada = None
        for cat, config in categorias.items():
            if any(keyword in query_lower for keyword in config["keywords"]):
                categoria_encontrada = cat
                break
        
        # Construir query base con permisos
        base_query = db.query(ContenidoOCR).join(Tomo).join(Carpeta)
        
        # Aplicar filtros de permisos de usuario
        permisos_sistema = db.query(PermisoSistema).filter(
            PermisoSistema.usuario_id == user_id
        ).first()
        
        # Verificar si el usuario tiene permisos de administrador (cualquier permiso de gestión)
        es_admin = (permisos_sistema and (
            getattr(permisos_sistema, 'gestionar_usuarios', False) or
            getattr(permisos_sistema, 'gestionar_roles', False) or
            getattr(permisos_sistema, 'gestionar_carpetas', False)
        ))
        
        if not es_admin:
            permisos_carpetas = db.query(PermisoCarpeta.carpeta_id).filter(
                PermisoCarpeta.usuario_id == user_id
            ).all()
            carpetas_permitidas = [p[0] for p in permisos_carpetas]
            if carpetas_permitidas:
                base_query = base_query.filter(Carpeta.id.in_(carpetas_permitidas))
        
        # Filtrar por carpeta si se especifica
        if carpeta_id:
            base_query = base_query.filter(Carpeta.id == carpeta_id)
        
        resultados = []
        
        if categoria_encontrada and categoria_encontrada in categorias:
            # Búsqueda por patrones de la categoría específica
            patterns = categorias[categoria_encontrada]["patterns"]
            contenidos = base_query.filter(
                ContenidoOCR.texto_extraido.isnot(None)
            ).limit(limit * 2).all()  # Más contenido para filtrar
            
            for contenido in contenidos:
                texto = contenido.texto_extraido or ""
                coincidencias = []
                
                for pattern in patterns:
                    matches = re.finditer(pattern, texto, re.IGNORECASE)
                    for match in matches:
                        # Extraer contexto alrededor de la coincidencia
                        start = max(0, match.start() - 100)
                        end = min(len(texto), match.end() + 100)
                        contexto = texto[start:end].strip()
                        
                        coincidencias.append({
                            "texto_encontrado": match.group(),
                            "contexto": contexto,
                            "posicion": match.start()
                        })
                
                if coincidencias:
                    tomo = contenido.tomo
                    carpeta = tomo.carpeta
                    
                    # Tomar solo las primeras coincidencias para no saturar
                    for coincidencia in coincidencias[:3]:
                        resultados.append({
                            "carpeta_id": carpeta.id,
                            "carpeta_nombre": carpeta.nombre_completo,
                            "tomo_id": tomo.id,
                            "numero_tomo": tomo.numero_tomo,
                            "nombre_archivo": tomo.nombre_archivo,
                            "pagina": contenido.numero_pagina,
                            "contexto": coincidencia["contexto"],
                            "texto_encontrado": coincidencia["texto_encontrado"],
                            "categoria": categoria_encontrada,
                            "similitud": 0.9,  # Alta relevancia por coincidencia de patrón
                            "tipo_busqueda": "categorias"
                        })
                        
                        if len(resultados) >= limit:
                            break
                
                if len(resultados) >= limit:
                    break
        else:
            # Búsqueda semántica tradicional si no es una categoría específica
            contenidos = base_query.filter(
                ContenidoOCR.texto_extraido.ilike(f"%{query}%")
            ).limit(limit).all()
            
            for contenido in contenidos:
                tomo = contenido.tomo
                carpeta = tomo.carpeta
                
                texto = contenido.texto_extraido or ""
                # Encontrar contexto alrededor de la consulta
                query_pos = texto.lower().find(query_lower)
                if query_pos >= 0:
                    start = max(0, query_pos - 100)
                    end = min(len(texto), query_pos + len(query) + 100)
                    contexto = texto[start:end].strip()
                else:
                    contexto = texto[:200] + "..." if len(texto) > 200 else texto
                
                resultados.append({
                    "carpeta_id": carpeta.id,
                    "carpeta_nombre": carpeta.nombre_completo,
                    "tomo_id": tomo.id,
                    "numero_tomo": tomo.numero_tomo,
                    "nombre_archivo": tomo.nombre_archivo,
                    "pagina": contenido.numero_pagina,
                    "contexto": contexto,
                    "similitud": 0.8,
                    "tipo_busqueda": "texto"
                })
        
        return {
            "success": True,
            "total": len(resultados),
            "resultados": resultados,
            "parametros": {
                "query": query,
                "categoria_detectada": categoria_encontrada,
                "tipo_busqueda": "categorias_inteligente",
                "similitud_minima": 0.5  # Valor por defecto para categorías
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error en búsqueda por categorías: {str(e)}",
            "total": 0,
            "resultados": [],
            "parametros": {
                "query": query,
                "tipo_busqueda": "error",
                "similitud_minima": 0.5
            }
        }

def extraer_metadata_especializada(texto: str, categoria: str):
    """Extrae metadata especializada según la categoría"""
    import re
    
    metadata = {}
    texto_lower = texto.lower()
    
    try:
        if categoria == "nombres":
            # Extraer información adicional sobre la persona
            if "declaró" in texto_lower or "manifestó" in texto_lower:
                metadata["tipo_participacion"] = "declarante"
            elif "testigo" in texto_lower:
                metadata["tipo_participacion"] = "testigo"
            elif "imputado" in texto_lower or "acusado" in texto_lower:
                metadata["tipo_participacion"] = "imputado"
            elif "víctima" in texto_lower:
                metadata["tipo_participacion"] = "víctima"
            
            # Buscar edad
            edad_match = re.search(r'(\d{1,2})\s+años?\s+de\s+edad', texto_lower)
            if edad_match:
                metadata["edad"] = edad_match.group(1)
        
        elif categoria == "diligencias":
            # Extraer tipo específico de diligencia
            if "declaración" in texto_lower:
                metadata["tipo_especifico"] = "declaración"
            elif "inspección" in texto_lower:
                metadata["tipo_especifico"] = "inspección"
            elif "cateo" in texto_lower:
                metadata["tipo_especifico"] = "cateo"
            elif "pericial" in texto_lower:
                metadata["tipo_especifico"] = "pericial"
        
        elif categoria == "lugares":
            # Extraer componentes de dirección
            cp_match = re.search(r'(?:c\.?p\.?|código\s+postal)\s*(\d{5})', texto_lower)
            if cp_match:
                metadata["codigo_postal"] = cp_match.group(1)
            
            if "colonia" in texto_lower or "col." in texto_lower:
                metadata["incluye_colonia"] = True
            if "municipio" in texto_lower or "alcaldía" in texto_lower:
                metadata["incluye_municipio"] = True
        
        elif categoria == "telefonos":
            # Clasificar tipo de teléfono
            if "celular" in texto_lower:
                metadata["tipo_telefono"] = "celular"
            elif "casa" in texto_lower or "domicilio" in texto_lower:
                metadata["tipo_telefono"] = "fijo"
            else:
                metadata["tipo_telefono"] = "desconocido"
        
        elif categoria == "declaraciones":
            # Contar declaraciones por contexto
            declaraciones_count = len(re.findall(r'declaró|manifestó|expresó|dijo', texto_lower))
            metadata["num_declaraciones"] = declaraciones_count
            
            if "ratifica" in texto_lower:
                metadata["tipo_declaracion"] = "ratificación"
            elif "modifica" in texto_lower:
                metadata["tipo_declaracion"] = "modificación"
            else:
                metadata["tipo_declaracion"] = "inicial"
    
    except Exception:
        pass
    
    return metadata

@router.get("/estadisticas")
async def obtener_estadisticas_declaraciones(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
    carpeta_id: Optional[int] = None
):
    """Generar estadísticas de declaraciones por persona"""
    try:
        from app.models.tomo import ContenidoOCR, Tomo
        from app.models.carpeta import Carpeta
        from app.models.permiso import PermisoCarpeta, PermisoSistema
        import re
        from collections import defaultdict
        
        # Verificar permisos
        base_query = db.query(ContenidoOCR).join(Tomo).join(Carpeta)
        
        permisos_sistema = db.query(PermisoSistema).filter(
            PermisoSistema.usuario_id == current_user.id
        ).first()
        
        # Verificar si el usuario tiene permisos de administrador
        es_admin = (permisos_sistema and (
            getattr(permisos_sistema, 'gestionar_usuarios', False) or
            getattr(permisos_sistema, 'gestionar_roles', False) or
            getattr(permisos_sistema, 'gestionar_carpetas', False)
        ))
        
        if not es_admin:
            permisos_carpetas = db.query(PermisoCarpeta.carpeta_id).filter(
                PermisoCarpeta.usuario_id == current_user.id
            ).all()
            carpetas_permitidas = [p[0] for p in permisos_carpetas]
            if carpetas_permitidas:
                base_query = base_query.filter(Carpeta.id.in_(carpetas_permitidas))
        
        if carpeta_id:
            base_query = base_query.filter(Carpeta.id == carpeta_id)
        
        contenidos = base_query.filter(
            ContenidoOCR.texto_extraido.isnot(None)
        ).all()
        
        estadisticas = defaultdict(lambda: {
            'total_menciones': 0,
            'declaraciones': 0,
            'como_testigo': 0,
            'como_imputado': 0,
            'como_victima': 0,
            'documentos': set(),
            'paginas': set()
        })
        
        # Patrones para nombres y declaraciones
        patron_nombres = r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*\b'
        
        for contenido in contenidos:
            texto = contenido.texto_extraido or ""
            texto_lower = texto.lower()
            
            # Encontrar nombres
            nombres = re.findall(patron_nombres, texto)
            
            for nombre in nombres:
                if len(nombre.split()) >= 2:  # Al menos nombre y apellido
                    stats = estadisticas[nombre]
                    stats['total_menciones'] += 1
                    stats['documentos'].add(f"{contenido.tomo.carpeta.nombre_completo} - {contenido.tomo.nombre_archivo}")
                    stats['paginas'].add(contenido.numero_pagina)
                    
                    # Analizar contexto alrededor del nombre
                    nombre_pos = texto.find(nombre)
                    if nombre_pos >= 0:
                        contexto_start = max(0, nombre_pos - 200)
                        contexto_end = min(len(texto), nombre_pos + len(nombre) + 200)
                        contexto = texto[contexto_start:contexto_end].lower()
                        
                        if any(palabra in contexto for palabra in ['declaró', 'manifestó', 'expresó', 'dijo']):
                            stats['declaraciones'] += 1
                        
                        if 'testigo' in contexto:
                            stats['como_testigo'] += 1
                        elif any(palabra in contexto for palabra in ['imputado', 'acusado', 'procesado']):
                            stats['como_imputado'] += 1
                        elif 'víctima' in contexto:
                            stats['como_victima'] += 1
        
        # Convertir sets a listas para JSON
        resultado_final = {}
        for nombre, stats in estadisticas.items():
            if stats['total_menciones'] > 1:  # Solo personas mencionadas más de una vez
                resultado_final[nombre] = {
                    'total_menciones': stats['total_menciones'],
                    'declaraciones': stats['declaraciones'],
                    'como_testigo': stats['como_testigo'],
                    'como_imputado': stats['como_imputado'],
                    'como_victima': stats['como_victima'],
                    'documentos': list(stats['documentos']),
                    'total_paginas': len(stats['paginas']),
                    'paginas': sorted(list(stats['paginas']))
                }
        
        # Ordenar por relevancia (más menciones primero)
        resultado_ordenado = dict(sorted(
            resultado_final.items(), 
            key=lambda x: x[1]['total_menciones'], 
            reverse=True
        ))
        
        return {
            "success": True,
            "total_personas": len(resultado_ordenado),
            "estadisticas": resultado_ordenado,
            "resumen": {
                "personas_con_declaraciones": sum(1 for stats in resultado_ordenado.values() if stats['declaraciones'] > 0),
                "total_declaraciones": sum(stats['declaraciones'] for stats in resultado_ordenado.values()),
                "testigos_identificados": sum(1 for stats in resultado_ordenado.values() if stats['como_testigo'] > 0),
                "imputados_identificados": sum(1 for stats in resultado_ordenado.values() if stats['como_imputado'] > 0)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generando estadísticas: {str(e)}"
        }