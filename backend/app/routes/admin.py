# backend/app/routes/admin.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.database import get_db
from app.models.usuario import Usuario, Rol
from app.models.permiso import PermisoCarpeta, PermisoSistema
from app.middlewares.auth_middleware import get_current_active_user, get_current_user
from app.middlewares.permission_middleware import require_admin
from app.utils.security import hash_password
from app.utils.auditoria_utils import registrar_auditoria
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Administración"],
    dependencies=[Depends(require_admin)]
)


# Schemas
class UsuarioCreate(BaseModel):
    username: str
    email: EmailStr
    nombre: str
    password: str
    rol_id: int
    activo: bool = True


class UsuarioUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    nombre: Optional[str] = None
    password: Optional[str] = None
    rol_id: Optional[int] = None
    activo: Optional[bool] = None


class UsuarioResponse(BaseModel):
    id: int
    username: str
    email: str
    nombre: str
    rol: Dict[str, Any]
    activo: bool
    ultimo_acceso: Optional[str]
    creado_en: str

    class Config:
        from_attributes = True


class RolResponse(BaseModel):
    id: int
    nombre: str
    codigo: Optional[str] = None
    descripcion: Optional[str] = None
    nivel_acceso: Optional[int] = 0

    class Config:
        from_attributes = True

class PermisoSistemaCreate(BaseModel):
    usuario_id: int
    gestionar_usuarios: bool = False
    gestionar_roles: bool = False
    gestionar_carpetas: bool = False
    procesar_ocr: bool = False
    ver_auditoria: bool = False
    configurar_sistema: bool = False
    exportar_datos: bool = False


class PermisoCarpetaCreate(BaseModel):
    usuario_id: int
    carpeta_id: int
    tipo: str  # 'lectura', 'escritura', 'admin'


# ==================== ROLES ====================

@router.get("/roles/{rol_id}", response_model=RolResponse)
async def obtener_rol(
    rol_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    GET /admin/roles/{rol_id}
    Obtener detalles de un rol específico.
    """
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    return rol

# ==================== USUARIOS ====================

@router.get("/usuarios", response_model=List[UsuarioResponse])
async def listar_usuarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    activo: Optional[bool] = Query(None),  # None = mostrar todos (activos e inactivos)
    rol_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    GET /admin/usuarios
    Listar todos los usuarios con filtros opcionales.
    Por defecto devuelve TODOS los usuarios (activos e inactivos).
    Usa ?activo=true para solo activos o ?activo=false para solo inactivos.
    """
    query = db.query(Usuario)

    if activo is not None:
        query = query.filter(Usuario.activo == activo)

    if rol_id is not None:
        query = query.filter(Usuario.rol_id == rol_id)

    # Ordenar por ID ascendente
    usuarios = query.order_by(Usuario.id.asc()).offset(skip).limit(limit).all()

    return [
        UsuarioResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            nombre=u.nombre_completo,
            rol={"id": u.rol.id, "nombre": u.rol.nombre},
            activo=u.activo,
            ultimo_acceso=u.ultimo_acceso.isoformat() if u.ultimo_acceso else None,
            creado_en=u.created_at.isoformat() if u.created_at else None
        )
        for u in usuarios
    ]


@router.get("/usuarios/{usuario_id}", response_model=UsuarioResponse)
async def obtener_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    GET /admin/usuarios/{usuario_id}
    Obtener detalles de un usuario específico.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    return UsuarioResponse(
        id=usuario.id,
        username=usuario.username,
        email=usuario.email,
        nombre=usuario.nombre,
        rol={"id": usuario.rol.id, "nombre": usuario.rol.nombre},
        activo=usuario.activo,
        ultimo_acceso=usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None,
        creado_en=usuario.created_at.isoformat()
    )


