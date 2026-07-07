import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.linea import Linea
from app.schemas.linea import (
	LineaCercanaResponse,
	LineaDetalle,
	LineaEnParada,
	LineaResumen,
	MicrobusActivoResponse,
	ParadaCercana,
	ParadasCercanasResponse,
	PuntoGeo,
)


def geojson_a_dict(wkb_element) -> Optional[Any]:
	if wkb_element is None:
		return None
	from shapely import wkb as shapely_wkb
	from shapely.geometry import mapping

	shape = shapely_wkb.loads(bytes(wkb_element.data), hex=False)
	return mapping(shape)


def punto_a_coordenadas(wkb_element) -> Optional[PuntoGeo]:
	if wkb_element is None:
		return None
	from shapely import wkb as shapely_wkb

	shape = shapely_wkb.loads(bytes(wkb_element.data), hex=False)
	return PuntoGeo(longitud=shape.x, latitud=shape.y)


# Map-matching: hasta cuántos metros de desvío tiene sentido "pegar" el punto
# GPS al recorrido; más lejos se asume que el micro está fuera de ruta (desvío
# real) y se deja la posición cruda.
SNAP_DESVIO_MAX_M = 100.0


def ajustar_punto_a_linea(
	db: Session,
	linea_id,
	sentido: str,
	longitud: float,
	latitud: float,
) -> Optional[tuple[float, float, float]]:
	"""Proyecta un punto GPS sobre el recorrido de la línea (map-matching).
	Devuelve (lon, lat, desvio_m) del punto proyectado, o None si la línea
	no tiene geometría para ese sentido."""
	fila = db.execute(
		text(
			"""
			SELECT ST_X(s.p) AS lon, ST_Y(s.p) AS lat,
			       ST_Distance(s.pt::geography, s.p::geography) AS desvio
			FROM (
			    SELECT ST_ClosestPoint(
			               CASE WHEN :sentido = 'ida' THEN l.recorrido_ida
			                    ELSE l.recorrido_vuelta END,
			               ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) AS p,
			           ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS pt
			    FROM lineas l
			    WHERE l.id = :linea_id
			) s
			"""
		),
		{"sentido": sentido, "lon": longitud, "lat": latitud, "linea_id": str(linea_id)},
	).mappings().first()

	if not fila or fila["lon"] is None:
		return None
	return float(fila["lon"]), float(fila["lat"]), float(fila["desvio"])


def obtener_lineas_activas(db: Session) -> list[LineaResumen]:
	lineas = db.query(Linea).filter(Linea.activa == True).order_by(Linea.numero).all()
	return [LineaResumen.model_validate(l) for l in lineas]


def obtener_linea_detalle(db: Session, linea_id) -> Optional[LineaDetalle]:
	linea = db.query(Linea).filter(Linea.id == linea_id, Linea.activa == True).first()
	if not linea:
		return None

	return LineaDetalle(
		id=linea.id,
		numero=linea.numero,
		nombre=linea.nombre,
		descripcion=linea.descripcion,
		activa=linea.activa,
		recorrido_ida=geojson_a_dict(linea.recorrido_ida),
		recorrido_vuelta=geojson_a_dict(linea.recorrido_vuelta),
		punto_partida_ida=punto_a_coordenadas(linea.punto_partida_ida),
		punto_llegada_ida=punto_a_coordenadas(linea.punto_llegada_ida),
		punto_partida_vuelta=punto_a_coordenadas(linea.punto_partida_vuelta),
		punto_llegada_vuelta=punto_a_coordenadas(linea.punto_llegada_vuelta),
	)


def obtener_lineas_cercanas(
	db: Session,
	longitud: float,
	latitud: float,
	radio_metros: int = 500,
) -> list[LineaCercanaResponse]:
	filas = db.execute(
		text("SELECT * FROM fn_lineas_cercanas(:lon, :lat, :radio)"),
		{"lon": longitud, "lat": latitud, "radio": radio_metros},
	).mappings().all()

	return [
		LineaCercanaResponse(
			linea_id=fila["linea_id"],
			numero=fila["numero"],
			nombre=fila["nombre"],
			distancia_minima_m=float(fila["distancia_minima_m"]),
			pasa_ida=fila["pasa_ida"],
			pasa_vuelta=fila["pasa_vuelta"],
		)
		for fila in filas
	]


