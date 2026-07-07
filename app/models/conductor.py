import enum
import uuid

from sqlalchemy import Boolean, Column, Date, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.core.database import Base


class SexoEnum(str, enum.Enum):
    M = "M"
    F = "F"


class CategoriaLicenciaEnum(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    P = "P"
    M = "M"


class Conductor(Base):
    __tablename__ = "conductores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    documento_identidad = Column(String(20), nullable=False, unique=True)
    nombre = Column(String(150), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    sexo = Column(Enum(SexoEnum, name="sexo_enum", create_type=False), nullable=False)
    telefono = Column(String(20), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    categoria_licencia = Column(
        Enum(CategoriaLicenciaEnum, name="categoria_licencia_enum", create_type=False),
        nullable=False,
    )
    foto_url = Column(Text, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
