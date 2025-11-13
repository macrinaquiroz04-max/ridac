# backend/app/routes/permisos.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Union
from pydantic import BaseModel
import logging

from app.database import get_db
from app.controllers.permiso_tomo_controller import PermisoTomoController
from app.middlewares.auth_middleware import get_current_user
from app.models.usuario import Usuario
from app.utils.auditoria_utils import registrar_auditoria

router = APIRouter()
logger = logging.getLogger(__name__)

# Función helper para generar descripción detallada de cambios de permisos
def generar_descripcion_cambios_permisos(
    usuario_info: str,
    permisos_anteriores: dict,
    permisos_nuevos: dict,
    tomo_nombre: str = None
) -> str:
    """
    Genera una descripción legible y detallada de los cambios de permisos.
    
    Ejemplos de salida:
    - "Se otorgaron permisos de LECTURA al usuario Juan Pérez (Analista)"
    - "Se quitaron permisos de BÚSQUEDA y EXPORTACIÓN al usuario María López"
    - "Se otorgó acceso COMPLETO al usuario Carlos García"
    """
    permisos_otorgados = []
    permisos_quitados = []
    
    # Mapeo de permisos a nombres legibles
    permisos_map = {
        'puede_ver': 'LECTURA',
        'puede_buscar': 'BÚSQUEDA',
        'puede_exportar': 'EXPORTACIÓN'
    }
    
    # Detectar cambios
    for key, nombre in permisos_map.items():
        antes = permisos_anteriores.get(key, False)
        ahora = permisos_nuevos.get(key, False)
        
        if not antes and ahora:
            permisos_otorgados.append(nombre)
        elif antes and not ahora:
            permisos_quitados.append(nombre)
    
    # Generar descripción
    descripciones = []
    
    if permisos_otorgados:
        if len(permisos_otorgados) == 3:
            descripciones.append(f"Se otorgó ACCESO COMPLETO a {usuario_info}")
        else:
            permisos_str = " y ".join(permisos_otorgados) if len(permisos_otorgados) == 2 else ", ".join(permisos_otorgados)
            descripciones.append(f"Se otorgaron permisos de {permisos_str} a {usuario_info}")
    
    if permisos_quitados:
        if len(permisos_quitados) == 3:
            descripciones.append(f"Se revocó TODO el acceso a {usuario_info}")
        else:
            permisos_str = " y ".join(permisos_quitados) if len(permisos_quitados) == 2 else ", ".join(permisos_quitados)
            descripciones.append(f"Se quitaron permisos de {permisos_str} a {usuario_info}")
    
    # Si no hay cambios
    if not descripciones:
        descripciones.append(f"Se actualizaron permisos de {usuario_info} (sin cambios efectivos)")
    
    # Agregar información del tomo si está disponible
    if tomo_nombre:
        descripciones[0] += f" para el tomo '{tomo_nombre}'"
    
    return " | ".join(descripciones)

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
    request: Request,
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
        # Logging mejorado
        logger.info(f"Asignando permiso - Usuario: {permiso_data.usuario_id}, Tomo: {permiso_data.tomo_id}")
        logger.debug(f"Permisos - Ver: {permiso_data.puede_ver}, Buscar: {permiso_data.puede_buscar}, Exportar: {permiso_data.puede_exportar}")
        
        # Verificar si ya existe un permiso para determinar si es nuevo o modificación
        from app.models.permiso_tomo import PermisoTomo
        permiso_existente = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == permiso_data.usuario_id,
            PermisoTomo.tomo_id == permiso_data.tomo_id
        ).first()
        
        # Obtener información del usuario afectado para auditoría
        usuario_afectado = db.query(Usuario).filter(Usuario.id == permiso_data.usuario_id).first()
        usuario_info = {
            "nombre": usuario_afectado.nombre_completo if usuario_afectado else "Desconocido",
            "username": usuario_afectado.username if usuario_afectado else "desconocido",
            "rol": usuario_afectado.rol.nombre if usuario_afectado and usuario_afectado.rol else "Sin rol"
        }
        
        # Obtener información del tomo
        from app.models.tomo import Tomo
        tomo = db.query(Tomo).filter(Tomo.id == permiso_data.tomo_id).first()
        tomo_info = {
            "nombre": tomo.nombre_archivo if tomo else "Desconocido",
            "numero_tomo": tomo.numero_tomo if tomo else None
        }
        
        # Guardar valores anteriores si existe
        valores_anteriores = None
        if permiso_existente:
            valores_anteriores = {
                "puede_ver": permiso_existente.puede_ver,
                "puede_buscar": permiso_existente.puede_buscar,
                "puede_exportar": permiso_existente.puede_exportar
            }
        
        permiso = PermisoTomoController.asignar_permiso(
            db=db,
            usuario_id=permiso_data.usuario_id,
            tomo_id=permiso_data.tomo_id,
            puede_ver=permiso_data.puede_ver,
            puede_buscar=permiso_data.puede_buscar,
            puede_exportar=permiso_data.puede_exportar,
            usuario_admin_id=current_user.id
        )
        
        logger.debug(f"Resultado del permiso: {permiso}")
        
        # Si se retorna None, significa que se eliminó un permiso vacío (TODOS en False)
        if permiso is None:
            # 📝 AUDITORÍA: REVOCACIÓN DE PERMISOS
            registrar_auditoria(
                request=request,
                usuario_id=current_user.id,
                accion="REVOCACION_PERMISOS",
                tabla_afectada="permisos_tomo",
                valores_anteriores={
                    "usuario_afectado": f"{usuario_info['nombre']} ({usuario_info['rol']})",
                    "username": usuario_info['username'],
                    "tomo": tomo_info['nombre'],
                    "usuario_id": permiso_data.usuario_id,
                    "tomo_id": permiso_data.tomo_id,
                    "permisos_anteriores": valores_anteriores
                }
            )
            return MensajeResponse(
                message=f"Permisos revocados para {usuario_info['nombre']} ({usuario_info['rol']})",
                success=True
            )
        
        # Determinar la acción basándose en si existía antes y qué permisos tiene ahora
        tiene_permisos_activos = permiso.puede_ver or permiso.puede_buscar or permiso.puede_exportar
        
        if not permiso_existente:
            # NUEVA ASIGNACIÓN
            accion = "ASIGNACION_PERMISOS"
            mensaje_log = f"Asignó permisos a {usuario_info['nombre']} ({usuario_info['rol']})"
        elif valores_anteriores:
            # Verificar si está agregando o quitando permisos
            permisos_antes = sum([valores_anteriores.get('puede_ver', False), 
                                 valores_anteriores.get('puede_buscar', False), 
                                 valores_anteriores.get('puede_exportar', False)])
            permisos_ahora = sum([permiso.puede_ver, permiso.puede_buscar, permiso.puede_exportar])
            
            if permisos_ahora > permisos_antes:
                accion = "AMPLIACION_PERMISOS"
                mensaje_log = f"Amplió permisos de {usuario_info['nombre']} ({usuario_info['rol']})"
            elif permisos_ahora < permisos_antes:
                accion = "REDUCCION_PERMISOS"
                mensaje_log = f"Redujo permisos de {usuario_info['nombre']} ({usuario_info['rol']})"
            else:
                accion = "MODIFICACION_PERMISOS"
                mensaje_log = f"Modificó permisos de {usuario_info['nombre']} ({usuario_info['rol']})"
        else:
            accion = "MODIFICACION_PERMISOS"
            mensaje_log = f"Modificó permisos de {usuario_info['nombre']} ({usuario_info['rol']})"
        
        logger.info(mensaje_log)
        
        # 📝 AUDITORÍA
        registrar_auditoria(
            request=request,
            usuario_id=current_user.id,
            accion=accion,
            tabla_afectada="permisos_tomo",
            registro_id=permiso.id,
            valores_anteriores=valores_anteriores,
            valores_nuevos={
                "usuario_afectado": f"{usuario_info['nombre']} ({usuario_info['rol']})",
                "username": usuario_info['username'],
                "tomo": tomo_info['nombre'],
                "usuario_id": permiso.usuario_id,
                "tomo_id": permiso.tomo_id,
                "puede_ver": permiso.puede_ver,
                "puede_buscar": permiso.puede_buscar,
                "puede_exportar": permiso.puede_exportar
            }
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
    request: Request,
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
        
        # Obtener información del usuario afectado para auditoría
        usuario_afectado = db.query(Usuario).filter(Usuario.id == permisos_data.usuario_id).first()
        usuario_info = f"{usuario_afectado.nombre_completo} ({usuario_afectado.rol.nombre})" if usuario_afectado and usuario_afectado.rol else "Usuario desconocido"
        
        # Generar descripción detallada para permisos masivos
        permisos_otorgados = []
        for key, value in permisos_data.permisos.items():
            if value:
                if key == 'puede_ver':
                    permisos_otorgados.append('LECTURA')
                elif key == 'puede_buscar':
                    permisos_otorgados.append('BÚSQUEDA')
                elif key == 'puede_exportar':
                    permisos_otorgados.append('EXPORTACIÓN')
        
        if len(permisos_otorgados) == 3:
            descripcion = f"Se otorgó ACCESO COMPLETO a {usuario_info} en {len(permisos_data.tomos_ids)} tomos"
        elif permisos_otorgados:
            permisos_str = ", ".join(permisos_otorgados)
            descripcion = f"Se otorgaron permisos de {permisos_str} a {usuario_info} en {len(permisos_data.tomos_ids)} tomos"
        else:
            descripcion = f"Se configuraron permisos personalizados para {usuario_info} en {len(permisos_data.tomos_ids)} tomos"
        
        # 📝 AUDITORÍA: Registrar permisos masivos
        registrar_auditoria(
            request=request,
            usuario_id=current_user.id,
            accion="MODIFICAR_PERMISOS",
            tabla_afectada="permisos_tomo",
            descripcion=descripcion,
            valores_nuevos={
                "usuario_afectado": usuario_info,
                "username": usuario_afectado.username if usuario_afectado else "desconocido",
                "total_tomos": len(permisos_data.tomos_ids),
                "tomos_ids": permisos_data.tomos_ids,
                "permisos": permisos_data.permisos,
                "permisos_legibles": ", ".join(permisos_otorgados) if permisos_otorgados else "Ninguno",
                "total_permisos": len(permisos),
                "tipo": "masivo"
            }
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
    request: Request,
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
        
        # Obtener información del usuario afectado y tomo para auditoría
        usuario_afectado = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        usuario_info = f"{usuario_afectado.nombre_completo} ({usuario_afectado.rol.nombre})" if usuario_afectado and usuario_afectado.rol else "Usuario desconocido"
        
        from app.models.tomo import Tomo
        tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
        tomo_nombre = tomo.nombre_archivo if tomo else "Tomo desconocido"
        
        # Generar descripción detallada del cambio
        descripcion = generar_descripcion_cambios_permisos(
            usuario_info=usuario_info,
            permisos_anteriores={
                "puede_ver": permiso_actual.puede_ver,
                "puede_buscar": permiso_actual.puede_buscar,
                "puede_exportar": permiso_actual.puede_exportar
            },
            permisos_nuevos={
                "puede_ver": permiso_actualizado.puede_ver,
                "puede_buscar": permiso_actualizado.puede_buscar,
                "puede_exportar": permiso_actualizado.puede_exportar
            },
            tomo_nombre=tomo_nombre
        )
        
        # 📝 AUDITORÍA
        registrar_auditoria(
            request=request,
            usuario_id=current_user.id,
            accion="MODIFICAR_PERMISOS",
            tabla_afectada="permisos_tomo",
            registro_id=permiso_actualizado.id,
            descripcion=descripcion,
            valores_anteriores={
                "puede_ver": permiso_actual.puede_ver,
                "puede_buscar": permiso_actual.puede_buscar,
                "puede_exportar": permiso_actual.puede_exportar
            },
            valores_nuevos={
                "usuario_afectado": usuario_info,
                "username": usuario_afectado.username if usuario_afectado else "desconocido",
                "tomo": tomo_nombre,
                "usuario_id": permiso_actualizado.usuario_id,
                "tomo_id": permiso_actualizado.tomo_id,
                "puede_ver": permiso_actualizado.puede_ver,
                "puede_buscar": permiso_actualizado.puede_buscar,
                "puede_exportar": permiso_actualizado.puede_exportar
            }
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
    request: Request,
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
        # Obtener info del permiso antes de revocar
        permisos_actuales = PermisoTomoController.obtener_permisos_usuario(db, usuario_id)
        permiso_a_revocar = next((p for p in permisos_actuales if p.tomo_id == tomo_id), None)
        
        revocado = PermisoTomoController.revocar_permiso(db, usuario_id, tomo_id)
        
        if not revocado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró permiso para revocar"
            )
        
        # 📝 AUDITORÍA
        if permiso_a_revocar:
            # Obtener información del usuario afectado y tomo
            usuario_afectado = db.query(Usuario).filter(Usuario.id == usuario_id).first()
            usuario_info = f"{usuario_afectado.nombre_completo} ({usuario_afectado.rol.nombre})" if usuario_afectado and usuario_afectado.rol else "Usuario desconocido"
            
            from app.models.tomo import Tomo
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
            tomo_nombre = tomo.nombre_archivo if tomo else "Tomo desconocido"
            
            registrar_auditoria(
                request=request,
                usuario_id=current_user.id,
                accion="REVOCAR_PERMISO",
                tabla_afectada="permisos_tomo",
                valores_anteriores={
                    "usuario_afectado": usuario_info,
                    "username": usuario_afectado.username if usuario_afectado else "desconocido",
                    "tomo": tomo_nombre,
                    "usuario_id": usuario_id,
                    "tomo_id": tomo_id,
                    "puede_ver": permiso_a_revocar.puede_ver,
                    "puede_buscar": permiso_a_revocar.puede_buscar,
                    "puede_exportar": permiso_a_revocar.puede_exportar
                }
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