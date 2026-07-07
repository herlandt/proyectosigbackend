# C3 · Parte 5 — Registrar routers en main.py y verificación final del Ciclo 3

## Objetivo
Conectar los routers de `microbuses` y `lineas` a la app FastAPI,
levantar el servidor y ejecutar todas las verificaciones del Ciclo 3.

---

## 1. Actualizar `main.py`

Agregar los imports y `include_router` de los dos nuevos routers:

```python
# main.py  (versión final del Ciclo 3)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, conductores, microbuses, lineas

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


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "Microbuses SIG API"}
```

---

## 2. Levantar el servidor

```bash
.\venv\Scripts\uvicorn main:app --reload
```

En `http://localhost:8000/docs` deben aparecer las secciones:
- **Autenticación** → `POST /auth/login`
- **Conductores** → `POST /registro`, `GET /me`
- **Microbuses** → `POST /registro`, `GET /mis-microbuses`
- **Líneas** → `GET /lineas`, `GET /lineas/{linea_id}`

---

## 3. Checklist de verificación del Ciclo 3

### 3.1 Insertar datos de prueba
Ejecutar el script de la Parte 4 (`datos_prueba_lineas.sql`) en pgAdmin.

### 3.2 Listar líneas

```bash
curl http://localhost:8000/lineas
```

**Resultado esperado**: array con las 5 líneas (sin geometría):
```json
[
  {"id": "...", "numero": "10", "nombre": "Línea 10 — Plan 3000", "activa": true},
  {"id": "...", "numero": "17", ...},
  ...
]
```

### 3.3 Detalle de línea con GeoJSON

```bash
# Reemplazar {id} con el UUID real de la línea 10
curl http://localhost:8000/lineas/{id}
```

**Resultado esperado**: JSON con `recorrido_ida` y `recorrido_vuelta` en formato GeoJSON:
```json
{
  "id": "...",
  "numero": "10",
  "recorrido_ida": {
    "type": "LineString",
    "coordinates": [[-63.14, -17.825], [-63.148, -17.818], ...]
  },
  "recorrido_vuelta": {...},
  "punto_partida_ida": {"longitud": -63.14, "latitud": -17.825},
  "punto_llegada_ida": {"longitud": -63.182, "latitud": -17.7834}
}
```

### 3.4 Registrar microbús (requiere JWT del Ciclo 2)

```bash
# 1. Login para obtener token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@ejemplo.com", "password": "mipassword123"}'

# 2. Registrar microbús (multipart/form-data)
curl -X POST http://localhost:8000/microbuses/registro \
  -H "Authorization: Bearer <TOKEN>" \
  -F "placa=ABC123" \
  -F "modelo=Toyota Coaster" \
  -F "cantidad_asientos=25" \
  -F "linea_id=<UUID_LINEA_10>" \
  -F "numero_interno=M-001" \
  -F "fecha_asignacion=2026-01-15" \
  -F "fotos=@/ruta/foto1.jpg" \
  -F "fotos=@/ruta/foto2.jpg"
```

**Resultado esperado**: `201 Created` con los datos del microbús y sus fotos.

### 3.5 Listar mis microbuses

```bash
curl http://localhost:8000/microbuses/mis-microbuses \
  -H "Authorization: Bearer <TOKEN>"
```

**Resultado esperado**: array con el microbús recién registrado.

---

## 4. Casos de error a verificar

| Escenario | Código esperado |
|---|---|
| `GET /lineas/{id}` con UUID inexistente | `404` |
| `POST /microbuses/registro` sin JWT | `401` |
| Registrar microbús con placa duplicada | `409` |
| Registrar microbús con `linea_id` inválido | `404` |
| Subir archivo que no es imagen | `422` |

---

## 5. Estado del proyecto al terminar el Ciclo 3

```
backend/
└── app/
    ├── models/
    │   ├── conductor.py      ✅ C2
    │   ├── linea.py          ✅ C1 (sin cambios en C3)
    │   ├── microbus.py       ✅ C1 (sin cambios en C3)
    │   ├── recorrido.py      ✅ C1
    │   └── telemetria.py     ✅ C1
    ├── schemas/
    │   ├── conductor.py      ✅ C2
    │   ├── microbus.py       ✅ C3 ← nuevo
    │   └── linea.py          ✅ C3 ← nuevo
    ├── routers/
    │   ├── auth.py           ✅ C2
    │   ├── conductores.py    ✅ C2
    │   ├── microbuses.py     ✅ C3 ← nuevo
    │   └── lineas.py         ✅ C3 ← nuevo
    └── services/
        ├── storage_service.py ✅ C2
        └── geo_service.py    ✅ C3 ← nuevo
```

---

## Siguiente ciclo
Ciclo 3 completado ✅ → **Ciclo 4 — Telemetría: el conductor transmite su posición GPS**
