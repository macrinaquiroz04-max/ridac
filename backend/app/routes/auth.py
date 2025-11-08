# backend/app/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.usuario import Usuario, TokenReset
from app.middlewares.auth_middleware import get_current_user, get_current_active_user
from app.config import settings
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.controllers.auth_controller import auth_controller
from app.utils.auditoria_utils import AuditoriaLogger
import logging
import secrets

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Autenticación"]
)


# Schemas de request/response
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class RefreshRequest(BaseModel):
    refresh_token: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    POST /auth/login
    Autenticar usuario y generar tokens JWT.
    """
    # Extraer información del request para auditoría
    from app.utils.auditoria_utils import AuditoriaLogger
    ip_address, user_agent = AuditoriaLogger.extraer_info_request(request)
    
    # Usar el controlador que ya tiene auditoría integrada
    # El controlador registrará el login con IP y User-Agent
    result = auth_controller.login(
        db=db,
        username_or_email=login_data.username,
        password=login_data.password,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    
    return LoginResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        user=result["user"]
    )


@router.post("/refresh", response_model=Dict[str, str])
async def refresh_token(
    refresh_data: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    POST /auth/refresh
    Refrescar access token usando refresh token.
    """
    from jose import JWTError, jwt

    try:
        # Decodificar refresh token
        payload = jwt.decode(
            refresh_data.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresco inválido"
            )

        # Verificar que el usuario existe y está activo
        user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()

        if not user or not user.activo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no válido"
            )

        # Generar nuevo access token
        new_access_token = create_access_token({"sub": str(user.id)})

        logger.info(f"Token refrescado para usuario: {user.username}")

        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }

    except JWTError as e:
        logger.error(f"Error al refrescar token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido"
        )


@router.post("/logout")
async def logout(
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    POST /auth/logout
    Cerrar sesión (en implementación real, invalidar tokens).
    """
    logger.info(f"Logout de usuario: {current_user.username}")

    return {
        "message": "Sesión cerrada correctamente",
        "user": current_user.username
    }


@router.post("/reset-password")
async def request_password_reset(
    reset_data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    POST /auth/reset-password
    Solicitar restablecimiento de contraseña.
    """
    # Buscar usuario por email
    user = db.query(Usuario).filter(Usuario.email == reset_data.email).first()

    # Por seguridad, siempre retornar éxito aunque el email no exista
    if not user:
        logger.info(f"Solicitud de reset para email inexistente: {reset_data.email}")
        return {
            "message": "Si el correo existe, recibirás instrucciones para restablecer tu contraseña"
        }

    # Generar token de reset
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)

    # Guardar token en base de datos
    token_reset = TokenReset(
        usuario_id=user.id,
        token=reset_token,
        expira_en=expires_at
    )

    db.add(token_reset)
    db.commit()

    logger.info(f"Token de reset generado para usuario: {user.username}")

    # TODO: Enviar email con el token
    # Por ahora, solo retornamos un mensaje (en producción, enviar email)

    return {
        "message": "Si el correo existe, recibirás instrucciones para restablecer tu contraseña",
        "token": reset_token  # Solo para testing, eliminar en producción
    }


@router.post("/reset-password/confirm")
async def confirm_password_reset(
    confirm_data: ResetPasswordConfirm,
    db: Session = Depends(get_db)
):
    """
    POST /auth/reset-password/confirm
    Confirmar restablecimiento de contraseña con token.
    """
    # Buscar token válido
    token_reset = db.query(TokenReset).filter(
        TokenReset.token == confirm_data.token,
        TokenReset.usado == False,
        TokenReset.expira_en > datetime.now()
    ).first()

    if not token_reset:
        logger.warning(f"Intento de reset con token inválido")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado"
        )

    # Actualizar contraseña
    user = db.query(Usuario).filter(Usuario.id == token_reset.usuario_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Validar nueva contraseña
    from app.utils.validators import validate_password
    is_valid, error_message = validate_password(confirm_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    user.password = hash_password(confirm_data.new_password)

    # Marcar token como usado
    token_reset.usado = True
    token_reset.usado_en = datetime.now()

    db.commit()

    logger.info(f"Contraseña restablecida para usuario: {user.username}")

    return {
        "message": "Contraseña restablecida correctamente"
    }


@router.post("/change-password")
async def change_password(
    change_data: ChangePasswordRequest,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    POST /auth/change-password
    Cambiar contraseña del usuario actual.
    """
    # Verificar contraseña actual
    if not verify_password(change_data.current_password, current_user.password):
        logger.warning(f"Intento de cambio de contraseña con contraseña incorrecta: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )

    # Validar nueva contraseña
    from app.utils.validators import validate_password
    is_valid, error_message = validate_password(change_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Actualizar contraseña
    current_user.password = hash_password(change_data.new_password)
    # Marcar que ya no necesita cambiar contraseña
    current_user.debe_cambiar_password = False
    db.commit()

    logger.info(f"Contraseña cambiada para usuario: {current_user.username}")

    return {
        "message": "Contraseña cambiada correctamente"
    }


@router.post("/cambiar-password")
async def cambiar_password_es(
    change_data: ChangePasswordRequest,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    POST /auth/cambiar-password
    Cambiar contraseña del usuario actual (alias en español).
    """
    return await change_password(change_data, current_user, db)


@router.get("/me")
async def get_current_user_info(
    current_user: Usuario = Depends(get_current_active_user)
):
    """
    GET /auth/me
    Obtener información del usuario actual.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "nombre": current_user.nombre_completo,
        "rol": current_user.rol.nombre if current_user.rol else "Usuario",
        "activo": current_user.activo,
        "ultimo_acceso": current_user.ultimo_acceso.isoformat() if current_user.ultimo_acceso else None,
        "creado_en": current_user.created_at.isoformat() if current_user.created_at else None,
        "foto_perfil": current_user.foto_perfil
    }
