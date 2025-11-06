# backend/app/middlewares/auth_middleware.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.models.usuario import Usuario
from app.config import settings
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Usuario:
    """
    Middleware para obtener el usuario actual desde el token JWT.
    Verifica que el token sea válido y que el usuario exista.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials

        # Decodificar el token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id is None:
            logger.warning("Token sin user_id")
            raise credentials_exception

        if token_type != "access":
            logger.warning(f"Token tipo incorrecto: {token_type}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tipo de token inválido"
            )

        # Verificar expiración
        exp = payload.get("exp")
        if exp is None or datetime.fromtimestamp(exp) < datetime.now():
            logger.warning(f"Token expirado para usuario {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado"
            )

    except JWTError as e:
        logger.error(f"Error JWT: {str(e)}")
        raise credentials_exception

    # Buscar usuario en la base de datos
    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()

    if user is None:
        logger.warning(f"Usuario no encontrado: {user_id}")
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    """
    Middleware para verificar que el usuario actual esté activo.
    """
    if not current_user.activo:
        logger.warning(f"Usuario inactivo intentó acceder: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )

    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Usuario]:
    """
    Middleware opcional que devuelve el usuario si hay token válido,
    o None si no hay token o es inválido.
    Útil para endpoints que funcionan con o sin autenticación.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
