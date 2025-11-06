from app.database import get_db
from app.models.usuario import Rol

db = next(get_db())

# Actualizar el rol "Admin" a "admin" (minúsculas)
rol = db.query(Rol).filter(Rol.nombre == 'Admin').first()
if rol:
    print(f"✓ Encontrado rol: {rol.nombre} (ID: {rol.id})")
    rol.nombre = 'admin'
    db.commit()
    print(f"✅ Rol actualizado a: {rol.nombre}")
else:
    print("❌ No se encontró el rol 'Admin'")

# Verificar también otros roles
roles = db.query(Rol).all()
print("\n📋 Roles actuales en la base de datos:")
for r in roles:
    print(f"  - {r.nombre} (ID: {r.id})")
