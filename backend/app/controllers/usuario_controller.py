# backend/app/controllers/usuario_controller.py

from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.models.usuario import Usuario, Rol
from app.models.permiso import PermisoSistema
from app.utils.logger import logger
from app.utils.password_hash import hash_password


class UsuarioController:
    """Controlador para gestión de usuarios"""

    def crear_usuario(
        self,
        db: Session,
        username: str,
        email: str,
        password: str,
        rol_id: int,
        departamento: Optional[str] = None,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Crear nuevo usuario

        Args:
            db: Sesión de base de datos
            username: Nombre de usuario único
            email: Email único
            password: Contraseña en texto plano
            rol_id: ID del rol
            departamento: Departamento del usuario
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Información del usuario creado
        """
        try:
            # Validar permisos del usuario actual
            if current_user_id:
                permisos = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                if not permisos or not permisos.gestionar_usuarios:
                    logger.warning(f"Usuario {current_user_id} sin permisos para crear usuarios")
                    return {
                        "success": False,
                        "message": "No tiene permisos para crear usuarios"
                    }

            # Validar campos requeridos
            if not username or len(username) < 3:
                return {
                    "success": False,
                    "message": "El username debe tener al menos 3 caracteres"
                }

            if not email or '@' not in email:
                return {
                    "success": False,
                    "message": "Email inválido"
                }

            if not password or len(password) < 8:
                return {
                    "success": False,
                    "message": "La contraseña debe tener al menos 8 caracteres"
                }

            # Verificar que el username no exista
            if db.query(Usuario).filter(Usuario.username == username).first():
                return {
                    "success": False,
                    "message": "El username ya existe"
                }

            # Verificar que el email no exista
            if db.query(Usuario).filter(Usuario.email == email).first():
                return {
                    "success": False,
                    "message": "El email ya está registrado"
                }

            # Verificar que el rol exista
            rol = db.query(Rol).filter(Rol.id == rol_id).first()
            if not rol:
                return {
                    "success": False,
                    "message": "Rol no válido"
                }

            # Crear usuario
            nuevo_usuario = Usuario(
                username=username,
                email=email,
                password_hash=hash_password(password),
                rol_id=rol_id,
                departamento=departamento,
                activo=True
            )

            db.add(nuevo_usuario)
            db.flush()

            # Crear permisos de sistema por defecto (todos en False)
            permisos_sistema = PermisoSistema(
                usuario_id=nuevo_usuario.id,
                gestionar_usuarios=False,
                crear_carpetas=False,
                eliminar_documentos=False,
                ver_reportes=False,
                exportar_datos=False,
                ver_auditoria=False
            )

            db.add(permisos_sistema)
            db.commit()
            db.refresh(nuevo_usuario)

            logger.info(f"Usuario creado: {nuevo_usuario.username} por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Usuario creado exitosamente",
                "user": {
                    "id": nuevo_usuario.id,
                    "username": nuevo_usuario.username,
                    "email": nuevo_usuario.email,
                    "rol": rol.nombre,
                    "departamento": nuevo_usuario.departamento,
                    "activo": nuevo_usuario.activo,
                    "fecha_creacion": nuevo_usuario.fecha_creacion.isoformat()
                }
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al crear usuario: {str(e)}")
            return {
                "success": False,
                "message": f"Error al crear usuario: {str(e)}"
            }

    def obtener_usuario(self, db: Session, user_id: int) -> Dict[str, Any]:
        """
        Obtener información de un usuario

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            dict: Información del usuario
        """
        try:
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # Obtener permisos
            permisos = db.query(PermisoSistema).filter(
                PermisoSistema.usuario_id == user_id
            ).first()

            return {
                "success": True,
                "user": {
                    "id": usuario.id,
                    "username": usuario.username,
                    "email": usuario.email,
                    "rol_id": usuario.rol_id,
                    "rol": usuario.rol.nombre if usuario.rol else None,
                    "departamento": usuario.departamento,
                    "activo": usuario.activo,
                    "fecha_creacion": usuario.fecha_creacion.isoformat(),
                    "ultimo_acceso": usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None,
                    "permisos_sistema": {
                        "gestionar_usuarios": permisos.gestionar_usuarios if permisos else False,
                        "crear_carpetas": permisos.crear_carpetas if permisos else False,
                        "eliminar_documentos": permisos.eliminar_documentos if permisos else False,
                        "ver_reportes": permisos.ver_reportes if permisos else False,
                        "exportar_datos": permisos.exportar_datos if permisos else False,
                        "ver_auditoria": permisos.ver_auditoria if permisos else False
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error al obtener usuario: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener usuario: {str(e)}"
            }

    def listar_usuarios(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        activo: Optional[bool] = None,
        rol_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Listar usuarios con filtros

        Args:
            db: Sesión de base de datos
            skip: Número de registros a saltar
            limit: Número máximo de registros
            search: Búsqueda por username o email
            activo: Filtrar por estado activo
            rol_id: Filtrar por rol

        Returns:
            dict: Lista de usuarios
        """
        try:
            query = db.query(Usuario)

            # Aplicar filtros
            if search:
                query = query.filter(
                    or_(
                        Usuario.username.ilike(f"%{search}%"),
                        Usuario.email.ilike(f"%{search}%")
                    )
                )

            if activo is not None:
                query = query.filter(Usuario.activo == activo)

            if rol_id is not None:
                query = query.filter(Usuario.rol_id == rol_id)

            # Contar total
            total = query.count()

            # Obtener usuarios con paginación
            usuarios = query.offset(skip).limit(limit).all()

            usuarios_list = []
            for usuario in usuarios:
                usuarios_list.append({
                    "id": usuario.id,
                    "username": usuario.username,
                    "email": usuario.email,
                    "rol": usuario.rol.nombre if usuario.rol else None,
                    "departamento": usuario.departamento,
                    "activo": usuario.activo,
                    "fecha_creacion": usuario.fecha_creacion.isoformat(),
                    "ultimo_acceso": usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None
                })

            return {
                "success": True,
                "total": total,
                "skip": skip,
                "limit": limit,
                "users": usuarios_list
            }

        except Exception as e:
            logger.error(f"Error al listar usuarios: {str(e)}")
            return {
                "success": False,
                "message": f"Error al listar usuarios: {str(e)}"
            }

    def actualizar_usuario(
        self,
        db: Session,
        user_id: int,
        username: Optional[str] = None,
        email: Optional[str] = None,
        rol_id: Optional[int] = None,
        departamento: Optional[str] = None,
        activo: Optional[bool] = None,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Actualizar información de usuario

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario a actualizar
            username: Nuevo username (opcional)
            email: Nuevo email (opcional)
            rol_id: Nuevo rol_id (opcional)
            departamento: Nuevo departamento (opcional)
            activo: Nuevo estado (opcional)
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Usuario actualizado
        """
        try:
            # Validar permisos
            if current_user_id and current_user_id != user_id:
                permisos = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                if not permisos or not permisos.gestionar_usuarios:
                    logger.warning(f"Usuario {current_user_id} sin permisos para actualizar usuarios")
                    return {
                        "success": False,
                        "message": "No tiene permisos para actualizar usuarios"
                    }

            # Buscar usuario
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # Actualizar campos
            if username is not None:
                # Verificar que no exista otro usuario con ese username
                existe = db.query(Usuario).filter(
                    Usuario.username == username,
                    Usuario.id != user_id
                ).first()

                if existe:
                    return {
                        "success": False,
                        "message": "El username ya existe"
                    }

                usuario.username = username

            if email is not None:
                # Verificar que no exista otro usuario con ese email
                existe = db.query(Usuario).filter(
                    Usuario.email == email,
                    Usuario.id != user_id
                ).first()

                if existe:
                    return {
                        "success": False,
                        "message": "El email ya está registrado"
                    }

                usuario.email = email

            if rol_id is not None:
                # Verificar que el rol exista
                rol = db.query(Rol).filter(Rol.id == rol_id).first()
                if not rol:
                    return {
                        "success": False,
                        "message": "Rol no válido"
                    }
                usuario.rol_id = rol_id

            if departamento is not None:
                usuario.departamento = departamento

            if activo is not None:
                usuario.activo = activo

            db.commit()
            db.refresh(usuario)

            logger.info(f"Usuario {user_id} actualizado por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Usuario actualizado exitosamente",
                "user": {
                    "id": usuario.id,
                    "username": usuario.username,
                    "email": usuario.email,
                    "rol": usuario.rol.nombre if usuario.rol else None,
                    "departamento": usuario.departamento,
                    "activo": usuario.activo
                }
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al actualizar usuario: {str(e)}")
            return {
                "success": False,
                "message": f"Error al actualizar usuario: {str(e)}"
            }

    def eliminar_usuario(
        self,
        db: Session,
        user_id: int,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Eliminar DEFINITIVAMENTE usuario de la base de datos

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario a eliminar
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Confirmación de eliminación
        """
        try:
            # Validar permisos
            permisos = db.query(PermisoSistema).filter(
                PermisoSistema.usuario_id == current_user_id
            ).first()

            if not permisos or not permisos.gestionar_usuarios:
                logger.warning(f"Usuario {current_user_id} sin permisos para eliminar usuarios")
                return {
                    "success": False,
                    "message": "No tiene permisos para eliminar usuarios"
                }

            # No permitir auto-eliminación
            if user_id == current_user_id:
                return {
                    "success": False,
                    "message": "No puede eliminarse a sí mismo"
                }

            # Buscar usuario
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # ELIMINAR DEFINITIVAMENTE de la base de datos
            db.delete(usuario)
            db.commit()

            logger.info(f"✅ Usuario {user_id} ({usuario.username}) ELIMINADO DEFINITIVAMENTE por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Usuario eliminado definitivamente"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al eliminar usuario: {str(e)}")
            return {
                "success": False,
                "message": f"Error al eliminar usuario: {str(e)}"
            }

    def desactivar_usuario(
        self,
        db: Session,
        user_id: int,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Desactivar usuario (soft delete - mantiene el registro pero inactivo)

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario a desactivar
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Confirmación de desactivación
        """
        try:
            # Validar permisos
            permisos = db.query(PermisoSistema).filter(
                PermisoSistema.usuario_id == current_user_id
            ).first()

            if not permisos or not permisos.gestionar_usuarios:
                logger.warning(f"Usuario {current_user_id} sin permisos para desactivar usuarios")
                return {
                    "success": False,
                    "message": "No tiene permisos para desactivar usuarios"
                }

            # No permitir auto-desactivación
            if user_id == current_user_id:
                return {
                    "success": False,
                    "message": "No puede desactivarse a sí mismo"
                }

            # Buscar usuario
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # Desactivar usuario (mantiene el registro)
            usuario.activo = False
            db.commit()

            logger.info(f"⏸️ Usuario {user_id} ({usuario.username}) DESACTIVADO por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Usuario desactivado exitosamente"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al desactivar usuario: {str(e)}")
            return {
                "success": False,
                "message": f"Error al desactivar usuario: {str(e)}"
            }

    def activar_usuario(
        self,
        db: Session,
        user_id: int,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Activar usuario previamente desactivado

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario a activar
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Confirmación de activación
        """
        try:
            # Validar permisos
            permisos = db.query(PermisoSistema).filter(
                PermisoSistema.usuario_id == current_user_id
            ).first()

            if not permisos or not permisos.gestionar_usuarios:
                logger.warning(f"Usuario {current_user_id} sin permisos para activar usuarios")
                return {
                    "success": False,
                    "message": "No tiene permisos para activar usuarios"
                }

            # Buscar usuario
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # Activar usuario
            usuario.activo = True
            db.commit()

            logger.info(f"▶️ Usuario {user_id} ({usuario.username}) ACTIVADO por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Usuario activado exitosamente"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al activar usuario: {str(e)}")
            return {
                "success": False,
                "message": f"Error al activar usuario: {str(e)}"
            }

    def listar_roles(self, db: Session) -> Dict[str, Any]:
        """
        Listar todos los roles disponibles

        Args:
            db: Sesión de base de datos

        Returns:
            dict: Lista de roles
        """
        try:
            roles = db.query(Rol).all()

            roles_list = []
            for rol in roles:
                roles_list.append({
                    "id": rol.id,
                    "nombre": rol.nombre,
                    "descripcion": rol.descripcion
                })

            return {
                "success": True,
                "roles": roles_list
            }

        except Exception as e:
            logger.error(f"Error al listar roles: {str(e)}")
            return {
                "success": False,
                "message": f"Error al listar roles: {str(e)}"
            }


# Instancia global del controlador
usuario_controller = UsuarioController()