def obtener_microbuses_activos(
	db: Session,
	linea_id: uuid.UUID,
	sentido: str,
) -> list[MicrobusActivoResponse]:
	filas = db.execute(
		text(
			"""
			SELECT microbus_id, placa, numero_interno,
			       longitud, latitud, velocidad, ultima_actualizacion
			FROM fn_microbuses_linea_activos(:linea_id, CAST(:sentido AS sentido_enum))
		"""
		),
		{"linea_id": str(linea_id), "sentido": sentido},
	).mappings().all()

	return [
		MicrobusActivoResponse(
			microbus_id=fila["microbus_id"],
			placa=fila["placa"],
			numero_interno=fila["numero_interno"],
			longitud=float(fila["longitud"]) if fila["longitud"] is not None else 0.0,
			latitud=float(fila["latitud"]) if fila["latitud"] is not None else 0.0,
			velocidad=float(fila["velocidad"]) if fila["velocidad"] is not None else 0.0,
			ultima_actualizacion=fila["ultima_actualizacion"],
		)
		for fila in filas
	]


def _horario_servicio():
    ahora = datetime.now()

    def _m(s):
        h, mm = s.split(":")
        return int(h) * 60 + int(mm)

    minutos = ahora.hour * 60 + ahora.minute
    en_serv = _m(settings.SERVICIO_INICIO) <= minutos <= _m(settings.SERVICIO_FIN)
    return en_serv, minutos


def _eta_frecuencia(numero: str, sentido: str, minutos: int) -> int:
    """ETA estimada del próximo micro por frecuencia (varía por línea/hora, en [1, F])."""
    try:
        n = int(numero)
    except ValueError:
        n = 0
    F = max(1, int(settings.FRECUENCIA_MIN))
    fase = (n * 3 + (7 if sentido == "vuelta" else 0)) % F
    e = (fase - minutos) % F
    return e if e >= 1 else F


def obtener_paradas_cercanas(db, longitud, latitud, radio_metros=500):
    """Paradas (OSM) agrupadas cerca de un punto. Por cada parada: qué líneas pasan
    y en cuántos minutos llega el próximo micro de cada una (modelo de frecuencia)."""
    filas = db.execute(text("""
        WITH cercanas AS (
            SELECT id, ubicacion,
                substring(split_part(codigo, '-', 1) FROM 2) AS linea,
                substr(split_part(codigo, '-', 2), 1, 1) AS sent
            FROM paradas
            WHERE id_externo >= 100000 AND codigo LIKE 'L%-%'
              AND ST_DWithin(ubicacion::geography,
                             ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radio)
        ),
        agrup AS (
            -- Agrupa en metros reales (UTM 20S), no en grados: 45 m de radio.
            SELECT *, ST_ClusterDBSCAN(ST_Transform(ubicacion, 32720), 45, 1) OVER () AS cid
            FROM cercanas
        )
        SELECT
            ST_X(ST_Centroid(ST_Collect(ubicacion))) AS lon,
            ST_Y(ST_Centroid(ST_Collect(ubicacion))) AS lat,
            ST_Distance(ST_Centroid(ST_Collect(ubicacion))::geography,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS dist,
            array_agg(DISTINCT linea || ':' || sent) AS ls
        FROM agrup
        GROUP BY cid
        ORDER BY dist ASC
        LIMIT 40
    """), {"lon": longitud, "lat": latitud, "radio": radio_metros}).mappings().all()

    en_serv, minutos = _horario_servicio()
    paradas = []
    for f in filas:
        lineas = []
        for tok in (f["ls"] or []):
            num, sent = tok.split(":")
            sentido = "ida" if sent == "i" else "vuelta"
            lineas.append(LineaEnParada(
                numero=num, sentido=sentido,
                eta_min=_eta_frecuencia(num, sentido, minutos),
            ))
        lineas.sort(key=lambda x: x.eta_min)
        paradas.append(ParadaCercana(
            longitud=float(f["lon"]), latitud=float(f["lat"]),
            distancia_m=round(float(f["dist"]), 1), lineas=lineas,
        ))
    return ParadasCercanasResponse(
        en_servicio=en_serv, frecuencia_min=settings.FRECUENCIA_MIN, paradas=paradas,
    )
