# C7 · Backend · Parte 1 — ConnectionManager (WebSocket)

## Objetivo
Crear el `ConnectionManager`: la clase que mantiene la lista de clientes
WebSocket conectados, agrupados por `linea_id`. Cuando llega telemetría
nueva, el manager redistribuye la posición a todos los usuarios que están
viendo esa línea en ese momento.

## Archivos a crear
```
app/routers/websocket.py    ← manager + endpoint WS
```

---

## 1. `app/routers/websocket.py`

```python
# app/routers/websocket.py
import json
import uuid
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Mantiene las conexiones WebSocket activas agrupadas por linea_id.
    Thread-safe para uso con un solo worker (Uvicorn single-process).
    Para multi-worker se necesitaría Redis pub/sub.
    """

    def __init__(self):
        # { linea_id (str) : [WebSocket, WebSocket, ...] }
        self._conexiones: Dict[str, List[WebSocket]] = {}

    async def conectar(self, linea_id: str, websocket: WebSocket):
        await websocket.accept()
        if linea_id not in self._conexiones:
            self._conexiones[linea_id] = []
        self._conexiones[linea_id].append(websocket)

    def desconectar(self, linea_id: str, websocket: WebSocket):
        if linea_id in self._conexiones:
            self._conexiones[linea_id].discard(websocket) \
                if hasattr(self._conexiones[linea_id], 'discard') \
                else self._conexiones[linea_id].remove(websocket) \
                if websocket in self._conexiones[linea_id] else None
            if not self._conexiones[linea_id]:
                del self._conexiones[linea_id]

    async def broadcast(self, linea_id: str, mensaje: dict):
        """Envía un mensaje JSON a todos los clientes de una línea."""
        conexiones = self._conexiones.get(linea_id, [])
        desconectados = []

        for ws in conexiones:
            try:
                await ws.send_json(mensaje)
            except Exception:
                desconectados.append(ws)

        # Limpiar conexiones caídas
        for ws in desconectados:
            self.desconectar(linea_id, ws)

    def clientes_activos(self, linea_id: str) -> int:
        return len(self._conexiones.get(linea_id, []))


# Instancia global — se comparte en toda la app
ws_manager = ConnectionManager()
```

---

## 2. Por qué es una instancia global

El `ws_manager` debe ser **un solo objeto** compartido entre:
- El router `/ws/lineas/{id}/posiciones` (que agrega conexiones)
- El router `/recorridos/{id}/telemetria` (que llama a `broadcast`)

Si se crearan dos instancias, el endpoint de telemetría no vería las
conexiones registradas por el WebSocket endpoint.

---

## 3. Limitación con múltiples workers

Esta implementación funciona con **un solo proceso Uvicorn** (`--workers 1`).
Con múltiples workers, cada proceso tiene su propio `ws_manager` en memoria
y los mensajes no se propagan entre workers.

Para producción con varios workers se usaría **Redis pub/sub** o
**PostgreSQL LISTEN/NOTIFY**. Para el alcance de este proyecto, un solo
worker es suficiente.

---

## Siguiente paso
→ **C7_B_P2_endpoint_websocket.md** — Endpoint `WS /ws/lineas/{id}/posiciones`
