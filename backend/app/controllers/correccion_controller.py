"""
Endpoints para corrección de diligencias por administradores
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel
import re

from app.database import get_db
from app.models.analisis_juridico import Diligencia
from app.models.usuario import Usuario
from app.middlewares.auth_middleware import get_current_user
from app.middlewares.permission_middleware import require_admin

router = APIRouter()


class DiligenciaEditar(BaseModel):
    """Modelo para editar una diligencia"""
    tipo_diligencia: Optional[str] = None
    fecha_diligencia: Optional[str] = None  # formato YYYY-MM-DD
    fecha_diligencia_texto: Optional[str] = None
    responsable: Optional[str] = None
    numero_oficio: Optional[str] = None
    descripcion: Optional[str] = None
    verificado: Optional[bool] = None


class DiligenciasFusionar(BaseModel):
    """Modelo para fusionar diligencias duplicadas"""
    ids_eliminar: List[int]  # IDs a eliminar
    id_mantener: int  # ID a mantener con los datos corregidos
    datos_finales: DiligenciaEditar  # Datos finales después de la fusión


@router.get("/admin/diligencias/problematicas")
async def obtener_diligencias_problematicas(
    carpeta_id: Optional[int] = None,
    tipo_problema: Optional[str] = Query(None, description="fechas_invalidas, texto_corrupto, duplicados_posibles"),
    limite: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Obtener diligencias con posibles problemas que necesitan corrección
    
    Tipos de problemas detectados:
    - fechas_invalidas: Fechas fuera de rango razonable
    - texto_corrupto: Texto con caracteres extraños o mal reconocido
    - duplicados_posibles: Diligencias muy similares
    - baja_confianza: Extracción con confianza < 0.5
    """
    query = db.query(Diligencia)
    
    if carpeta_id:
        query = query.filter(Diligencia.carpeta_id == carpeta_id)
    
    problemas = []
    
    if tipo_problema == "fechas_invalidas" or not tipo_problema:
        # Fechas antes de 1990 o después de 2030
        query_fechas = query.filter(
            or_(
                Diligencia.fecha_diligencia < date(1990, 1, 1),
                Diligencia.fecha_diligencia > date(2030, 12, 31)
            )
        )
        
        for dil in query_fechas.limit(limite).all():
            problemas.append({
                **_formatear_diligencia(dil),
                "tipo_problema": "fecha_invalida",
                "descripcion_problema": f"Fecha sospechosa: {dil.fecha_diligencia}"
            })
    
    if tipo_problema == "texto_corrupto" or not tipo_problema:
        # Responsables con caracteres raros o muy cortos
        query_texto = query.filter(
            or_(
                Diligencia.responsable.ilike('%@%'),
                Diligencia.responsable.ilike('%#%'),
                Diligencia.responsable.ilike('%MNSTENO%'),  # MINISTERIO mal escrito
                Diligencia.responsable.ilike('%WINISTERIO%'),
                Diligencia.responsable.ilike('%MINZSTERIO%'),
                Diligencia.responsable.ilike('%MINISTERIOERIO%'),  # Duplicación OCR
                Diligencia.responsable.ilike('%PERTENECIENTE%'),  # Palabra extraña
                Diligencia.responsable.ilike('%resistido%'),  # OCR corrupto
                Diligencia.responsable.ilike('%Roland%'),  # Nombre extraño
                Diligencia.responsable.ilike('%Summity%'),
                and_(
                    Diligencia.responsable.isnot(None),
                    Diligencia.responsable.op('~')(r'[0-9]{3,}')  # 3+ números seguidos
                )
            )
        )
        
        for dil in query_texto.limit(limite).all():
            problemas.append({
                **_formatear_diligencia(dil),
                "tipo_problema": "texto_corrupto",
                "descripcion_problema": f"Texto sospechoso en responsable: {dil.responsable}"
            })
    
    if tipo_problema == "baja_confianza" or not tipo_problema:
        query_confianza = query.filter(
            Diligencia.confianza < 0.5,
            Diligencia.verificado == False
        )
        
        for dil in query_confianza.limit(limite).all():
            problemas.append({
                **_formatear_diligencia(dil),
                "tipo_problema": "baja_confianza",
                "descripcion_problema": f"Confianza baja: {round(dil.confianza * 100)}%"
            })
    
    # Ordenar por ID y limitar
    problemas = sorted(problemas, key=lambda x: x['id'])[:limite]
    
    return {
        "total": len(problemas),
        "problemas": problemas
    }


