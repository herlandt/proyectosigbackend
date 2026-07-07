import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator


class MicrobusCreate(BaseModel):
	placa: str
	modelo: str
	cantidad_asientos: int
	linea_id: uuid.UUID
	numero_interno: str
	fecha_asignacion: date

	@field_validator("placa", "modelo", "numero_interno")
	@classmethod
	def no_vacio(cls, v: str) -> str:
		if not v.strip():
			raise ValueError("El campo no puede estar vacío")
		return v.strip().upper()

	@field_validator("cantidad_asientos")
	@classmethod
	def asientos_positivos(cls, v: int) -> int:
		if v <= 0:
			raise ValueError("La cantidad de asientos debe ser mayor a 0")
		return v


class MicrobusFotoResponse(BaseModel):
	id: uuid.UUID
	foto_url: str
	orden: int

	model_config = {"from_attributes": True}


class MicrobusResponse(BaseModel):
	id: uuid.UUID
	placa: str
	modelo: str
	cantidad_asientos: int
	conductor_id: uuid.UUID
	linea_id: uuid.UUID
	numero_interno: str
	fecha_asignacion: date
	fecha_baja: Optional[date] = None
	fotos: list[MicrobusFotoResponse] = []

	model_config = {"from_attributes": True}
