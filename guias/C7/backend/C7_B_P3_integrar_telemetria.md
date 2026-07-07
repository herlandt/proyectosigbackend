# C7 · Backend · Parte 3 — Integrar telemetría con el WebSocket

## Objetivo
Descomentar y completar el `# TODO C7` que quedó en el endpoint de telemetría
(C4). Cada vez que un conductor envía su posición GPS, el backend la guarda
en la BD y simultáneamente la redistribuye a todos los usuarios conectados
al WebSocket de esa línea.

## Archivos a modificar
```
app/routers/recorridos.py    ← descomentar TODO C7 y hacer el broadcast
```

---

## 1. Cambio en `POST /recorridos/{id}/telemetria`

Localizar el bloque con el comentario `# TODO C7` y reemplazarlo:

```python
# ANTES (C4):
# TODO C7: notificar al WebSocket manager para redistribuir posición
# ws_manager.broadcast_posicion(recorrido.linea_id, nuevo_punto)

# DESPUÉS (C7):
import asyncio
from app.routers.websocket import ws_manager

# Solo hace broadcast si hay clientes conectados (evita trabajo innecesario)
if ws_manager.clientes_activos(str(recorrido.linea_id)) > 0:
    mensaje = {
        "microbus_id":    str(nuevo_punto.recorrido_id),   # usar microbus_id
        "placa":          microbus.placa,
        "numero_interno": microbus.numero_interno,
        "longitud":       datos.longitud,
        "latitud":        datos.latitud,
        "velocidad":      float(datos.velocidad),
        "sentido":        str(recorrido.sentido.value),
    }
    asyncio.create_task(ws_manager.broadcast(str(recorrido.linea_id), mensaje))
```

---

## 2. Obtener datos del microbús en el endpoint de telemetría

Para armar el mensaje necesitamos `placa` y `numero_interno` del microbús.
El endpoint de telemetría ya tiene el `recorrido`, y el recorrido tiene
`microbus_id`. Agregar la consulta del microbús:

```python
# Agregar DESPUÉS de guardar el punto de telemetría y ANTES del broadcast:
from app.models.microbus import Microbus

microbus = db.query(Microbus).filter(
    Microbus.id == recorrido.microbus_id
).first()
```

---

## 3. Versión completa del endpoint de telemetría con C7

```python
@router.post("/{recorrido_id}/telemetria", response_model=TelemetriaResponse)
async def enviar_telemetria(          # ← cambiar a async def
    recorrido_id: uuid.UUID,
    datos: TelemetriaCreate,
    conductor: Conductor = Depends(get_current_conductor),
    db: Session = Depends(get_db),
):
    import asyncio
    from app.models.microbus import Microbus
    from app.routers.websocket import ws_manager

    recorrido = _obtener_recorrido_activo(recorrido_id, conductor, db)

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

    # Broadcast a usuarios conectados al WebSocket de esta línea
    if ws_manager.clientes_activos(str(recorrido.linea_id)) > 0:
        microbus = db.query(Microbus).filter(
            Microbus.id == recorrido.microbus_id
        ).first()
        if microbus:
            mensaje = {
                "microbus_id":    str(recorrido.microbus_id),
                "placa":          microbus.placa,
                "numero_interno": microbus.numero_interno,
                "longitud":       datos.longitud,
                "latitud":        datos.latitud,
                "velocidad":      float(datos.velocidad),
                "sentido":        recorrido.sentido.value,
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
```

> **Por qué `async def` y `asyncio.create_task`**: el broadcast WebSocket
> es una operación `async`. Usar `create_task` lo ejecuta en background sin
> bloquear la respuesta HTTP al conductor. El conductor recibe `200 OK`
> inmediatamente mientras el broadcast se envía a los usuarios.

---

## 4. Verificación en la BD

Confirmar que el endpoint de telemetría sigue guardando datos correctamente:

```sql
SELECT COUNT(*) FROM telemetria WHERE recorrido_id = '<ID>';
```

---

## Siguiente paso
→ **C7_B_P4_verificacion_backend.md** — Verificación del backend completo del C7
