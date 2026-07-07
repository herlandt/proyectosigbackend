from sqlalchemy import BigInteger, Column, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.core.database import Base


class RedTransbordo(Base):
    """Conexión a pie entre dos paradas cercanas de líneas distintas (transbordo)."""

    __tablename__ = "red_transbordos"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    parada_origen = Column(UUID(as_uuid=True), ForeignKey("paradas.id", ondelete="CASCADE"), nullable=False)
    parada_destino = Column(UUID(as_uuid=True), ForeignKey("paradas.id", ondelete="CASCADE"), nullable=False)
    distancia_m = Column(Float, nullable=False)
    tiempo_seg = Column(Float, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
