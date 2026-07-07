# C4 · Parte 4 — Registrar router en main.py y verificación final del Ciclo 4

## Objetivo
Conectar el router de recorridos a la app FastAPI y ejecutar todas las
verificaciones del Ciclo 4: inicio de recorrido, envío de telemetría,
finalización normal y por fuerza mayor.

---

## 1. Actualizar `main.py`

```python
# main.py  (versión final del Ciclo 4)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, conductores, microbuses, lineas, recorridos

app = FastAPI(
    title="Sistema de Información Geográfica — Microbuses Santa Cruz",
    description="API REST para el sistema de microbuses de Santa Cruz de la Sierra, Bolivia.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conductores.router)
app.include_router(microbuses.router)
app.include_router(lineas.router)
app.include_router(recorridos.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "Microbuses SIG API"}
```

---

## 2. Levantar el servidor

```bash
.\venv\Scripts\uvicorn main:app --reload
```

En `http://localhost:8000/docs` debe aparecer la sección **Recorridos** con:
- `POST /recorridos/iniciar`
- `POST /recorridos/{recorrido_id}/telemetria`
- `POST /recorridos/{recorrido_id}/terminar`
- `POST /recorridos/{recorrido_id}/salir`

---

## 3. Checklist de verificación del Ciclo 4

### Prerequisitos
- Tener un conductor registrado y su JWT (Ciclo 2)
- Tener un microbús registrado en la línea 10 (Ciclo 3)

### 3.1 Iniciar recorrido

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

**Resultado**: `201` con `recorrido_id`. Guardar el `recorrido_id` para los siguientes pasos.

Verificar en pgAdmin:
```sql
SELECT id, sentido, fecha_inicio, fecha_fin, tipo_finalizacion
FROM recorridos
ORDER BY fecha_inicio DESC LIMIT 5;
```

### 3.2 Enviar telemetría (simular 3 puntos seguidos)

```bash
# Punto 1
curl -X POST http://localhost:8000/recorridos/<RECORRIDO_ID>/telemetria \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "longitud": -63.148, "latitud": -17.818,
    "fecha": "2026-05-05", "hora": "08:00:30",
    "velocidad": 35.5, "distancia_recorrida": 1.2, "tiempo_transcurrido": 30
  }'

# Punto 2 (30 segundos después)
curl -X POST http://localhost:8000/recorridos/<RECORRIDO_ID>/telemetria \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "longitud": -63.156, "latitud": -17.810,
    "fecha": "2026-05-05", "hora": "08:01:00",
    "velocidad": 38.2, "distancia_recorrida": 2.5, "tiempo_transcurrido": 60
  }'

# Punto 3
curl -X POST http://localhost:8000/recorridos/<RECORRIDO_ID>/telemetria \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "longitud": -63.164, "latitud": -17.802,
    "fecha": "2026-05-05", "hora": "08:01:30",
    "velocidad": 30.0, "distancia_recorrida": 3.8, "tiempo_transcurrido": 90
  }'
```

Verificar en BD que se insertaron 3 filas en `telemetria`:
```sql
SELECT ST_X(ubicacion) AS lon, ST_Y(ubicacion) AS lat, velocidad, distancia_recorrida
FROM telemetria
WHERE recorrido_id = '<RECORRIDO_ID>'
ORDER BY timestamp_evento;
```

### 3.3 Terminar recorrido (finalización normal)

```bash
curl -X POST http://localhost:8000/recorridos/<RECORRIDO_ID>/terminar \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"longitud": -63.182, "latitud": -17.783}'
```

**Resultado**: `200` con resumen del recorrido.
Verificar en BD que `fecha_fin` y `tipo_finalizacion = 'normal'` se guardaron.

---

### 3.4 Probar finalización por fuerza mayor (nuevo recorrido)

Iniciar un **segundo** recorrido y terminarlo con `/salir`:

```bash
# Iniciar nuevo recorrido
curl -X POST http://localhost:8000/recorridos/iniciar \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"microbus_id": "<UUID_MICROBUS>", "sentido": "vuelta",
       "longitud": -63.182, "latitud": -17.783}'

# Salir por fuerza mayor
curl -X POST http://localhost:8000/recorridos/<NUEVO_ID>/salir \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "longitud": -63.165, "latitud": -17.800,
    "motivo_salida": "Falla mecánica en el motor"
  }'
```

### 3.5 Casos de error a verificar

| Escenario | Código esperado |
|---|---|
| Iniciar recorrido con microbús de otro conductor | `404` |
| Iniciar cuando ya hay un recorrido activo | `409` |
| Enviar telemetría a recorrido ya finalizado | `409` |
| Enviar telemetría a recorrido de otro conductor | `403` |
| `/salir` con `motivo_salida` vacío o solo espacios | `422` |
| Terminar un recorrido ya terminado | `409` |

---

## 4. Estado del proyecto al terminar el Ciclo 4

```
backend/
└── app/
    ├── schemas/
    │   ├── conductor.py      ✅ C2
    │   ├── microbus.py       ✅ C3
    │   ├── linea.py          ✅ C3
    │   ├── recorrido.py      ✅ C4 ← nuevo
    │   └── telemetria.py     ✅ C4 ← nuevo
    └── routers/
        ├── auth.py           ✅ C2
        ├── conductores.py    ✅ C2
        ├── microbuses.py     ✅ C3
        ├── lineas.py         ✅ C3
        └── recorridos.py     ✅ C4 ← nuevo (4 endpoints)
```

---

## 5. Qué queda para los ciclos siguientes

| Ciclo | Qué se agrega sobre lo de C4 |
|---|---|
| C5 | `GET /lineas/{id}` devuelve GeoJSON → Flutter dibuja la ruta |
| C6 | `GET /lineas/cercanas` + `GET /lineas/{id}/eta` → líneas cercanas y ETA |
| C7 | Se descomenta el `# TODO C7` → WebSocket distribuye posiciones en tiempo real |

---

## Siguiente ciclo
Ciclo 4 completado ✅ → **Ciclo 5 — App Usuario: visualización de rutas en el mapa**

> El Ciclo 5 es puramente Flutter (no toca el backend).
> El Ciclo 6 sí agrega endpoints nuevos al backend.
