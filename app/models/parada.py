import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.core.database import Base


class Parada(Base):
    """Parada de microbús (nodo del grafo de ruta óptima)."""

    __tablename__ = "paradas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_externo = Column(Integer)        # IdPunto del DatosLineas.xls
    codigo = Column(String(50))         # ej. "S-2"
    nombre = Column(String(150))
    ubicacion = Column(Geometry("POINT", srid=4326), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
