import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_conductor
from app.models.conductor import Conductor
from app.models.microbus import Microbus
from app.models.recorrido import Recorrido
from app.models.telemetria import Telemetria
from app.schemas.recorrido import (
	RecorridoIniciar,
	RecorridoIniciadoResponse,
	RecorridoResumenResponse,
	RecorridoSalir,
	RecorridoTerminar,
)
from app.schemas.telemetria import TelemetriaCreate, TelemetriaResponse

router = APIRouter(prefix="/recorridos", tags=["Recorridos"])


def _obtener_recorrido_activo(
	recorrido_id: uuid.UUID,
	conductor: Conductor,
	db: Session,
) -> Recorrido:
	recorrido = db.query(Recorrido).filter(Recorrido.id == recorrido_id).first()

	if not recorrido:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Recorrido no encontrado",
		)
	if recorrido.conductor_id != conductor.id:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="No tienes permiso para operar este recorrido",
		)
	if recorrido.fecha_fin is not None:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="El recorrido ya fue finalizado",
		)
	return recorrido


@router.post(
	"/iniciar",
	response_model=RecorridoIniciadoResponse,
	status_code=status.HTTP_201_CREATED,
)
def iniciar_recorrido(
	datos: RecorridoIniciar,
	conductor: Conductor = Depends(get_current_conductor),
	db: Session = Depends(get_db),
):
	microbus = db.query(Microbus).filter(
		Microbus.id == datos.microbus_id,
		Microbus.conductor_id == conductor.id,
		Microbus.fecha_baja == None,
	).first()
	if not microbus:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Microbús no encontrado o no pertenece a este conductor",
		)

	recorrido_activo = db.query(Recorrido).filter(
		Recorrido.microbus_id == datos.microbus_id,
		Recorrido.fecha_fin == None,
	).first()
	if recorrido_activo:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="El microbús ya tiene un recorrido activo. Termínalo antes de iniciar uno nuevo.",
		)

	punto_inicio = from_shape(Point(datos.longitud, datos.latitud), srid=4326)

	nuevo_recorrido = Recorrido(
		id=uuid.uuid4(),
		microbus_id=datos.microbus_id,
		conductor_id=conductor.id,
		linea_id=microbus.linea_id,
		sentido=datos.sentido,
		ubicacion_inicio=punto_inicio,
	)
	db.add(nuevo_recorrido)
	db.commit()
	db.refresh(nuevo_recorrido)

	return RecorridoIniciadoResponse(
		recorrido_id=nuevo_recorrido.id,
		microbus_id=nuevo_recorrido.microbus_id,
		linea_id=nuevo_recorrido.linea_id,
		sentido=nuevo_recorrido.sentido,
		fecha_inicio=nuevo_recorrido.fecha_inicio,
	)


@router.post("/{recorrido_id}/telemetria", response_model=TelemetriaResponse)
async def enviar_telemetria(
	recorrido_id: uuid.UUID,
	datos: TelemetriaCreate,
	conductor: Conductor = Depends(get_current_conductor),
	db: Session = Depends(get_db),
):
	import asyncio
	from app.routers.websocket import ws_manager
	from app.services.geo_service import SNAP_DESVIO_MAX_M, ajustar_punto_a_linea
	recorrido = _obtener_recorrido_activo(recorrido_id, conductor, db)

	ubicacion = from_shape(Point(datos.longitud, datos.latitud), srid=4326)

	# Map-matching: se guarda la posición cruda como fuente de verdad, y además
	# la proyección sobre el recorrido (si el micro está razonablemente en ruta).
	# La vista vw_microbuses_activos y el WebSocket usan la proyectada.
	lon_pub, lat_pub = datos.longitud, datos.latitud
	ubicacion_ruta = None
	desvio_m = None
	snap = ajustar_punto_a_linea(
		db, recorrido.linea_id, recorrido.sentido.value, datos.longitud, datos.latitud,
	)
	if snap:
		snap_lon, snap_lat, desvio_m = snap
		if desvio_m <= SNAP_DESVIO_MAX_M:
			ubicacion_ruta = from_shape(Point(snap_lon, snap_lat), srid=4326)
			lon_pub, lat_pub = snap_lon, snap_lat

	nuevo_punto = Telemetria(
		id=uuid.uuid4(),
		recorrido_id=recorrido.id,
		ubicacion=ubicacion,
		fecha=datos.fecha,
		hora=datos.hora,
		velocidad=datos.velocidad,
		distancia_recorrida=datos.distancia_recorrida,
		tiempo_transcurrido=datos.tiempo_transcurrido,
		precision_m=datos.precision_m,
		ubicacion_ruta=ubicacion_ruta,
		desvio_ruta_m=round(desvio_m, 1) if desvio_m is not None else None,
	)
	db.add(nuevo_punto)
	db.commit()
	db.refresh(nuevo_punto)

	if ws_manager.clientes_activos(str(recorrido.linea_id)) > 0:
		microbus = db.query(Microbus).filter(
			Microbus.id == recorrido.microbus_id,
		).first()
		if microbus:
			mensaje = {
				"microbus_id": str(recorrido.microbus_id),
				"placa": microbus.placa,
				"numero_interno": microbus.numero_interno,
				"longitud": lon_pub,
				"latitud": lat_pub,
				"velocidad": float(datos.velocidad),
				"sentido": recorrido.sentido.value,
			}
			asyncio.create_task(
				ws_manager.broadcast(str(recorrido.linea_id), mensaje)
			)

	return TelemetriaResponse(
		id=nuevo_punto.id,
		recorrido_id=nuevo_punto.recorrido_id,
		longitud=datos.longitud,
		latitud=datos.latitud,
		velocidad=datos.velocidad,
		distancia_recorrida=float(nuevo_punto.distancia_recorrida),
		tiempo_transcurrido=nuevo_punto.tiempo_transcurrido,
	)


