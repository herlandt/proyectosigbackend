"""Registro central de modelos ORM.

Importar este paquete (o cualquiera de sus nombres) garantiza que TODAS las clases
queden registradas en `Base.metadata` — necesario para Alembic (autogenerate) y para
evitar errores de relaciones por strings sin resolver.
"""

from app.core.database import Base  # noqa: F401

from app.models.conductor import (  # noqa: F401
    CategoriaLicenciaEnum,
    Conductor,
    SexoEnum,
)
from app.models.linea import Linea  # noqa: F401
from app.models.microbus import Microbus, Microbusfoto  # noqa: F401
from app.models.recorrido import (  # noqa: F401
    Recorrido,
    SentidoEnum,
    TipoFinalizacionEnum,
)
from app.models.parada import Parada  # noqa: F401
from app.models.red_arista import RedArista  # noqa: F401
from app.models.red_transbordo import RedTransbordo  # noqa: F401
from app.models.telemetria import Telemetria  # noqa: F401

__all__ = [
    "Base",
    "Conductor",
    "SexoEnum",
    "CategoriaLicenciaEnum",
    "Linea",
    "Microbus",
    "Microbusfoto",
    "Parada",
    "RedArista",
    "RedTransbordo",
    "Recorrido",
    "SentidoEnum",
    "TipoFinalizacionEnum",
    "Telemetria",
]
