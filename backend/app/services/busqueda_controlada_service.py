from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.tomo import Tomo, ContenidoOCR
from app.models.permiso_tomo import PermisoTomo
from app.models.usuario import Usuario

class ResultadoBusqueda:
    def __init__(self, tomo_id: int, pagina: int, texto: str, fecha: Optional[datetime] = None):
        self.tomo_id = tomo_id
        self.pagina = pagina
        self.texto = texto
        self.fecha = fecha
        self.contexto = ""  # Fragmento de texto alrededor de la coincidencia

class BusquedaControladaService:
    def __init__(self, db: Session):
        self.db = db

    def verificar_permiso(self, usuario_id: int, tomo_id: int) -> Dict[str, bool]:
        """Verifica si el usuario tiene los permisos necesarios para buscar en el tomo"""
        usuario = self.db.query(Usuario).join(Usuario.rol).filter(Usuario.id == usuario_id).first()
        if not usuario:
            return {"puede_buscar": False, "puede_descargar": False}

        permiso = self.db.query(PermisoTomo).filter(
            and_(
                PermisoTomo.usuario_id == usuario_id,
                PermisoTomo.tomo_id == tomo_id,
                PermisoTomo.puede_buscar == True,
                or_(
                    PermisoTomo.fecha_fin_acceso.is_(None),
                    PermisoTomo.fecha_fin_acceso >= datetime.now()
                )
            )
        ).first()

        return {
            "puede_buscar": permiso is not None,
            "puede_descargar": usuario.rol.nombre in ["admin", "Admin", "Administrador"] and permiso is not None
        }

    def buscar_en_tomo(
        self,
        usuario_id: int,
        tomo_id: int,
        texto_busqueda: str,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None,
        pagina_inicio: Optional[int] = None,
        pagina_fin: Optional[int] = None
    ) -> List[ResultadoBusqueda]:
        """
        Realiza una búsqueda controlada en un tomo específico
        """
        if not self.verificar_permiso(usuario_id, tomo_id):
            raise PermissionError("No tiene permisos para buscar en este tomo")

        query = self.db.query(ContenidoOCR).filter(ContenidoOCR.tomo_id == tomo_id)

        # Aplicar filtros de página si se especifican
        if pagina_inicio:
            query = query.filter(ContenidoOCR.numero_pagina >= pagina_inicio)
        if pagina_fin:
            query = query.filter(ContenidoOCR.numero_pagina <= pagina_fin)

        # Realizar la búsqueda
        resultados = []
        for contenido in query.all():
            if texto_busqueda.lower() in contenido.texto.lower():
                # Encontrar el contexto (100 caracteres antes y después)
                pos = contenido.texto.lower().find(texto_busqueda.lower())
                inicio = max(0, pos - 100)
                fin = min(len(contenido.texto), pos + len(texto_busqueda) + 100)
                
                resultado = ResultadoBusqueda(
                    tomo_id=tomo_id,
                    pagina=contenido.numero_pagina,
                    texto=texto_busqueda,
                    fecha=contenido.fecha_documento
                )
                resultado.contexto = f"...{contenido.texto[inicio:fin]}..."
                resultados.append(resultado)

        return resultados

    def buscar_en_tomos_permitidos(
        self,
        usuario_id: int,
        texto_busqueda: str,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[int, List[ResultadoBusqueda]]:
        """
        Realiza una búsqueda en todos los tomos a los que el usuario tiene acceso
        """
        # Obtener todos los tomos con permiso de búsqueda
        permisos = self.db.query(PermisoTomo).filter(
            and_(
                PermisoTomo.usuario_id == usuario_id,
                PermisoTomo.puede_buscar == True,
                or_(
                    PermisoTomo.fecha_fin_acceso.is_(None),
                    PermisoTomo.fecha_fin_acceso >= datetime.now()
                )
            )
        ).all()

        resultados = {}
        for permiso in permisos:
            try:
                resultados_tomo = self.buscar_en_tomo(
                    usuario_id,
                    permiso.tomo_id,
                    texto_busqueda,
                    fecha_inicio,
                    fecha_fin
                )
                if resultados_tomo:
                    resultados[permiso.tomo_id] = resultados_tomo
            except Exception as e:
                print(f"Error al buscar en tomo {permiso.tomo_id}: {str(e)}")
                continue

        return resultados