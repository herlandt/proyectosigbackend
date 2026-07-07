import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.core.database import Base


class Linea(Base):
    __tablename__ = "lineas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero = Column(String(20), nullable=False, unique=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text)
    recorrido_ida = Column(Geometry("LINESTRING", srid=4326), nullable=False)
    recorrido_vuelta = Column(Geometry("LINESTRING", srid=4326), nullable=False)
    punto_partida_ida = Column(Geometry("POINT", srid=4326))
    punto_llegada_ida = Column(Geometry("POINT", srid=4326))
    punto_partida_vuelta = Column(Geometry("POINT", srid=4326))
    punto_llegada_vuelta = Column(Geometry("POINT", srid=4326))
    activa = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
