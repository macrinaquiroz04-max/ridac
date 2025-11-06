# backend/app/controllers/__init__.py

from .test_controller import test_controller, TestController
from .auth_controller import auth_controller, AuthController
from .usuario_controller import usuario_controller, UsuarioController
from .carpeta_controller import carpeta_controller, CarpetaController
from .tomo_controller import tomo_controller, TomoController
from .permiso_controller import permiso_controller, PermisoController
from .busqueda_controller import busqueda_controller, BusquedaController

__all__ = [
    # Instancias
    "test_controller",
    "auth_controller",
    "usuario_controller",
    "carpeta_controller",
    "tomo_controller",
    "permiso_controller",
    "busqueda_controller",
    # Clases
    "TestController",
    "AuthController",
    "UsuarioController",
    "CarpetaController",
    "TomoController",
    "PermisoController",
    "BusquedaController",
]
