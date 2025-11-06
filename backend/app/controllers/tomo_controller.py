# backend/app/controllers/tomo_controller.py

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
import shutil
import uuid

from app.models.carpeta import Carpeta
from app.models.tomo import Tomo, ContenidoOCR
from app.models.permiso import PermisoCarpeta
from app.utils.logger import logger
from app.config import settings


class TomoController:
    """Controlador para gestión de tomos y subida de PDFs"""

    def subir_tomo(
        self,
        db: Session,
        carpeta_id: int,
        numero_tomo: int,
        archivo: BinaryIO,
        nombre_archivo: str,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Subir nuevo tomo PDF

        Args:
            db: Sesión de base de datos
            carpeta_id: ID de la carpeta
            numero_tomo: Número del tomo
            archivo: Archivo PDF
            nombre_archivo: Nombre del archivo
            current_user_id: ID del usuario que sube

        Returns:
            dict: Información del tomo subido
        """
        try:
            # Verificar que la carpeta existe
            carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()

            if not carpeta:
                return {
                    "success": False,
                    "message": "Carpeta no encontrada"
                }

            # Verificar permisos del usuario
            permiso = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == current_user_id,
                PermisoCarpeta.carpeta_id == carpeta_id
            ).first()

            if not permiso or not permiso.puede_editar:
                logger.warning(f"Usuario {current_user_id} sin permisos para subir tomos a carpeta {carpeta_id}")
                return {
                    "success": False,
                    "message": "No tiene permisos para subir archivos a esta carpeta"
                }

            # Verificar que el archivo sea PDF
            if not nombre_archivo.lower().endswith('.pdf'):
                return {
                    "success": False,
                    "message": "Solo se permiten archivos PDF"
                }

            # Verificar que no exista un tomo con el mismo número en esta carpeta
            tomo_existente = db.query(Tomo).filter(
                Tomo.carpeta_id == carpeta_id,
                Tomo.numero_tomo == numero_tomo
            ).first()

            if tomo_existente:
                return {
                    "success": False,
                    "message": f"Ya existe el tomo {numero_tomo} en esta carpeta"
                }

            # Crear directorio de la carpeta si no existe
            nombre_carpeta_sanitizado = carpeta.nombre.replace("/", "_").replace("\\", "_")
            carpeta_path = Path(settings.UPLOAD_PATH) / nombre_carpeta_sanitizado

            try:
                carpeta_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Error al crear directorio: {str(e)}")
                return {
                    "success": False,
                    "message": f"Error al crear directorio: {str(e)}"
                }

            # Generar nombre único para el archivo
            extension = Path(nombre_archivo).suffix
            nombre_unico = f"tomo_{numero_tomo}_{uuid.uuid4().hex[:8]}{extension}"
            ruta_archivo = carpeta_path / nombre_unico

            # Guardar archivo
            try:
                with open(ruta_archivo, 'wb') as f:
                    shutil.copyfileobj(archivo, f)

                # Obtener tamaño del archivo en MB
                tamaño_bytes = ruta_archivo.stat().st_size
                tamaño_mb = round(tamaño_bytes / (1024 * 1024), 2)

            except Exception as e:
                logger.error(f"Error al guardar archivo: {str(e)}")
                return {
                    "success": False,
                    "message": f"Error al guardar archivo: {str(e)}"
                }

            # Contar páginas del PDF (opcional)
            total_paginas = None
            try:
                from PyPDF2 import PdfReader
                pdf_reader = PdfReader(str(ruta_archivo))
                total_paginas = len(pdf_reader.pages)
            except Exception as e:
                logger.warning(f"No se pudo contar páginas del PDF: {str(e)}")

            # Crear registro en base de datos
            nuevo_tomo = Tomo(
                carpeta_id=carpeta_id,
                numero_tomo=numero_tomo,
                nombre_archivo=nombre_archivo,
                ruta_archivo=str(ruta_archivo),
                tamaño_mb=tamaño_mb,
                total_paginas=total_paginas,
                estado_ocr='pendiente',
                progreso_ocr=0,
                subido_por=current_user_id
            )

            db.add(nuevo_tomo)
            db.commit()
            db.refresh(nuevo_tomo)

            logger.info(f"Tomo subido: {nombre_archivo} a carpeta {carpeta_id} por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Tomo subido exitosamente",
                "tomo": {
                    "id": nuevo_tomo.id,
                    "carpeta_id": carpeta_id,
                    "numero_tomo": numero_tomo,
                    "nombre_archivo": nombre_archivo,
                    "tamaño_mb": tamaño_mb,
                    "total_paginas": total_paginas,
                    "estado_ocr": nuevo_tomo.estado_ocr,
                    "fecha_subida": nuevo_tomo.fecha_subida.isoformat()
                }
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al subir tomo: {str(e)}")
            return {
                "success": False,
                "message": f"Error al subir tomo: {str(e)}"
            }

    def obtener_tomo(
        self,
        db: Session,
        tomo_id: int,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtener información de un tomo

        Args:
            db: Sesión de base de datos
            tomo_id: ID del tomo
            current_user_id: ID del usuario que consulta

        Returns:
            dict: Información del tomo
        """
        try:
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()

            if not tomo:
                return {
                    "success": False,
                    "message": "Tomo no encontrado"
                }

            # Verificar permisos
            if current_user_id:
                permiso = db.query(PermisoCarpeta).filter(
                    PermisoCarpeta.usuario_id == current_user_id,
                    PermisoCarpeta.carpeta_id == tomo.carpeta_id
                ).first()

                if not permiso or not permiso.puede_ver:
                    logger.warning(f"Usuario {current_user_id} sin permisos para ver tomo {tomo_id}")
                    return {
                        "success": False,
                        "message": "No tiene permisos para ver este tomo"
                    }

            return {
                "success": True,
                "tomo": {
                    "id": tomo.id,
                    "carpeta_id": tomo.carpeta_id,
                    "carpeta_nombre": tomo.carpeta.nombre,
                    "numero_tomo": tomo.numero_tomo,
                    "nombre_archivo": tomo.nombre_archivo,
                    "ruta_archivo": tomo.ruta_archivo,
                    "tamaño_mb": float(tomo.tamaño_mb) if tomo.tamaño_mb else None,
                    "total_paginas": tomo.total_paginas,
                    "estado_ocr": tomo.estado_ocr,
                    "progreso_ocr": tomo.progreso_ocr,
                    "error_ocr": tomo.error_ocr,
                    "fecha_subida": tomo.fecha_subida.isoformat(),
                    "subido_por": tomo.subido_por_usuario.username if tomo.subido_por_usuario else None
                }
            }

        except Exception as e:
            logger.error(f"Error al obtener tomo: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener tomo: {str(e)}"
            }

    def listar_tomos(
        self,
        db: Session,
        carpeta_id: Optional[int] = None,
        estado_ocr: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Listar tomos con filtros

        Args:
            db: Sesión de base de datos
            carpeta_id: Filtrar por carpeta
            estado_ocr: Filtrar por estado OCR
            skip: Número de registros a saltar
            limit: Número máximo de registros
            current_user_id: ID del usuario que consulta

        Returns:
            dict: Lista de tomos
        """
        try:
            query = db.query(Tomo)

            # Filtrar por carpeta
            if carpeta_id:
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

                query = query.filter(Tomo.carpeta_id == carpeta_id)
            else:
                # Si no se especifica carpeta, filtrar solo carpetas con permiso
                if current_user_id:
                    carpetas_permitidas = db.query(PermisoCarpeta.carpeta_id).filter(
                        PermisoCarpeta.usuario_id == current_user_id
                    ).all()

                    carpetas_ids = [c[0] for c in carpetas_permitidas]
                    query = query.filter(Tomo.carpeta_id.in_(carpetas_ids))

            # Filtrar por estado OCR
            if estado_ocr:
                query = query.filter(Tomo.estado_ocr == estado_ocr)

            # Contar total
            total = query.count()

            # Obtener tomos con paginación
            tomos = query.order_by(Tomo.fecha_subida.desc()).offset(skip).limit(limit).all()

            tomos_list = []
            for tomo in tomos:
                tomos_list.append({
                    "id": tomo.id,
                    "carpeta_id": tomo.carpeta_id,
                    "carpeta_nombre": tomo.carpeta.nombre_completo,
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
                "total": total,
                "skip": skip,
                "limit": limit,
                "tomos": tomos_list
            }

        except Exception as e:
            logger.error(f"Error al listar tomos: {str(e)}")
            return {
                "success": False,
                "message": f"Error al listar tomos: {str(e)}"
            }

    def actualizar_tomo(
        self,
        db: Session,
        tomo_id: int,
        numero_tomo: Optional[int] = None,
        estado_ocr: Optional[str] = None,
        progreso_ocr: Optional[int] = None,
        error_ocr: Optional[str] = None,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Actualizar información de un tomo

        Args:
            db: Sesión de base de datos
            tomo_id: ID del tomo
            numero_tomo: Nuevo número de tomo (opcional)
            estado_ocr: Nuevo estado OCR (opcional)
            progreso_ocr: Nuevo progreso OCR (opcional)
            error_ocr: Error de OCR (opcional)
            current_user_id: ID del usuario que actualiza

        Returns:
            dict: Tomo actualizado
        """
        try:
            # Buscar tomo
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()

            if not tomo:
                return {
                    "success": False,
                    "message": "Tomo no encontrado"
                }

            # Verificar permisos
            if current_user_id:
                permiso = db.query(PermisoCarpeta).filter(
                    PermisoCarpeta.usuario_id == current_user_id,
                    PermisoCarpeta.carpeta_id == tomo.carpeta_id
                ).first()

                if not permiso or not permiso.puede_editar:
                    logger.warning(f"Usuario {current_user_id} sin permisos para editar tomo {tomo_id}")
                    return {
                        "success": False,
                        "message": "No tiene permisos para editar este tomo"
                    }

            # Actualizar campos
            if numero_tomo is not None:
                # Verificar que no exista otro tomo con ese número en la misma carpeta
                existe = db.query(Tomo).filter(
                    Tomo.carpeta_id == tomo.carpeta_id,
                    Tomo.numero_tomo == numero_tomo,
                    Tomo.id != tomo_id
                ).first()

                if existe:
                    return {
                        "success": False,
                        "message": f"Ya existe otro tomo con el número {numero_tomo} en esta carpeta"
                    }

                tomo.numero_tomo = numero_tomo

            if estado_ocr is not None:
                valid_estados = ['pendiente', 'procesando', 'completado', 'error']
                if estado_ocr not in valid_estados:
                    return {
                        "success": False,
                        "message": f"Estado OCR inválido. Debe ser: {', '.join(valid_estados)}"
                    }
                tomo.estado_ocr = estado_ocr

            if progreso_ocr is not None:
                if progreso_ocr < 0 or progreso_ocr > 100:
                    return {
                        "success": False,
                        "message": "El progreso debe estar entre 0 y 100"
                    }
                tomo.progreso_ocr = progreso_ocr

            if error_ocr is not None:
                tomo.error_ocr = error_ocr

            db.commit()
            db.refresh(tomo)

            logger.info(f"Tomo {tomo_id} actualizado por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Tomo actualizado exitosamente",
                "tomo": {
                    "id": tomo.id,
                    "numero_tomo": tomo.numero_tomo,
                    "estado_ocr": tomo.estado_ocr,
                    "progreso_ocr": tomo.progreso_ocr,
                    "error_ocr": tomo.error_ocr
                }
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al actualizar tomo: {str(e)}")
            return {
                "success": False,
                "message": f"Error al actualizar tomo: {str(e)}"
            }

    def eliminar_tomo(
        self,
        db: Session,
        tomo_id: int,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Eliminar tomo (archivo y registro)

        Args:
            db: Sesión de base de datos
            tomo_id: ID del tomo a eliminar
            current_user_id: ID del usuario que ejecuta la acción

        Returns:
            dict: Confirmación de eliminación
        """
        try:
            # Buscar tomo
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()

            if not tomo:
                return {
                    "success": False,
                    "message": "Tomo no encontrado"
                }

            # Verificar permisos
            permiso = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == current_user_id,
                PermisoCarpeta.carpeta_id == tomo.carpeta_id
            ).first()

            if not permiso or not permiso.puede_eliminar:
                logger.warning(f"Usuario {current_user_id} sin permisos para eliminar tomo {tomo_id}")
                return {
                    "success": False,
                    "message": "No tiene permisos para eliminar este tomo"
                }

            # Eliminar archivo físico
            try:
                archivo_path = Path(tomo.ruta_archivo)
                if archivo_path.exists():
                    archivo_path.unlink()
                    logger.info(f"Archivo físico eliminado: {tomo.ruta_archivo}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo físico: {str(e)}")

            # Eliminar registro (esto eliminará en cascada contenido_ocr y tareas_ocr)
            db.delete(tomo)
            db.commit()

            logger.info(f"Tomo {tomo_id} eliminado por usuario {current_user_id}")

            return {
                "success": True,
                "message": "Tomo eliminado exitosamente"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error al eliminar tomo: {str(e)}")
            return {
                "success": False,
                "message": f"Error al eliminar tomo: {str(e)}"
            }

    def descargar_tomo(
        self,
        db: Session,
        tomo_id: int,
        current_user_id: int
    ) -> Dict[str, Any]:
        """
        Obtener ruta para descargar tomo

        Args:
            db: Sesión de base de datos
            tomo_id: ID del tomo
            current_user_id: ID del usuario que descarga

        Returns:
            dict: Ruta del archivo para descarga
        """
        try:
            # Buscar tomo
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()

            if not tomo:
                return {
                    "success": False,
                    "message": "Tomo no encontrado"
                }

            # Verificar permisos
            permiso = db.query(PermisoCarpeta).filter(
                PermisoCarpeta.usuario_id == current_user_id,
                PermisoCarpeta.carpeta_id == tomo.carpeta_id
            ).first()

            if not permiso or not permiso.puede_descargar:
                logger.warning(f"Usuario {current_user_id} sin permisos para descargar tomo {tomo_id}")
                return {
                    "success": False,
                    "message": "No tiene permisos para descargar este tomo"
                }

            # Verificar que el archivo existe
            archivo_path = Path(tomo.ruta_archivo)
            if not archivo_path.exists():
                logger.error(f"Archivo físico no encontrado: {tomo.ruta_archivo}")
                return {
                    "success": False,
                    "message": "Archivo no encontrado en el sistema"
                }

            logger.info(f"Tomo {tomo_id} descargado por usuario {current_user_id}")

            return {
                "success": True,
                "file_path": tomo.ruta_archivo,
                "nombre_archivo": tomo.nombre_archivo,
                "tamaño_mb": float(tomo.tamaño_mb) if tomo.tamaño_mb else None
            }

        except Exception as e:
            logger.error(f"Error al descargar tomo: {str(e)}")
            return {
                "success": False,
                "message": f"Error al descargar tomo: {str(e)}"
            }

    def obtener_contenido_ocr(
        self,
        db: Session,
        tomo_id: int,
        pagina: Optional[int] = None,
        current_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Obtener contenido OCR de un tomo o página específica

        Args:
            db: Sesión de base de datos
            tomo_id: ID del tomo
            pagina: Número de página específica (opcional)
            current_user_id: ID del usuario que consulta

        Returns:
            dict: Contenido OCR
        """
        try:
            # Buscar tomo
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()

            if not tomo:
                return {
                    "success": False,
                    "message": "Tomo no encontrado"
                }

            # Verificar permisos
            if current_user_id:
                permiso = db.query(PermisoCarpeta).filter(
                    PermisoCarpeta.usuario_id == current_user_id,
                    PermisoCarpeta.carpeta_id == tomo.carpeta_id
                ).first()

                if not permiso or not permiso.puede_ver:
                    return {
                        "success": False,
                        "message": "No tiene permisos para ver este tomo"
                    }

            # Obtener contenido OCR
            query = db.query(ContenidoOCR).filter(ContenidoOCR.tomo_id == tomo_id)

            if pagina is not None:
                query = query.filter(ContenidoOCR.pagina == pagina)

            contenido_list = query.order_by(ContenidoOCR.pagina).all()

            if not contenido_list:
                return {
                    "success": False,
                    "message": "No hay contenido OCR disponible para este tomo"
                }

            contenido_data = []
            for contenido in contenido_list:
                # Extraer información de carátula si existe
                es_caratula = False
                razon_caratula = None
                
                if contenido.datos_adicionales:
                    es_caratula = contenido.datos_adicionales.get('ignorada', False) or \
                                 contenido.datos_adicionales.get('es_caratula', False)
                    razon_caratula = contenido.datos_adicionales.get('razon')
                
                contenido_data.append({
                    "numero_pagina": contenido.numero_pagina,  # ← NÚMERO FÍSICO DEL PDF
                    "texto_extraido": contenido.texto_extraido,
                    "confianza": float(contenido.confianza) if contenido.confianza else 0.0,
                    "es_caratula": es_caratula,
                    "razon": razon_caratula,
                    "motor_usado": contenido.datos_adicionales.get('motor') if contenido.datos_adicionales else None,
                    "fecha_proceso": contenido.created_at.isoformat() if hasattr(contenido, 'created_at') else None
                })

            return {
                "success": True,
                "tomo_id": tomo_id,
                "tomo_nombre": tomo.nombre_archivo,
                "total_paginas": len(contenido_data),
                "contenido": contenido_data
            }

        except Exception as e:
            logger.error(f"Error al obtener contenido OCR: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener contenido OCR: {str(e)}"
            }


# Instancia global del controlador
tomo_controller = TomoController()
