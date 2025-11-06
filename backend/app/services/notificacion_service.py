from datetime import datetime
from typing import Optional, List, Dict
import json
from sqlalchemy.orm import Session
from app.models.notificacion import Notificacion
from app.models.usuario import Usuario

class NotificacionService:
    def __init__(self, db: Session):
        self.db = db

    def crear_notificacion(
        self,
        usuario_id: int,
        tipo: str,
        mensaje: str,
        titulo: str = None,
        url_accion: str = None,
        metadata: Optional[Dict] = None
    ) -> Notificacion:
        """
        Crea una nueva notificación para un usuario
        """
        # Si no se proporciona título, generarlo del tipo
        if not titulo:
            titulo = tipo.replace('_', ' ').title()
        
        notificacion = Notificacion(
            usuario_id=usuario_id,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            url_accion=url_accion,
            datos_extra=metadata  # Usar datos_extra en lugar de datos_adicionales
        )
        self.db.add(notificacion)
        self.db.commit()
        self.db.refresh(notificacion)
        return notificacion

    def notificar_eliminacion_tomo(
        self,
        usuario_id: int,
        tomo_nombre: str,
        tomo_id: int,
        carpeta_id: Optional[int] = None
    ) -> Notificacion:
        """
        Crea una notificación específica para cuando se elimina un tomo
        """
        mensaje = f"El tomo '{tomo_nombre}' ha sido eliminado correctamente."
        metadata = {
            "tomo_id": tomo_id,
            "carpeta_id": carpeta_id,
            "fecha_eliminacion": datetime.now().isoformat()
        }
        
        return self.crear_notificacion(
            usuario_id=usuario_id,
            tipo="TOMO_ELIMINADO",
            mensaje=mensaje,
            metadata=metadata
        )

    def marcar_como_leida(self, notificacion_id: int) -> bool:
        """
        Marca una notificación como leída
        """
        notificacion = self.db.query(Notificacion).filter(
            Notificacion.id == notificacion_id
        ).first()

        if notificacion:
            notificacion.leida = True
            notificacion.leida_at = datetime.now()
            self.db.commit()
            return True
        return False

    def obtener_notificaciones_usuario(
        self,
        usuario_id: int,
        solo_no_leidas: bool = False,
        limit: int = 50
    ) -> List[Notificacion]:
        """
        Obtiene las notificaciones de un usuario
        """
        query = self.db.query(Notificacion).filter(
            Notificacion.usuario_id == usuario_id
        )

        if solo_no_leidas:
            query = query.filter(Notificacion.leida == False)

        return query.order_by(Notificacion.created_at.desc()).limit(limit).all()