# C6 · Parte 5 — Verificación final del Ciclo 6

## Objetivo
Verificar que los tres endpoints nuevos funcionan correctamente con datos reales.
Para probar el ETA se necesita un conductor activo transmitiendo desde C4.

---

## 1. Verificar que todos los módulos cargan

```bash
.\venv\Scripts\python -c "
from app.schemas.linea import LineaCercanaResponse, MicrobusActivoResponse, EtaResponse
from app.services.geo_service import obtener_lineas_cercanas, obtener_microbuses_activos
from app.services.eta_service import calcular_eta
from app.routers.lineas import router
print('C6 OK — todos los modulos cargan')
"
```

---

## 2. Levantar el servidor

```bash
.\venv\Scripts\uvicorn main:app --reload
```

En `http://localhost:8000/docs` verificar que aparecen los 5 endpoints de Líneas:
- `GET /lineas/cercanas`
- `GET /lineas`
- `GET /lineas/{linea_id}`
- `GET /lineas/{linea_id}/microbuses-activos`
- `GET /lineas/{linea_id}/eta`

---

## 3. Checklist de verificación

### 3.1 Líneas cercanas

```bash
# Plaza 24 de Septiembre, radio 1000 metros
curl "http://localhost:8000/lineas/cercanas?lon=-63.1822&lat=-17.7834&radio=1000"
```

**Resultado esperado**: array con las líneas que tienen recorridos cerca del centro.
Si están cargados los datos del C3, deben aparecer varias líneas ordenadas por
`distancia_minima_m` de menor a mayor.

```json
[
  {
    "linea_id": "...",
    "numero": "10",
    "nombre": "Línea 10 — Plan 3000",
    "distancia_minima_m": 45.2,
    "pasa_ida": true,
    "pasa_vuelta": true
  },
  ...
]
```

### 3.2 Radio sin líneas cercanas

```bash
# Punto fuera de Santa Cruz (desierto)
curl "http://localhost:8000/lineas/cercanas?lon=-62.0&lat=-16.5&radio=500"
```

**Resultado esperado**: array vacío `[]`.

### 3.3 Microbuses activos (sin conductor transmitiendo)

```bash
curl "http://localhost:8000/lineas/{UUID_LINEA_10}/microbuses-activos?sentido=ida"
```

**Resultado esperado**: array vacío `[]` (ningún conductor está transmitiendo aún).

### 3.4 ETA sin conductor activo

```bash
curl "http://localhost:8000/lineas/{UUID_LINEA_10}/eta?lon=-63.1822&lat=-17.7834&sentido=ida"
```

**Resultado esperado**: `404` con mensaje `"No hay microbuses activos..."`.

---

## 4. Prueba completa con conductor activo

Para probar microbuses activos y ETA se necesita simular un conductor.
Ejecutar la siguiente secuencia:

**Paso 1 — Login del conductor (C2):**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@ejemplo.com", "password": "mipassword123"}'
# Guardar el access_token
```

**Paso 2 — Iniciar recorrido (C4):**
```bash
curl -X POST http://localhost:8000/recorridos/iniciar \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"microbus_id": "<UUID>", "sentido": "ida",
       "longitud": -63.148, "latitud": -17.818}'
# Guardar el recorrido_id
```

**Paso 3 — Enviar telemetría (C4):**
```bash
curl -X POST http://localhost:8000/recorridos/<ID>/telemetria \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"longitud": -63.148, "latitud": -17.818,
       "fecha": "2026-05-05", "hora": "08:00:00",
       "velocidad": 30.0, "distancia_recorrida": 1.5,
       "tiempo_transcurrido": 90}'
```

**Paso 4 — Ahora consultar microbuses activos:**
```bash
curl "http://localhost:8000/lineas/<UUID_LINEA>/microbuses-activos?sentido=ida"
```

**Resultado esperado**: array con el microbús, su posición y velocidad.

**Paso 5 — ETA desde el centro de Santa Cruz:**
```bash
curl "http://localhost:8000/lineas/<UUID_LINEA>/eta?lon=-63.1822&lat=-17.7834&sentido=ida"
```

**Resultado esperado**:
```json
{
  "microbus_id": "...",
  "placa": "ABC123",
  "numero_interno": "M-001",
  "longitud": -63.148,
  "latitud": -17.818,
  "distancia_metros": 3820.5,
  "velocidad_kmh": 30.0,
  "eta_minutos": 7.6
}
```

---

## 5. Casos de error a verificar

| Escenario | Código esperado |
|---|---|
| `/lineas/cercanas` sin `lon` o `lat` | `422` |
| `/lineas/cercanas` con `radio` > 5000 | `422` |
| `/lineas/{id}/microbuses-activos` con sentido inválido | `422` |
| `/lineas/{id}/eta` sin microbuses activos | `404` |
| `/lineas/cercanas` (probar que no lo captura `/{linea_id}`) | `200` con lista |

---

## 6. Estado del proyecto al terminar el Ciclo 6

```
backend/
└── app/
    ├── schemas/
    │   └── linea.py          ✅ + LineaCercanaResponse, MicrobusActivoResponse, EtaResponse
    ├── services/
    │   ├── geo_service.py    ✅ + obtener_lineas_cercanas, obtener_microbuses_activos
    │   └── eta_service.py    ✅ calcular_eta  ← nuevo
    └── routers/
        └── lineas.py         ✅ 5 endpoints (reemplazado en C6)
```

---

## Siguiente ciclo
Ciclo 6 completado ✅ → **Ciclo 7 — WebSocket, "Esperando microbús" y cierre**

> El C7 es el último ciclo del backend. Implementa el WebSocket que conecta
> el envío de telemetría del conductor con la pantalla "Esperando microbús"
> del usuario en tiempo real.
