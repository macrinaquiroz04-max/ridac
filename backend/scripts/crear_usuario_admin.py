from app.database import get_db
from app.models.usuario import Usuario, Rol
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = next(get_db())

# Verificar si existe usuario "admin"
admin = db.query(Usuario).filter(Usuario.username == 'admin').first()

if admin:
    print(f"✅ Usuario 'admin' ya existe (ID: {admin.id})")
    # Actualizar su contraseña por si acaso
    admin.password = pwd_context.hash("admin123")
    db.commit()
    print("✅ Contraseña de 'admin' actualizada a 'admin123'")
else:
    # Obtener el rol admin
    rol_admin = db.query(Rol).filter(Rol.nombre == 'admin').first()
    
    if not rol_admin:
        print("❌ No existe el rol 'admin' en la base de datos")
    else:
        # Crear usuario admin
        nuevo_admin = Usuario(
            username='admin',
            email='admin@fgjcdmx.gob.mx',
            password=pwd_context.hash('admin123'),
            nombre='Administrador',
            rol_id=rol_admin.id,
            activo=True,
            debe_cambiar_password=False
        )
        
        db.add(nuevo_admin)
        db.commit()
        db.refresh(nuevo_admin)
        
        print(f"✅ Usuario 'admin' creado exitosamente (ID: {nuevo_admin.id})")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"   Rol: {rol_admin.nombre}")

# Mostrar todos los usuarios
print("\n📋 Usuarios en el sistema:")
usuarios = db.query(Usuario).join(Rol).all()
for u in usuarios:
    rol = db.query(Rol).filter(Rol.id == u.rol_id).first()
    print(f"  • {u.username} - Rol: {rol.nombre if rol else 'Sin rol'} - Activo: {u.activo}")
