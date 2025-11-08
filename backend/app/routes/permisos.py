# backend/app/routes/permisos.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Union
from pydantic import BaseModel

from app.database import get_db
from app.controllers.permiso_tomo_controller import PermisoTomoController
from app.middlewares.auth_middleware import get_current_user
from app.models.usuario import Usuario

router = APIRouter()

# Modelos Pydantic para requests/responses
class PermisoTomoCreate(BaseModel):
    usuario_id: int
    tomo_id: int
    puede_ver: bool = True
    puede_buscar: bool = False
    puede_exportar: bool = False

class PermisoTomoUpdate(BaseModel):
    puede_ver: Optional[bool] = None
    puede_buscar: Optional[bool] = None
    puede_exportar: Optional[bool] = None

class PermisosMasivos(BaseModel):
    usuario_id: int
    tomos_ids: List[int]
    permisos: Dict[str, bool]

class PermisoTomoResponse(BaseModel):
    id: int
    usuario_id: int
    tomo_id: int
    puede_ver: bool
    puede_buscar: bool
    puede_exportar: bool
    created_at: str
    
    class Config:
        from_attributes = True

class MensajeResponse(BaseModel):
    message: str
    success: bool = True

# Tipo de respuesta que puede ser un permiso o un mensaje
PermisoTomoResult = Union[PermisoTomoResponse, MensajeResponse]

@router.post("/tomos/permisos")
async def asignar_permiso_tomo(
    permiso_data: PermisoTomoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
) -> PermisoTomoResult:
    """
    Asigna permisos específicos a un usuario para un tomo
    Solo administradores pueden asignar permisos
    """
    # Verificar permisos de administrador
    if not PermisoTomoController.verificar_permisos_administrador(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden asignar permisos de tomos"
        )
    
    try:
        # Debug logging
        print(f"DEBUG: Asignando permiso - Usuario: {permiso_data.usuario_id}, Tomo: {permiso_data.tomo_id}")
        print(f"DEBUG: Permisos - Ver: {permiso_data.puede_ver}, Buscar: {permiso_data.puede_buscar}, Exportar: {permiso_data.puede_exportar}")
        
        permiso = PermisoTomoController.asignar_permiso(
            db=db,
            usuario_id=permiso_data.usuario_id,
            tomo_id=permiso_data.tomo_id,
            puede_ver=permiso_data.puede_ver,
            puede_buscar=permiso_data.puede_buscar,
            puede_exportar=permiso_data.puede_exportar,
            usuario_admin_id=current_user.id
        )
        
        print(f"DEBUG: Resultado del permiso: {permiso}")
        
        # Si se retorna None, significa que se eliminó un permiso vacío
        if permiso is None:
            return MensajeResponse(
                message="Permiso eliminado - todos los permisos estaban desactivados",
                success=True
            )
        
        return PermisoTomoResponse(
            id=permiso.id,
            usuario_id=permiso.usuario_id,
            tomo_id=permiso.tomo_id,
            puede_ver=permiso.puede_ver,
            puede_buscar=permiso.puede_buscar,
            puede_exportar=permiso.puede_exportar,
            created_at=permiso.created_at.isoformat()
        )
    except Exception as e:
        print(f"ERROR en asignar_permiso_tomo: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al asignar permiso: {str(e)}"
        )

