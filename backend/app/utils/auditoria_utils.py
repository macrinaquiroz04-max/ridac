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
                user_agent=user_agent,
                descripcion=descripcion
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
        descripcion = f"Login exitoso del usuario '{username}'"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="LOGIN_EXITOSO",
            tabla_afectada="usuarios",
            registro_id=usuario_id,
            valores_nuevos={"username": username, "evento": "login_exitoso"},
            descripcion=descripcion,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def registrar_login_fallido(username: str, ip_address: str = None, user_agent: str = None):
        """Registrar intento de login fallido"""
        # Construir descripción con información completa
        descripcion = f"Intento de login fallido del usuario '{username}'"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=None,  # No hay usuario válido
            accion="LOGIN_FALLIDO",
            tabla_afectada="usuarios",
            valores_nuevos={"username": username, "evento": "login_fallido"},
            descripcion=descripcion,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def registrar_logout(usuario_id: int, username: str, ip_address: str = None):
        """Registrar logout"""
        descripcion = f"Logout del usuario '{username}'"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="LOGOUT",
            tabla_afectada="usuarios",
            registro_id=usuario_id,
            valores_nuevos={"username": username, "evento": "logout"},
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_creacion_usuario(usuario_admin_id: int, nuevo_usuario_id: int, datos_usuario: dict, ip_address: str = None):
        """Registrar creación de usuario"""
        username = datos_usuario.get('username', 'Usuario desconocido')
        nombre_completo = datos_usuario.get('nombre_completo', '')
        
        descripcion = f"Se creó el usuario '{username}'"
        if nombre_completo:
            descripcion += f" ({nombre_completo})"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_admin_id,
            accion="CREAR_USUARIO",
            tabla_afectada="usuarios",
            registro_id=nuevo_usuario_id,
            valores_nuevos=datos_usuario,
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_modificacion_usuario(usuario_admin_id: int, usuario_modificado_id: int, valores_anteriores: dict, valores_nuevos: dict, ip_address: str = None):
        """Registrar modificación de usuario"""
        username = valores_nuevos.get('username') or valores_anteriores.get('username', 'Usuario desconocido')
        nombre_completo = valores_nuevos.get('nombre_completo') or valores_anteriores.get('nombre_completo', '')
        
        descripcion = f"Se modificó el usuario '{username}'"
        if nombre_completo:
            descripcion += f" ({nombre_completo})"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_admin_id,
            accion="MODIFICAR_USUARIO",
            tabla_afectada="usuarios",
            registro_id=usuario_modificado_id,
            valores_anteriores=valores_anteriores,
            valores_nuevos=valores_nuevos,
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_eliminacion_usuario(usuario_admin_id: int, usuario_eliminado_id: int, datos_usuario: dict, ip_address: str = None):
        """Registrar eliminación de usuario"""
        # Construir descripción con información completa
        username = datos_usuario.get('username', 'Usuario desconocido')
        nombre_completo = datos_usuario.get('nombre_completo', '')
        
        descripcion = f"Se eliminó el usuario '{username}'"
        if nombre_completo:
            descripcion += f" ({nombre_completo})"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_admin_id,
            accion="ELIMINAR_USUARIO",
            tabla_afectada="usuarios",
            registro_id=usuario_eliminado_id,
            valores_anteriores=datos_usuario,
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_cambio_permisos(usuario_admin_id: int, usuario_afectado_id: int, permisos_anteriores: dict, permisos_nuevos: dict, ip_address: str = None, usuario_info: str = None):
        """Registrar cambio de permisos con descripción detallada"""
        
        # Generar descripción legible
        permisos_otorgados = []
        permisos_quitados = []
        
        permisos_map = {
            'puede_ver': 'LECTURA',
            'puede_buscar': 'BÚSQUEDA',
            'puede_exportar': 'EXPORTACIÓN'
        }
        
        for key, nombre in permisos_map.items():
            antes = permisos_anteriores.get(key, False)
            ahora = permisos_nuevos.get(key, False)
            
            if not antes and ahora:
                permisos_otorgados.append(nombre)
            elif antes and not ahora:
                permisos_quitados.append(nombre)
        
        # Construir descripción
        usuario_desc = usuario_info if usuario_info else f"Usuario ID {usuario_afectado_id}"
        
        if permisos_otorgados and permisos_quitados:
            descripcion = f"Se otorgaron permisos de {', '.join(permisos_otorgados)} y se quitaron permisos de {', '.join(permisos_quitados)} a {usuario_desc}"
        elif permisos_otorgados:
            if len(permisos_otorgados) == 3:
                descripcion = f"Se otorgó ACCESO COMPLETO a {usuario_desc}"
            else:
                descripcion = f"Se otorgaron permisos de {', '.join(permisos_otorgados)} a {usuario_desc}"
        elif permisos_quitados:
            if len(permisos_quitados) == 3:
                descripcion = f"Se revocó TODO el acceso a {usuario_desc}"
            else:
                descripcion = f"Se quitaron permisos de {', '.join(permisos_quitados)} a {usuario_desc}"
        else:
            descripcion = f"Se actualizaron permisos de {usuario_desc}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_admin_id,
            accion="MODIFICAR_PERMISOS",
            tabla_afectada="permisos_sistema",
            registro_id=usuario_afectado_id,
            descripcion=descripcion,
            valores_anteriores=permisos_anteriores,
            valores_nuevos=permisos_nuevos,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_cambio_password(usuario_id: int, ip_address: str = None):
        """Registrar cambio de contraseña"""
        descripcion = f"Cambio de contraseña"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="CAMBIAR_PASSWORD",
            tabla_afectada="usuarios",
            registro_id=usuario_id,
            valores_nuevos={"evento": "cambio_password"},
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_procesamiento_ocr(usuario_id: int, tomo_id: int, archivo: str, ip_address: str = None):
        """Registrar procesamiento de OCR"""
        descripcion = f"Se procesó OCR del archivo '{archivo}'"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="PROCESAR_OCR",
            tabla_afectada="tomos",
            registro_id=tomo_id,
            valores_nuevos={"archivo": archivo, "evento": "ocr_procesado"},
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_creacion_carpeta(usuario_id: int, carpeta_id: int, nombre_carpeta: str, ip_address: str = None):
        """Registrar creación de carpeta"""
        descripcion = f"Se creó la carpeta '{nombre_carpeta}'"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="CREAR_CARPETA",
            tabla_afectada="carpetas",
            registro_id=carpeta_id,
            valores_nuevos={"nombre": nombre_carpeta, "evento": "carpeta_creada"},
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_eliminacion_carpeta(usuario_id: int, carpeta_id: int, nombre_carpeta: str, ip_address: str = None):
        """Registrar eliminación de carpeta"""
        descripcion = f"Se eliminó la carpeta '{nombre_carpeta}'"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="ELIMINAR_CARPETA",
            tabla_afectada="carpetas",
            registro_id=carpeta_id,
            valores_anteriores={"nombre": nombre_carpeta, "evento": "carpeta_eliminada"},
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_busqueda(usuario_id: int, termino_busqueda: str, tipo_busqueda: str, resultados: int, ip_address: str = None):
        """Registrar búsqueda realizada"""
        descripcion = f"Búsqueda {tipo_busqueda}: '{termino_busqueda}' ({resultados} resultados)"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
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
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_subir_tomo(usuario_id: int, tomo_id: int, nombre_tomo: str, carpeta: str = None, ip_address: str = None):
        """Registrar subida de tomo"""
        descripcion = f"Se subió el tomo '{nombre_tomo}'"
        if carpeta:
            descripcion += f" a la carpeta '{carpeta}'"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="SUBIR_TOMO",
            tabla_afectada="tomos",
            registro_id=tomo_id,
            valores_nuevos={"nombre": nombre_tomo, "carpeta": carpeta},
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_eliminar_tomo(usuario_id: int, tomo_id: int, nombre_tomo: str, ip_address: str = None):
        """Registrar eliminación de tomo"""
        descripcion = f"Se eliminó el tomo '{nombre_tomo}'"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="ELIMINAR_TOMO",
            tabla_afectada="tomos",
            registro_id=tomo_id,
            valores_anteriores={"nombre": nombre_tomo},
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_modificar_carpeta(usuario_id: int, carpeta_id: int, nombre_anterior: str, nombre_nuevo: str, ip_address: str = None):
        """Registrar modificación de carpeta"""
        descripcion = f"Se modificó la carpeta '{nombre_anterior}' a '{nombre_nuevo}'"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="MODIFICAR_CARPETA",
            tabla_afectada="carpetas",
            registro_id=carpeta_id,
            valores_anteriores={"nombre": nombre_anterior},
            valores_nuevos={"nombre": nombre_nuevo},
            descripcion=descripcion,
            ip_address=ip_address
        )
    
    @staticmethod
    def registrar_actualizar_embeddings(usuario_id: int, total_actualizados: int, ip_address: str = None):
        """Registrar actualización de embeddings"""
        descripcion = f"Se actualizaron {total_actualizados} embeddings"
        if ip_address:
            descripcion += f" desde la IP {ip_address}"
        
        AuditoriaLogger.registrar_evento(
            usuario_id=usuario_id,
            accion="ACTUALIZAR_EMBEDDINGS",
            tabla_afectada="tomos",
            valores_nuevos={"total_actualizados": total_actualizados},
            descripcion=descripcion,
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
def registrar_auditoria(usuario_id: int, accion: str, request: Request = None, **kwargs):
    """Función de conveniencia para registrar auditoría con auto-generación de descripciones"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 AUDIT DEBUG: Acción={accion}, Usuario={usuario_id}")
    
    # Extraer IP y user agent del request si está disponible
    if request and 'ip_address' not in kwargs:
        ip, user_agent = AuditoriaLogger.extraer_info_request(request)
        kwargs['ip_address'] = ip
        kwargs['user_agent'] = user_agent
        logger.info(f"🔍 AUDIT DEBUG: IP={ip}")
    
    # Auto-generar descripción si no existe
    if 'descripcion' not in kwargs or not kwargs['descripcion']:
        descripcion = _generar_descripcion_automatica(accion, kwargs)
        if descripcion:
            kwargs['descripcion'] = descripcion
            logger.info(f"🔍 AUDIT DEBUG: Descripción={descripcion}")
    
    logger.info(f"🔍 AUDIT DEBUG: kwargs={list(kwargs.keys())}")
    AuditoriaLogger.registrar_evento(usuario_id, accion, **kwargs)
    logger.info(f"✅ AUDIT DEBUG: Registro completado")

def _generar_descripcion_automatica(accion: str, datos: dict) -> str:
    """Generar descripción automática basada en la acción y los datos"""
    ip = datos.get('ip_address', '')
    valores_nuevos = datos.get('valores_nuevos', {})
    valores_anteriores = datos.get('valores_anteriores', {})
    
    descripcion = ""
    
    if accion == "CREAR_USUARIO":
        username = valores_nuevos.get('username', 'Usuario')
        nombre = valores_nuevos.get('nombre_completo', '')
        descripcion = f"Se creó el usuario '{username}'"
        if nombre:
            descripcion += f" ({nombre})"
    
    elif accion == "MODIFICAR_USUARIO":
        username = valores_nuevos.get('username') or valores_anteriores.get('username', 'Usuario')
        descripcion = f"Se modificó el usuario '{username}'"
    
    elif accion == "ELIMINAR_USUARIO":
        username = valores_anteriores.get('username', 'Usuario')
        nombre = valores_anteriores.get('nombre_completo', '')
        descripcion = f"Se eliminó el usuario '{username}'"
        if nombre:
            descripcion += f" ({nombre})"
    
    elif accion == "SUBIR_TOMO":
        nombre_archivo = valores_nuevos.get('nombre_archivo', 'archivo')
        carpeta_nombre = valores_nuevos.get('carpeta_nombre', '')
        descripcion = f"Se subió el tomo '{nombre_archivo}'"
        if carpeta_nombre:
            descripcion += f" a la carpeta '{carpeta_nombre}'"
    
    elif accion == "ELIMINAR_TOMO":
        nombre = valores_anteriores.get('nombre_archivo') or valores_nuevos.get('nombre_archivo', 'Tomo')
        descripcion = f"Se eliminó el tomo '{nombre}'"
    
    elif accion == "CREAR_CARPETA":
        nombre = valores_nuevos.get('nombre') or valores_nuevos.get('carpeta_nombre', 'Carpeta')
        descripcion = f"Se creó la carpeta '{nombre}'"
    
    elif accion == "MODIFICAR_CARPETA":
        nombre_anterior = valores_anteriores.get('nombre', '')
        nombre_nuevo = valores_nuevos.get('nombre', '')
        if nombre_anterior and nombre_nuevo:
            descripcion = f"Se modificó la carpeta '{nombre_anterior}' a '{nombre_nuevo}'"
        else:
            descripcion = f"Se modificó una carpeta"
    
    elif accion == "ELIMINAR_CARPETA":
        nombre = valores_anteriores.get('nombre') or valores_nuevos.get('nombre', 'Carpeta')
        descripcion = f"Se eliminó la carpeta '{nombre}'"
    
    elif accion == "PROCESAR_OCR":
        archivo = valores_nuevos.get('archivo', 'archivo')
        descripcion = f"Se procesó OCR del archivo '{archivo}'"
    
    elif accion == "CAMBIAR_PASSWORD":
        descripcion = "Cambio de contraseña"
    
    elif accion == "ACTUALIZAR_EMBEDDINGS":
        total = valores_nuevos.get('total_actualizados', 0)
        descripcion = f"Se actualizaron {total} embeddings"
    
    elif accion == "REALIZAR_BUSQUEDA":
        termino = valores_nuevos.get('termino', '')
        tipo = valores_nuevos.get('tipo', 'simple')
        resultados = valores_nuevos.get('resultados', 0)
        descripcion = f"Búsqueda {tipo}: '{termino}' ({resultados} resultados)"
    
    elif accion == "BUSQUEDA_TOMO":
        query = valores_nuevos.get('query', '')
        tomo_nombre = valores_nuevos.get('tomo_nombre', 'Tomo')
        resultados = valores_nuevos.get('total_resultados', 0)
        descripcion = f"Búsqueda en tomo '{tomo_nombre}': '{query}' ({resultados} resultados)"
    
    elif accion == "EXPORTAR_DATOS":
        tipo = valores_nuevos.get('tipo', 'datos')
        descripcion = f"Exportación de {tipo}"
    
    elif accion == "ACCEDER_AUDITORIA":
        descripcion = "Acceso al sistema de auditoría"
    
    elif accion == "CONFIGURACION":
        descripcion = "Cambio en la configuración del sistema"
    
    # Agregar IP si existe
    if descripcion and ip:
        descripcion += f" desde la IP {ip}"
    
    return descripcion

def audit_login_success(usuario_id: int, username: str, request: Request = None):
    """Auditar login exitoso"""
    ip, user_agent = AuditoriaLogger.extraer_info_request(request)
    AuditoriaLogger.registrar_login_exitoso(usuario_id, username, ip, user_agent)

def audit_login_failed(username: str, request: Request = None):
    """Auditar login fallido"""
    ip, user_agent = AuditoriaLogger.extraer_info_request(request)
    AuditoriaLogger.registrar_login_fallido(username, ip, user_agent)