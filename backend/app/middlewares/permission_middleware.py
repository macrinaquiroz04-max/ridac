# backend/app/middlewares/permission_middleware.py

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from functools import wraps

from app.database import get_db
from app.models.usuario import Usuario
from app.models.permiso import PermisoCarpeta, PermisoSistema
from app.middlewares.auth_middleware import get_current_active_user
import logging

logger = logging.getLogger(__name__)


class PermissionChecker:
    """
    Clase para verificar permisos de usuario.
    Puede usarse como dependencia en rutas de FastAPI.
    """

    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    def __call__(
        self,
        current_user: Usuario = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> Usuario:
        """
        Verifica que el usuario tenga los permisos requeridos.
        """
        # Los administradores tienen todos los permisos
        if current_user.rol.nombre in ["admin", "administrador"]:
            return current_user

        # Obtener permisos del usuario
        user_permissions = db.query(PermisoSistema).filter(
            PermisoSistema.usuario_id == current_user.id
        ).all()

        user_permission_names = [p.permiso for p in user_permissions]

        # Verificar que tenga todos los permisos requeridos
        for permission in self.required_permissions:
            if permission not in user_permission_names:
                logger.warning(
                    f"Usuario {current_user.username} sin permiso: {permission}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No tiene permiso: {permission}"
                )

        return current_user


class FolderPermissionChecker:
    """
    Clase para verificar permisos sobre carpetas específicas.
    """

    def __init__(self, permission_type: str = "lectura"):
        """
        Args:
            permission_type: 'lectura', 'escritura', o 'admin'
        """
        self.permission_type = permission_type

    def __call__(
        self,
        carpeta_id: int,
        current_user: Usuario = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> Usuario:
        """
        Verifica que el usuario tenga permiso sobre la carpeta.
        """
        # Los administradores tienen acceso total
        if current_user.rol.nombre in ["admin", "administrador"]:
            return current_user

        # Buscar permiso específico
        permiso = db.query(PermisoCarpeta).filter(
            PermisoCarpeta.usuario_id == current_user.id,
            PermisoCarpeta.carpeta_id == carpeta_id
        ).first()

        if not permiso:
            logger.warning(
                f"Usuario {current_user.username} sin acceso a carpeta {carpeta_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene acceso a esta carpeta"
            )

        # Verificar tipo de permiso
        permission_levels = {
            "lectura": 1,
            "escritura": 2,
            "admin": 3
        }

        user_level = permission_levels.get(permiso.tipo, 0)
        required_level = permission_levels.get(self.permission_type, 0)

        if user_level < required_level:
            logger.warning(
                f"Usuario {current_user.username} con permiso insuficiente "
                f"({permiso.tipo}) para carpeta {carpeta_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Necesita permiso de {self.permission_type}"
            )

        return current_user


def require_permission(*permissions: str):
    """
    Decorador/dependencia para requerir permisos específicos.
    Uso: @router.get("/", dependencies=[Depends(require_permission("ver_usuarios"))])
    """
    return Depends(PermissionChecker(list(permissions)))


def require_folder_permission(permission_type: str = "lectura"):
    """
    Decorador/dependencia para requerir permisos sobre carpetas.
    Uso: dependencies=[Depends(require_folder_permission("escritura"))]
    """
    return Depends(FolderPermissionChecker(permission_type))


def require_admin(
    current_user: Usuario = Depends(get_current_active_user)
) -> Usuario:
    """
    Dependencia para requerir rol de administrador.
    Acepta 'admin' (minúscula) como rol válido.
    Uso: current_user: Usuario = Depends(require_admin)
    """
    admin_roles = ["admin", "administrador"]  # Solo minúsculas
    
    if current_user.rol.nombre not in admin_roles:
        logger.warning(
            f"Usuario no admin intentó acceso: {current_user.username} (rol: {current_user.rol.nombre})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere privilegios de administrador"
        )

    return current_user


async def check_folder_access(
    carpeta_id: int,
    user: Usuario,
    db: Session,
    required_permission: str = "lectura"
) -> bool:
    """
    Función auxiliar para verificar acceso a carpeta.
    Retorna True si tiene acceso, False si no.
    """
    # Administradores tienen acceso total
    if user.rol.nombre in ["admin", "Admin", "Administrador"]:
        return True

    # Buscar permiso
    permiso = db.query(PermisoCarpeta).filter(
        PermisoCarpeta.usuario_id == user.id,
        PermisoCarpeta.carpeta_id == carpeta_id
    ).first()

    if not permiso:
        return False

    # Verificar nivel de permiso
    permission_levels = {
        "lectura": 1,
        "escritura": 2,
        "admin": 3
    }

    user_level = permission_levels.get(permiso.tipo, 0)
    required_level = permission_levels.get(required_permission, 0)

    return user_level >= required_level


# Alias para compatibilidad con autocorrector_controller
get_current_user = get_current_active_user
