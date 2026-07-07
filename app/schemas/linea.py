import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class PuntoGeo(BaseModel):
	longitud: float
	latitud: float


class LineaResumen(BaseModel):
	id: uuid.UUID
	numero: str
	nombre: str
	descripcion: Optional[str] = None
	activa: bool

	model_config = {"from_attributes": True}


class LineaDetalle(BaseModel):
	id: uuid.UUID
	numero: str
	nombre: str
	descripcion: Optional[str] = None
	activa: bool

	recorrido_ida: Any
	recorrido_vuelta: Any

	punto_partida_ida: Optional[PuntoGeo] = None
	punto_llegada_ida: Optional[PuntoGeo] = None
	punto_partida_vuelta: Optional[PuntoGeo] = None
	punto_llegada_vuelta: Optional[PuntoGeo] = None


class LineaCercanaResponse(BaseModel):
	linea_id: uuid.UUID
	numero: str
	nombre: str
	distancia_minima_m: float
	pasa_ida: bool
	pasa_vuelta: bool


class MicrobusActivoResponse(BaseModel):
	microbus_id: uuid.UUID
	placa: str
	numero_interno: str
	longitud: float
	latitud: float
	velocidad: float
	ultima_actualizacion: Optional[datetime] = None

	model_config = {"from_attributes": True}


class EtaResponse(BaseModel):
	microbus_id: uuid.UUID
	placa: str
	numero_interno: str
	longitud: float
	latitud: float
	distancia_metros: float
	velocidad_kmh: float
	eta_minutos: float


# ── Paradas cercanas (qué líneas pasan por una parada y en cuánto llegan) ──
class LineaEnParada(BaseModel):
	numero: str
	sentido: str
	eta_min: int


class ParadaCercana(BaseModel):
	longitud: float
	latitud: float
	distancia_m: float
	lineas: list[LineaEnParada]


class ParadasCercanasResponse(BaseModel):
	en_servicio: bool
	frecuencia_min: float
	paradas: list[ParadaCercana]
