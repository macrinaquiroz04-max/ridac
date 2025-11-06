# backend/app/routes/usuarios.py
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid
from PIL import Image
import os

from app.database import get_db
from app.models.usuario import Usuario
from app.middlewares.auth_middleware import get_current_user

router = APIRouter(
    tags=["Usuarios"]
)

# Configuración de uploads
UPLOAD_DIR = Path("uploads/profiles")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

@router.post("/upload-profile-image")
async def upload_profile_image(
    profile_image: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Subir imagen de perfil del usuario"""
    
    # Validar extensión
    file_extension = Path(profile_image.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de archivo no permitido. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validar tamaño
    content = await profile_image.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo es demasiado grande. Máximo 5MB."
        )
    
    try:
        # Generar nombre único
        file_id = str(uuid.uuid4())
        filename = f"profile_{current_user.id}_{file_id}{file_extension}"
        file_path = UPLOAD_DIR / filename
        
        # Guardar archivo
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Redimensionar imagen (opcional)
        try:
            with Image.open(file_path) as img:
                # Redimensionar a máximo 300x300 manteniendo proporción
                img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                img.save(file_path, optimize=True, quality=85)
        except Exception as e:
            print(f"Error redimensionando imagen: {e}")
            # Si falla el redimensionado, continuar con la imagen original
        
        # Actualizar usuario en BD
        user = db.query(Usuario).filter(Usuario.id == current_user.id).first()
        if user:
            # Eliminar imagen anterior si existe
            if user.foto_perfil and user.foto_perfil.startswith("uploads/"):
                old_path = Path(user.foto_perfil)
                if old_path.exists():
                    old_path.unlink()
            
            user.foto_perfil = f"uploads/profiles/{filename}"
            db.commit()
        
        return {
            "success": True,
            "message": "Imagen de perfil actualizada",
            "image_url": f"uploads/profiles/{filename}"
        }
        
    except Exception as e:
        # Limpiar archivo si hubo error
        if file_path.exists():
            file_path.unlink()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la imagen: {str(e)}"
        )

@router.post("/update-profile-image")
async def update_profile_image(
    image_data: dict,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar URL de imagen de perfil (para reset a default)"""
    
    try:
        user = db.query(Usuario).filter(Usuario.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Si se está reseteando a default, eliminar imagen actual
        if image_data.get("image_url") is None and user.foto_perfil:
            if user.foto_perfil.startswith("uploads/"):
                old_path = Path(user.foto_perfil)
                if old_path.exists():
                    old_path.unlink()
        
        user.foto_perfil = image_data.get("image_url")
        db.commit()
        
        return {
            "success": True,
            "message": "Imagen de perfil actualizada"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar imagen: {str(e)}"
        )

@router.get("/profile-image")
async def get_profile_image(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener imagen de perfil del usuario"""
    
    user = db.query(Usuario).filter(Usuario.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return {
        "image_url": user.foto_perfil or "images/profiles/default-avatar.svg"
    }

@router.get("/profile-image/{user_id}")
async def serve_profile_image(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Servir imagen de perfil de un usuario específico"""
    
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user or not user.foto_perfil:
        # Devolver imagen por defecto
        default_path = Path(__file__).parent.parent.parent.parent / "frontend" / "images" / "default-avatar.svg"
        if default_path.exists():
            return FileResponse(default_path, media_type="image/svg+xml")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Imagen no encontrada"
            )
    
    # Construir ruta completa de la imagen
    if user.foto_perfil.startswith("uploads/"):
        image_path = Path(__file__).parent.parent.parent / user.foto_perfil
    else:
        image_path = Path(user.foto_perfil)
    
    if not image_path.exists():
        # Devolver imagen por defecto si no existe
        default_path = Path(__file__).parent.parent.parent.parent / "frontend" / "images" / "default-avatar.svg"
        if default_path.exists():
            return FileResponse(default_path, media_type="image/svg+xml")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Imagen no encontrada"
            )
    
    # Determinar tipo de contenido
    extension = image_path.suffix.lower()
    media_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml'
    }
    media_type = media_types.get(extension, 'image/jpeg')
    
    return FileResponse(image_path, media_type=media_type)