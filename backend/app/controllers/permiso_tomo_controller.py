# backend/app/controllers/permiso_tomo_controller.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional, Dict
from datetime import datetime

from app.models.permiso_tomo import PermisoTomo
from app.models.usuario import Usuario
from app.models.tomo import Tomo, ContenidoOCR
from app.models.carpeta import Carpeta
from app.utils.limpieza_automatica import LimpiezaAutomatica

class PermisoTomoController:
    
    @staticmethod
    def asignar_permiso(db: Session, usuario_id: int, tomo_id: int, 
                       puede_ver: bool = True, puede_buscar: bool = False, 
                       puede_exportar: bool = False, usuario_admin_id: int = None) -> PermisoTomo:
        """
        Asigna permisos específicos a un usuario para un tomo determinado
        Optimizado para concurrencia con 20 usuarios simultáneos
        """
        try:
            # Verificar que el usuario existe
            usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario con ID {usuario_id} no encontrado"
                )
            
            # Verificar que el tomo existe
            tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
            if not tomo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tomo con ID {tomo_id} no encontrado"
                )
            
            # Buscar permiso existente
            permiso_existente = db.query(PermisoTomo).filter(
                PermisoTomo.usuario_id == usuario_id,
                PermisoTomo.tomo_id == tomo_id
            ).first()
            
            if permiso_existente:
                # Actualizar permisos existentes
                permiso_existente.puede_ver = puede_ver
                permiso_existente.puede_buscar = puede_buscar
                permiso_existente.puede_exportar = puede_exportar
                permiso_existente.updated_at = datetime.utcnow()
                
                # Si todos los permisos están en False, eliminar el registro
                if not puede_ver and not puede_buscar and not puede_exportar:
                    db.delete(permiso_existente)
                    db.commit()
                    # Limpieza automática del usuario
                    try:
                        LimpiezaAutomatica.verificar_y_limpiar_usuario(db, usuario_id)
                    except Exception as e:
                        print(f"Warning: Error en limpieza automática: {e}")
                    return None
                
                db.commit()
                db.refresh(permiso_existente)
                return permiso_existente
            else:
                # Solo crear nuevo permiso si al menos uno está en True
                if not puede_ver and not puede_buscar and not puede_exportar:
                    return None
                    
                # Crear nuevo permiso
                nuevo_permiso = PermisoTomo(
                    usuario_id=usuario_id,
                    tomo_id=tomo_id,
                    puede_ver=puede_ver,
                    puede_buscar=puede_buscar,
                    puede_exportar=puede_exportar
                )
                
                db.add(nuevo_permiso)
                db.commit()
                db.refresh(nuevo_permiso)
                return nuevo_permiso
                
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al asignar permiso: {str(e)}"
            )
    
    @staticmethod
    def obtener_permisos_usuario(db: Session, usuario_id: int) -> List[PermisoTomo]:
        """
        Obtiene todos los permisos de tomos asignados a un usuario
        """
        return db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == usuario_id
        ).all()
    
    @staticmethod
    def obtener_permisos_tomo(db: Session, tomo_id: int) -> List[PermisoTomo]:
        """
        Obtiene todos los usuarios que tienen permisos para un tomo específico
        """
        return db.query(PermisoTomo).filter(
            PermisoTomo.tomo_id == tomo_id
        ).all()
    
    @staticmethod
    def verificar_permiso(db: Session, usuario_id: int, tomo_id: int, 
                         tipo_permiso: str = "ver") -> bool:
        """
        Verifica si un usuario tiene un permiso específico para un tomo
        tipo_permiso: 'ver', 'descargar', 'exportar'
        """
        permiso = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == usuario_id,
            PermisoTomo.tomo_id == tomo_id
        ).first()
        
        if not permiso:
            return False
        
        if tipo_permiso == "ver":
            return permiso.puede_ver
        elif tipo_permiso == "buscar":
            return permiso.puede_buscar
        elif tipo_permiso == "exportar":
            return permiso.puede_exportar
        else:
            return False
    
    @staticmethod
    def revocar_permiso(db: Session, usuario_id: int, tomo_id: int) -> bool:
        """
        Revoca todos los permisos de un usuario para un tomo específico
        """
        permiso = db.query(PermisoTomo).filter(
            PermisoTomo.usuario_id == usuario_id,
            PermisoTomo.tomo_id == tomo_id
        ).first()
        
        if permiso:
            db.delete(permiso)
            db.commit()
            return True
        return False
    
    @staticmethod
    def asignar_permisos_masivos(db: Session, usuario_id: int, tomos_ids: List[int],
                                permisos: Dict[str, bool], usuario_admin_id: int = None) -> List[PermisoTomo]:
        """
        Asigna permisos para múltiples tomos a un usuario de una vez
        Optimizado para operaciones en lote con 20 usuarios simultáneos
        """
        permisos_creados = []
        
        try:
            # Verificar usuario una sola vez
            usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Usuario con ID {usuario_id} no encontrado"
                )
            
            # Procesar en lotes de 10 para evitar bloqueos largos
            batch_size = 10
            for i in range(0, len(tomos_ids), batch_size):
                batch_tomos = tomos_ids[i:i + batch_size]
                
                for tomo_id in batch_tomos:
                    # Verificar si el tomo existe
                    tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
                    if not tomo:
                        continue  # Saltar tomos inexistentes, no fallar todo
                    
                    # Buscar permiso existente
                    permiso_existente = db.query(PermisoTomo).filter(
                        PermisoTomo.usuario_id == usuario_id,
                        PermisoTomo.tomo_id == tomo_id
                    ).first()
                    
                    puede_ver = permisos.get("puede_ver", True)
                    puede_buscar = permisos.get("puede_buscar", False)
                    puede_exportar = permisos.get("puede_exportar", False)
                    
                    if permiso_existente:
                        # Actualizar existente
                        permiso_existente.puede_ver = puede_ver
                        permiso_existente.puede_buscar = puede_buscar
                        permiso_existente.puede_exportar = puede_exportar
                        permiso_existente.updated_at = datetime.utcnow()
                        
                        # Eliminar si todos están en False
                        if not puede_ver and not puede_buscar and not puede_exportar:
                            db.delete(permiso_existente)
                        else:
                            permisos_creados.append(permiso_existente)
                    else:
                        # Crear nuevo solo si al menos uno es True
                        if puede_ver or puede_buscar or puede_exportar:
                            nuevo_permiso = PermisoTomo(
                                usuario_id=usuario_id,
                                tomo_id=tomo_id,
                                puede_ver=puede_ver,
                                puede_buscar=puede_buscar,
                                puede_exportar=puede_exportar
                            )
                            db.add(nuevo_permiso)
                            permisos_creados.append(nuevo_permiso)
                
                # Flush intermedio para evitar acumulación de memoria
                db.flush()
            
            # Commit final
            db.commit()
            
            # Limpieza automática después del commit
            try:
                LimpiezaAutomatica.verificar_y_limpiar_usuario(db, usuario_id)
            except Exception as e:
                print(f"Warning: Error en limpieza automática masiva: {e}")
            
            # IMPORTANTE: Recargar todos los permisos del usuario desde la BD
            # para asegurar que la respuesta refleje el estado real
            permisos_actuales = db.query(PermisoTomo).filter(
                PermisoTomo.usuario_id == usuario_id
            ).all()
            
            print(f"✅ Permisos masivos aplicados. Total permisos del usuario: {len(permisos_actuales)}")
            
            return permisos_actuales
            
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error en asignación masiva: {str(e)}"
            )
    
    @staticmethod
    def obtener_tomos_con_acceso(db: Session, usuario_id: int) -> List[Dict]:
        """
        Obtiene todos los tomos a los que un usuario tiene acceso con información detallada
        """
        query = db.query(
            PermisoTomo, Tomo, Carpeta
        ).join(
            Tomo, PermisoTomo.tomo_id == Tomo.id
        ).join(
            Carpeta, Tomo.carpeta_id == Carpeta.id
        ).filter(
            PermisoTomo.usuario_id == usuario_id,
            PermisoTomo.puede_ver == True
        )
        
        resultados = query.all()
        
        tomos_con_permisos = []
        for permiso, tomo, carpeta in resultados:
            tomos_con_permisos.append({
                "tomo_id": tomo.id,
                "numero_tomo": tomo.numero_tomo,
                "nombre_archivo": tomo.nombre_archivo,
                "carpeta_nombre": carpeta.nombre,
                "carpeta_codigo": carpeta.numero_expediente,
                "permisos": {
                    "puede_ver": permiso.puede_ver,
                    "puede_buscar": permiso.puede_buscar,
                    "puede_exportar": permiso.puede_exportar
                },
                "fecha_asignacion": permiso.created_at
            })
        
        return tomos_con_permisos
    
    @staticmethod
    def obtener_usuarios_con_permisos_carpeta(db: Session, carpeta_id: int) -> List[Dict]:
        """
        Obtiene todos los usuarios que tienen permisos para tomos de una carpeta específica
        """
        query = db.query(
            Usuario, PermisoTomo, Tomo
        ).join(
            PermisoTomo, Usuario.id == PermisoTomo.usuario_id
        ).join(
            Tomo, PermisoTomo.tomo_id == Tomo.id
        ).filter(
            Tomo.carpeta_id == carpeta_id
        ).distinct()
        
        resultados = query.all()
        
        usuarios_permisos = {}
        for usuario, permiso, tomo in resultados:
            if usuario.id not in usuarios_permisos:
                usuarios_permisos[usuario.id] = {
                    "usuario_id": usuario.id,
                    "username": usuario.username,
                    "nombre": usuario.nombre,
                    "tomos_con_acceso": []
                }
            
            usuarios_permisos[usuario.id]["tomos_con_acceso"].append({
                "tomo_id": tomo.id,
                "numero_tomo": tomo.numero_tomo,
                "permisos": {
                    "puede_ver": permiso.puede_ver,
                    "puede_buscar": permiso.puede_buscar,
                    "puede_exportar": permiso.puede_exportar
                }
            })
        
        return list(usuarios_permisos.values())
    
    @staticmethod
    def obtener_tomos_accesibles_usuario(db: Session, usuario_id: int) -> List[Dict]:
        """
        Obtiene todos los tomos a los que tiene acceso un usuario específico
        """
        # Buscar tomos accesibles para usuario
        
        # Verificar que el usuario existe
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {usuario_id} no encontrado"
            )
        

        
        # Consultar tomos con permisos del usuario incluyendo información de carpeta
        query = db.query(PermisoTomo, Tomo, Carpeta).join(
            Tomo, PermisoTomo.tomo_id == Tomo.id
        ).join(
            Carpeta, Tomo.carpeta_id == Carpeta.id
        ).filter(
            PermisoTomo.usuario_id == usuario_id
        ).order_by(Carpeta.nombre, Tomo.numero_tomo)
        
        resultados = query.all()

        
        tomos_accesibles = []
        for permiso, tomo, carpeta in resultados:
            # Procesando tomo con permisos
            
            # Solo incluir si tiene al menos un permiso activo
            if permiso.puede_ver or permiso.puede_buscar or permiso.puede_exportar:
                # Usar un valor por defecto para las páginas por ahora
                total_paginas = 0
                try:
                    # Obtener el número de páginas del contenido OCR
                    total_paginas = db.query(ContenidoOCR).filter(
                        ContenidoOCR.tomo_id == tomo.id
                    ).count()

                except Exception as e:

                    total_paginas = 0
                
                tomo_data = {
                    "id": tomo.id,  # Agregar campo 'id' que espera el frontend
                    "tomo_id": tomo.id,
                    "numero_tomo": tomo.numero_tomo,
                    "nombre_archivo": tomo.nombre_archivo,
                    "total_paginas": total_paginas,
                    "carpeta_id": carpeta.id,
                    "carpeta_nombre": carpeta.nombre,
                    "carpeta_codigo": carpeta.numero_expediente,
                    "permisos": {
                        "puede_ver": permiso.puede_ver,
                        "puede_buscar": permiso.puede_buscar,
                        "puede_exportar": permiso.puede_exportar
                    }
                }
                tomos_accesibles.append(tomo_data)
                # Tomo agregado a la lista
            # Solo incluir tomos con permisos activos
        return tomos_accesibles
    
    @staticmethod
    def verificar_permisos_administrador(db: Session, usuario_id: int) -> bool:
        """
        Verifica si un usuario tiene permisos de administrador para gestionar permisos
        """
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario or not usuario.rol:
            return False
        
        # Solo administradores pueden gestionar permisos de tomos
        roles_admin = ["admin", "Admin", "Administrador", "Director"]
        return usuario.rol.nombre in roles_admin