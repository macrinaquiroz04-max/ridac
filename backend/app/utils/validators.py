# backend/app/utils/validators.py

import re
from typing import Optional
from pathlib import Path

def validate_email(email: str) -> bool:
    """Validar formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """Validar username (alfanumérico, 3-50 caracteres)"""
    if len(username) < 3:
        return False, "El username debe tener al menos 3 caracteres"
    if len(username) > 50:
        return False, "El username no puede tener más de 50 caracteres"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "El username solo puede contener letras, números, guiones y guiones bajos"
    return True, None

def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """Validar contraseña (mínimo 6 caracteres)"""
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres"
    if len(password) > 100:
        return False, "La contraseña no puede tener más de 100 caracteres"
    return True, None

def validate_file_extension(filename: str, allowed_extensions: list[str]) -> bool:
    """Validar extensión de archivo"""
    ext = Path(filename).suffix.lower()
    return ext in [e.lower() if e.startswith('.') else f'.{e.lower()}' for e in allowed_extensions]

def sanitize_filename(filename: str) -> str:
    """Sanitizar nombre de archivo"""
    # Remover caracteres peligrosos
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limitar longitud
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    name = name[:200]
    return f"{name}.{ext}" if ext else name

def validate_numero_expediente(numero: str) -> tuple[bool, Optional[str]]:
    """Validar formato de número de expediente"""
    if not numero:
        return True, None  # Es opcional
    if len(numero) > 100:
        return False, "El número de expediente no puede tener más de 100 caracteres"
    # Permitir alfanuméricos, guiones, barras y espacios
    if not re.match(r'^[a-zA-Z0-9\-/\s]+$', numero):
        return False, "El número de expediente contiene caracteres no permitidos"
    return True, None
