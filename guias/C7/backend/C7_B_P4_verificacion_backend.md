# C7 · Backend · Parte 4 — Verificación del backend completo

## Objetivo
Verificar que el WebSocket funciona end-to-end: el conductor envía telemetría
y el usuario recibe la posición en tiempo real sin polling.

---

## 1. Verificar que todos los módulos cargan

```bash
.\venv\Scripts\python -c "
from app.routers.websocket import router, ws_manager
from app.routers.recorridos import router as r_recorridos
import main
print('C7 backend OK')
"
```

---

## 2. Levantar el servidor

```bash
.\venv\Scripts\uvicorn main:app --reload
```

En `http://localhost:8000/docs` verificar que aparece en la sección WebSocket:
- `WS /ws/lineas/{linea_id}/posiciones`

---

## 3. Prueba del WebSocket con wscat

Instalar `wscat` (cliente WebSocket de línea de comandos):
```bash
npm install -g wscat
```

**Terminal 1 — conectar como usuario:**
```bash
wscat -c "ws://localhost:8000/ws/lineas/<UUID_LINEA_10>/posiciones"
```
Debe mostrar `Connected` y quedar esperando mensajes.

**Terminal 2 — enviar telemetría como conductor:**
```bash
# 1. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@ejemplo.com", "password": "mipassword123"}'

# 2. Iniciar recorrido
curl -X POST http://localhost:8000/recorridos/iniciar \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"microbus_id": "<UUID>", "sentido": "ida",
       "longitud": -63.148, "latitud": -17.818}'

# 3. Enviar telemetría
curl -X POST http://localhost:8000/recorridos/<ID>/telemetria \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"longitud": -63.156, "latitud": -17.810,
       "fecha": "2026-05-05", "hora": "08:00:30",
       "velocidad": 35.0, "distancia_recorrida": 1.5,
       "tiempo_transcurrido": 30}'
```

**Resultado esperado en Terminal 1**: aparece automáticamente el JSON:
```json
{
  "microbus_id": "...",
  "placa": "ABC123",
  "numero_interno": "M-001",
  "longitud": -63.156,
  "latitud": -17.810,
  "velocidad": 35.0,
  "sentido": "ida"
}
```

---

## 4. Prueba con múltiples clientes

Abrir 3 terminales con wscat conectadas a la misma línea. Enviar telemetría
una sola vez. Los 3 clientes deben recibir el mensaje simultáneamente.

---

## 5. Checklist final del backend completo

| Endpoint | Ciclo | Estado |
|---|---|---|
| `POST /auth/login` | C2 | ✅ |
| `POST /conductores/registro` | C2 | ✅ |
| `GET /conductores/me` | C2 | ✅ |
| `POST /microbuses/registro` | C3 | ✅ |
| `GET /microbuses/mis-microbuses` | C3 | ✅ |
| `GET /lineas` | C3 | ✅ |
| `GET /lineas/{id}` | C3 | ✅ |
| `POST /recorridos/iniciar` | C4 | ✅ |
| `POST /recorridos/{id}/telemetria` | C4+C7 | ✅ |
| `POST /recorridos/{id}/terminar` | C4 | ✅ |
| `POST /recorridos/{id}/salir` | C4 | ✅ |
| `GET /lineas/cercanas` | C6 | ✅ |
| `GET /lineas/{id}/microbuses-activos` | C6 | ✅ |
| `GET /lineas/{id}/eta` | C6 | ✅ |
| `WS /ws/lineas/{id}/posiciones` | C7 | ✅ |

---

## Estado final del proyecto backend

```
backend/
├── main.py                         ✅ 6 routers registrados
├── .env                            ✅
├── requirements.txt                ✅
└── app/
    ├── core/
    │   ├── config.py               ✅
    │   ├── database.py             ✅
    │   ├── security.py             ✅
    │   └── dependencies.py        ✅
    ├── models/
    │   ├── conductor.py            ✅
    │   ├── linea.py                ✅
    │   ├── microbus.py             ✅
    │   ├── recorrido.py            ✅
    │   └── telemetria.py           ✅
    ├── schemas/
    │   ├── conductor.py            ✅
    │   ├── microbus.py             ✅
    │   ├── linea.py                ✅ (5 schemas)
    │   ├── recorrido.py            ✅
    │   └── telemetria.py           ✅
    ├── routers/
    │   ├── auth.py                 ✅
    │   ├── conductores.py          ✅
    │   ├── microbuses.py           ✅
    │   ├── lineas.py               ✅ (5 endpoints)
    │   ├── recorridos.py           ✅ (4 endpoints + broadcast)
    │   └── websocket.py            ✅ ConnectionManager + WS endpoint
    └── services/
        ├── storage_service.py      ✅
        ├── geo_service.py          ✅
        └── eta_service.py          ✅
```

**Backend completado ✅** — 15 endpoints + 1 WebSocket
