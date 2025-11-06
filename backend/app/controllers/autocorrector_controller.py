"""
Controlador para autocorrección legal de textos OCR
Endpoints para corregir errores en alcaldías, colonias, términos legales y detectar duplicados
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.usuario import Usuario
from app.models.analisis_juridico import (
    Diligencia, PersonaIdentificada, LugarIdentificado, FechaImportante
)
from app.middlewares.permission_middleware import require_admin, get_current_user
from app.services.legal_autocorrector_service import legal_autocorrector
# Importar el servicio PostgreSQL con fuzzy search
from app.services.sepomex_service_postgresql import sepomex_service_postgresql as sepomex_service
# Nuevos servicios para entidades legales
from app.services.catalogo_fiscalias_service import catalogo_fiscalias
from app.services.detector_contextual_service import detector_contextual
from app.services.pdf_pagina_service import pdf_pagina_service


router = APIRouter(
    prefix="/autocorrector",
    tags=["✍️ Autocorrector Legal"]
)


# ============================================
# MODELOS PYDANTIC
# ============================================

class TextoCorregir(BaseModel):
    """Modelo para solicitud de corrección de texto"""
    texto: str
    tipo_correccion: Optional[str] = "completo"  # completo, alcaldia, colonia, direccion, termino_legal


class DireccionCorregir(BaseModel):
    """Modelo para corrección de dirección"""
    direccion: str
    colonia: Optional[str] = None
    alcaldia: Optional[str] = None
    codigo_postal: Optional[str] = None  # Para validación con SEPOMEX


class ResultadoCorreccion(BaseModel):
    """Modelo de respuesta de corrección"""
    texto_original: str
    texto_corregido: str
    fue_corregido: bool
    correcciones: List[Dict]
    total_correcciones: int


class DetectarDuplicadosRequest(BaseModel):
    """Modelo para detectar duplicados"""
    carpeta_id: int
    tipo_entidad: str  # diligencias, personas, lugares
    umbral_similitud: Optional[float] = 0.9


# ============================================
# NUEVOS MODELOS PARA ENTIDADES LEGALES
# ============================================

class NormalizarFiscaliaRequest(BaseModel):
    """Modelo para normalizar fiscalía"""
    texto: str


class NormalizarAgenciaRequest(BaseModel):
    """Modelo para normalizar agencia MP"""
    codigo: str


class NormalizarDelitoRequest(BaseModel):
    """Modelo para normalizar delito"""
    texto: str


class ClasificarTextoRequest(BaseModel):
    """Modelo para clasificar texto (nombre vs colonia)"""
    texto: str
    ventana_contexto: Optional[str] = None


class ProcesarDocumentoRequest(BaseModel):
    """Modelo para procesar documento OCR completo"""
    texto_completo: str


class ExtraerPaginaPDFRequest(BaseModel):
    """Modelo para extraer número de página real del PDF"""
    pdf_path: str
    pagina_visor: int  # 0-indexed


class BuscarEnPDFRequest(BaseModel):
    """Modelo para buscar texto en PDF"""
    pdf_path: str
    texto_buscado: str
    case_sensitive: Optional[bool] = False


class CorregirDiligenciasRequest(BaseModel):
    """Modelo para corregir diligencias de una carpeta"""
    carpeta_id: int
    auto_corregir: bool = False  # Si es False, solo reporta correcciones
    eliminar_duplicados: bool = False


# ============================================
# ENDPOINTS - CORRECCIÓN DE TEXTO
# ============================================

@router.post("/corregir-texto", response_model=ResultadoCorreccion)
async def corregir_texto(
    request: TextoCorregir,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Corregir un texto con errores OCR
    - Alcaldías de CDMX
    - Colonias
    - Términos legales
    - Errores comunes de OCR
    """
    try:
        if request.tipo_correccion == "alcaldia":
            texto_corregido, fue_corregido = legal_autocorrector.corregir_alcaldia(request.texto)
            return ResultadoCorreccion(
                texto_original=request.texto,
                texto_corregido=texto_corregido,
                fue_corregido=fue_corregido,
                correcciones=[{"tipo": "alcaldia"}] if fue_corregido else [],
                total_correcciones=1 if fue_corregido else 0
            )
        
        elif request.tipo_correccion == "colonia":
            texto_corregido, fue_corregido = legal_autocorrector.corregir_colonia(request.texto)
            return ResultadoCorreccion(
                texto_original=request.texto,
                texto_corregido=texto_corregido,
                fue_corregido=fue_corregido,
                correcciones=[{"tipo": "colonia"}] if fue_corregido else [],
                total_correcciones=1 if fue_corregido else 0
            )
        
        elif request.tipo_correccion == "termino_legal":
            texto_corregido, fue_corregido = legal_autocorrector.corregir_termino_legal(request.texto)
            return ResultadoCorreccion(
                texto_original=request.texto,
                texto_corregido=texto_corregido,
                fue_corregido=fue_corregido,
                correcciones=[{"tipo": "termino_legal"}] if fue_corregido else [],
                total_correcciones=1 if fue_corregido else 0
            )
        
        else:  # completo
            resultado = legal_autocorrector.corregir_texto_completo(request.texto)
            return ResultadoCorreccion(
                texto_original=resultado['texto_original'],
                texto_corregido=resultado['texto_corregido'],
                fue_corregido=resultado['fue_corregido'],
                correcciones=resultado['correcciones_realizadas'],
                total_correcciones=resultado['total_correcciones']
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al corregir texto: {str(e)}"
        )


