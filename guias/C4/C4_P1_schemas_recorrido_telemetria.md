# C4 · Parte 1 — Schemas Pydantic: Recorrido y Telemetría

## Objetivo
Definir los contratos de entrada/salida para iniciar recorridos, enviar
puntos GPS de telemetría, y finalizar recorridos (normal o por fuerza mayor).

## Archivos a crear
```
app/schemas/recorrido.py
app/schemas/telemetria.py
```

---

## 1. `app/schemas/recorrido.py`

```python
# app/schemas/recorrido.py
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class SentidoEnum(str, Enum):
    ida = "ida"
    vuelta = "vuelta"


class TipoFinalizacionEnum(str, Enum):
    normal = "normal"
    fuerza_mayor = "fuerza_mayor"


# ── Entrada: iniciar recorrido ────────────────────────────────────────────────
class RecorridoIniciar(BaseModel):
    microbus_id: uuid.UUID
    sentido: SentidoEnum
    longitud: float
    latitud: float


# ── Entrada: terminar recorrido (normal) ──────────────────────────────────────
class RecorridoTerminar(BaseModel):
    longitud: float
    latitud: float


# ── Entrada: salir del recorrido (fuerza mayor) ───────────────────────────────
class RecorridoSalir(BaseModel):
    longitud: float
    latitud: float
    motivo_salida: str

    @field_validator("motivo_salida")
    @classmethod
    def motivo_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El motivo de salida es obligatorio")
        return v.strip()


# ── Salida: respuesta al iniciar ──────────────────────────────────────────────
class RecorridoIniciadoResponse(BaseModel):
    recorrido_id: uuid.UUID
    microbus_id: uuid.UUID
    linea_id: uuid.UUID
    sentido: SentidoEnum
    fecha_inicio: datetime

    model_config = {"from_attributes": True}


# ── Salida: resumen al terminar ───────────────────────────────────────────────
class RecorridoResumenResponse(BaseModel):
    recorrido_id: uuid.UUID
    sentido: SentidoEnum
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    tipo_finalizacion: Optional[TipoFinalizacionEnum] = None
    distancia_total_km: Optional[float] = None
    tiempo_total_seg: Optional[int] = None
    motivo_salida: Optional[str] = None

    model_config = {"from_attributes": True}
```

---

## 2. `app/schemas/telemetria.py`

```python
# app/schemas/telemetria.py
import uuid
from datetime import date, time

from pydantic import BaseModel, field_validator


# ── Entrada: punto GPS enviado cada 30 segundos ───────────────────────────────
class TelemetriaCreate(BaseModel):
    longitud: float
    latitud: float
    fecha: date
    hora: time
    velocidad: float
    distancia_recorrida: float      # km acumulados desde inicio
    tiempo_transcurrido: int        # segundos desde inicio

    @field_validator("velocidad", "distancia_recorrida")
    @classmethod
    def no_negativo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("El valor no puede ser negativo")
        return v

    @field_validator("tiempo_transcurrido")
    @classmethod
    def tiempo_no_negativo(cls, v: int) -> int:
        if v < 0:
            raise ValueError("El tiempo no puede ser negativo")
        return v


# ── Salida: confirmación de recepción ─────────────────────────────────────────
class TelemetriaResponse(BaseModel):
    id: uuid.UUID
    recorrido_id: uuid.UUID
    longitud: float
    latitud: float
    velocidad: float
    distancia_recorrida: float
    tiempo_transcurrido: int

    model_config = {"from_attributes": True}
```

---

## Verificación de esta parte

```bash
.\venv\Scripts\python -c "
from app.schemas.recorrido import RecorridoIniciar, RecorridoSalir, RecorridoResumenResponse
from app.schemas.telemetria import TelemetriaCreate, TelemetriaResponse
print('schemas C4 OK')
"
```

### Validación clave — `motivo_salida` no puede estar vacío

```bash
.\venv\Scripts\python -c "
from app.schemas.recorrido import RecorridoSalir
try:
    RecorridoSalir(longitud=-63.18, latitud=-17.78, motivo_salida='   ')
    print('ERROR: deberia fallar')
except Exception as e:
    print('Validacion OK:', e)
"
```

---

## Siguiente paso
→ **C4_P2_router_iniciar.md** — Endpoint `POST /recorridos/iniciar`
