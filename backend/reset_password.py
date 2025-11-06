#!/usr/bin/env python3
"""Script para resetear contraseña de un usuario"""

from app.database import SessionLocal
from app.models.usuario import Usuario
from app.utils.password_hash import hash_password

def reset_user_password(username: str, new_password: str):
    """Resetear contraseña de un usuario"""
    db = SessionLocal()
    try:
        # Buscar usuario
        user = db.query(Usuario).filter(Usuario.username == username).first()
        
        if not user:
            print(f"❌ Usuario '{username}' no encontrado")
            return False
        
        # Generar nuevo hash
        new_hash = hash_password(new_password)
        print(f"✓ Hash generado: {new_hash}")
        print(f"✓ Longitud del hash: {len(new_hash)}")
        
        # Actualizar contraseña
        user.password_hash = new_hash
        db.commit()
        
        print(f"✅ Contraseña actualizada para usuario '{username}'")
        
        # Verificar que se guardó correctamente
        db.refresh(user)
        print(f"✓ Hash en BD: {user.password_hash[:30]}...")
        print(f"✓ Longitud en BD: {len(user.password_hash)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Uso: python reset_password.py <username> <nueva_contraseña>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    if reset_user_password(username, password):
        print("\n🎉 ¡Contraseña actualizada exitosamente!")
    else:
        print("\n❌ Error al actualizar contraseña")
        sys.exit(1)