@router.post("/{recorrido_id}/terminar", response_model=RecorridoResumenResponse)
def terminar_recorrido(
	recorrido_id: uuid.UUID,
	datos: RecorridoTerminar,
	conductor: Conductor = Depends(get_current_conductor),
	db: Session = Depends(get_db),
):
	recorrido = _obtener_recorrido_activo(recorrido_id, conductor, db)

	ubicacion_fin = from_shape(Point(datos.longitud, datos.latitud), srid=4326)
	ahora = datetime.now(timezone.utc)

	recorrido.fecha_fin = ahora
	recorrido.tipo_finalizacion = "normal"
	recorrido.ubicacion_fin = ubicacion_fin
	recorrido.tiempo_total_seg = int((ahora - recorrido.fecha_inicio).total_seconds())

	ultimo_punto = (
		db.query(Telemetria)
		.filter(Telemetria.recorrido_id == recorrido.id)
		.order_by(Telemetria.timestamp_evento.desc())
		.first()
	)
	if ultimo_punto:
		recorrido.distancia_total_km = float(ultimo_punto.distancia_recorrida)

	db.commit()
	db.refresh(recorrido)

	return RecorridoResumenResponse(
		recorrido_id=recorrido.id,
		sentido=recorrido.sentido,
		fecha_inicio=recorrido.fecha_inicio,
		fecha_fin=recorrido.fecha_fin,
		tipo_finalizacion=recorrido.tipo_finalizacion,
		distancia_total_km=float(recorrido.distancia_total_km) if recorrido.distancia_total_km else None,
		tiempo_total_seg=recorrido.tiempo_total_seg,
	)


@router.post("/{recorrido_id}/salir", response_model=RecorridoResumenResponse)
def salir_recorrido(
	recorrido_id: uuid.UUID,
	datos: RecorridoSalir,
	conductor: Conductor = Depends(get_current_conductor),
	db: Session = Depends(get_db),
):
	recorrido = _obtener_recorrido_activo(recorrido_id, conductor, db)

	ubicacion_fin = from_shape(Point(datos.longitud, datos.latitud), srid=4326)
	ahora = datetime.now(timezone.utc)

	recorrido.fecha_fin = ahora
	recorrido.tipo_finalizacion = "fuerza_mayor"
	recorrido.motivo_salida = datos.motivo_salida
	recorrido.ubicacion_fin = ubicacion_fin
	recorrido.tiempo_total_seg = int((ahora - recorrido.fecha_inicio).total_seconds())

	ultimo_punto = (
		db.query(Telemetria)
		.filter(Telemetria.recorrido_id == recorrido.id)
		.order_by(Telemetria.timestamp_evento.desc())
		.first()
	)
	if ultimo_punto:
		recorrido.distancia_total_km = float(ultimo_punto.distancia_recorrida)

	db.commit()
	db.refresh(recorrido)

	return RecorridoResumenResponse(
		recorrido_id=recorrido.id,
		sentido=recorrido.sentido,
		fecha_inicio=recorrido.fecha_inicio,
		fecha_fin=recorrido.fecha_fin,
		tipo_finalizacion=recorrido.tipo_finalizacion,
		distancia_total_km=float(recorrido.distancia_total_km) if recorrido.distancia_total_km else None,
		tiempo_total_seg=recorrido.tiempo_total_seg,
		motivo_salida=recorrido.motivo_salida,
	)
