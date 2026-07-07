import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class SentidoEnum(str, Enum):
	ida = "ida"
	vuelta = "vuelta"


class TipoFinalizacionEnum(str, Enum):
	normal = "normal"
	fuerza_mayor = "fuerza_mayor"


class RecorridoIniciar(BaseModel):
	microbus_id: uuid.UUID
	sentido: SentidoEnum
	longitud: float
	latitud: float


class RecorridoTerminar(BaseModel):
	longitud: float
	latitud: float


class RecorridoSalir(BaseModel):
	longitud: float
	latitud: float
	motivo_salida: str

	@field_validator("motivo_salida")
	@classmethod
	def motivo_no_vacio(cls, v: str) -> str:
		if not v.strip():
			raise ValueError("El motivo de salida es obligatorio")
		return v.strip()


class RecorridoIniciadoResponse(BaseModel):
	recorrido_id: uuid.UUID
	microbus_id: uuid.UUID
	linea_id: uuid.UUID
	sentido: SentidoEnum
	fecha_inicio: datetime

	model_config = {"from_attributes": True}


class RecorridoResumenResponse(BaseModel):
	recorrido_id: uuid.UUID
	sentido: SentidoEnum
	fecha_inicio: datetime
	fecha_fin: Optional[datetime] = None
	tipo_finalizacion: Optional[TipoFinalizacionEnum] = None
	distancia_total_km: Optional[float] = None
	tiempo_total_seg: Optional[int] = None
	motivo_salida: Optional[str] = None

	model_config = {"from_attributes": True}