@router.post("/tomos/permisos/masivos", response_model=List[PermisoTomoResponse])
async def asignar_permisos_masivos(
    permisos_data: PermisosMasivos,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Asigna permisos a múltiples tomos para un usuario
    """
    # Verificar permisos de administrador
    if not PermisoTomoController.verificar_permisos_administrador(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden asignar permisos de tomos"
        )
    
    try:
        permisos = PermisoTomoController.asignar_permisos_masivos(
            db=db,
            usuario_id=permisos_data.usuario_id,
            tomos_ids=permisos_data.tomos_ids,
            permisos=permisos_data.permisos,
            usuario_admin_id=current_user.id
        )
        
        return [
            PermisoTomoResponse(
                id=permiso.id,
                usuario_id=permiso.usuario_id,
                tomo_id=permiso.tomo_id,
                puede_ver=permiso.puede_ver,
                puede_buscar=permiso.puede_buscar,
                puede_exportar=permiso.puede_exportar,
                created_at=permiso.created_at.isoformat()
            )
            for permiso in permisos
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al asignar permisos masivos: {str(e)}"
        )

@router.get("/usuarios/{usuario_id}/tomos/permisos")
async def obtener_permisos_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene todos los permisos de tomos de un usuario
    """
    # Los usuarios pueden ver sus propios permisos, los admins pueden ver cualquiera
    if current_user.id != usuario_id and not PermisoTomoController.verificar_permisos_administrador(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta información"
        )
    
    try:
        permisos = PermisoTomoController.obtener_permisos_usuario(db, usuario_id)
        return [
            {
                "id": permiso.id,
                "tomo_id": permiso.tomo_id,
                "puede_ver": permiso.puede_ver,
                "puede_buscar": permiso.puede_buscar,
                "puede_exportar": permiso.puede_exportar,
                "fecha_asignacion": permiso.created_at.isoformat()
            }
            for permiso in permisos
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener permisos: {str(e)}"
        )

@router.get("/usuarios/{usuario_id}/tomos-accesibles")
async def obtener_tomos_accesibles_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene todos los tomos a los que tiene acceso un usuario con información detallada
    """
    # Los usuarios pueden ver sus propios tomos, los administradores pueden ver cualquiera
    if current_user.id != usuario_id and not PermisoTomoController.verificar_permisos_administrador(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta información"
        )
    
    try:
        # Devolver array directo, compatible con frontend
        tomos_accesibles = PermisoTomoController.obtener_tomos_accesibles_usuario(db, usuario_id)
        return tomos_accesibles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener tomos accesibles: {str(e)}"
        )
            detail=f"Error al obtener tomos accesibles: {str(e)}"
        )

@router.get("/tomos/{tomo_id}/permisos")
async def obtener_permisos_tomo(
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene todos los usuarios que tienen permisos para un tomo específico
    Solo administradores pueden ver esta información
    """
    if not PermisoTomoController.verificar_permisos_administrador(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver los permisos de tomos"
        )
    
    try:
        permisos = PermisoTomoController.obtener_permisos_tomo(db, tomo_id)
        return [
            {
                "id": permiso.id,
                "usuario_id": permiso.usuario_id,
                "puede_ver": permiso.puede_ver,
                "puede_buscar": permiso.puede_buscar,
                "puede_exportar": permiso.puede_exportar,
                "fecha_asignacion": permiso.created_at.isoformat()
            }
            for permiso in permisos
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener permisos del tomo: {str(e)}"
        )

@router.put("/usuarios/{usuario_id}/tomos/{tomo_id}/permisos")
async def actualizar_permiso_tomo(
    usuario_id: int,
    tomo_id: int,
    permiso_update: PermisoTomoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualiza los permisos de un usuario para un tomo específico
    """
    if not PermisoTomoController.verificar_permisos_administrador(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden modificar permisos de tomos"
        )
    
    try:
        # Obtener permisos actuales
        permisos_actuales = PermisoTomoController.obtener_permisos_usuario(db, usuario_id)
        permiso_actual = next((p for p in permisos_actuales if p.tomo_id == tomo_id), None)
        
        if not permiso_actual:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró permiso existente para este usuario y tomo"
            )
        
        # Actualizar solo los campos proporcionados
        puede_ver = permiso_update.puede_ver if permiso_update.puede_ver is not None else permiso_actual.puede_ver
        puede_buscar = permiso_update.puede_buscar if permiso_update.puede_buscar is not None else permiso_actual.puede_buscar
        puede_exportar = permiso_update.puede_exportar if permiso_update.puede_exportar is not None else permiso_actual.puede_exportar
        
        permiso_actualizado = PermisoTomoController.asignar_permiso(
            db=db,
            usuario_id=usuario_id,
            tomo_id=tomo_id,
            puede_ver=puede_ver,
            puede_buscar=puede_buscar,
            puede_exportar=puede_exportar,
            usuario_admin_id=current_user.id
        )
        
        return {
            "id": permiso_actualizado.id,
            "usuario_id": permiso_actualizado.usuario_id,
            "tomo_id": permiso_actualizado.tomo_id,
            "puede_ver": permiso_actualizado.puede_ver,
            "puede_buscar": permiso_actualizado.puede_buscar,
            "puede_exportar": permiso_actualizado.puede_exportar,
            "fecha_actualizacion": permiso_actualizado.updated_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar permiso: {str(e)}"
        )

@router.delete("/usuarios/{usuario_id}/tomos/{tomo_id}/permisos")
async def revocar_permiso_tomo(
    usuario_id: int,
    tomo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Revoca todos los permisos de un usuario para un tomo específico
    """
    if not PermisoTomoController.verificar_permisos_administrador(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden revocar permisos de tomos"
        )
    
    try:
        revocado = PermisoTomoController.revocar_permiso(db, usuario_id, tomo_id)
        
        if not revocado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró permiso para revocar"
            )
        
        return {"message": "Permiso revocado exitosamente"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al revocar permiso: {str(e)}"
        )

@router.get("/carpetas/{carpeta_id}/usuarios-con-permisos")
async def obtener_usuarios_con_permisos_carpeta(
    carpeta_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtiene todos los usuarios que tienen permisos para tomos de una carpeta específica
    """
    if not PermisoTomoController.verificar_permisos_administrador(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden ver los permisos de carpetas"
        )
    
    try:
        usuarios_permisos = PermisoTomoController.obtener_usuarios_con_permisos_carpeta(db, carpeta_id)
        return usuarios_permisos
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuarios con permisos: {str(e)}"
        )

@router.get("/verificar/{usuario_id}/tomo/{tomo_id}")
async def verificar_permiso_usuario_tomo(
    usuario_id: int,
    tomo_id: int,
    tipo_permiso: str = "ver",
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Verifica si un usuario tiene un permiso específico para un tomo
    """
    # Solo admins o el mismo usuario pueden verificar permisos
    if current_user.id != usuario_id and not PermisoTomoController.verificar_permisos_administrador(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para verificar esta información"
        )
    
    if tipo_permiso not in ["ver", "buscar", "exportar"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de permiso inválido. Debe ser: ver, buscar o exportar"
        )
    
    try:
        tiene_permiso = PermisoTomoController.verificar_permiso(db, usuario_id, tomo_id, tipo_permiso)
        return {
            "usuario_id": usuario_id,
            "tomo_id": tomo_id,
            "tipo_permiso": tipo_permiso,
            "tiene_permiso": tiene_permiso
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar permiso: {str(e)}"
        )