@router.post("/corregir-direccion")
async def corregir_direccion(
    request: DireccionCorregir,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Corregir una dirección completa con validación SEPOMEX
    
    Si se proporciona código postal, valida la colonia contra el catálogo oficial de SEPOMEX
    """
    try:
        resultado = {}
        
        # Corregir dirección principal
        direccion_corregida, fue_corregida_dir, detalles_dir = legal_autocorrector.corregir_direccion(request.direccion)
        resultado['direccion'] = {
            'original': request.direccion,
            'corregida': direccion_corregida,
            'fue_corregida': fue_corregida_dir,
            'detalles': detalles_dir
        }
        
        # Corregir colonia si está presente
        colonia_corregida = request.colonia
        fue_corregida_col = False
        
        if request.colonia:
            colonia_corregida, fue_corregida_col = legal_autocorrector.corregir_colonia(request.colonia)
            resultado['colonia'] = {
                'original': request.colonia,
                'corregida': colonia_corregida,
                'fue_corregida': fue_corregida_col
            }
        
        # Corregir alcaldía si está presente
        alcaldia_corregida = request.alcaldia
        fue_corregida_alc = False
        
        if request.alcaldia:
            alcaldia_corregida, fue_corregida_alc = legal_autocorrector.corregir_alcaldia(request.alcaldia)
            resultado['alcaldia'] = {
                'original': request.alcaldia,
                'corregida': alcaldia_corregida,
                'fue_corregida': fue_corregida_alc
            }
        
        # Validación con SEPOMEX si se proporcionó código postal
        if request.codigo_postal and colonia_corregida:
            try:
                validacion_sepomex = await sepomex_service.validar_colonia_en_cp(
                    colonia_corregida, 
                    request.codigo_postal
                )
                
                resultado['sepomex_validacion'] = validacion_sepomex
                
                # Si SEPOMEX sugiere una colonia similar, agregarla como sugerencia
                if not validacion_sepomex.get('valida') and validacion_sepomex.get('similares'):
                    resultado['colonia']['sugerencias_sepomex'] = validacion_sepomex['similares'][:5]
                    
            except Exception as e:
                # Si falla SEPOMEX, continuar sin validación
                resultado['sepomex_validacion'] = {
                    'error': f'No se pudo validar con SEPOMEX: {str(e)}',
                    'codigo_postal': request.codigo_postal
                }
        
        return resultado
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al corregir dirección: {str(e)}"
        )


# ============================================
# ENDPOINTS - DETECCIÓN Y CORRECCIÓN DE DUPLICADOS
# ============================================

@router.post("/detectar-duplicados")
async def detectar_duplicados(
    request: DetectarDuplicadosRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Detectar registros duplicados en una carpeta
    """
    try:
        if request.tipo_entidad == "diligencias":
            registros = db.query(Diligencia).filter(
                Diligencia.carpeta_id == request.carpeta_id
            ).all()
            
            registros_dict = [
                {
                    'id': r.id,
                    'tipo_diligencia': r.tipo_diligencia or '',
                    'fecha_diligencia': str(r.fecha_diligencia or ''),
                    'responsable': r.responsable or ''
                }
                for r in registros
            ]
            
            duplicados = legal_autocorrector.detectar_duplicados(
                registros_dict,
                campos_comparar=['tipo_diligencia', 'fecha_diligencia', 'responsable'],
                umbral_similitud=request.umbral_similitud
            )
            
            # Convertir índices a IDs reales
            grupos_duplicados = []
            for grupo in duplicados:
                ids_grupo = [registros_dict[idx]['id'] for idx in grupo]
                detalles = [
                    {
                        'id': registros_dict[idx]['id'],
                        'tipo': registros_dict[idx]['tipo_diligencia'],
                        'fecha': registros_dict[idx]['fecha_diligencia'],
                        'responsable': registros_dict[idx]['responsable']
                    }
                    for idx in grupo
                ]
                grupos_duplicados.append({
                    'ids': ids_grupo,
                    'cantidad': len(ids_grupo),
                    'detalles': detalles
                })
            
            return {
                'carpeta_id': request.carpeta_id,
                'tipo_entidad': request.tipo_entidad,
                'total_registros': len(registros),
                'total_duplicados_encontrados': sum(len(g['ids']) for g in grupos_duplicados),
                'grupos_duplicados': grupos_duplicados
            }
        
        elif request.tipo_entidad == "personas":
            registros = db.query(PersonaIdentificada).filter(
                PersonaIdentificada.carpeta_id == request.carpeta_id
            ).all()
            
            registros_dict = [
                {
                    'id': r.id,
                    'nombre_completo': r.nombre_completo or '',
                    'direccion': r.direccion or '',
                    'rol': r.rol or ''
                }
                for r in registros
            ]
            
            duplicados = legal_autocorrector.detectar_duplicados(
                registros_dict,
                campos_comparar=['nombre_completo', 'direccion'],
                umbral_similitud=request.umbral_similitud
            )
            
            grupos_duplicados = []
            for grupo in duplicados:
                ids_grupo = [registros_dict[idx]['id'] for idx in grupo]
                detalles = [
                    {
                        'id': registros_dict[idx]['id'],
                        'nombre': registros_dict[idx]['nombre_completo'],
                        'direccion': registros_dict[idx]['direccion']
                    }
                    for idx in grupo
                ]
                grupos_duplicados.append({
                    'ids': ids_grupo,
                    'cantidad': len(ids_grupo),
                    'detalles': detalles
                })
            
            return {
                'carpeta_id': request.carpeta_id,
                'tipo_entidad': request.tipo_entidad,
                'total_registros': len(registros),
                'total_duplicados_encontrados': sum(len(g['ids']) for g in grupos_duplicados),
                'grupos_duplicados': grupos_duplicados
            }
        
        elif request.tipo_entidad == "lugares":
            registros = db.query(LugarIdentificado).filter(
                LugarIdentificado.carpeta_id == request.carpeta_id
            ).all()
            
            registros_dict = [
                {
                    'id': r.id,
                    'nombre_lugar': r.nombre_lugar or '',
                    'direccion_completa': r.direccion_completa or '',
                    'colonia': r.colonia or ''
                }
                for r in registros
            ]
            
            duplicados = legal_autocorrector.detectar_duplicados(
                registros_dict,
                campos_comparar=['nombre_lugar', 'direccion_completa'],
                umbral_similitud=request.umbral_similitud
            )
            
            grupos_duplicados = []
            for grupo in duplicados:
                ids_grupo = [registros_dict[idx]['id'] for idx in grupo]
                detalles = [
                    {
                        'id': registros_dict[idx]['id'],
                        'nombre': registros_dict[idx]['nombre_lugar'],
                        'direccion': registros_dict[idx]['direccion_completa']
                    }
                    for idx in grupo
                ]
                grupos_duplicados.append({
                    'ids': ids_grupo,
                    'cantidad': len(ids_grupo),
                    'detalles': detalles
                })
            
            return {
                'carpeta_id': request.carpeta_id,
                'tipo_entidad': request.tipo_entidad,
                'total_registros': len(registros),
                'total_duplicados_encontrados': sum(len(g['ids']) for g in grupos_duplicados),
                'grupos_duplicados': grupos_duplicados
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de entidad no soportado: {request.tipo_entidad}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al detectar duplicados: {str(e)}"
        )


@router.post("/corregir-carpeta")
async def corregir_carpeta(
    request: CorregirDiligenciasRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Corregir todas las diligencias, personas y lugares de una carpeta
    Solo administradores
    """
    try:
        resultado = {
            'carpeta_id': request.carpeta_id,
            'correcciones': [],
            'duplicados_eliminados': []
        }
        
        # 1. Corregir DILIGENCIAS
        diligencias = db.query(Diligencia).filter(
            Diligencia.carpeta_id == request.carpeta_id
        ).all()
        
        for diligencia in diligencias:
            # Corregir tipo de diligencia
            if diligencia.tipo_diligencia:
                tipo_corregido, fue_corregido = legal_autocorrector.corregir_termino_legal(diligencia.tipo_diligencia)
                if fue_corregido:
                    resultado['correcciones'].append({
                        'entidad': 'diligencia',
                        'id': diligencia.id,
                        'campo': 'tipo_diligencia',
                        'original': diligencia.tipo_diligencia,
                        'corregido': tipo_corregido
                    })
                    if request.auto_corregir:
                        diligencia.tipo_diligencia = tipo_corregido
            
            # Corregir responsable
            if diligencia.responsable:
                resp_corregido = legal_autocorrector.corregir_texto_completo(diligencia.responsable)
                if resp_corregido['fue_corregido']:
                    resultado['correcciones'].append({
                        'entidad': 'diligencia',
                        'id': diligencia.id,
                        'campo': 'responsable',
                        'original': diligencia.responsable,
                        'corregido': resp_corregido['texto_corregido']
                    })
                    if request.auto_corregir:
                        diligencia.responsable = resp_corregido['texto_corregido']
        
        # 2. Corregir PERSONAS
        personas = db.query(PersonaIdentificada).filter(
            PersonaIdentificada.carpeta_id == request.carpeta_id
        ).all()
        
        for persona in personas:
            # Corregir colonia
            if persona.colonia:
                colonia_corregida, fue_corregida = legal_autocorrector.corregir_colonia(persona.colonia)
                if fue_corregida:
                    resultado['correcciones'].append({
                        'entidad': 'persona',
                        'id': persona.id,
                        'campo': 'colonia',
                        'original': persona.colonia,
                        'corregido': colonia_corregida
                    })
                    if request.auto_corregir:
                        persona.colonia = colonia_corregida
            
            # Corregir municipio (alcaldía)
            if persona.municipio:
                municipio_corregido, fue_corregido = legal_autocorrector.corregir_alcaldia(persona.municipio)
                if fue_corregido:
                    resultado['correcciones'].append({
                        'entidad': 'persona',
                        'id': persona.id,
                        'campo': 'municipio',
                        'original': persona.municipio,
                        'corregido': municipio_corregido
                    })
                    if request.auto_corregir:
                        persona.municipio = municipio_corregido
            
            # Corregir dirección
            if persona.direccion:
                dir_corregida, fue_corregida, _ = legal_autocorrector.corregir_direccion(persona.direccion)
                if fue_corregida:
                    resultado['correcciones'].append({
                        'entidad': 'persona',
                        'id': persona.id,
                        'campo': 'direccion',
                        'original': persona.direccion,
                        'corregido': dir_corregida
                    })
                    if request.auto_corregir:
                        persona.direccion = dir_corregida
        
        # 3. Corregir LUGARES
        lugares = db.query(LugarIdentificado).filter(
            LugarIdentificado.carpeta_id == request.carpeta_id
        ).all()
        
        for lugar in lugares:
            # Corregir colonia
            if lugar.colonia:
                colonia_corregida, fue_corregida = legal_autocorrector.corregir_colonia(lugar.colonia)
                if fue_corregida:
                    resultado['correcciones'].append({
                        'entidad': 'lugar',
                        'id': lugar.id,
                        'campo': 'colonia',
                        'original': lugar.colonia,
                        'corregido': colonia_corregida
                    })
                    if request.auto_corregir:
                        lugar.colonia = colonia_corregida
            
            # Corregir municipio (alcaldía)
            if lugar.municipio:
                municipio_corregido, fue_corregido = legal_autocorrector.corregir_alcaldia(lugar.municipio)
                if fue_corregido:
                    resultado['correcciones'].append({
                        'entidad': 'lugar',
                        'id': lugar.id,
                        'campo': 'municipio',
                        'original': lugar.municipio,
                        'corregido': municipio_corregido
                    })
                    if request.auto_corregir:
                        lugar.municipio = municipio_corregido
        
        # 4. Detectar y eliminar duplicados (si se solicitó)
        if request.eliminar_duplicados:
            # Detectar duplicados en diligencias
            registros_diligencias = [
                {
                    'id': d.id,
                    'tipo_diligencia': d.tipo_diligencia or '',
                    'fecha_diligencia': str(d.fecha_diligencia or ''),
                    'responsable': d.responsable or ''
                }
                for d in diligencias
            ]
            
            duplicados_dilig = legal_autocorrector.detectar_duplicados(
                registros_diligencias,
                umbral_similitud=0.95
            )
            
            # Eliminar duplicados (mantener el primero de cada grupo)
            for grupo in duplicados_dilig:
                ids_eliminar = [registros_diligencias[idx]['id'] for idx in grupo[1:]]  # Todos menos el primero
                for id_eliminar in ids_eliminar:
                    db.query(Diligencia).filter(Diligencia.id == id_eliminar).delete()
                    resultado['duplicados_eliminados'].append({
                        'entidad': 'diligencia',
                        'id_eliminado': id_eliminar,
                        'id_conservado': registros_diligencias[grupo[0]]['id']
                    })
        
        # Guardar cambios si auto_corregir está activado
        if request.auto_corregir:
            db.commit()
        
        return {
            **resultado,
            'total_correcciones': len(resultado['correcciones']),
            'total_duplicados_eliminados': len(resultado['duplicados_eliminados']),
            'auto_corregir': request.auto_corregir,
            'mensaje': 'Correcciones aplicadas' if request.auto_corregir else 'Correcciones detectadas (no aplicadas)'
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al corregir carpeta: {str(e)}"
        )


# ============================================
# NUEVOS ENDPOINTS - ENTIDADES LEGALES FGJCDMX
# ============================================

@router.post("/normalizar-fiscalia", summary="Normalizar nombre de fiscalía")
async def normalizar_fiscalia(
    request: NormalizarFiscaliaRequest,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Normaliza el nombre de una fiscalía a su nombre oficial.
    
    Ejemplo:
    - "FISCALIA DELITOS SEXUALES" → "FISCALÍA CENTRAL DE INVESTIGACIÓN DELITOS SEXUALES"
    - "FDS" → "FISCALÍA CENTRAL DE INVESTIGACIÓN DELITOS SEXUALES"
    """
    try:
        resultado = catalogo_fiscalias.normalizar_fiscalia(request.texto)
        
        return {
            'texto_original': request.texto,
            'resultado': resultado,
            'fue_normalizado': resultado['encontrado'],
            'similitud': resultado['similitud']
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al normalizar fiscalía: {str(e)}"
        )


@router.post("/normalizar-agencia-mp", summary="Normalizar código de agencia MP")
async def normalizar_agencia_mp(
    request: NormalizarAgenciaRequest,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Normaliza el código de una agencia del Ministerio Público.
    
    Ejemplo:
    - "FDS-6" → "AGENCIA INVESTIGADORA DEL M.P. FDS-6"
    - "AO-1" → "AGENCIA INVESTIGADORA DEL M.P. AO-1"
    """
    try:
        resultado = catalogo_fiscalias.normalizar_agencia_mp(request.codigo)
        
        return {
            'codigo_original': request.codigo,
            'resultado': resultado,
            'encontrado': resultado['encontrado']
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al normalizar agencia: {str(e)}"
        )


@router.post("/normalizar-delito", summary="Normalizar delito y detectar agravantes")
async def normalizar_delito(
    request: NormalizarDelitoRequest,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Normaliza el nombre de un delito y detecta agravantes automáticamente.
    
    Ejemplo:
    - "ABUSO SEXUAL AGRAVADO POR PARENTESCO" → {
        normalizado: "ABUSO SEXUAL - AGRAVADO, POR PARENTESCO",
        codigo: "181",
        agravante: "PARENTESCO"
      }
    """
    try:
        resultado = catalogo_fiscalias.normalizar_delito(request.texto)
        
        return {
            'texto_original': request.texto,
            'resultado': resultado,
            'fue_normalizado': resultado['encontrado'],
            'similitud': resultado['similitud']
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al normalizar delito: {str(e)}"
        )


@router.post("/clasificar-texto", summary="Clasificar texto (persona vs colonia)")
async def clasificar_texto(
    request: ClasificarTextoRequest,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Clasifica un texto como PERSONA, COLONIA o AMBIGUO usando análisis contextual.
    
    Distingue:
    - "MIGUEL SOLARES" → PERSONA (nombre + apellido común)
    - "SAN ÁNGEL" → COLONIA (existe en SEPOMEX + artículo "SAN")
    - "DEL VALLE" → COLONIA (existe en SEPOMEX + artículo "DEL")
    
    Retorna:
    - clasificacion: "PERSONA" | "COLONIA" | "AMBIGUO"
    - certeza: 0-100 (porcentaje de confianza)
    - evidencias: Lista de razones para la clasificación
    """
    try:
        resultado = detector_contextual.analizar_contexto(
            request.texto, 
            request.ventana_contexto
        )
        
        return {
            'texto_analizado': request.texto,
            'clasificacion': resultado['clasificacion'],
            'certeza': resultado['certeza'],
            'evidencias': resultado['evidencias'],
            'scores': resultado.get('scores', {})
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al clasificar texto: {str(e)}"
        )


@router.post("/procesar-documento-ocr", summary="Procesar documento OCR completo")
async def procesar_documento_ocr(
    request: ProcesarDocumentoRequest,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Procesa un documento OCR completo y extrae todas las entidades:
    - Personas identificadas
    - Colonias identificadas
    - Fiscalías mencionadas
    - Delitos mencionados
    - Agencias MP mencionadas
    
    Retorna un análisis completo del documento con todas las entidades clasificadas.
    """
    try:
        # Detectar nombres y colonias
        entidades = detector_contextual.procesar_documento_ocr(request.texto_completo)
        
        # Buscar fiscalías en el texto
        fiscalias_detectadas = []
        lineas = request.texto_completo.split('\n')
        for linea in lineas:
            if 'fiscal' in linea.lower():
                resultado_fiscalia = catalogo_fiscalias.normalizar_fiscalia(linea)
                if resultado_fiscalia['encontrado']:
                    fiscalias_detectadas.append(resultado_fiscalia)
        
        # Buscar delitos
        delitos_detectados = []
        for linea in lineas:
            if any(palabra in linea.upper() for palabra in ['ABUSO', 'VIOLACION', 'HOMICIDIO', 'ROBO', 'FRAUDE']):
                resultado_delito = catalogo_fiscalias.normalizar_delito(linea)
                if resultado_delito['encontrado']:
                    delitos_detectados.append(resultado_delito)
        
        return {
            'personas': entidades['personas'],
            'colonias': entidades['colonias'],
            'ambiguos': entidades['ambiguos'],
            'fiscalias': fiscalias_detectadas,
            'delitos': delitos_detectados,
            'estadisticas': {
                'total_personas': len(entidades['personas']),
                'total_colonias': len(entidades['colonias']),
                'total_ambiguos': len(entidades['ambiguos']),
                'total_fiscalias': len(fiscalias_detectadas),
                'total_delitos': len(delitos_detectados)
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar documento: {str(e)}"
        )


@router.post("/extraer-pagina-pdf", summary="Extraer número de página REAL del PDF")
async def extraer_pagina_pdf(
    request: ExtraerPaginaPDFRequest,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Extrae el número de página REAL del PDF usando la posición en el archivo.
    
    IMPORTANTE: Este endpoint usa SIEMPRE la numeración secuencial del PDF.
    NO intenta detectar números manuscritos, "TOMO", ni fojas impresas.
    
    Para carpetas judiciales con múltiples tomos:
    - Página 1 del visor → Foja 1
    - Página 195 del visor → Foja 195
    - Página 821 del visor → Foja 821
    
    Ignora:
    - ❌ Números manuscritos en el documento (ej: "190" escrito a mano)
    - ❌ "TOMO I", "TOMO II" en esquinas
    - ❌ Fojas internas que no coincidan con posición
    
    Retorna:
    - pagina_real: Número = posición en PDF (1-indexed)
    - pagina_visor: Índice en el PDF (0-indexed)
    - confianza: 100% (usa posición exacta del PDF)
    """
    try:
        # forzar_secuencial=True para usar SIEMPRE posición del PDF
        resultado = pdf_pagina_service.extraer_numero_pagina_real(
            request.pdf_path,
            request.pagina_visor,
            forzar_secuencial=True
        )
        
        return resultado
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al extraer página: {str(e)}"
        )


@router.post("/buscar-en-pdf", summary="Buscar texto en PDF y obtener páginas reales")
async def buscar_en_pdf(
    request: BuscarEnPDFRequest,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Busca un texto en todo el PDF y devuelve las páginas REALES donde aparece.
    
    Útil para encontrar:
    - Número de carpeta
    - Nombre de persona
    - Fiscalía específica
    - Tipo de delito
    
    Retorna lista de coincidencias con:
    - pagina_real: Número de página del documento
    - pagina_visor: Índice en el visor
    - coincidencias: Cantidad de veces que aparece el texto
    - contexto: Texto alrededor de la coincidencia
    """
    try:
        resultados = pdf_pagina_service.buscar_pagina_por_contenido(
            request.pdf_path,
            request.texto_buscado,
            request.case_sensitive
        )
        
        return {
            'texto_buscado': request.texto_buscado,
            'total_coincidencias': len(resultados),
            'resultados': resultados
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al buscar en PDF: {str(e)}"
        )


@router.get("/metadatos-numeracion-pdf/{pdf_path:path}", summary="Analizar esquema de numeración del PDF")
async def metadatos_numeracion_pdf(
    pdf_path: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Analiza todo el PDF para determinar qué esquema de numeración usa.
    
    Detecta:
    - Si usa numeración secuencial (1, 2, 3...)
    - Si usa fojas con numeración interna
    - Si tiene saltos en la numeración
    - Dónde aparecen los números (header/footer)
    
    Útil para entender la estructura de carpetas judiciales complejas.
    """
    try:
        metadatos = pdf_pagina_service.extraer_metadatos_numeracion(pdf_path)
        
        return metadatos
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al analizar metadatos: {str(e)}"
        )
