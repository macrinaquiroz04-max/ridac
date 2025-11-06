"""
Controlador para streaming de progreso en tiempo real (Server-Sent Events)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario
from app.middlewares.auth_middleware import get_current_user
import asyncio
import json
from datetime import datetime
from jose import jwt, JWTError
from app.config import settings

router = APIRouter()

# Estado global de procesamiento (mismo que en analisis_controller)
from app.controllers.analisis_admin_controller import procesamiento_estado


async def verificar_token(token: str, db: Session):
    """
    Verifica el token de autenticación para SSE
    (EventSource no soporta headers personalizados, así que usamos query string)
    """
    try:
        from app.models.usuario import Usuario
        
        print(f"🔐 Verificando token SSE...")
        print(f"   Token recibido: {token[:50]}...")
        
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        print(f"   ✅ Token decodificado: {payload}")
        
        # El "sub" contiene el USER_ID, no el email
        user_id = payload.get("sub")
        print(f"   👤 User ID del token: {user_id}")
        
        if user_id is None:
            print("   ❌ No hay 'sub' en el token")
            raise HTTPException(status_code=401, detail="Token inválido - sin sub")
        
        # Buscar por ID, no por email
        usuario = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
        
        if usuario is None:
            print(f"   ❌ Usuario no encontrado con ID: {user_id}")
            raise HTTPException(status_code=401, detail=f"Usuario no encontrado con ID {user_id}")
        
        print(f"   ✅ Usuario autenticado: {usuario.email}")
        return usuario
    
    except JWTError as e:
        print(f"   ❌ Error JWT: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")


async def event_stream(tomo_id: int, tipo_proceso: str = "ocr"):
    """
    Genera eventos SSE con el progreso del procesamiento
    """
    estado_key = f"{tipo_proceso}_{tomo_id}"
    
    while True:
        # Obtener estado actual
        estado = procesamiento_estado.get(estado_key, {
            "estado": "no_iniciado",
            "progreso": 0,
            "mensaje": "No hay proceso activo"
        })
        
        # Formatear datos para SSE
        data = {
            "estado": estado.get("estado", "no_iniciado"),
            "progreso": estado.get("progreso", 0),
            "pagina_actual": estado.get("pagina_actual", 0),
            "total_paginas": estado.get("total_paginas", 0),
            "mensaje": estado.get("mensaje", ""),
            "tiempo_transcurrido": estado.get("tiempo_transcurrido", 0),
            "tiempo_estimado": estado.get("tiempo_estimado", 0),
            "velocidad": estado.get("velocidad", 0),
            "personas_encontradas": estado.get("personas_encontradas", 0),
            "errores": len(estado.get("errores", [])),
            "timestamp": datetime.now().isoformat()
        }
        
        # Enviar evento
        yield f"data: {json.dumps(data)}\n\n"
        
        # Si terminó (completado o error), enviar evento final y cerrar
        if estado.get("estado") in ["completado", "error"]:
            await asyncio.sleep(1)  # Dar tiempo a que se muestre el 100%
            break
        
        # Esperar 1 segundo antes del siguiente update
        await asyncio.sleep(1)


@router.get("/api/progress/ocr/{tomo_id}")
async def stream_ocr_progress(
    tomo_id: int,
    token: str = Query(..., description="Token de autenticación"),
    db: Session = Depends(get_db)
):
    """
    Endpoint SSE para streaming de progreso de OCR en tiempo real
    
    Uso desde JavaScript:
    ```javascript
    const token = localStorage.getItem('token');
    const eventSource = new EventSource(`/api/progress/ocr/12?token=${token}`);
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Progreso:', data.progreso, '%');
    };
    ```
    """
    # Verificar autenticación
    await verificar_token(token, db)
    
    return StreamingResponse(
        event_stream(tomo_id, "ocr"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/api/progress/analisis/{tomo_id}")
async def stream_analisis_progress(
    tomo_id: int,
    token: str = Query(..., description="Token de autenticación"),
    db: Session = Depends(get_db)
):
    """
    Endpoint SSE para streaming de progreso de análisis NLP
    """
    # Verificar autenticación
    await verificar_token(token, db)
    
    return StreamingResponse(
        event_stream(tomo_id, "analisis"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no"
        }
    )
