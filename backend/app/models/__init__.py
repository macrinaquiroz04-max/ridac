# Models Package
from app.models.usuario import Usuario, Rol, TokenReset
from app.models.carpeta import Carpeta
from app.models.tomo import Tomo, ContenidoOCR
from app.models.tarea_ocr import TareaOCR
from app.models.permiso import PermisoCarpeta, PermisoSistema
from app.models.auditoria import Auditoria
from app.models.extraccion import (
    ExtraccionTomo, DiligenciaTomo, PersonaMencionada,
    Declaracion, AlertaInactividad
)
from app.models.permiso_tomo import PermisoTomo
from app.models.documento_ocr import DocumentoOCR
from app.models.notificacion import Notificacion
from app.models.analisis_ia import AnalisisIA, ResultadoAnalisis
from app.models.analisis_juridico import (
    Diligencia, PersonaIdentificada, DeclaracionPersona,
    LugarIdentificado, FechaImportante, AlertaMP, EstadisticaCarpeta
)
from app.models.relationships import *

__all__ = [
    "Usuario",
    "Rol",
    "TokenReset",
    "Carpeta",
    "Tomo",
    "ContenidoOCR",
    "TareaOCR",
    "PermisoCarpeta",
    "PermisoSistema",
    "Auditoria",
    "ExtraccionTomo",
    "DiligenciaTomo",
    "PersonaMencionada",
    "Declaracion",
    "AlertaInactividad",
    "PermisoTomo",
    "DocumentoOCR",
    "Notificacion",
    "AnalisisIA",
    "ResultadoAnalisis",
    "Diligencia",
    "PersonaIdentificada",
    "DeclaracionPersona",
    "LugarIdentificado",
    "FechaImportante",
    "AlertaMP",
    "EstadisticaCarpeta"
]
