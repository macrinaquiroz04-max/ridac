# backend/app/middlewares/error_handler_middleware.py

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import traceback
import logging

from app.utils.error_logger import ErrorLogger

logger = logging.getLogger("sistema_ocr")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware que captura TODOS los errores y los registra
    Evita que el sistema se detenga por errores inesperados
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            # Intentar procesar la petición normalmente
            response = await call_next(request)
            return response
            
        except Exception as exc:
            # Capturar CUALQUIER error que ocurra
            error_context = {
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else "unknown",
                "headers": dict(request.headers)
            }
            
            # Registrar el error
            ErrorLogger.log_error(
                error=exc,
                context=f"HTTP Request: {request.method} {request.url.path}",
                request_data=error_context,
                severity="ERROR" if not isinstance(exc, (ValueError, KeyError)) else "WARNING"
            )
            
            # Log también en consola para debugging
            logger.error(
                f"Error capturado en {request.method} {request.url.path}: {exc}",
                exc_info=True
            )
            
            # Devolver respuesta de error pero mantener el sistema funcionando
            error_response = {
                "status": "error",
                "message": "Ha ocurrido un error, pero el sistema sigue funcionando",
                "detail": str(exc),
                "path": request.url.path,
                "method": request.method
            }
            
            # Determinar código de estado HTTP apropiado
            status_code = 500
            if isinstance(exc, ValueError):
                status_code = 400
            elif isinstance(exc, KeyError):
                status_code = 422
            elif isinstance(exc, PermissionError):
                status_code = 403
            
            return JSONResponse(
                status_code=status_code,
                content=error_response
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que registra todas las peticiones
    Útil para debugging y auditoría
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Registrar petición entrante
        logger.info(f"→ {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
        
        try:
            response = await call_next(request)
            
            # Registrar respuesta exitosa
            logger.info(f"← {request.method} {request.url.path} - Status: {response.status_code}")
            
            # Si la respuesta es un error (4xx o 5xx), registrarlo
            if response.status_code >= 400:
                ErrorLogger.log_warning(
                    message=f"HTTP {response.status_code} en {request.method} {request.url.path}",
                    context="HTTP Response",
                    extra_data={
                        "status_code": response.status_code,
                        "method": request.method,
                        "path": request.url.path
                    }
                )
            
            return response
            
        except Exception as exc:
            # Este caso ya lo maneja ErrorHandlerMiddleware
            raise exc
