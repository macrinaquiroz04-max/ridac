# backend/app/middlewares/access_token_middleware.py
# Protección por token compartido para despliegue en plataformas públicas (HF Spaces, etc.)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import settings


# Rutas exentas — health check y docs de HF Spaces
_EXEMPT_PATHS = {"/health", "/", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}


class AccessTokenMiddleware(BaseHTTPMiddleware):
    """
    Si API_ACCESS_TOKEN está configurado, exige el header X-Access-Token en
    todos los endpoints excepto los exentos.
    Si API_ACCESS_TOKEN está vacío/None, el middleware no hace nada
    (compatible con desarrollo local sin token).
    """

    async def dispatch(self, request: Request, call_next):
        token_requerido = settings.API_ACCESS_TOKEN

        # Sin token configurado → no proteger (dev local / Render privado)
        if not token_requerido:
            return await call_next(request)

        # Rutas exentas
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Verificar header
        token_enviado = request.headers.get("X-Access-Token", "")
        if token_enviado != token_requerido:
            return JSONResponse(
                status_code=403,
                content={"detail": "Acceso no autorizado. Token inválido."},
            )

        return await call_next(request)
