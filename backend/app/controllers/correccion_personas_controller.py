"""
Endpoints para corrección y limpieza de personas identificadas
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_, func
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import re

from app.database import get_db
from app.models.analisis_juridico import PersonaIdentificada, DeclaracionPersona
from app.models.usuario import Usuario
from app.middlewares.auth_middleware import get_current_user
from app.middlewares.permission_middleware import require_admin

router = APIRouter()


class PersonaEditar(BaseModel):
    """Modelo para editar una persona"""
    nombre_completo: Optional[str] = None
    nombre_normalizado: Optional[str] = None
    alias: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    rol: Optional[str] = None
    verificado: Optional[bool] = None


class PersonasFusionar(BaseModel):
    """Modelo para fusionar personas duplicadas"""
    ids_eliminar: List[int]  # IDs a eliminar
    id_mantener: int  # ID a mantener con los datos corregidos
    datos_finales: PersonaEditar  # Datos finales después de la fusión


@router.get("/admin/personas/problematicas")
async def obtener_personas_problematicas(
    carpeta_id: Optional[int] = None,
    tipo_problema: Optional[str] = Query(None, description="nombres_invalidos, conceptos, duplicados"),
    limite: int = Query(200, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Obtener personas con nombres inválidos o que son conceptos/lugares
    
    Detecta:
    - Conceptos: "Mecanismo Ciudadano", "Abuso Sexual", "Tribunal Superior"
    - Lugares: "Ciudad De", "San Luis", "Roma Norte"
    - Fragmentos: "Dal Ce", "Gabriel Hern" (nombres cortados)
    - Roles mal detectados: "Ministerio Publico" como persona
    - Duplicados: Variaciones del mismo nombre
    """
    query = db.query(PersonaIdentificada)
    
    if carpeta_id:
        query = query.filter(PersonaIdentificada.carpeta_id == carpeta_id)
    
    problemas = []
    
    # Patrones de nombres inválidos
    conceptos_legales = [
        'MECANISMO CIUDADANO', 'MECAITISNO', 'MECARISMO', 'MECANISINO',
        'ABUSO SEXUAL', 'VIOLENCIA CONTRA', 'TRIBUNAL SUPERIOR',
        'MINISTERIO PUBLICO', 'ACUERDO MINISTERIAL', 'DICTAMEN PERICIAL',
        'SUPREMA CORTE', 'SALA CIVIL', 'JUSTICIA',
        'DESARROLLO INTEGRAL', 'LIBRE DESA', 'NORMAS OFICIALES',
        'PERITO OFICIAL', 'INFORME', 'REVISTA', 'SOCIEDAD MEXICANA'
    ]
    
    lugares = [
        'CIUDAD DE', 'SAN LUIS', 'ROMA NORTE', 'LEONA VICARIO',
        'PRIMER PISO', 'SEGUNDO PISO', 'TERCER PISO',
        'SANTA MAR', 'AVENIDA', 'CALLE'
    ]
    
    fragmentos_invalidos = [
        'DAL CE', 'SAA NE', 'ILE EA', 'TAA VE', 'WWB IA', 'TUL EA',
        'LGRO DA', 'MAN UG', 'TAIC ZY', 'ESY DARL', 'EDL EA',
        'GABRIEL HERN', 'GABRIEL HEM', 'HORACIO CAV',
        'FECHA HORA', 'FEEHA HORA', 'CLOUD FOTOS'
    ]
    
    if tipo_problema == "nombres_invalidos" or not tipo_problema:
        # Buscar conceptos legales
        for concepto in conceptos_legales:
            query_concepto = query.filter(
                PersonaIdentificada.nombre_completo.ilike(f'%{concepto}%')
            )
            
            for persona in query_concepto.limit(50).all():
                problemas.append({
                    **_formatear_persona(persona),
                    "tipo_problema": "concepto_legal",
                    "descripcion_problema": f"Es un concepto legal, no una persona: '{concepto}'"
                })
    
    if tipo_problema == "conceptos" or not tipo_problema:
        # Buscar lugares
        for lugar in lugares:
            query_lugar = query.filter(
                PersonaIdentificada.nombre_completo.ilike(f'%{lugar}%')
            )
            
            for persona in query_lugar.limit(50).all():
                problemas.append({
                    **_formatear_persona(persona),
                    "tipo_problema": "lugar",
                    "descripcion_problema": f"Es un lugar, no una persona: '{lugar}'"
                })
        
        # Buscar fragmentos inválidos
        for fragmento in fragmentos_invalidos:
            query_frag = query.filter(
                PersonaIdentificada.nombre_completo.ilike(f'%{fragmento}%')
            )
            
            for persona in query_frag.limit(50).all():
                problemas.append({
                    **_formatear_persona(persona),
                    "tipo_problema": "fragmento",
                    "descripcion_problema": f"Fragmento de OCR inválido: '{fragmento}'"
                })
    
    # Nombres muy cortos (menos de 5 caracteres)
    query_cortos = query.filter(
        func.length(PersonaIdentificada.nombre_completo) < 8
    )
    
    for persona in query_cortos.limit(50).all():
        if persona.id not in [p['id'] for p in problemas]:
            problemas.append({
                **_formatear_persona(persona),
                "tipo_problema": "nombre_corto",
                "descripcion_problema": f"Nombre muy corto: '{persona.nombre_completo}'"
            })
    
    # Nombres con muchos números (probablemente teléfonos)
    query_numeros = query.filter(
        PersonaIdentificada.nombre_completo.op('~')(r'[0-9]{4,}')
    )
    
    for persona in query_numeros.limit(50).all():
        if persona.id not in [p['id'] for p in problemas]:
            problemas.append({
                **_formatear_persona(persona),
                "tipo_problema": "con_numeros",
                "descripcion_problema": f"Nombre con muchos números: '{persona.nombre_completo}'"
            })
    
    # Eliminar duplicados por ID
    problemas_unicos = {p['id']: p for p in problemas}
    problemas = list(problemas_unicos.values())
    
    # Ordenar por ID y limitar
    problemas = sorted(problemas, key=lambda x: x['id'])[:limite]
    
    return {
        "total": len(problemas),
        "problemas": problemas
    }


