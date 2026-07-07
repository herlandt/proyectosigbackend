# C4 · Parte 3 — Router recorridos: telemetría, terminar y salir

## Objetivo
Completar `app/routers/recorridos.py` con los tres endpoints restantes:
- `POST /recorridos/{id}/telemetria` — recibe un punto GPS cada 30 segundos
- `POST /recorridos/{id}/terminar` — finalización normal
- `POST /recorridos/{id}/salir` — salida por fuerza mayor (motivo obligatorio)

---

## 1. Función auxiliar de seguridad

Antes de los endpoints, agregar una función privada que verifica que el
recorrido existe **y** pertenece al conductor del JWT. Se reutiliza en los
tres endpoints:

```python
# Agregar en app/routers/recorridos.py, antes de los endpoints

def _obtener_recorrido_activo(
    recorrido_id: uuid.UUID,
    conductor: Conductor,
    db: Session,
) -> Recorrido:
    """
    Devuelve el recorrido si existe, está activo y pertenece al conductor.
    Lanza 404 o 403 en caso contrario.
    """
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
```

---

## 2. `POST /recorridos/{id}/telemetria`

```python
@router.post("/{recorrido_id}/telemetria", response_model=TelemetriaResponse)
def enviar_telemetria(
    recorrido_id: uuid.UUID,
    datos: TelemetriaCreate,
    conductor: Conductor = Depends(get_current_conductor),
    db: Session = Depends(get_db),
):
    recorrido = _obtener_recorrido_activo(recorrido_id, conductor, db)

    # Convertir coordenadas a geometría PostGIS
    ubicacion = from_shape(Point(datos.longitud, datos.latitud), srid=4326)

    nuevo_punto = Telemetria(
        id=uuid.uuid4(),
        recorrido_id=recorrido.id,
        ubicacion=ubicacion,
        fecha=datos.fecha,
        hora=datos.hora,
        velocidad=datos.velocidad,
        distancia_recorrida=datos.distancia_recorrida,
        tiempo_transcurrido=datos.tiempo_transcurrido,
    )
    db.add(nuevo_punto)
    db.commit()
    db.refresh(nuevo_punto)

    # TODO C7: notificar al WebSocket manager para redistribuir posición
    # ws_manager.broadcast_posicion(recorrido.linea_id, nuevo_punto)

    return TelemetriaResponse(
        id=nuevo_punto.id,
        recorrido_id=nuevo_punto.recorrido_id,
        longitud=datos.longitud,
        latitud=datos.latitud,
        velocidad=datos.velocidad,
        distancia_recorrida=float(nuevo_punto.distancia_recorrida),
        tiempo_transcurrido=nuevo_punto.tiempo_transcurrido,
    )
```

---

## 3. `POST /recorridos/{id}/terminar`

```python
@router.post("/{recorrido_id}/terminar", response_model=RecorridoResumenResponse)
def terminar_recorrido(
    recorrido_id: uuid.UUID,
    datos: RecorridoTerminar,
    conductor: Conductor = Depends(get_current_conductor),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
    recorrido = _obtener_recorrido_activo(recorrido_id, conductor, db)

    ubicacion_fin = from_shape(Point(datos.longitud, datos.latitud), srid=4326)
    ahora = datetime.now(timezone.utc)

    recorrido.fecha_fin = ahora
    recorrido.tipo_finalizacion = "normal"
    recorrido.ubicacion_fin = ubicacion_fin
    recorrido.tiempo_total_seg = int((ahora - recorrido.fecha_inicio).total_seconds())

    # Tomar la distancia acumulada del último punto de telemetría
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
```

---

## 4. `POST /recorridos/{id}/salir`

```python
@router.post("/{recorrido_id}/salir", response_model=RecorridoResumenResponse)
def salir_recorrido(
    recorrido_id: uuid.UUID,
    datos: RecorridoSalir,
    conductor: Conductor = Depends(get_current_conductor),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
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
```

---

## 5. Imports completos al inicio de `recorridos.py`

Al principio del archivo agregar todos los imports que se necesitan:

```python
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
```

---

## 6. Por qué el `# TODO C7`

En el endpoint de telemetría hay un comentario marcado `# TODO C7`.
En el Ciclo 7 se implementa el WebSocket que distribuye posiciones en tiempo
real. Cuando ese manager exista, se descomenta esa línea y la app del usuario
recibirá las posiciones sin polling. Por ahora el dato queda guardado en la BD
y listo para cuando se consulte.

---

## Siguiente paso
→ **C4_P4_main_y_verificacion.md** — Registrar router y verificación final del Ciclo 4
