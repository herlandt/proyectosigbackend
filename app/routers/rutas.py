from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ruta import RutaOptimaResponse
from app.services import routing_service

router = APIRouter(prefix="/rutas", tags=["Rutas"])


@router.get("/optima", response_model=List[RutaOptimaResponse])
def ruta_optima(
    origen_lon: float = Query(..., description="Longitud del punto A"),
    origen_lat: float = Query(..., description="Latitud del punto A"),
    destino_lon: float = Query(..., description="Longitud del punto B"),
    destino_lat: float = Query(..., description="Latitud del punto B"),
    db: Session = Depends(get_db),
):
    """Varias alternativas de ruta entre dos puntos (estilo Moovit).

    Corre Dijkstra sobre la red real de microbuses con caminatas de acceso/egreso
    y transbordos. Devuelve una LISTA de rutas ordenada con la de MENOS transbordos
    primero. Cada tramo viene marcado como 'linea' o 'caminata'.
    """
    rutas = routing_service.calcular_rutas_optimas(
        db, origen_lon, origen_lat, destino_lon, destino_lat
    )
    if not rutas:
        raise HTTPException(
            status_code=404,
            detail="No se encontró una ruta entre los puntos dados (¿grafo cargado?)",
        )
    return rutas
