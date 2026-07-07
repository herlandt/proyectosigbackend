import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.core.database import Base


class Telemetria(Base):
    __tablename__ = "telemetria"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recorrido_id = Column(UUID(as_uuid=True), ForeignKey("recorridos.id", ondelete="CASCADE"), nullable=False)
    ubicacion = Column(Geometry("POINT", srid=4326), nullable=False)
    fecha = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)
    timestamp_evento = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    velocidad = Column(Numeric(6, 2), nullable=False, default=0)
    distancia_recorrida = Column(Numeric(10, 3), nullable=False, default=0)
    tiempo_transcurrido = Column(Integer, nullable=False, default=0)
    precision_m = Column(Numeric(6, 1), nullable=True)
    # Map-matching: posición proyectada sobre el recorrido de la línea (NULL si
    # el micro estaba a más de SNAP_DESVIO_MAX_M de la ruta) y desvío medido.
    ubicacion_ruta = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    desvio_ruta_m = Column(Numeric(8, 1), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    recorrido = relationship("Recorrido", back_populates="telemetria")