@router.post("/usuarios", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    usuario_data: UsuarioCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    POST /admin/usuarios
    Crear nuevo usuario.
    """
    # Validar contraseña
    from app.utils.validators import validate_password
    is_valid, error_message = validate_password(usuario_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Verificar que no exista username o email
    existing_user = db.query(Usuario).filter(
        (Usuario.username == usuario_data.username) |
        (Usuario.email == usuario_data.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username o email ya existe"
        )

    # Verificar que el rol exista
    rol = db.query(Rol).filter(Rol.id == usuario_data.rol_id).first()
    if not rol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )

    # Hash de la contraseña
    hashed_password = hash_password(usuario_data.password)

    # Crear usuario con SQLAlchemy (deja que la secuencia genere el ID)
    nuevo_usuario = Usuario(
        username=usuario_data.username,
        email=usuario_data.email,
        nombre_completo=usuario_data.nombre,
        password=hashed_password,
        rol_id=usuario_data.rol_id,
        activo=usuario_data.activo,
        debe_cambiar_password=True,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    logger.info(f"Usuario creado: {nuevo_usuario.username} por {current_user.username}")

    # 📝 REGISTRAR AUDITORÍA
    registrar_auditoria(
        usuario_id=current_user.id,
        accion="CREAR_USUARIO",
        request=request,
        tabla_afectada="usuarios",
        registro_id=nuevo_usuario.id,
        valores_nuevos={
            "username": nuevo_usuario.username,
            "email": nuevo_usuario.email,
            "nombre_completo": nuevo_usuario.nombre_completo,
            "rol_id": nuevo_usuario.rol_id,
            "activo": nuevo_usuario.activo
        }
    )

    return UsuarioResponse(
        id=nuevo_usuario.id,
        username=nuevo_usuario.username,
        email=nuevo_usuario.email,
        nombre=nuevo_usuario.nombre,
        rol={"id": nuevo_usuario.rol.id, "nombre": nuevo_usuario.rol.nombre},
        activo=nuevo_usuario.activo,
        ultimo_acceso=None,
        creado_en=nuevo_usuario.created_at.isoformat()
    )


@router.put("/usuarios/{usuario_id}", response_model=UsuarioResponse)
async def actualizar_usuario(
    usuario_id: int,
    usuario_data: UsuarioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    PUT /admin/usuarios/{usuario_id}
    Actualizar usuario existente.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Actualizar campos
    if usuario_data.username is not None:
        # Verificar que no exista otro usuario con ese username
        existing = db.query(Usuario).filter(
            Usuario.username == usuario_data.username,
            Usuario.id != usuario_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username ya existe"
            )
        usuario.username = usuario_data.username

    if usuario_data.email is not None:
        # Verificar que no exista otro usuario con ese email
        existing = db.query(Usuario).filter(
            Usuario.email == usuario_data.email,
            Usuario.id != usuario_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ya existe"
            )
        usuario.email = usuario_data.email

    if usuario_data.nombre is not None:
        usuario.nombre_completo = usuario_data.nombre

    if usuario_data.password is not None:
        # Validar contraseña
        from app.utils.validators import validate_password
        is_valid, error_message = validate_password(usuario_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        usuario.password = hash_password(usuario_data.password)

    if usuario_data.rol_id is not None:
        rol = db.query(Rol).filter(Rol.id == usuario_data.rol_id).first()
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rol no encontrado"
            )
        usuario.rol_id = usuario_data.rol_id

    # Guardar valores anteriores para auditoría
    valores_anteriores = {
        "username": usuario.username,
        "email": usuario.email,
        "nombre_completo": usuario.nombre_completo,
        "rol_id": usuario.rol_id,
        "activo": usuario.activo
    }

    if usuario_data.activo is not None:
        usuario.activo = usuario_data.activo

    db.commit()
    db.refresh(usuario)

    # 📝 REGISTRAR AUDITORÍA
    registrar_auditoria(
        usuario_id=current_user.id,
        accion="MODIFICAR_USUARIO",
        request=request,
        tabla_afectada="usuarios",
        registro_id=usuario.id,
        valores_anteriores=valores_anteriores,
        valores_nuevos={
            "username": usuario.username,
            "email": usuario.email,
            "nombre_completo": usuario.nombre_completo,
            "rol_id": usuario.rol_id,
            "activo": usuario.activo
        }
    )

    logger.info(f"Usuario actualizado: {usuario.username} por {current_user.username}")

    return UsuarioResponse(
        id=usuario.id,
        username=usuario.username,
        email=usuario.email,
        nombre=usuario.nombre,
        rol={"id": usuario.rol.id, "nombre": usuario.rol.nombre},
        activo=usuario.activo,
        ultimo_acceso=usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None,
        creado_en=usuario.created_at.isoformat()
    )


@router.delete("/usuarios/{usuario_id}")
async def eliminar_usuario(
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    DELETE /admin/usuarios/{usuario_id}
    Eliminar usuario DEFINITIVAMENTE de la base de datos.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # No permitir auto-eliminación
    if usuario.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propio usuario"
        )

    try:
        # ELIMINAR DEFINITIVAMENTE
        username = usuario.username
        
        # Guardar datos para auditoría antes de eliminar
        valores_anteriores = {
            "username": usuario.username,
            "email": usuario.email,
            "nombre_completo": usuario.nombre_completo,
            "rol_id": usuario.rol_id,
            "activo": usuario.activo
        }
        
        # Eliminar con expire_on_commit=False para evitar cargar relaciones
        db.expire_on_commit = False
        db.delete(usuario)
        db.commit()

        logger.info(f"✅ Usuario ELIMINADO DEFINITIVAMENTE: {username} por {current_user.username}")

        # 📝 REGISTRAR AUDITORÍA
        registrar_auditoria(
            usuario_id=current_user.id,
            accion="ELIMINAR_USUARIO",
            request=request,
            tabla_afectada="usuarios",
            registro_id=usuario_id,
            valores_anteriores=valores_anteriores
        )

        return {
            "message": "Usuario eliminado definitivamente",
            "usuario_id": usuario_id
        }
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error eliminando usuario {usuario_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar usuario: {str(e)}"
        )


@router.patch("/usuarios/{usuario_id}/desactivar")
async def desactivar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    PATCH /admin/usuarios/{usuario_id}/desactivar
    Desactivar usuario (soft delete - mantiene registro pero inactivo).
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # No permitir auto-desactivación
    if usuario.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivarse a sí mismo"
        )

    # Desactivar usuario
    usuario.activo = False
    db.commit()

    logger.info(f"⏸️ Usuario DESACTIVADO: {usuario.username} por {current_user.username}")

    return {
        "message": "Usuario desactivado correctamente",
        "usuario_id": usuario_id,
        "activo": False
    }


@router.patch("/usuarios/{usuario_id}/activar")
async def activar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    PATCH /admin/usuarios/{usuario_id}/activar
    Activar usuario previamente desactivado.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Activar usuario
    usuario.activo = True
    db.commit()

    logger.info(f"▶️ Usuario ACTIVADO: {usuario.username} por {current_user.username}")

    return {
        "message": "Usuario activado correctamente",
        "usuario_id": usuario_id,
        "activo": True
    }


# ==================== ROLES ====================

@router.get("/roles")
async def listar_roles(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    GET /admin/roles
    Listar todos los roles disponibles.
    """
    roles = db.query(Rol).all()

    return [
        {
            "id": r.id,
            "nombre": r.nombre,
            "descripcion": r.descripcion
        }
        for r in roles
    ]


# ==================== PERMISOS ====================

@router.get("/usuarios/{usuario_id}/permisos-sistema")
async def listar_permisos_sistema(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    GET /admin/usuarios/{usuario_id}/permisos-sistema
    Listar permisos de sistema de un usuario.
    """
    permisos = db.query(PermisoSistema).filter(
        PermisoSistema.usuario_id == usuario_id
    ).all()

    return [
        {
            "id": p.id,
            "gestionar_usuarios": p.gestionar_usuarios,
            "gestionar_roles": p.gestionar_roles,
            "gestionar_carpetas": p.gestionar_carpetas,
            "procesar_ocr": p.procesar_ocr,
            "ver_auditoria": p.ver_auditoria,
            "configurar_sistema": p.configurar_sistema,
            "exportar_datos": p.exportar_datos,
            "created_at": p.created_at.isoformat() if p.created_at else None
        }
        for p in permisos
    ]


@router.post("/usuarios/{usuario_id}/permisos-sistema", status_code=status.HTTP_201_CREATED)
async def agregar_permiso_sistema(
    usuario_id: int,
    permiso_data: PermisoSistemaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    POST /admin/usuarios/{usuario_id}/permisos-sistema
    Agregar permiso de sistema a un usuario.
    """
    # Verificar que el usuario exista
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Verificar si ya existe un registro de permisos para el usuario
    existing = db.query(PermisoSistema).filter(
        PermisoSistema.usuario_id == usuario_id
    ).first()

    if existing:
        # Actualizar permisos existentes
        existing.gestionar_usuarios = permiso_data.gestionar_usuarios
        existing.gestionar_roles = permiso_data.gestionar_roles
        existing.gestionar_carpetas = permiso_data.gestionar_carpetas
        existing.procesar_ocr = permiso_data.procesar_ocr
        existing.ver_auditoria = permiso_data.ver_auditoria
        existing.configurar_sistema = permiso_data.configurar_sistema
        existing.exportar_datos = permiso_data.exportar_datos
        permiso = existing
    else:
        # Crear nuevo permiso
        permiso = PermisoSistema(
            usuario_id=usuario_id,
            gestionar_usuarios=permiso_data.gestionar_usuarios,
            gestionar_roles=permiso_data.gestionar_roles,
            gestionar_carpetas=permiso_data.gestionar_carpetas,
            procesar_ocr=permiso_data.procesar_ocr,
            ver_auditoria=permiso_data.ver_auditoria,
            configurar_sistema=permiso_data.configurar_sistema,
            exportar_datos=permiso_data.exportar_datos
        )
        db.add(permiso)

    db.commit()
    db.refresh(permiso)

    logger.info(f"Permisos sistema actualizados para {usuario.username}")

    return {
        "id": permiso.id,
        "gestionar_usuarios": permiso.gestionar_usuarios,
        "gestionar_roles": permiso.gestionar_roles,
        "gestionar_carpetas": permiso.gestionar_carpetas,
        "procesar_ocr": permiso.procesar_ocr,
        "ver_auditoria": permiso.ver_auditoria,
        "configurar_sistema": permiso.configurar_sistema,
        "exportar_datos": permiso.exportar_datos,
        "usuario_id": permiso.usuario_id,
        "created_at": permiso.created_at.isoformat() if permiso.created_at else None
    }


@router.delete("/permisos-sistema/{permiso_id}")
async def eliminar_permiso_sistema(
    permiso_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    DELETE /admin/permisos-sistema/{permiso_id}
    Eliminar permiso de sistema.
    """
    permiso = db.query(PermisoSistema).filter(PermisoSistema.id == permiso_id).first()

    if not permiso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permiso no encontrado"
        )

    db.delete(permiso)
    db.commit()

    logger.info(f"Permisos sistema eliminados para usuario {permiso.usuario_id}")

    return {
        "message": "Permiso eliminado correctamente",
        "permiso_id": permiso_id
    }


@router.get("/usuarios/{usuario_id}/permisos-carpetas")
async def listar_permisos_carpetas(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    GET /admin/usuarios/{usuario_id}/permisos-carpetas
    Listar permisos de carpetas de un usuario.
    """
    permisos = db.query(PermisoCarpeta).filter(
        PermisoCarpeta.usuario_id == usuario_id
    ).all()

    return [
        {
            "id": p.id,
            "carpeta_id": p.carpeta_id,
            "carpeta_nombre": p.carpeta.nombre if p.carpeta else None,
            "tipo": p.tipo,
            "creado_en": p.creado_en.isoformat()
        }
        for p in permisos
    ]


@router.post("/usuarios/{usuario_id}/permisos-carpetas", status_code=status.HTTP_201_CREATED)
async def agregar_permiso_carpeta(
    usuario_id: int,
    permiso_data: PermisoCarpetaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    POST /admin/usuarios/{usuario_id}/permisos-carpetas
    Agregar permiso de carpeta a un usuario.
    """
    # Verificar que el usuario exista
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Verificar que la carpeta exista
    from app.models.carpeta import Carpeta
    carpeta = db.query(Carpeta).filter(Carpeta.id == permiso_data.carpeta_id).first()
    if not carpeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carpeta no encontrada"
        )

    # Verificar que no exista ya el permiso
    existing = db.query(PermisoCarpeta).filter(
        PermisoCarpeta.usuario_id == usuario_id,
        PermisoCarpeta.carpeta_id == permiso_data.carpeta_id
    ).first()

    if existing:
        # Actualizar tipo de permiso
        existing.tipo = permiso_data.tipo
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "usuario_id": existing.usuario_id,
            "carpeta_id": existing.carpeta_id,
            "tipo": existing.tipo,
            "creado_en": existing.creado_en.isoformat()
        }

    # Crear permiso
    permiso = PermisoCarpeta(
        usuario_id=usuario_id,
        carpeta_id=permiso_data.carpeta_id,
        tipo=permiso_data.tipo
    )

    db.add(permiso)
    db.commit()
    db.refresh(permiso)

    logger.info(f"Permiso carpeta agregado: {permiso_data.tipo} en carpeta {carpeta.nombre} a {usuario.username}")

    return {
        "id": permiso.id,
        "usuario_id": permiso.usuario_id,
        "carpeta_id": permiso.carpeta_id,
        "tipo": permiso.tipo,
        "creado_en": permiso.creado_en.isoformat()
    }


@router.delete("/permisos-carpetas/{permiso_id}")
async def eliminar_permiso_carpeta(
    permiso_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin)
):
    """
    DELETE /admin/permisos-carpetas/{permiso_id}
    Eliminar permiso de carpeta.
    """
    permiso = db.query(PermisoCarpeta).filter(PermisoCarpeta.id == permiso_id).first()

    if not permiso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permiso no encontrado"
        )

    db.delete(permiso)
    db.commit()

    logger.info(f"Permiso carpeta eliminado: {permiso.tipo}")

    return {
        "message": "Permiso eliminado correctamente",
        "permiso_id": permiso_id
    }


# ==================== TOMOS ACCESIBLES USUARIO ====================

@router.get("/permisos/usuarios/{usuario_id}/tomos-accesibles")
async def obtener_tomos_accesibles_usuario(
    usuario_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener tomos accesibles para un usuario específico"""
    try:
        # Solo admin y el propio usuario pueden ver sus tomos accesibles
        if current_user["rol"] != "Admin" and current_user["id"] != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para ver esta información"
            )

        resultado = permiso_controller.obtener_tomos_accesibles_usuario(usuario_id, db)
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=resultado["message"]
            )
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en endpoint tomos accesibles usuario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


# ==================== EMBEDDINGS ====================

@router.post("/generar-embeddings")
async def generar_embeddings_documentos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
    carpeta_id: Optional[int] = Query(None, description="Procesar solo una carpeta específica"),
    forzar: bool = Query(False, description="Regenerar embeddings existentes")
):
    """
    POST /admin/generar-embeddings
    Generar embeddings para todos los documentos (o una carpeta específica)
    """
    try:
        from app.controllers.busqueda_controller import busqueda_controller
        from app.models.tomo import ContenidoOCR
        from app.models.carpeta import Carpeta
        
        # Construir query base
        query = db.query(ContenidoOCR)
        
        if not forzar:
            # Solo procesar documentos sin embeddings
            query = query.filter(ContenidoOCR.embeddings.is_(None))
        
        if carpeta_id:
            # Filtrar por carpeta específica
            from app.models.tomo import Tomo
            query = query.join(Tomo).filter(Tomo.carpeta_id == carpeta_id)
        
        documentos = query.all()
        
        if not documentos:
            mensaje = "No hay documentos para procesar"
            if carpeta_id:
                mensaje += f" en la carpeta {carpeta_id}"
            if not forzar:
                mensaje += " (sin embeddings)"
            
            return {
                "success": True,
                "message": mensaje,
                "procesados": 0,
                "errores": 0
            }
        
        logger.info(f"Iniciando generación de embeddings para {len(documentos)} documentos")
        
        procesados = 0
        errores = 0
        
        # Agrupar documentos por tomo_id para procesamiento eficiente
        tomos_procesados = set()
        
        for documento in documentos:
            try:
                # Evitar procesar el mismo tomo múltiples veces
                if documento.tomo_id in tomos_procesados:
                    procesados += 1
                    continue
                
                # Generar embeddings para todo el tomo
                resultado = busqueda_controller.actualizar_embeddings_contenido(
                    db=db,
                    tomo_id=documento.tomo_id
                )
                
                # Marcar tomo como procesado
                tomos_procesados.add(documento.tomo_id)
                
                if resultado.get("success", False):
                    # Contar todos los documentos del tomo como procesados
                    docs_tomo = db.query(ContenidoOCR).filter(
                        ContenidoOCR.tomo_id == documento.tomo_id
                    ).count()
                    procesados += docs_tomo
                else:
                    errores += 1
                    logger.warning(f"Error procesando tomo {documento.tomo_id}: {resultado.get('message', 'Error desconocido')}")
                    
            except Exception as e:
                errores += 1
                logger.error(f"Error procesando tomo {documento.tomo_id}: {str(e)}")
        
        logger.info(f"Generación de embeddings completada: {procesados} procesados, {errores} errores")
        
        return {
            "success": True,
            "message": f"Procesamiento completado: {procesados} documentos procesados, {errores} errores",
            "procesados": procesados,
            "errores": errores,
            "total": len(documentos)
        }
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Las librerías de búsqueda semántica no están disponibles. Instale: pip install sentence-transformers scikit-learn"
        )
    except Exception as e:
        logger.error(f"Error generando embeddings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )
