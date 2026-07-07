import uuid

from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.core.database import Base


class Microbus(Base):
    __tablename__ = "microbuses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placa = Column(String(20), nullable=False, unique=True)
    modelo = Column(String(100), nullable=False)
    cantidad_asientos = Column(Integer, nullable=False)
    conductor_id = Column(UUID(as_uuid=True), ForeignKey("conductores.id", ondelete="RESTRICT"), nullable=False)
    linea_id = Column(UUID(as_uuid=True), ForeignKey("lineas.id", ondelete="RESTRICT"), nullable=False)
    numero_interno = Column(String(20), nullable=False)
    fecha_asignacion = Column(Date, nullable=False, server_default=func.current_date())
    fecha_baja = Column(Date)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    conductor = relationship("Conductor", backref="microbuses")
    linea = relationship("Linea", backref="microbuses")
    fotos = relationship("Microbusfoto", back_populates="microbus", cascade="all, delete-orphan")


class Microbusfoto(Base):
    __tablename__ = "microbuses_fotos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    microbus_id = Column(UUID(as_uuid=True), ForeignKey("microbuses.id", ondelete="CASCADE"), nullable=False)
    foto_url = Column(Text, nullable=False)
    orden = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    microbus = relationship("Microbus", back_populates="fotos")
