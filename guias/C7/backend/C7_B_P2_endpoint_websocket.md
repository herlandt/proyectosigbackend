# C7 · Backend · Parte 2 — Endpoint WebSocket

## Objetivo
Agregar el endpoint `WS /ws/lineas/{linea_id}/posiciones` al router WebSocket.
El cliente Flutter se conecta aquí y recibe actualizaciones de posición
cada vez que un conductor envía telemetría.

## Archivos a modificar
```
app/routers/websocket.py    ← agregar el endpoint al final
```

---

## 1. Agregar el endpoint al final de `websocket.py`

```python
# Agregar al final de app/routers/websocket.py

@router.websocket("/ws/lineas/{linea_id}/posiciones")
async def websocket_posiciones(
    linea_id: str,
    websocket: WebSocket,
):
    """
    Canal WebSocket para recibir posiciones en tiempo real de los microbuses
    de una línea. El cliente se conecta y espera mensajes JSON con este formato:

    {
        "microbus_id":    "uuid",
        "placa":          "ABC123",
        "numero_interno": "M-001",
        "longitud":       -63.148,
        "latitud":        -17.818,
        "velocidad":      35.5,
        "sentido":        "ida"
    }

    La conexión se mantiene abierta hasta que el cliente la cierra.
    """
    await ws_manager.conectar(linea_id, websocket)
    try:
        # Mantener la conexión viva escuchando mensajes del cliente
        # (el cliente no envía datos, pero keep-alive es necesario)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.desconectar(linea_id, websocket)
```

---

## 2. Mensaje que se envía por el WebSocket

Cuando un conductor envía telemetría, el endpoint de recorridos llamará
a `ws_manager.broadcast`. El mensaje tiene este formato:

```json
{
  "microbus_id":    "550e8400-e29b-41d4-a716-446655440000",
  "placa":          "ABC123",
  "numero_interno": "M-001",
  "longitud":       -63.148,
  "latitud":        -17.818,
  "velocidad":      35.5,
  "sentido":        "ida"
}
```

Flutter recibe este JSON, actualiza la posición del marcador en el mapa
y recalcula el ETA.

---

## 3. Registrar el router en `main.py`

Agregar al `main.py`:

```python
from app.routers import auth, conductores, microbuses, lineas, recorridos, websocket

# Al final de los include_router:
app.include_router(websocket.router)
```

> A diferencia de los otros routers, el WebSocket no lleva prefix porque
> la URL completa es `ws://host/ws/lineas/{id}/posiciones`.

---

## Siguiente paso
→ **C7_B_P3_integrar_telemetria.md** — Conectar telemetría con el WebSocket
