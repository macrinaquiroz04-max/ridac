from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
import shutil
from datetime import datetime

from app.database import get_db
from app.models.tomo import Tomo
from app.models.usuario import Usuario
from app.models.permiso_tomo import PermisoTomo
from app.models.documento_ocr import DocumentoOCR
from app.middlewares.auth_middleware import get_current_user

router = APIRouter()

@router.post("/tomos/{tomo_id}/documento")
async def guardar_documento_ocr(
    tomo_id: int,
    nombre: str = Form(...),
    contenido: str = Form(...),
    descripcion: Optional[str] = Form(None),
    tipo: str = Form("ocr_extract"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Guardar documento extraído con OCR en un tomo específico
    """
    try:
        # Verificar que el usuario tiene permisos sobre el tomo
        permiso = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == current_user.id,
            PermisoTomo.tomo_id == tomo_id,
            PermisoTomo.activo == True
        ).first()
        
        if not permiso:
            raise HTTPException(
                status_code=403, 
                detail="No tienes permisos para agregar documentos a este tomo"
            )
        
        # Verificar que el tomo existe
        tomo = db.query(Tomo).filter(Tomo.id == tomo_id, Tomo.activo == True).first()
        if not tomo:
            raise HTTPException(status_code=404, detail="Tomo no encontrado")
        
        # Crear documento OCR
        documento = DocumentoOCR(
            tomo_id=tomo_id,
            usuario_id=current_user.id,
            nombre=nombre,
            contenido=contenido,
            descripcion=descripcion,
            tipo=tipo,
            fecha_creacion=datetime.now(),
            activo=True
        )
        
        db.add(documento)
        db.commit()
        db.refresh(documento)
        
        return {
            "success": True,
            "message": "Documento guardado exitosamente",
            "documento_id": documento.id,
            "tomo": tomo.nombre
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/tomos/{tomo_id}/documentos")
async def obtener_documentos_tomo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener documentos OCR de un tomo específico
    """
    try:
        # Verificar permisos
        permiso = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == current_user.id,
            PermisoTomo.tomo_id == tomo_id,
            PermisoTomo.activo == True
        ).first()
        
        if not permiso:
            raise HTTPException(
                status_code=403, 
                detail="No tienes permisos para ver los documentos de este tomo"
            )
        
        # Obtener documentos
        documentos = db.query(DocumentoOCR).filter(
            DocumentoOCR.tomo_id == tomo_id,
            DocumentoOCR.activo == True
        ).order_by(DocumentoOCR.fecha_creacion.desc()).all()
        
        return [
            {
                "id": doc.id,
                "nombre": doc.nombre,
                "descripcion": doc.descripcion,
                "tipo": doc.tipo,
                "fecha_creacion": doc.fecha_creacion.isoformat(),
                "usuario": doc.usuario.nombre_completo if doc.usuario else "Usuario desconocido",
                "contenido_preview": doc.contenido[:200] + "..." if len(doc.contenido) > 200 else doc.contenido
            }
            for doc in documentos
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/documentos/{documento_id}")
async def obtener_documento_completo(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener contenido completo de un documento OCR
    """
    try:
        documento = db.query(DocumentoOCR).filter(
            DocumentoOCR.id == documento_id,
            DocumentoOCR.activo == True
        ).first()
        
        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        # Verificar permisos sobre el tomo
        permiso = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == current_user.id,
            PermisoTomo.tomo_id == documento.tomo_id,
            PermisoTomo.activo == True
        ).first()
        
        if not permiso:
            raise HTTPException(
                status_code=403, 
                detail="No tienes permisos para ver este documento"
            )
        
        return {
            "id": documento.id,
            "nombre": documento.nombre,
            "contenido": documento.contenido,
            "descripcion": documento.descripcion,
            "tipo": documento.tipo,
            "fecha_creacion": documento.fecha_creacion.isoformat(),
            "tomo": documento.tomo.nombre,
            "usuario": documento.usuario.nombre_completo if documento.usuario else "Usuario desconocido"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.delete("/documentos/{documento_id}")
async def eliminar_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Eliminar documento OCR (soft delete)
    """
    try:
        documento = db.query(DocumentoOCR).filter(
            DocumentoOCR.id == documento_id,
            DocumentoOCR.activo == True
        ).first()
        
        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        # Solo el creador o admin puede eliminar
        if documento.usuario_id != current_user.id and current_user.rol.nombre != "Admin":
            raise HTTPException(
                status_code=403,
                detail="Solo puedes eliminar tus propios documentos"
            )
        
        documento.activo = False
        documento.fecha_eliminacion = datetime.now()
        
        db.commit()
        
        return {"success": True, "message": "Documento eliminado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.put("/documentos/{documento_id}")
async def actualizar_documento(
    documento_id: int,
    nombre: Optional[str] = Form(None),
    contenido: Optional[str] = Form(None),
    descripcion: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualizar documento OCR
    """
    try:
        documento = db.query(DocumentoOCR).filter(
            DocumentoOCR.id == documento_id,
            DocumentoOCR.activo == True
        ).first()
        
        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        # Solo el creador puede editar
        if documento.usuario_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Solo puedes editar tus propios documentos"
            )
        
        # Actualizar campos si se proporcionan
        if nombre is not None:
            documento.nombre = nombre
        if contenido is not None:
            documento.contenido = contenido
        if descripcion is not None:
            documento.descripcion = descripcion
            
        documento.fecha_modificacion = datetime.now()
        
        db.commit()
        db.refresh(documento)
        
        return {
            "success": True,
            "message": "Documento actualizado exitosamente",
            "documento": {
                "id": documento.id,
                "nombre": documento.nombre,
                "descripcion": documento.descripcion
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.get("/documentos/buscar")
async def buscar_documentos(
    query: str,
    tomo_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Buscar en contenido de documentos OCR
    """
    try:
        # Obtener tomos con permisos
        tomos_con_permisos = db.query(PermisoTomo.tomo_id).filter(
            PermisoTomo.usuario_id == current_user.id,
            PermisoTomo.activo == True
        ).subquery()
        
        # Query base
        query_docs = db.query(DocumentoOCR).filter(
            DocumentoOCR.tomo_id.in_(tomos_con_permisos),
            DocumentoOCR.activo == True
        )
        
        # Filtrar por tomo específico si se proporciona
        if tomo_id:
            query_docs = query_docs.filter(DocumentoOCR.tomo_id == tomo_id)
        
        # Buscar en nombre, descripción y contenido
        search_filter = (
            DocumentoOCR.nombre.ilike(f"%{query}%") |
            DocumentoOCR.descripcion.ilike(f"%{query}%") |
            DocumentoOCR.contenido.ilike(f"%{query}%")
        )
        
        documentos = query_docs.filter(search_filter).order_by(
            DocumentoOCR.fecha_creacion.desc()
        ).limit(50).all()
        
        resultados = []
        for doc in documentos:
            # Buscar contexto en el contenido
            contenido_lower = doc.contenido.lower()
            query_lower = query.lower()
            
            inicio = contenido_lower.find(query_lower)
            if inicio != -1:
                # Extraer contexto alrededor de la coincidencia
                inicio_contexto = max(0, inicio - 100)
                fin_contexto = min(len(doc.contenido), inicio + len(query) + 100)
                contexto = doc.contenido[inicio_contexto:fin_contexto]
                
                if inicio_contexto > 0:
                    contexto = "..." + contexto
                if fin_contexto < len(doc.contenido):
                    contexto = contexto + "..."
            else:
                contexto = doc.contenido[:200] + "..." if len(doc.contenido) > 200 else doc.contenido
            
            resultados.append({
                "id": doc.id,
                "nombre": doc.nombre,
                "descripcion": doc.descripcion,
                "contexto": contexto,
                "tomo": doc.tomo.nombre,
                "fecha_creacion": doc.fecha_creacion.isoformat(),
                "usuario": doc.usuario.nombre_completo if doc.usuario else "Usuario desconocido"
            })
        
        return {
            "resultados": resultados,
            "total": len(resultados),
            "query": query
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")