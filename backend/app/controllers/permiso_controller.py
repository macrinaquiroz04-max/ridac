# backend/app/controllers/permiso_controller.py

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

from app.models.usuario import Usuario
from app.models.carpeta import Carpeta
from app.models.permiso import PermisoSistema, PermisoCarpeta
from app.utils.logger import logger


class PermisoController:
    """Controlador para gestión de permisos de sistema y carpetas"""

    def obtener_permisos_sistema(
        self,
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Obtener permisos de sistema de un usuario

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            dict: Permisos de sistema
        """
        try:
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            permisos = db.query(PermisoSistema).filter(
                PermisoSistema.usuario_id == user_id
            ).first()

            if not permisos:
                return {
                    "success": True,
                    "permisos": {
                        "gestionar_usuarios": False,
                        "crear_carpetas": False,
                        "eliminar_documentos": False,
                        "ver_reportes": False,
                        "exportar_datos": False,
                        "ver_auditoria": False
                    }
                }

            return {
                "success": True,
                "usuario_id": user_id,
                "username": usuario.username,
                "permisos": {
                    "gestionar_usuarios": permisos.gestionar_usuarios,
                    "crear_carpetas": permisos.crear_carpetas,
                    "eliminar_documentos": permisos.eliminar_documentos,
                    "ver_reportes": permisos.ver_reportes,
                    "exportar_datos": permisos.exportar_datos,
                    "ver_auditoria": permisos.ver_auditoria
                }
            }

        except Exception as e:
            logger.error(f"Error al obtener permisos de sistema: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener permisos: {str(e)}"
            }

    def actualizar_permisos_sistema(
        self,
        db: Session,
        user_id: int,
        gestionar_usuarios: Optional[bool] = None,
        crear_carpetas: Optional[bool] = None,
        eliminar_documentos: Optional[bool] = None,
        ver_reportes: Optional[bool] = None,
        exportar_datos: Optional[bool] = None,
        ver_auditoria: Optional[bool] = None,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Actualizar permisos de sistema de un usuario

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario a modificar
            gestionar_usuarios: Permiso para gestionar usuarios
            crear_carpetas: Permiso para crear carpetas
            eliminar_documentos: Permiso para eliminar documentos
            ver_reportes: Permiso para ver reportes
            exportar_datos: Permiso para exportar datos
            ver_auditoria: Permiso para ver auditoría
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Permisos actualizados
        """
        try:
            # Validar permisos del usuario actual
            if current_user_id:
                permisos_actuales = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                if not permisos_actuales or not permisos_actuales.gestionar_usuarios:
                    logger.warning(f"Usuario {current_user_id} sin permisos para modificar permisos")
                    return {
                        "success": False,
                        "message": "No tiene permisos para modificar permisos de sistema"
                    }

            # Verificar que el usuario existe
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # Buscar o crear permisos
            permisos = db.query(PermisoSistema).filter(
                PermisoSistema.usuario_id == user_id
            ).first()

            if not permisos:
                permisos = PermisoSistema(
                    usuario_id=user_id,
                    gestionar_usuarios=False,
                    crear_carpetas=False,
                    eliminar_documentos=False,
                    ver_reportes=False,
                    exportar_datos=False,
                    ver_auditoria=False
                )
                db.add(permisos)

            # Actualizar permisos
            if gestionar_usuarios is not None:
                permisos.gestionar_usuarios = gestionar_usuarios

            if crear_carpetas is not None:
                permisos.crear_carpetas = crear_carpetas

            if eliminar_documentos is not None:
                permisos.eliminar_documentos = eliminar_documentos

            if ver_reportes is not None:
                permisos.ver_reportes = ver_reportes

            if exportar_datos is not None:
                permisos.exportar_datos = exportar_datos

            if ver_auditoria is not None:
                permisos.ver_auditoria = ver_auditoria

            db.commit()
            db.refresh(permisos)

            logger.info(f"Permisos de sistema actualizados para usuario {user_id} por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Permisos actualizados exitosamente",
                "usuario_id": user_id,
                "permisos": {
                    "gestionar_usuarios": permisos.gestionar_usuarios,
                    "crear_carpetas": permisos.crear_carpetas,
                    "eliminar_documentos": permisos.eliminar_documentos,
                    "ver_reportes": permisos.ver_reportes,
                    "exportar_datos": permisos.exportar_datos,
                    "ver_auditoria": permisos.ver_auditoria
                }
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al actualizar permisos de sistema: {str(e)}")
            return {
                "success": False,
                "message": f"Error al actualizar permisos: {str(e)}"
            }

    def obtener_permisos_carpeta(
        self,
        db: Session,
        user_id: int,
        carpeta_id: int
    ) -> Dict[str, Any]:
        """
        Obtener permisos de un usuario sobre una carpeta

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            carpeta_id: ID de la carpeta

        Returns:
            dict: Permisos sobre la carpeta
        """
        try:
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
            carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            if not carpeta:
                return {
                    "success": False,
                    "message": "Carpeta no encontrada"
                }

            permiso = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == user_id,
                PermisoCarpeta.carpeta_id == carpeta_id
            ).first()

            if not permiso:
                return {
                    "success": True,
                    "permisos": {
                        "puede_ver": False,
                        "puede_descargar": False,
                        "puede_editar": False,
                        "puede_eliminar": False
                    }
                }

            return {
                "success": True,
                "usuario_id": user_id,
                "username": usuario.username,
                "carpeta_id": carpeta_id,
                "carpeta_nombre": carpeta.nombre_completo,
                "permisos": {
                    "puede_ver": permiso.puede_ver,
                    "puede_descargar": permiso.puede_descargar,
                    "puede_editar": permiso.puede_editar,
                    "puede_eliminar": permiso.puede_eliminar
                }
            }

        except Exception as e:
            logger.error(f"Error al obtener permisos de carpeta: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener permisos: {str(e)}"
            }

    def asignar_permisos_carpeta(
        self,
        db: Session,
        user_id: int,
        carpeta_id: int,
        puede_ver: bool = False,
        puede_descargar: bool = False,
        puede_editar: bool = False,
        puede_eliminar: bool = False,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Asignar o actualizar permisos de un usuario sobre una carpeta

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            carpeta_id: ID de la carpeta
            puede_ver: Permiso para ver
            puede_descargar: Permiso para descargar
            puede_editar: Permiso para editar
            puede_eliminar: Permiso para eliminar
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Permisos asignados
        """
        try:
            # Validar permisos del usuario actual
            if current_user_id:
                # Verificar si tiene permisos de sistema para gestionar usuarios
                permisos_sistema = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                tiene_permisos_sistema = permisos_sistema and permisos_sistema.gestionar_usuarios

                # O si tiene permisos de editar en la carpeta
                permiso_carpeta_actual = db.query(PermisoCarpeta).filter(
                    PermisoCarpeta.usuario_id == current_user_id,
                    PermisoCarpeta.carpeta_id == carpeta_id
                ).first()

                tiene_permisos_carpeta = permiso_carpeta_actual and permiso_carpeta_actual.puede_editar

                if not (tiene_permisos_sistema or tiene_permisos_carpeta):
                    logger.warning(f"Usuario {current_user_id} sin permisos para asignar permisos en carpeta {carpeta_id}")
                    return {
                        "success": False,
                        "message": "No tiene permisos para asignar permisos en esta carpeta"
                    }

            # Verificar que el usuario y carpeta existan
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
            carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            if not carpeta:
                return {
                    "success": False,
                    "message": "Carpeta no encontrada"
                }

            # Buscar o crear permiso
            permiso = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == user_id,
                PermisoCarpeta.carpeta_id == carpeta_id
            ).first()

            if not permiso:
                permiso = PermisoCarpeta(
                    usuario_id=user_id,
                    carpeta_id=carpeta_id,
                    puede_ver=puede_ver,
                    puede_descargar=puede_descargar,
                    puede_editar=puede_editar,
                    puede_eliminar=puede_eliminar
                )
                db.add(permiso)
            else:
                # Actualizar permisos existentes
                permiso.puede_ver = puede_ver
                permiso.puede_descargar = puede_descargar
                permiso.puede_editar = puede_editar
                permiso.puede_eliminar = puede_eliminar

            db.commit()
            db.refresh(permiso)

            logger.info(f"Permisos de carpeta {carpeta_id} asignados a usuario {user_id} por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Permisos asignados exitosamente",
                "usuario_id": user_id,
                "carpeta_id": carpeta_id,
                "permisos": {
                    "puede_ver": permiso.puede_ver,
                    "puede_descargar": permiso.puede_descargar,
                    "puede_editar": permiso.puede_editar,
                    "puede_eliminar": permiso.puede_eliminar
                }
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al asignar permisos de carpeta: {str(e)}")
            return {
                "success": False,
                "message": f"Error al asignar permisos: {str(e)}"
            }

    def revocar_permisos_carpeta(
        self,
        db: Session,
        user_id: int,
        carpeta_id: int,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Revocar todos los permisos de un usuario sobre una carpeta

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            carpeta_id: ID de la carpeta
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Confirmación de revocación
        """
        try:
            # Validar permisos del usuario actual
            permisos_sistema = db.query(PermisoSistema).filter(
                PermisoSistema.usuario_id == current_user_id
            ).first()

            tiene_permisos_sistema = permisos_sistema and permisos_sistema.gestionar_usuarios

            permiso_carpeta_actual = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == current_user_id,
                PermisoCarpeta.carpeta_id == carpeta_id
            ).first()

            tiene_permisos_carpeta = permiso_carpeta_actual and permiso_carpeta_actual.puede_editar

            if not (tiene_permisos_sistema or tiene_permisos_carpeta):
                logger.warning(f"Usuario {current_user_id} sin permisos para revocar permisos en carpeta {carpeta_id}")
                return {
                    "success": False,
                    "message": "No tiene permisos para revocar permisos en esta carpeta"
                }

            # Buscar permiso
            permiso = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == user_id,
                PermisoCarpeta.carpeta_id == carpeta_id
            ).first()

            if not permiso:
                return {
                    "success": False,
                    "message": "El usuario no tiene permisos asignados en esta carpeta"
                }

            # Eliminar permiso
            db.delete(permiso)
            db.commit()

            logger.info(f"Permisos de carpeta {carpeta_id} revocados a usuario {user_id} por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Permisos revocados exitosamente"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al revocar permisos de carpeta: {str(e)}")
            return {
                "success": False,
                "message": f"Error al revocar permisos: {str(e)}"
            }

    def listar_usuarios_carpeta(
        self,
        db: Session,
        carpeta_id: int,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Listar todos los usuarios con permisos en una carpeta

        Args:
            db: Sesión de base de datos
            carpeta_id: ID de la carpeta
            current_user_id: ID del usuario que consulta

        Returns:
            dict: Lista de usuarios con sus permisos
        """
        try:
            # Verificar que la carpeta existe
            carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

            if not carpeta:
                return {
                    "success": False,
                    "message": "Carpeta no encontrada"
                }

            # Verificar permisos del usuario actual
            if current_user_id:
                permiso_actual = db.query(PermisoCarpeta).filter(
                    PermisoCarpeta.usuario_id == current_user_id,
                    PermisoCarpeta.carpeta_id == carpeta_id
                ).first()

                if not permiso_actual or not permiso_actual.puede_ver:
                    # Verificar si es administrador
                    permisos_sistema = db.query(PermisoSistema).filter(
                        PermisoSistema.usuario_id == current_user_id
                    ).first()

                    if not permisos_sistema or not permisos_sistema.ver_auditoria:
                        return {
                            "success": False,
                            "message": "No tiene permisos para ver esta carpeta"
                        }

            # Obtener permisos de la carpeta
            permisos = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.carpeta_id == carpeta_id
            ).all()

            usuarios_list = []
            for permiso in permisos:
                usuario = permiso.usuario
                usuarios_list.append({
                    "usuario_id": usuario.id,
                    "username": usuario.username,
                    "email": usuario.email,
                    "permisos": {
                        "puede_ver": permiso.puede_ver,
                        "puede_descargar": permiso.puede_descargar,
                        "puede_editar": permiso.puede_editar,
                        "puede_eliminar": permiso.puede_eliminar
                    }
                })

            return {
                "success": True,
                "carpeta_id": carpeta_id,
                "carpeta_nombre": carpeta.nombre_completo,
                "total_usuarios": len(usuarios_list),
                "usuarios": usuarios_list
            }

        except Exception as e:
            logger.error(f"Error al listar usuarios de carpeta: {str(e)}")
            return {
                "success": False,
                "message": f"Error al listar usuarios: {str(e)}"
            }

    def listar_carpetas_usuario(
        self,
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Listar todas las carpetas a las que un usuario tiene acceso

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            dict: Lista de carpetas con permisos
        """
        try:
            # Verificar que el usuario existe
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()

            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # Obtener permisos del usuario
            permisos = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == user_id
            ).all()

            carpetas_list = []
            for permiso in permisos:
                carpeta = permiso.carpeta
                if carpeta.activo:  # Solo carpetas activas
                    carpetas_list.append({
                        "carpeta_id": carpeta.id,
                        "nombre_completo": carpeta.nombre_completo,
                        "numero_expediente": carpeta.numero_expediente,
                        "permisos": {
                            "puede_ver": permiso.puede_ver,
                            "puede_descargar": permiso.puede_descargar,
                            "puede_editar": permiso.puede_editar,
                            "puede_eliminar": permiso.puede_eliminar
                        }
                    })

            return {
                "success": True,
                "usuario_id": user_id,
                "username": usuario.username,
                "total_carpetas": len(carpetas_list),
                "carpetas": carpetas_list
            }

        except Exception as e:
            logger.error(f"Error al listar carpetas de usuario: {str(e)}")
            return {
                "success": False,
                "message": f"Error al listar carpetas: {str(e)}"
            }

    def obtener_tomos_accesibles_usuario(self, user_id: int, db):
        """Obtener tomos accesibles para un usuario específico"""
        try:
            from app.models.usuario import Usuario
            from app.models.tomo import Tomo
            from app.models.permiso_tomo import PermisoTomo
            
            # Verificar que el usuario existe
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado"
                }

            # Obtener permisos de tomos del usuario
            permisos_query = db.query(PermisoTomo).filter(
                PermisoTomo.usuario_id == user_id
            ).all()

            tomos_list = []
            total_ver = 0
            total_buscar = 0
            total_exportar = 0

            for permiso in permisos_query:
                if permiso.tomo:
                    tomo_data = {
                        "id": permiso.tomo.id,
                        "numero": permiso.tomo.numero_tomo,
                        "nombre_archivo": permiso.tomo.nombre_archivo,
                        "carpeta_id": permiso.tomo.carpeta_id,
                        "nombre_carpeta": permiso.tomo.carpeta.nombre if permiso.tomo.carpeta else None,
                        "puede_ver": permiso.puede_ver,
                        "puede_buscar": permiso.puede_buscar,
                        "puede_exportar": permiso.puede_exportar,
                        "fecha_creacion": permiso.tomo.fecha_subida.isoformat() if permiso.tomo.fecha_subida else None
                    }
                    tomos_list.append(tomo_data)
                    
                    if permiso.puede_ver:
                        total_ver += 1
                    if permiso.puede_buscar:
                        total_buscar += 1
                    if permiso.puede_exportar:
                        total_exportar += 1

            return {
                "success": True,
                "usuario_id": user_id,
                "username": usuario.username,
                "total_tomos": len(tomos_list),
                "total_ver": total_ver,
                "total_buscar": total_buscar,
                "total_exportar": total_exportar,
                "tomos": tomos_list
            }

        except Exception as e:
            logger.error(f"Error al obtener tomos accesibles de usuario: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener tomos accesibles: {str(e)}"
            }


# Instancia global del controlador
permiso_controller = PermisoController()
