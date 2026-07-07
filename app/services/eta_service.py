import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.linea import EtaResponse


def calcular_eta(
	db: Session,
	linea_id: uuid.UUID,
	sentido: str,
	longitud: float,
	latitud: float,
) -> Optional[EtaResponse]:
	filas = db.execute(
		text(
			"""
			SELECT microbus_id, placa, numero_interno,
			       longitud, latitud,
			       distancia_metros, velocidad_kmh, eta_minutos
			FROM fn_eta_microbus_cercano(
			    :linea_id,
			    CAST(:sentido AS sentido_enum),
			    :lon,
			    :lat
			)
			LIMIT 1
		"""
		),
		{
			"linea_id": str(linea_id),
			"sentido": sentido,
			"lon": longitud,
			"lat": latitud,
		},
	).mappings().all()

	if not filas:
		return None

	fila = filas[0]
	return EtaResponse(
		microbus_id=fila["microbus_id"],
		placa=fila["placa"],
		numero_interno=fila["numero_interno"],
		longitud=float(fila["longitud"]) if fila["longitud"] else 0.0,
		latitud=float(fila["latitud"]) if fila["latitud"] else 0.0,
		distancia_metros=float(fila["distancia_metros"]),
		velocidad_kmh=float(fila["velocidad_kmh"]),
		eta_minutos=float(fila["eta_minutos"]),
	)
