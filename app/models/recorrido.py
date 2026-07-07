import enum
import uuid

from geoalchemy2 import Geometry
from sqlalchemy import Column, Enum, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.core.database import Base


class SentidoEnum(str, enum.Enum):
    ida = "ida"
    vuelta = "vuelta"


class TipoFinalizacionEnum(str, enum.Enum):
    normal = "normal"
    fuerza_mayor = "fuerza_mayor"


class Recorrido(Base):
    __tablename__ = "recorridos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    microbus_id = Column(UUID(as_uuid=True), ForeignKey("microbuses.id", ondelete="RESTRICT"), nullable=False)
    conductor_id = Column(UUID(as_uuid=True), ForeignKey("conductores.id", ondelete="RESTRICT"), nullable=False)
    linea_id = Column(UUID(as_uuid=True), ForeignKey("lineas.id", ondelete="RESTRICT"), nullable=False)
    sentido = Column(Enum(SentidoEnum, name="sentido_enum", create_type=False), nullable=False)
    fecha_inicio = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    fecha_fin = Column(TIMESTAMP(timezone=True))
    tipo_finalizacion = Column(Enum(TipoFinalizacionEnum, name="tipo_finalizacion_enum", create_type=False))
    motivo_salida = Column(Text)
    ubicacion_inicio = Column(Geometry("POINT", srid=4326), nullable=False)
    ubicacion_fin = Column(Geometry("POINT", srid=4326))
    distancia_total_km = Column(Numeric(10, 3))
    tiempo_total_seg = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    microbus = relationship("Microbus", backref="recorridos")
    conductor = relationship("Conductor", backref="recorridos")
    linea = relationship("Linea", backref="recorridos")
    telemetria = relationship("Telemetria", back_populates="recorrido", cascade="all, delete-orphan")
