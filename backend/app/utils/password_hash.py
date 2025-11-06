# backend/app/utils/password_hash.py

import bcrypt

def hash_password(password: str) -> str:
    """Hashear contraseña con bcrypt (trunca a 72 bytes si es necesario)"""
    # Convertir a bytes y truncar a 72 bytes si es necesario
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generar hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña (trunca a 72 bytes si es necesario)"""
    # Convertir a bytes y truncar a 72 bytes si es necesario
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Verificar hash
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)
