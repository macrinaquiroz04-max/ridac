# backend/app/controllers/auth_controller.py

from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import traceback
import os

from app.models.usuario import Usuario, TokenReset
from app.models.permiso import PermisoSistema
from app.utils.logger import logger
from app.utils.password_hash import hash_password, verify_password
from app.utils.jwt_handler import create_access_token, create_refresh_token, verify_token
from app.utils.auditoria_utils import AuditoriaLogger


class AuthController:
    """Controlador para autenticación y gestión de sesiones"""

    def login(self, db: Session, username_or_email: str, password: str, ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """
        Autenticar usuario y generar tokens JWT

        Args:
            db: Sesión de base de datos
            username_or_email: Username o email del usuario
            password: Contraseña en texto plano
            ip_address: Dirección IP del cliente
            user_agent: User agent del navegador

        Returns:
            dict: Tokens de acceso y refresh con información del usuario
            
        🛡️ PROTECCIÓN ANTI-CRASH:
        - Captura errores de BD
        - Registra en logs
        - Siempre devuelve respuesta
        """
        import traceback
        
        try:
            # Buscar usuario por username o email
            usuario = db.query(Usuario).filter(
                or_(
                    Usuario.username == username_or_email,
                    Usuario.email == username_or_email
                )
            ).first()

            if not usuario:
                logger.warning(f"Intento de login fallido: usuario no encontrado ({username_or_email})")
                
                # Registrar intento fallido en auditoría
                try:
                    AuditoriaLogger.registrar_login_fallido(username_or_email, ip_address, user_agent)
                except Exception as audit_error:
                    logger.warning(f"Error al registrar auditoría de login fallido: {audit_error}")
                
                return {
                    "success": False,
                    "message": "Credenciales inválidas"
                }

            # Verificar si el usuario está activo
            if not usuario.activo:
                logger.warning(f"Intento de login de usuario inactivo: {usuario.username}")
                return {
                    "success": False,
                    "message": "Usuario inactivo. Contacte al administrador."
                }

            # Verificar contraseña
            if not verify_password(password, usuario.password):
                logger.warning(f"Intento de login fallido: contraseña incorrecta para {usuario.username}")
                
                # Registrar intento fallido en auditoría
                try:
                    AuditoriaLogger.registrar_login_fallido(usuario.username, ip_address, user_agent)
                except Exception as audit_error:
                    logger.warning(f"Error al registrar auditoría de login fallido: {audit_error}")
                
                return {
                    "success": False,
                    "message": "Credenciales inválidas"
                }

            # Actualizar último acceso
            usuario.ultimo_acceso = datetime.utcnow()
            db.commit()

            # Obtener permisos del sistema
            permisos_sistema = db.query(PermisoSistema).filter(
                PermisoSistema.usuario_id == usuario.id
            ).first()

            # Crear payload para JWT
            token_data = {
                "sub": str(usuario.id),
                "username": usuario.username,
                "email": usuario.email,
                "rol_id": usuario.rol_id
            }

            # Generar tokens
            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)

            logger.info(f"Login exitoso: {usuario.username}")

            # Registrar login exitoso en auditoría
            try:
                AuditoriaLogger.registrar_login_exitoso(
                    usuario_id=usuario.id,
                    username=usuario.username,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            except Exception as audit_error:
                logger.warning(f"Error al registrar auditoría de login: {audit_error}")

            return {
                "success": True,
                "message": "Login exitoso",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": usuario.id,
                    "username": usuario.username,
                    "email": usuario.email,
                    "rol_id": usuario.rol_id,
                    "rol": usuario.rol.nombre if usuario.rol else None,
                    "nombre_completo": usuario.nombre_completo,
                    "debe_cambiar_password": usuario.debe_cambiar_password,
                    "permisos_sistema": {
                        "gestionar_usuarios": permisos_sistema.gestionar_usuarios if permisos_sistema else False,
                        "gestionar_roles": permisos_sistema.gestionar_roles if permisos_sistema else False,
                        "gestionar_carpetas": permisos_sistema.gestionar_carpetas if permisos_sistema else False,
                        "procesar_ocr": permisos_sistema.procesar_ocr if permisos_sistema else False,
                        "ver_auditoria": permisos_sistema.ver_auditoria if permisos_sistema else False
                    }
                }
            }

        except Exception as e:
            # 🔥 CAPTURA DE ERROR CON LOGGING DETALLADO
            error_trace = traceback.format_exc()
            
            db.rollback()
            
            # Guardar error en log específico de auth
            log_dir = "logs/auth_errors"
            os.makedirs(log_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"{log_dir}/auth_controller_error_{timestamp}.log"
            
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(f"=" * 80 + "\n")
                f.write(f"ERROR EN AUTH CONTROLLER - {datetime.now().isoformat()}\n")
                f.write(f"=" * 80 + "\n\n")
                f.write(f"Usuario: {username_or_email}\n")
                f.write(f"IP: {ip_address}\n")
                f.write(f"User-Agent: {user_agent}\n\n")
                f.write(f"TIPO DE ERROR: {type(e).__name__}\n")
                f.write(f"MENSAJE: {str(e)}\n\n")
                f.write(f"TRACEBACK:\n")
                f.write(error_trace)
                f.write("\n" + "=" * 80 + "\n")
            
            logger.error(f"🚨 ERROR EN AUTH CONTROLLER - Log: {log_file}")
            logger.error(f"   Usuario: {username_or_email}")
            logger.error(f"   Error: {type(e).__name__}: {str(e)}")
            
            return {
                "success": False,
                "message": "Error temporal del servidor. Por favor intente nuevamente.",
                "error_logged": True,
                "error_file": log_file
            }

    def logout(self, db: Session, user_id: int) -> Dict[str, Any]:
        """
        Cerrar sesión de usuario (en este sistema solo registra el evento)

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            dict: Confirmación de logout
        """
        try:
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            logger.info(f"Logout: {usuario.username}")

            # Registrar logout en auditoría
            try:
                AuditoriaLogger.registrar_logout(
                    usuario_id=usuario.id,
                    username=usuario.username
                )
            except Exception as audit_error:
                logger.warning(f"Error al registrar auditoría de logout: {audit_error}")

            return {
                "success": True,
                "message": "Sesión cerrada exitosamente"
            }

        except Exception as e:
            logger.error(f"Error en logout: {str(e)}")
            return {
                "success": False,
                "message": f"Error al cerrar sesión: {str(e)}"
            }

    def refresh(self, db: Session, refresh_token: str) -> Dict[str, Any]:
        """
        Renovar access token usando refresh token

        Args:
            db: Sesión de base de datos
            refresh_token: Token de refresco válido

        Returns:
            dict: Nuevo access token
        """
        try:
            # Verificar refresh token
            payload = verify_token(refresh_token)

            if not payload:
                return {
                    "success": False,
                    "message": "Token inválido o expirado"
                }

            # Verificar que sea refresh token
            if payload.get("type") != "refresh":
                return {
                    "success": False,
                    "message": "Token inválido"
                }

            user_id = int(payload.get("sub"))

            # Verificar que el usuario siga activo
            usuario = db.query(Usuario).filter(
                Usuario.id == user_id,
                Usuario.activo == True
            ).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado o inactivo"
                }

            # Crear nuevo access token
            token_data = {
                "sub": str(usuario.id),
                "username": usuario.username,
                "email": usuario.email,
                "rol_id": usuario.rol_id
            }

            access_token = create_access_token(token_data)

            logger.info(f"Token renovado para: {usuario.username}")

            return {
                "success": True,
                "message": "Token renovado exitosamente",
                "access_token": access_token,
                "token_type": "bearer"
            }

        except Exception as e:
            logger.error(f"Error en refresh: {str(e)}")
            return {
                "success": False,
                "message": f"Error al renovar token: {str(e)}"
            }

    def request_password_reset(self, db: Session, email: str) -> Dict[str, Any]:
        """
        Solicitar reseteo de contraseña

        Args:
            db: Sesión de base de datos
            email: Email del usuario

        Returns:
            dict: Token de reseteo (en producción se enviaría por email)
        """
        try:
            usuario = db.query(Usuario).filter(Usuario.email == email).first()

            if not usuario:
                # Por seguridad, no revelar si el email existe
                logger.warning(f"Solicitud de reset para email no existente: {email}")
                return {
                    "success": True,
                    "message": "Si el email existe, recibirá instrucciones de reseteo"
                }

            if not usuario.activo:
                return {
                    "success": False,
                    "message": "Usuario inactivo"
                }

            # Generar token único
            reset_token = secrets.token_urlsafe(32)
            expira_en = datetime.utcnow() + timedelta(hours=24)

            # Crear registro de token
            token_reset = TokenReset(
                usuario_id=usuario.id,
                token=reset_token,
                expira_en=expira_en,
                usado=False
            )

            db.add(token_reset)
            db.commit()

            logger.info(f"Token de reset generado para: {usuario.username}")

            # En producción, aquí se enviaría un email
            # Por ahora retornamos el token directamente
            return {
                "success": True,
                "message": "Token de reseteo generado",
                "reset_token": reset_token,  # En producción NO se retornaría
                "expires_in_hours": 24
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error en request_password_reset: {str(e)}")
            return {
                "success": False,
                "message": f"Error al solicitar reseteo: {str(e)}"
            }

    def reset_password(
        self,
        db: Session,
        reset_token: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Resetear contraseña usando token

        Args:
            db: Sesión de base de datos
            reset_token: Token de reseteo válido
            new_password: Nueva contraseña

        Returns:
            dict: Confirmación de cambio de contraseña
        """
        try:
            # Buscar token válido
            token_record = db.query(TokenReset).filter(
                TokenReset.token == reset_token,
                TokenReset.usado == False,
                TokenReset.expira_en > datetime.utcnow()
            ).first()

            if not token_record:
                logger.warning("Intento de reset con token inválido o expirado")
                return {
                    "success": False,
                    "message": "Token inválido o expirado"
                }

            # Obtener usuario
            usuario = db.query(Usuario).filter(
                Usuario.id == token_record.usuario_id
            ).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # Validar nueva contraseña
            if len(new_password) < 8:
                return {
                    "success": False,
                    "message": "La contraseña debe tener al menos 8 caracteres"
                }

            # Actualizar contraseña
            usuario.password = hash_password(new_password)

            # Marcar token como usado
            token_record.usado = True

            db.commit()

            logger.info(f"Contraseña reseteada para: {usuario.username}")

            return {
                "success": True,
                "message": "Contraseña actualizada exitosamente"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error en reset_password: {str(e)}")
            return {
                "success": False,
                "message": f"Error al resetear contraseña: {str(e)}"
            }

    def change_password(
        self,
        db: Session,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Cambiar contraseña (requiere contraseña actual)

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            current_password: Contraseña actual
            new_password: Nueva contraseña

        Returns:
            dict: Confirmación de cambio
        """
        try:
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # Verificar contraseña actual
            if not verify_password(current_password, usuario.password):
                logger.warning(f"Intento de cambio de contraseña con contraseña incorrecta: {usuario.username}")
                return {
                    "success": False,
                    "message": "Contraseña actual incorrecta"
                }

            # Validar nueva contraseña
            if len(new_password) < 8:
                return {
                    "success": False,
                    "message": "La contraseña debe tener al menos 8 caracteres"
                }

            # Actualizar contraseña
            usuario.password = hash_password(new_password)
            db.commit()

            logger.info(f"Contraseña cambiada para: {usuario.username}")

            # Registrar cambio de contraseña en auditoría
            try:
                AuditoriaLogger.registrar_cambio_password(
                    usuario_id=usuario.id,
                    username=usuario.username
                )
            except Exception as audit_error:
                logger.warning(f"Error al registrar auditoría de cambio de contraseña: {audit_error}")

            return {
                "success": True,
                "message": "Contraseña actualizada exitosamente"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error en change_password: {str(e)}")
            return {
                "success": False,
                "message": f"Error al cambiar contraseña: {str(e)}"
            }

    def verify_token_validity(self, token: str) -> Dict[str, Any]:
        """
        Verificar si un token es válido

        Args:
            token: Token JWT a verificar

        Returns:
            dict: Estado de validez del token
        """
        try:
            payload = verify_token(token)

            if not payload:
                return {
                    "success": False,
                    "valid": False,
                    "message": "Token inválido o expirado"
                }

            return {
                "success": True,
                "valid": True,
                "message": "Token válido",
                "user_id": int(payload.get("sub")),
                "username": payload.get("username"),
                "token_type": payload.get("type")
            }

        except Exception as e:
            logger.error(f"Error en verify_token_validity: {str(e)}")
            return {
                "success": False,
                "valid": False,
                "message": f"Error al verificar token: {str(e)}"
            }


# Instancia global del controlador
auth_controller = AuthController()
