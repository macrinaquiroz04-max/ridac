# backend/app/controllers/carpeta_controller.py

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.models.carpeta import Carpeta
from app.models.permiso import PermisoSistema, PermisoCarpeta
from app.utils.logger import logger
from app.config import settings


class CarpetaController:
    """Controlador para gestión de carpetas"""

    def crear_carpeta(
        self,
        db: Session,
        nombre_completo: str,
        numero_expediente: Optional[str] = None,
        descripcion: Optional[str] = None,
        current_user_id: int = None
    ) -> Dict[str, Any]:
        """
        Crear nueva carpeta

        Args:
            db: Sesión de base de datos
            nombre_completo: Nombre completo de la carpeta
            numero_expediente: Número de expediente
            descripcion: Descripción de la carpeta
            current_user_id: ID del usuario que crea la carpeta

        Returns:
            dict: Información de la carpeta creada
        """
        try:
            # Validar permisos
            if current_user_id:
                permisos = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                if not permisos or not permisos.crear_carpetas:
                    logger.warning(f"Usuario {current_user_id} sin permisos para crear carpetas")
                    return {
                        "success": False,
                        "message": "No tiene permisos para crear carpetas"
                    }

            # Validar campos requeridos
            if not nombre_completo or len(nombre_completo) < 3:
                return {
                    "success": False,
                    "message": "El nombre de la carpeta debe tener al menos 3 caracteres"
                }

            # Verificar que no exista una carpeta con el mismo nombre
            if db.query(Carpeta).filter(Carpeta.nombre_completo == nombre_completo).first():
                return {
                    "success": False,
                    "message": "Ya existe una carpeta con ese nombre"
                }

            # Crear carpeta física en el sistema de archivos
            carpeta_path = Path(settings.UPLOAD_PATH) / nombre_completo.replace("/", "_").replace("\\", "_")

            try:
                carpeta_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Error al crear directorio físico: {str(e)}")
                return {
                    "success": False,
                    "message": f"Error al crear directorio: {str(e)}"
                }

            # Crear registro en base de datos
            nueva_carpeta = Carpeta(
                nombre_completo=nombre_completo,
                numero_expediente=numero_expediente,
                descripcion=descripcion,
                creado_por=current_user_id,
                activo=True
            )

            db.add(nueva_carpeta)
            db.flush()

            # Asignar permisos completos al creador
            if current_user_id:
                permiso_creador = PermisoCarpeta(
                    usuario_id=current_user_id,
                    carpeta_id=nueva_carpeta.id,
                    puede_ver=True,
                    puede_descargar=True,
                    puede_editar=True,
                    puede_eliminar=True
                )
                db.add(permiso_creador)

            db.commit()
            db.refresh(nueva_carpeta)

            logger.info(f"Carpeta creada: {nueva_carpeta.nombre_completo} por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Carpeta creada exitosamente",
                "carpeta": {
                    "id": nueva_carpeta.id,
                    "nombre_completo": nueva_carpeta.nombre_completo,
                    "numero_expediente": nueva_carpeta.numero_expediente,
                    "descripcion": nueva_carpeta.descripcion,
                    "activo": nueva_carpeta.activo,
                    "fecha_creacion": nueva_carpeta.fecha_creacion.isoformat(),
                    "ruta_fisica": str(carpeta_path)
                }
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al crear carpeta: {str(e)}")
            return {
                "success": False,
                "message": f"Error al crear carpeta: {str(e)}"
            }

    def obtener_carpeta(
        self,
        db: Session,
        carpeta_id: int,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtener información de una carpeta

        Args:
            db: Sesión de base de datos
            carpeta_id: ID de la carpeta
            current_user_id: ID del usuario que consulta

        Returns:
            dict: Información de la carpeta
        """
        try:
            carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

            if not carpeta:
                return {
                    "success": False,
                    "message": "Carpeta no encontrada"
                }

            # Verificar permisos del usuario
            if current_user_id:
                permiso = db.query(PermisoCarpeta).filter(
                    PermisoCarpeta.usuario_id == current_user_id,
                    PermisoCarpeta.carpeta_id == carpeta_id
                ).first()

                if not permiso or not permiso.puede_ver:
                    # Verificar si es administrador
                    permisos_sistema = db.query(PermisoSistema).filter(
                        PermisoSistema.usuario_id == current_user_id
                    ).first()

                    if not permisos_sistema or not permisos_sistema.ver_auditoria:
                        logger.warning(f"Usuario {current_user_id} sin permisos para ver carpeta {carpeta_id}")
                        return {
                            "success": False,
                            "message": "No tiene permisos para ver esta carpeta"
                        }

            # Contar tomos
            total_tomos = len(carpeta.tomos)

            return {
                "success": True,
                "carpeta": {
                    "id": carpeta.id,
                    "nombre_completo": carpeta.nombre_completo,
                    "numero_expediente": carpeta.numero_expediente,
                    "descripcion": carpeta.descripcion,
                    "activo": carpeta.activo,
                    "fecha_creacion": carpeta.fecha_creacion.isoformat(),
                    "creado_por": carpeta.creador.username if carpeta.creador else None,
                    "total_tomos": total_tomos
                }
            }

        except Exception as e:
            logger.error(f"Error al obtener carpeta: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener carpeta: {str(e)}"
            }

    def listar_carpetas(
        self,
        db: Session,
        current_user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        activo: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Listar carpetas con filtros (solo las que el usuario tiene permiso)

        Args:
            db: Sesión de base de datos
            current_user_id: ID del usuario que consulta
            skip: Número de registros a saltar
            limit: Número máximo de registros
            search: Búsqueda por nombre o expediente
            activo: Filtrar por estado activo

        Returns:
            dict: Lista de carpetas
        """
        try:
            # Obtener permisos del usuario
            permisos_sistema = None
            if current_user_id:
                permisos_sistema = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

            # Si es administrador, puede ver todas
            es_admin = permisos_sistema and permisos_sistema.ver_auditoria

            if es_admin:
                query = db.query(Carpeta)
            else:
                # Filtrar solo carpetas con permiso (PermisoCarpeta usa 'tipo')
                query = db.query(Carpeta).join(PermisoCarpeta).filter(
                    PermisoCarpeta.usuario_id == current_user_id
                )

            # Aplicar filtros
            if search:
                query = query.filter(
                    (Carpeta.nombre_completo.ilike(f"%{search}%")) |
                    (Carpeta.numero_expediente.ilike(f"%{search}%"))
                )

            if activo is not None:
                query = query.filter(Carpeta.activo == activo)

            # Contar total
            total = query.count()

            # Obtener carpetas con paginación
            carpetas = query.offset(skip).limit(limit).all()

            carpetas_list = []
            for carpeta in carpetas:
                total_tomos = len(carpeta.tomos)

                carpetas_list.append({
                    "id": carpeta.id,
                    "nombre_completo": carpeta.nombre_completo,
                    "numero_expediente": carpeta.numero_expediente,
                    "descripcion": carpeta.descripcion,
                    "activo": carpeta.activo,
                    "fecha_creacion": carpeta.fecha_creacion.isoformat(),
                    "creado_por": carpeta.creador.username if carpeta.creador else None,
                    "total_tomos": total_tomos
                })

            return {
                "success": True,
                "total": total,
                "skip": skip,
                "limit": limit,
                "carpetas": carpetas_list
            }

        except Exception as e:
            logger.error(f"Error al listar carpetas: {str(e)}")
            return {
                "success": False,
                "message": f"Error al listar carpetas: {str(e)}"
            }

    def actualizar_carpeta(
        self,
        db: Session,
        carpeta_id: int,
        nombre_completo: Optional[str] = None,
        numero_expediente: Optional[str] = None,
        descripcion: Optional[str] = None,
        activo: Optional[bool] = None,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Actualizar información de una carpeta

        Args:
            db: Sesión de base de datos
            carpeta_id: ID de la carpeta
            nombre_completo: Nuevo nombre (opcional)
            numero_expediente: Nuevo número de expediente (opcional)
            descripcion: Nueva descripción (opcional)
            activo: Nuevo estado (opcional)
            current_user_id: ID del usuario que actualiza

        Returns:
            dict: Carpeta actualizada
        """
        try:
            # Buscar carpeta
            carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

            if not carpeta:
                return {
                    "success": False,
                    "message": "Carpeta no encontrada"
                }

            # Verificar permisos
            if current_user_id:
                permiso = db.query(PermisoCarpeta).filter(
                    PermisoCarpeta.usuario_id == current_user_id,
                    PermisoCarpeta.carpeta_id == carpeta_id
                ).first()

                if not permiso or not permiso.puede_editar:
                    logger.warning(f"Usuario {current_user_id} sin permisos para editar carpeta {carpeta_id}")
                    return {
                        "success": False,
                        "message": "No tiene permisos para editar esta carpeta"
                    }

            # Actualizar campos
            if nombre_completo is not None:
                # Verificar que no exista otra carpeta con ese nombre
                existe = db.query(Carpeta).filter(
                    Carpeta.nombre_completo == nombre_completo,
                    Carpeta.id != carpeta_id
                ).first()

                if existe:
                    return {
                        "success": False,
                        "message": "Ya existe otra carpeta con ese nombre"
                    }

                carpeta.nombre_completo = nombre_completo

            if numero_expediente is not None:
                carpeta.numero_expediente = numero_expediente

            if descripcion is not None:
                carpeta.descripcion = descripcion

            if activo is not None:
                carpeta.activo = activo

            db.commit()
            db.refresh(carpeta)

            logger.info(f"Carpeta {carpeta_id} actualizada por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Carpeta actualizada exitosamente",
                "carpeta": {
                    "id": carpeta.id,
                    "nombre_completo": carpeta.nombre_completo,
                    "numero_expediente": carpeta.numero_expediente,
                    "descripcion": carpeta.descripcion,
                    "activo": carpeta.activo
                }
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al actualizar carpeta: {str(e)}")
            return {
                "success": False,
                "message": f"Error al actualizar carpeta: {str(e)}"
            }

    def eliminar_carpeta(
        self,
        db: Session,
        carpeta_id: int,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Eliminar (desactivar) carpeta

        Args:
            db: Sesión de base de datos
            carpeta_id: ID de la carpeta a eliminar
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Confirmación de eliminación
        """
        try:
            # Buscar carpeta
            carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

            if not carpeta:
                return {
                    "success": False,
                    "message": "Carpeta no encontrada"
                }

            # Verificar permisos
            permiso = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == current_user_id,
                PermisoCarpeta.carpeta_id == carpeta_id
            ).first()

            if not permiso or not permiso.puede_eliminar:
                # Verificar permisos de sistema
                permisos_sistema = db.query(PermisoSistema).filter(
                    PermisoSistema.usuario_id == current_user_id
                ).first()

                if not permisos_sistema or not permisos_sistema.eliminar_documentos:
                    logger.warning(f"Usuario {current_user_id} sin permisos para eliminar carpeta {carpeta_id}")
                    return {
                        "success": False,
                        "message": "No tiene permisos para eliminar esta carpeta"
                    }

            # En lugar de eliminar físicamente, desactivamos
            carpeta.activo = False
            db.commit()

            logger.info(f"Carpeta {carpeta_id} desactivada por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Carpeta desactivada exitosamente"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al eliminar carpeta: {str(e)}")
            return {
                "success": False,
                "message": f"Error al eliminar carpeta: {str(e)}"
            }

    def obtener_tomos_carpeta(
        self,
        db: Session,
        carpeta_id: int,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtener lista de tomos de una carpeta

        Args:
            db: Sesión de base de datos
            carpeta_id: ID de la carpeta
            current_user_id: ID del usuario que consulta

        Returns:
            dict: Lista de tomos
        """
        try:
            # Buscar carpeta
            carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

            if not carpeta:
                return {
                    "success": False,
                    "message": "Carpeta no encontrada"
                }

            # Verificar permisos
            if current_user_id:
                permiso = db.query(PermisoCarpeta).filter(
                    PermisoCarpeta.usuario_id == current_user_id,
                    PermisoCarpeta.carpeta_id == carpeta_id
                ).first()

                if not permiso or not permiso.puede_ver:
                    return {
                        "success": False,
                        "message": "No tiene permisos para ver esta carpeta"
                    }

            # Obtener tomos
            tomos_list = []
            for tomo in carpeta.tomos:
                tomos_list.append({
                    "id": tomo.id,
                    "numero_tomo": tomo.numero_tomo,
                    "nombre_archivo": tomo.nombre_archivo,
                    "tamaño_mb": float(tomo.tamaño_mb) if tomo.tamaño_mb else None,
                    "total_paginas": tomo.total_paginas,
                    "estado_ocr": tomo.estado_ocr,
                    "progreso_ocr": tomo.progreso_ocr,
                    "fecha_subida": tomo.fecha_subida.isoformat(),
                    "subido_por": tomo.subido_por_usuario.username if tomo.subido_por_usuario else None
                })

            return {
                "success": True,
                "carpeta": carpeta.nombre_completo,
                "total_tomos": len(tomos_list),
                "tomos": tomos_list
            }

        except Exception as e:
            logger.error(f"Error al obtener tomos de carpeta: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener tomos: {str(e)}"
            }


# Instancia global del controlador
carpeta_controller = CarpetaController()
