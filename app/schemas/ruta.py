from typing import List, Optional

from pydantic import BaseModel


class ParadaEnRuta(BaseModel):
    id_punto: Optional[int] = None
    descripcion: Optional[str] = None
    longitud: float
    latitud: float


class TramoRuta(BaseModel):
    """Un segmento del viaje. tipo='linea' (viaje en micro) o 'caminata' (a pie)."""
    tipo: str = "linea"
    linea_numero: str
    sentido: str
    tiempo_seg: float
    distancia_m: float
    espera_min: float = 0.0   # espera estimada del próximo micro antes de subir (tipo='linea')
    paradas: List[ParadaEnRuta]


class RutaOptimaResponse(BaseModel):
    tiempo_total_seg: float
    tiempo_total_min: float
    distancia_total_m: float
    transbordos: int
    caminata_origen_m: float   # del punto A a la primera parada
    caminata_destino_m: float  # de la última parada al punto B
    espera_total_min: float = 0.0   # suma de esperas (próximo micro en cada subida)
    frecuencia_min: float = 15.0    # frecuencia asumida de los micros
    en_servicio: bool = True        # si la hora actual está en horario de servicio
    tramos: List[TramoRuta]