@router.delete("/admin/personas/{persona_id}")
async def eliminar_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Eliminar una persona inválida (concepto, lugar, fragmento OCR)
    """
    persona = db.query(PersonaIdentificada).filter(PersonaIdentificada.id == persona_id).first()
    
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    nombre = persona.nombre_completo
    db.delete(persona)
    db.commit()
    
    return {
        "success": True,
        "mensaje": f"Persona eliminada: {nombre}"
    }


@router.post("/admin/personas/eliminar-masivo")
async def eliminar_personas_masivo(
    ids: List[int],
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Eliminar múltiples personas inválidas de una vez
    """
    if len(ids) > 100:
        raise HTTPException(status_code=400, detail="Máximo 100 personas por lote")
    
    personas = db.query(PersonaIdentificada).filter(PersonaIdentificada.id.in_(ids)).all()
    
    if not personas:
        raise HTTPException(status_code=404, detail="No se encontraron personas")
    
    nombres_eliminados = [p.nombre_completo for p in personas]
    
    for persona in personas:
        db.delete(persona)
    
    db.commit()
    
    return {
        "success": True,
        "total_eliminadas": len(personas),
        "nombres": nombres_eliminados[:10]  # Solo primeros 10 para respuesta
    }


@router.post("/admin/personas/limpiar-automatico")
async def limpiar_personas_automatico(
    carpeta_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Limpieza automática de personas inválidas
    Elimina conceptos legales, lugares, fragmentos y nombres muy cortos
    """
    query = db.query(PersonaIdentificada)
    
    if carpeta_id:
        query = query.filter(PersonaIdentificada.carpeta_id == carpeta_id)
    
    # Patrones a eliminar
    patrones_eliminar = [
        # Conceptos legales
        '%MECANISMO CIUDADANO%', '%MECAITISNO%', '%MECARISMO%',
        '%ABUSO SEXUAL%', '%VIOLENCIA CONTRA%', '%TRIBUNAL%',
        '%MINISTERIO PUBLICO%', '%SUPREMA CORTE%', '%SALA CIVIL%',
        '%DICTAMEN PERICIAL%', '%INFORME%', '%NORMAS OFICIALES%',
        '%DERECHO PENAL%', '%ABUSO SEXILAL%', '%TESIS AISLADA%',
        
        # Referencias bibliográficas
        '%SIGMUND FREUD%', '%DICCIONARIO LAROUSSE%',
        '%EDICIONES JUR%', '%AMORRORTU EDITORES%', '%EDITORIAL LUMEN%',
        '%OBRAS COMPLETAS%', '%EDICIONES LA ROCCA%',
        
        # Organizaciones
        '%NACIONES UNIDAS%', '%SEGUNDA GUERRA MUNDIAL%',
        '%CIENCIAS SOCIALES%', '%CONFERENCIA GENIERAL%',
        
        # Títulos y conceptos
        '%STATEMENT VALIDITY%', '%BASED CONTENT%',
        '%DESARROLLO PSICOSEXUAL%', '%SEXUAL INFANTIL%',
        '%SISTEMADE ADMINISTRACI%',
        
        # Lugares
        '%CIUDAD DE%', '%SAN LUIS%', '%ROMA NORTE%',
        '%PRIMER PISO%', '%TERCER PISO%', '%COSTA RICA%',
        
        # Encabezados
        '%FECHA HORA%', '%FECHA HOTA TEL%', '%CLOUD FOTOS%',
        
        # Fragmentos OCR
        '%PHCRATIT%', '%DELFAMEN%', '%CUESTIONARIODE%',
        '%HINSIEO%', '%DALILES%', '%LDVEARB%', '%VOTRES%',
        '%INFORES%', '%DIGRIIDAD%', '%NDE APOYSMYAFUECREGDA%'
    ]
    
    personas_eliminar = []
    
    for patron in patrones_eliminar:
        encontradas = query.filter(PersonaIdentificada.nombre_completo.ilike(patron)).all()
        personas_eliminar.extend(encontradas)
    
    # Nombres muy cortos (menos de 6 caracteres)
    cortos = query.filter(func.length(PersonaIdentificada.nombre_completo) < 6).all()
    personas_eliminar.extend(cortos)
    
    # Eliminar duplicados
    personas_unicas = {p.id: p for p in personas_eliminar}
    personas_eliminar = list(personas_unicas.values())
    
    nombres_eliminados = [p.nombre_completo for p in personas_eliminar]
    
    for persona in personas_eliminar:
        db.delete(persona)
    
    db.commit()
    
    return {
        "success": True,
        "total_eliminadas": len(personas_eliminar),
        "ejemplos": nombres_eliminados[:20]
    }


@router.put("/admin/personas/{persona_id}")
async def editar_persona(
    persona_id: int,
    datos: PersonaEditar,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Editar información de una persona
    """
    persona = db.query(PersonaIdentificada).filter(PersonaIdentificada.id == persona_id).first()
    
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    
    # Actualizar campos proporcionados
    if datos.nombre_completo is not None:
        persona.nombre_completo = datos.nombre_completo
    
    if datos.nombre_normalizado is not None:
        persona.nombre_normalizado = datos.nombre_normalizado
    
    if datos.alias is not None:
        persona.alias = datos.alias
    
    if datos.direccion is not None:
        persona.direccion = datos.direccion
    
    if datos.telefono is not None:
        persona.telefono = datos.telefono
    
    if datos.rol is not None:
        persona.rol = datos.rol
    
    if datos.verificado is not None:
        persona.verificado = datos.verificado
        if datos.verificado:
            persona.corregido_por_id = current_user.id
    
    persona.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(persona)
    
    return {
        "success": True,
        "mensaje": "Persona actualizada correctamente",
        "persona": _formatear_persona(persona)
    }


def _formatear_persona(persona: PersonaIdentificada) -> dict:
    """Formatear persona para respuesta"""
    return {
        "id": persona.id,
        "nombre_completo": persona.nombre_completo,
        "nombre_normalizado": persona.nombre_normalizado,
        "rol": persona.rol,
        "direccion": persona.direccion,
        "telefono": persona.telefono,
        "total_menciones": persona.total_menciones,
        "total_declaraciones": persona.total_declaraciones,
        "confianza": round(persona.confianza, 2) if persona.confianza else 0,
        "verificado": persona.verificado,
        "carpeta_id": persona.carpeta_id,
        "tomo_id": persona.tomo_id
    }
