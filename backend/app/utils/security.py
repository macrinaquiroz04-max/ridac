# backend/app/utils/security.py

"""
Módulo de seguridad que agrupa funciones de autenticación y autorización
"""

from app.utils.password_hash import hash_password, verify_password
from app.utils.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token"
]
