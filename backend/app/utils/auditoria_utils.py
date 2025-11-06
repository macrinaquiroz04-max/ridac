# backend/app/utils/auditoria_utils.py

import json
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Request
from typing import Optional, Dict, Any

from app.models.auditoria import Auditoria
from app.database import SessionLocal

class AuditoriaLogger:
    """Clase para registrar eventos de auditoría"""
    
    @staticmethod
    def registrar_evento(
        usuario_id: Optional[int],
        accion: str,
        tabla_afectada: Optional[str] = None,
        registro_id: Optional[int] = None,
        valores_anteriores: Optional[Dict[str, Any]] = None,
        valores_nuevos: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        descripcion: Optional[str] = None,
        db: Optional[Session] = None
    ):
        """
        Registrar un evento de auditoría
        
        Args:
            usuario_id: ID del usuario que realiza la acción
            accion: Tipo de acción realizada
            tabla_afectada: Tabla de la base de datos afectada
            registro_id: ID del registro afectado
            valores_anteriores: Valores antes del cambio
            valores_nuevos: Valores después del cambio
            ip_address: Dirección IP del usuario
            user_agent: User agent del navegador
            descripcion: Descripción adicional del evento
            db: Sesión de base de datos (opcional)
        """
        
        # Usar sesión existente o crear una nueva
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Limpiar contraseñas de los valores
            if valores_anteriores:
                valores_anteriores = AuditoriaLogger._limpiar_contraseñas(valores_anteriores)
            if valores_nuevos:
                valores_nuevos = AuditoriaLogger._limpiar_contraseñas(valores_nuevos)
            
            # Crear registro de auditoría
            auditoria = Auditoria(
                usuario_id=usuario_id,
                accion=accion,
                tabla_afectada=tabla_afectada,
                registro_id=registro_id,
                valores_anteriores=valores_anteriores,
                valores_nuevos=valores_nuevos,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.add(auditoria)
            db.commit()
            
            print(f"📝 Auditoría registrada: {accion} por usuario {usuario_id}")
            
        except Exception as e:
            print(f"❌ Error registrando auditoría: {e}")
            db.rollback()
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def _limpiar_contraseñas(valores: Dict[str, Any]) -> Dict[str, Any]:
        """Remover campos de contraseña de los valores"""
        campos_sensibles = ['password', 'password_hash', 'nueva_password', 'password_anterior']
        valores_limpios = {}
        
        for key, value in valores.items():
            if key.lower() not in campos_sensibles:
                valores_limpios[key] = value
            else:
                valores_limpios[key] = "***OCULTO***"
        
        return valores_limpios
    
    @staticmethod
    def registrar_login_exitoso(usuario_id: int, username: str, ip_address: str = None, user_agent: str = None):
        """Registrar login exitoso"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="LOGIN_EXITOSO",
            tabla_afectada="usuarios",
            registro_id=usuario_id,
            valores_nuevos={"username": username, "evento": "login_exitoso"},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def registrar_login_fallido(username: str, ip_address: str = None, user_agent: str = None):
        """Registrar intento de login fallido"""
        AuditoriaLogger.registrar_evento(
            usuario_id=None,  # No hay usuario válido
            accion="LOGIN_FALLIDO",
            tabla_afectada="usuarios",
            valores_nuevos={"username": username, "evento": "login_fallido"},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def registrar_logout(usuario_id: int, username: str, ip_address: str = None):
        """Registrar logout"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="LOGOUT",
            tabla_afectada="usuarios",
            registro_id=usuario_id,
            valores_nuevos={"username": username, "evento": "logout"},
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_creacion_usuario(usuario_admin_id: int, nuevo_usuario_id: int, datos_usuario: dict, ip_address: str = None):
        """Registrar creación de usuario"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_admin_id,
            accion="CREAR_USUARIO",
            tabla_afectada="usuarios",
            registro_id=nuevo_usuario_id,
            valores_nuevos=datos_usuario,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_modificacion_usuario(usuario_admin_id: int, usuario_modificado_id: int, valores_anteriores: dict, valores_nuevos: dict, ip_address: str = None):
        """Registrar modificación de usuario"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_admin_id,
            accion="MODIFICAR_USUARIO",
            tabla_afectada="usuarios",
            registro_id=usuario_modificado_id,
            valores_anteriores=valores_anteriores,
            valores_nuevos=valores_nuevos,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_eliminacion_usuario(usuario_admin_id: int, usuario_eliminado_id: int, datos_usuario: dict, ip_address: str = None):
        """Registrar eliminación de usuario"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_admin_id,
            accion="ELIMINAR_USUARIO",
            tabla_afectada="usuarios",
            registro_id=usuario_eliminado_id,
            valores_anteriores=datos_usuario,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_cambio_permisos(usuario_admin_id: int, usuario_afectado_id: int, permisos_anteriores: dict, permisos_nuevos: dict, ip_address: str = None):
        """Registrar cambio de permisos"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_admin_id,
            accion="MODIFICAR_PERMISOS",
            tabla_afectada="permisos_sistema",
            registro_id=usuario_afectado_id,
            valores_anteriores=permisos_anteriores,
            valores_nuevos=permisos_nuevos,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_cambio_password(usuario_id: int, ip_address: str = None):
        """Registrar cambio de contraseña"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="CAMBIAR_PASSWORD",
            tabla_afectada="usuarios",
            registro_id=usuario_id,
            valores_nuevos={"evento": "cambio_password"},
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_procesamiento_ocr(usuario_id: int, tomo_id: int, archivo: str, ip_address: str = None):
        """Registrar procesamiento de OCR"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="PROCESAR_OCR",
            tabla_afectada="tomos",
            registro_id=tomo_id,
            valores_nuevos={"archivo": archivo, "evento": "ocr_procesado"},
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_creacion_carpeta(usuario_id: int, carpeta_id: int, nombre_carpeta: str, ip_address: str = None):
        """Registrar creación de carpeta"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="CREAR_CARPETA",
            tabla_afectada="carpetas",
            registro_id=carpeta_id,
            valores_nuevos={"nombre": nombre_carpeta, "evento": "carpeta_creada"},
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_eliminacion_carpeta(usuario_id: int, carpeta_id: int, nombre_carpeta: str, ip_address: str = None):
        """Registrar eliminación de carpeta"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="ELIMINAR_CARPETA",
            tabla_afectada="carpetas",
            registro_id=carpeta_id,
            valores_anteriores={"nombre": nombre_carpeta, "evento": "carpeta_eliminada"},
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_busqueda(usuario_id: int, termino_busqueda: str, tipo_busqueda: str, resultados: int, ip_address: str = None):
        """Registrar búsqueda realizada"""
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="REALIZAR_BUSQUEDA",
            tabla_afectada="busquedas",
            valores_nuevos={
                "termino": termino_busqueda,
                "tipo": tipo_busqueda,
                "resultados": resultados,
                "evento": "busqueda_realizada"
            },
            ip_address=ip_address
        )
    
    @staticmethod
    def extraer_info_request(request: Request):
        """Extraer información del request para auditoría"""
        ip_address = None
        user_agent = None
        
        if request:
            # Intentar obtener IP real (considerando proxies)
            x_forwarded_for = request.headers.get("X-Forwarded-For", "")
            x_real_ip = request.headers.get("X-Real-IP", "")
            client_host = request.client.host if request.client else None
            
            # Obtener primera IP de X-Forwarded-For (la real)
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(",")[0].strip()
            elif x_real_ip:
                ip_address = x_real_ip
            else:
                ip_address = client_host
            
            user_agent = request.headers.get("User-Agent", "")
        
        return ip_address, user_agent

# Funciones de conveniencia
def registrar_auditoria(usuario_id: int, accion: str, **kwargs):
    """Función de conveniencia para registrar auditoría"""
    AuditoriaLogger.registrar_evento(usuario_id, accion, **kwargs)

def audit_login_success(usuario_id: int, username: str, request: Request = None):
    """Auditar login exitoso"""
    ip, user_agent = AuditoriaLogger.extraer_info_request(request)
    AuditoriaLogger.registrar_login_exitoso(usuario_id, username, ip, user_agent)

def audit_login_failed(username: str, request: Request = None):
    """Auditar login fallido"""
    ip, user_agent = AuditoriaLogger.extraer_info_request(request)
    AuditoriaLogger.registrar_login_fallido(username, ip, user_agent)