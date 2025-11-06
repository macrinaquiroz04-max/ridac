from app.database import get_db
from app.models.usuario import Usuario
from sqlalchemy import text

db = next(get_db())

# Obtener usuarios excepto admin y eduardo
usuarios_a_borrar = db.query(Usuario).filter(
    Usuario.username != 'admin',
    Usuario.username != 'eduardo'  # Proteger también a eduardo
).all()

print(f"📋 Total de usuarios a eliminar: {len(usuarios_a_borrar)}")
print("=" * 50)

if len(usuarios_a_borrar) == 0:
    print("✅ No hay usuarios para eliminar")
else:
    for usuario in usuarios_a_borrar:
        print(f"\n🗑️  Borrando: {usuario.username} (ID: {usuario.id})")
        user_id = usuario.id
        
        try:
            # Borrar permisos
            result = db.execute(text("DELETE FROM permisos_carpeta WHERE usuario_id = :id"), {"id": user_id})
            print(f"   ✓ Eliminados {result.rowcount} permisos de carpeta")
            
            result = db.execute(text("DELETE FROM permisos_tomo WHERE usuario_id = :id"), {"id": user_id})
            print(f"   ✓ Eliminados {result.rowcount} permisos de tomo")
            
            # Eliminar el usuario
            db.delete(usuario)
            db.commit()
            print(f"   ✅ Usuario {usuario.username} ELIMINADO DEFINITIVAMENTE")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            db.rollback()
    
    print("\n" + "=" * 50)
    print(f"✅ Proceso completado - {len(usuarios_a_borrar)} usuario(s) eliminado(s)")

# Verificar usuarios restantes
print("\n📋 Usuarios restantes en la base de datos:")
usuarios_restantes = db.query(Usuario).all()
for u in usuarios_restantes:
    print(f"  ✓ {u.username} (ID: {u.id})")
