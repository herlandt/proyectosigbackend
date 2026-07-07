import uuid
from datetime import date, time
from typing import Optional

from pydantic import BaseModel, field_validator


class TelemetriaCreate(BaseModel):
	longitud: float
	latitud: float
	fecha: date
	hora: time
	velocidad: float
	distancia_recorrida: float
	tiempo_transcurrido: int
	precision_m: Optional[float] = None  # accuracy del fix GPS (metros)

	@field_validator("velocidad", "distancia_recorrida")
	@classmethod
	def no_negativo(cls, v: float) -> float:
		if v < 0:
			raise ValueError("El valor no puede ser negativo")
		return v

	@field_validator("tiempo_transcurrido")
	@classmethod
	def tiempo_no_negativo(cls, v: int) -> int:
		if v < 0:
			raise ValueError("El tiempo no puede ser negativo")
		return v


class TelemetriaResponse(BaseModel):
	id: uuid.UUID
	recorrido_id: uuid.UUID
	longitud: float
	latitud: float
	velocidad: float
	distancia_recorrida: float
	tiempo_transcurrido: int

	model_config = {"from_attributes": True}