@router.put("/admin/diligencias/{diligencia_id}")
async def editar_diligencia(
    diligencia_id: int,
    datos: DiligenciaEditar,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Editar una diligencia corrigiendo datos mal extraídos
    """
    diligencia = db.query(Diligencia).filter(Diligencia.id == diligencia_id).first()
    
    if not diligencia:
        raise HTTPException(status_code=404, detail="Diligencia no encontrada")
    
    # Actualizar campos proporcionados
    if datos.tipo_diligencia is not None:
        diligencia.tipo_diligencia = datos.tipo_diligencia
    
    if datos.fecha_diligencia is not None:
        try:
            diligencia.fecha_diligencia = date.fromisoformat(datos.fecha_diligencia)
        except:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido (usar YYYY-MM-DD)")
    
    if datos.fecha_diligencia_texto is not None:
        diligencia.fecha_diligencia_texto = datos.fecha_diligencia_texto
    
    if datos.responsable is not None:
        diligencia.responsable = datos.responsable
    
    if datos.numero_oficio is not None:
        diligencia.numero_oficio = datos.numero_oficio
    
    if datos.descripcion is not None:
        diligencia.descripcion = datos.descripcion
    
    if datos.verificado is not None:
        diligencia.verificado = datos.verificado
        if datos.verificado:
            diligencia.corregido_por_id = current_user.id
    
    diligencia.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(diligencia)
    
    return {
        "success": True,
        "mensaje": "Diligencia actualizada correctamente",
        "diligencia": _formatear_diligencia(diligencia)
    }


@router.post("/admin/diligencias/autocorregir/{diligencia_id}")
async def autocorregir_diligencia(
    diligencia_id: int,
    forzar: bool = False,  # Parámetro para forzar corrección aunque esté verificado
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Autocorregir fecha obviamente incorrecta
    Ejemplo: 1949 → 2019, 2823 → 2023, MINISTERIOERIO → MINISTERIO
    """
    diligencia = db.query(Diligencia).filter(Diligencia.id == diligencia_id).first()
    
    if not diligencia:
        raise HTTPException(status_code=404, detail="Diligencia no encontrada")
    
    # Si ya está verificado y no es forzado, no hacer nada
    if diligencia.verificado and not forzar:
        return {
            "success": False,
            "mensaje": "Diligencia ya verificada (usa forzar=true para rehacer corrección)",
            "diligencia": _formatear_diligencia(diligencia)
        }
    
    cambios = []
    
    # Corregir fecha si está fuera de rango
    if diligencia.fecha_diligencia:
        year = diligencia.fecha_diligencia.year
        nueva_fecha = None
        
        # 1949 → 2019 (probablemente OCR leyó 2 como 1)
        if 1940 <= year <= 1999:
            year_corregido = year + 70  # 1949 → 2019
            if 2010 <= year_corregido <= 2025:
                nueva_fecha = diligencia.fecha_diligencia.replace(year=year_corregido)
                cambios.append(f"Fecha: {year} → {year_corregido}")
        
        # 2823 → 2023 (OCR leyó 0 como 8)
        elif year >= 2100:
            year_str = str(year)
            # Intentar corregir dígitos comunes
            year_str = year_str.replace('8', '0', 1)  # 2823 → 2023
            year_corregido = int(year_str)
            if 2010 <= year_corregido <= 2025:
                nueva_fecha = diligencia.fecha_diligencia.replace(year=year_corregido)
                cambios.append(f"Fecha: {year} → {year_corregido}")
        
        if nueva_fecha:
            diligencia.fecha_diligencia = nueva_fecha
    
    # Corregir texto común en responsable
    if diligencia.responsable:
        texto_original = diligencia.responsable
        texto_corregido = texto_original
        
        # PASO 1: Correcciones de palabras completas primero (orden importa)
        correcciones_completas = {
            'MINISTERIOERIO PÚBLICO': 'MINISTERIO PÚBLICO',  # Duplicación específica
            'MINISTERIOERIO': 'MINISTERIO',  # Luego la palabra sola
        }
        
        for mal, bien in correcciones_completas.items():
            if mal.upper() in texto_corregido.upper():
                texto_corregido = re.sub(re.escape(mal), bien, texto_corregido, flags=re.IGNORECASE)
                if bien:
                    cambios.append(f"Responsable: '{mal}' → '{bien}'")
        
        # PASO 2: Correcciones de palabras individuales
        correcciones_palabras = {
            'MNSTENO': 'MINISTERIO',
            'WINISTERIO': 'MINISTERIO',
            'MINZSTERIO': 'MINISTERIO',
            'MINIST ': 'MINISTERIO ',  # Con espacio para no afectar MINISTERIO
            'POBLICO': 'PÚBLICO',
            'PUBLICO': 'PÚBLICO',
            'POBLICA': 'PÚBLICA',
            'PUBLICA': 'PÚBLICA',
            'PROCURADURÍ': 'PROCURADURÍA',
        }
        
        for mal, bien in correcciones_palabras.items():
            if mal.upper() in texto_corregido.upper():
                texto_corregido = re.sub(re.escape(mal), bien, texto_corregido, flags=re.IGNORECASE)
                if bien:
                    cambios.append(f"Responsable: '{mal.strip()}' → '{bien.strip()}'")
        
        # PASO 3: Eliminar palabras extrañas
        palabras_eliminar = [
            'PERTENECIENTE', 'fue resistido', 'Roland Summity', 'Roland', 'Summity'
        ]
        
        for palabra in palabras_eliminar:
            if palabra.upper() in texto_corregido.upper():
                texto_corregido = re.sub(r'\b' + re.escape(palabra) + r'\b', '', texto_corregido, flags=re.IGNORECASE)
                cambios.append(f"Responsable: Eliminado '{palabra}'")
        
        # PASO 4: Limpiar espacios múltiples y "PÚBLICO PÚBLICO"
        texto_corregido = ' '.join(texto_corregido.split())
        
        # Eliminar duplicaciones de PÚBLICO
        texto_corregido = re.sub(r'PÚBLICO\s+PÚBLICO(\s+PÚBLICO)*', 'PÚBLICO', texto_corregido, flags=re.IGNORECASE)
        
        # Si quedó muy corto o solo números, intentar corregir
        if len(texto_corregido.strip()) < 5 or texto_corregido.strip().replace(' ', '').isdigit():
            # Probablemente corrupto, intentar poner valor por defecto según tipo
            if diligencia.tipo_diligencia and 'ENTREVISTA' in diligencia.tipo_diligencia.upper():
                texto_corregido = ''  # Entrevistas pueden no tener responsable
            else:
                texto_corregido = 'DEL MINISTERIO PÚBLICO'
                cambios.append(f"Responsable: Asignado valor por defecto")
        
        if texto_corregido != texto_original:
            diligencia.responsable = texto_corregido if texto_corregido.strip() else None
    
    
    if cambios:
        diligencia.verificado = True
        diligencia.corregido_por_id = current_user.id
        diligencia.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(diligencia)
        
        return {
            "success": True,
            "mensaje": "Diligencia autocorregida",
            "cambios": cambios,
            "diligencia": _formatear_diligencia(diligencia)
        }
    else:
        return {
            "success": False,
            "mensaje": "No se detectaron correcciones automáticas posibles",
            "diligencia": _formatear_diligencia(diligencia)
        }



@router.delete("/admin/diligencias/{diligencia_id}")
async def eliminar_diligencia(
    diligencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Eliminar una diligencia duplicada o incorrecta
    """
    diligencia = db.query(Diligencia).filter(Diligencia.id == diligencia_id).first()
    
    if not diligencia:
        raise HTTPException(status_code=404, detail="Diligencia no encontrada")
    
    db.delete(diligencia)
    db.commit()
    
    return {
        "success": True,
        "mensaje": "Diligencia eliminada correctamente"
    }


@router.post("/admin/diligencias/fusionar")
async def fusionar_diligencias(
    datos: DiligenciasFusionar,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Fusionar diligencias duplicadas en una sola
    """
    # Verificar que la diligencia a mantener existe
    dil_mantener = db.query(Diligencia).filter(Diligencia.id == datos.id_mantener).first()
    
    if not dil_mantener:
        raise HTTPException(status_code=404, detail="Diligencia a mantener no encontrada")
    
    # Actualizar con datos finales
    if datos.datos_finales.tipo_diligencia:
        dil_mantener.tipo_diligencia = datos.datos_finales.tipo_diligencia
    
    if datos.datos_finales.fecha_diligencia:
        try:
            dil_mantener.fecha_diligencia = date.fromisoformat(datos.datos_finales.fecha_diligencia)
        except:
            pass
    
    if datos.datos_finales.responsable:
        dil_mantener.responsable = datos.datos_finales.responsable
    
    if datos.datos_finales.numero_oficio:
        dil_mantener.numero_oficio = datos.datos_finales.numero_oficio
    
    dil_mantener.verificado = True
    dil_mantener.corregido_por_id = current_user.id
    dil_mantener.updated_at = datetime.utcnow()
    
    # Eliminar duplicados
    eliminados = 0
    for id_eliminar in datos.ids_eliminar:
        dil_eliminar = db.query(Diligencia).filter(Diligencia.id == id_eliminar).first()
        if dil_eliminar and dil_eliminar.id != datos.id_mantener:
            db.delete(dil_eliminar)
            eliminados += 1
    
    db.commit()
    db.refresh(dil_mantener)
    
    return {
        "success": True,
        "mensaje": f"Fusionadas {eliminados} diligencias duplicadas",
        "diligencia_final": _formatear_diligencia(dil_mantener)
    }


@router.get("/admin/diligencias/{diligencia_id}/similares")
async def buscar_similares(
    diligencia_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    Buscar diligencias similares que podrían ser duplicados
    """
    diligencia = db.query(Diligencia).filter(Diligencia.id == diligencia_id).first()
    
    if not diligencia:
        raise HTTPException(status_code=404, detail="Diligencia no encontrada")
    
    # Buscar similares por fecha y tipo
    similares = db.query(Diligencia).filter(
        Diligencia.carpeta_id == diligencia.carpeta_id,
        Diligencia.id != diligencia_id,
        or_(
            # Mismo tipo y fecha cercana
            and_(
                Diligencia.tipo_diligencia == diligencia.tipo_diligencia,
                Diligencia.fecha_diligencia == diligencia.fecha_diligencia
            ),
            # Mismo orden cronológico (muy sospechoso)
            Diligencia.orden_cronologico == diligencia.orden_cronologico
        )
    ).limit(10).all()
    
    return {
        "diligencia_original": _formatear_diligencia(diligencia),
        "similares": [_formatear_diligencia(s) for s in similares]
    }


def _formatear_diligencia(dil: Diligencia) -> dict:
    """Formatear diligencia para respuesta"""
    return {
        "id": dil.id,
        "tipo_diligencia": dil.tipo_diligencia,
        "fecha": dil.fecha_diligencia.isoformat() if dil.fecha_diligencia else None,
        "fecha_texto": dil.fecha_diligencia_texto,
        "responsable": dil.responsable,
        "numero_oficio": dil.numero_oficio,
        "descripcion": dil.descripcion,
        "pagina": dil.numero_pagina,
        "orden": dil.orden_cronologico,
        "confianza": round(dil.confianza, 2) if dil.confianza else 0,
        "verificado": dil.verificado,
        "carpeta_id": dil.carpeta_id,
        "tomo_id": dil.tomo_id
    }
