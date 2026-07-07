import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.linea import (
	EtaResponse,
	LineaCercanaResponse,
	LineaDetalle,
	LineaResumen,
	MicrobusActivoResponse,
	ParadasCercanasResponse,
)
from app.services.eta_service import calcular_eta
from app.services.geo_service import (
	obtener_linea_detalle,
	obtener_lineas_activas,
	obtener_lineas_cercanas,
	obtener_microbuses_activos,
	obtener_paradas_cercanas,
)

router = APIRouter(prefix="/lineas", tags=["Lineas"])


@router.get("/cercanas", response_model=list[LineaCercanaResponse])
def lineas_cercanas(
	lon: float = Query(..., description="Longitud del punto"),
	lat: float = Query(..., description="Latitud del punto"),
	radio: int = Query(500, ge=50, le=5000, description="Radio de busqueda en metros"),
	db: Session = Depends(get_db),
):
	return obtener_lineas_cercanas(db, longitud=lon, latitud=lat, radio_metros=radio)


@router.get("/paradas-cercanas", response_model=ParadasCercanasResponse)
def paradas_cercanas(
	lon: float = Query(..., description="Longitud del punto"),
	lat: float = Query(..., description="Latitud del punto"),
	radio: int = Query(500, ge=50, le=3000, description="Radio en metros"),
	db: Session = Depends(get_db),
):
	"""Paradas cercanas a un punto, con las líneas que pasan por cada una y el
	tiempo estimado del próximo micro (por frecuencia)."""
	return obtener_paradas_cercanas(db, longitud=lon, latitud=lat, radio_metros=radio)


@router.get("", response_model=list[LineaResumen])
def listar_lineas(db: Session = Depends(get_db)):
	return obtener_lineas_activas(db)


@router.get("/{linea_id}", response_model=LineaDetalle)
def detalle_linea(linea_id: uuid.UUID, db: Session = Depends(get_db)):
	linea = obtener_linea_detalle(db, linea_id)
	if not linea:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Linea no encontrada",
		)
	return linea


@router.get("/{linea_id}/microbuses-activos", response_model=list[MicrobusActivoResponse])
def microbuses_activos(
	linea_id: uuid.UUID,
	sentido: str = Query(..., pattern="^(ida|vuelta)$"),
	db: Session = Depends(get_db),
):
	return obtener_microbuses_activos(db, linea_id=linea_id, sentido=sentido)


@router.get("/{linea_id}/eta", response_model=Optional[EtaResponse])
def eta_microbus(
	linea_id: uuid.UUID,
	lon: float = Query(..., description="Longitud del usuario"),
	lat: float = Query(..., description="Latitud del usuario"),
	sentido: str = Query(..., pattern="^(ida|vuelta)$"),
	db: Session = Depends(get_db),
):
	eta = calcular_eta(
		db,
		linea_id=linea_id,
		sentido=sentido,
		longitud=lon,
		latitud=lat,
	)
	if eta is None:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="No hay microbuses activos en esta linea en este momento",
		)
	return eta
