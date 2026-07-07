# C4 · Parte 2 — Router recorridos: `POST /recorridos/iniciar`

## Objetivo
Implementar el endpoint que el conductor usa para arrancar un recorrido.
Valida que el microbús le pertenezca, que no tenga ya un recorrido activo,
registra la ubicación inicial y devuelve el `recorrido_id` que la app
guardará para enviar telemetría.

## Archivos a crear
```
app/routers/recorridos.py    ← solo la función iniciar por ahora
```

---

## 1. `app/routers/recorridos.py` (iniciar)

```python
# app/routers/recorridos.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_conductor
from app.models.conductor import Conductor
from app.models.microbus import Microbus
from app.models.recorrido import Recorrido
from app.schemas.recorrido import RecorridoIniciar, RecorridoIniciadoResponse

router = APIRouter(prefix="/recorridos", tags=["Recorridos"])


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
    # 1. Verificar que el microbús pertenece al conductor autenticado
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

    # 2. Verificar que el microbús no tiene ya un recorrido activo
    recorrido_activo = db.query(Recorrido).filter(
        Recorrido.microbus_id == datos.microbus_id,
        Recorrido.fecha_fin == None,
    ).first()
    if recorrido_activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El microbús ya tiene un recorrido activo. Termínalo antes de iniciar uno nuevo.",
        )

    # 3. Convertir coordenadas a geometría PostGIS
    punto_inicio = from_shape(Point(datos.longitud, datos.latitud), srid=4326)

    # 4. Crear el recorrido
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
```

---

## 2. Cómo funciona `from_shape`

GeoAlchemy2 provee `from_shape` para convertir objetos Shapely a WKBElement
que PostgreSQL/PostGIS entiende:

```python
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

# Coordenadas: (longitud, latitud) — siempre en ese orden para WGS84
punto = from_shape(Point(-63.182, -17.783), srid=4326)
```

> **Orden de coordenadas**: siempre `(longitud, latitud)` = `(x, y)`.
> Es un error común invertirlos. Longitud es el eje X (Este-Oeste),
> latitud es el eje Y (Norte-Sur).

---

## 3. Flujo completo de inicio de recorrido

```
Flutter Conductor           API                     BD
  │                          │                       │
  │  POST /recorridos/iniciar│                       │
  │  { microbus_id, sentido, │                       │
  │    longitud, latitud }   │                       │
  │ ──────────────────────► │                       │
  │                          │  ¿microbus mío?       │
  │                          │ ─────────────────────►│
  │                          │  ¿recorrido activo?   │
  │                          │ ─────────────────────►│
  │                          │                       │
  │                          │  INSERT INTO recorridos│
  │                          │ ─────────────────────►│
  │                          │                       │
  │  201 { recorrido_id, ... }│                      │
  │ ◄──────────────────────  │                       │
  │                          │                       │
  │  [guarda recorrido_id]   │                       │
  │  [arranca Timer 30s]     │                       │
```

La app Flutter guarda el `recorrido_id` y arranca el servicio de telemetría
en background que lo usará en cada envío.

---

## Verificación de esta parte

```bash
.\venv\Scripts\python -c "
from app.routers.recorridos import router
print('router recorridos (iniciar) OK')
"
```

Prueba del endpoint (requiere JWT y microbús registrado del C3):
```bash
curl -X POST http://localhost:8000/recorridos/iniciar \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "microbus_id": "<UUID_MICROBUS>",
    "sentido": "ida",
    "longitud": -63.140,
    "latitud": -17.825
  }'
```

**Resultado esperado**: `201 Created` con `recorrido_id`.

---

## Siguiente paso
→ **C4_P3_router_telemetria_terminar_salir.md** — Los otros 3 endpoints del recorrido
