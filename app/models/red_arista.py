from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Column, Enum, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.core.database import Base
from app.models.recorrido import SentidoEnum


class RedArista(Base):
    """Tramo dirigido entre dos paradas consecutivas de una línea/sentido.
    Peso del grafo = tiempo_seg (Dijkstra)."""

    __tablename__ = "red_aristas"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    linea_id = Column(UUID(as_uuid=True), ForeignKey("lineas.id", ondelete="CASCADE"), nullable=False)
    sentido = Column(Enum(SentidoEnum, name="sentido_enum", create_type=False), nullable=False)
    parada_origen = Column(UUID(as_uuid=True), ForeignKey("paradas.id", ondelete="CASCADE"), nullable=False)
    parada_destino = Column(UUID(as_uuid=True), ForeignKey("paradas.id", ondelete="CASCADE"), nullable=False)
    orden = Column(Integer, nullable=False)
    distancia_m = Column(Float, nullable=False)
    tiempo_seg = Column(Float, nullable=False)
    geom = Column(Geometry("LINESTRING", srid=4326))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
