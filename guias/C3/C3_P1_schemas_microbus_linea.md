# C3 · Parte 1 — Schemas Pydantic: Microbús y Línea

## Objetivo
Definir los contratos de entrada/salida para microbuses y líneas.
Los schemas de línea son los más importantes: deben devolver el recorrido
en **GeoJSON** listo para que `flutter_map` lo dibuje directamente.

## Archivos a crear
```
app/schemas/microbus.py
app/schemas/linea.py
```

---

## 1. `app/schemas/microbus.py`

```python
# app/schemas/microbus.py
import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator


# ── Entrada: registro de microbús ──────────────────────────────────────────────
class MicrobusCreate(BaseModel):
    placa: str
    modelo: str
    cantidad_asientos: int
    linea_id: uuid.UUID
    numero_interno: str
    fecha_asignacion: date

    @field_validator("placa", "modelo", "numero_interno")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El campo no puede estar vacío")
        return v.strip().upper()

    @field_validator("cantidad_asientos")
    @classmethod
    def asientos_positivos(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("La cantidad de asientos debe ser mayor a 0")
        return v


# ── Salida: datos de la foto ───────────────────────────────────────────────────
class MicrobusFotoResponse(BaseModel):
    id: uuid.UUID
    foto_url: str
    orden: int

    model_config = {"from_attributes": True}


# ── Salida: microbús completo ──────────────────────────────────────────────────
class MicrobusResponse(BaseModel):
    id: uuid.UUID
    placa: str
    modelo: str
    cantidad_asientos: int
    conductor_id: uuid.UUID
    linea_id: uuid.UUID
    numero_interno: str
    fecha_asignacion: date
    fecha_baja: Optional[date] = None
    fotos: list[MicrobusFotoResponse] = []

    model_config = {"from_attributes": True}
```

---

## 2. `app/schemas/linea.py`

El campo más importante es `recorrido_ida` y `recorrido_vuelta`: se sirven como
string GeoJSON (ya serializado por PostGIS con `ST_AsGeoJSON`). Flutter los
parsea directamente con `jsonDecode`.

```python
# app/schemas/linea.py
import uuid
from typing import Any, Optional

from pydantic import BaseModel


# ── Salida: punto geográfico (para marcadores verde/rojo) ──────────────────────
class PuntoGeo(BaseModel):
    longitud: float
    latitud: float


# ── Salida: línea en lista (sin geometría, más liviano) ───────────────────────
class LineaResumen(BaseModel):
    id: uuid.UUID
    numero: str
    nombre: str
    descripcion: Optional[str] = None
    activa: bool

    model_config = {"from_attributes": True}


# ── Salida: línea completa con GeoJSON para el mapa ───────────────────────────
class LineaDetalle(BaseModel):
    id: uuid.UUID
    numero: str
    nombre: str
    descripcion: Optional[str] = None
    activa: bool

    # Recorridos como string GeoJSON (serializado desde PostGIS)
    recorrido_ida: Any        # dict con {"type": "LineString", "coordinates": [...]}
    recorrido_vuelta: Any

    # Puntos extremos para los marcadores verde (partida) y rojo (llegada)
    punto_partida_ida: Optional[PuntoGeo] = None
    punto_llegada_ida: Optional[PuntoGeo] = None
    punto_partida_vuelta: Optional[PuntoGeo] = None
    punto_llegada_vuelta: Optional[PuntoGeo] = None
```

> **Por qué `recorrido_ida: Any`**: GeoAlchemy2 devuelve las geometrías en
> formato WKB (binario). El `geo_service` las convierte a dict GeoJSON antes
> de construir este schema. Usar `Any` permite recibir el dict ya armado sin
> validación adicional.

---

## Verificación de esta parte

```bash
.\venv\Scripts\python -c "
from app.schemas.microbus import MicrobusCreate, MicrobusResponse
from app.schemas.linea import LineaResumen, LineaDetalle
print('schemas C3 OK')
"
```

---

## Siguiente paso
→ **C3_P2_geo_service.md** — Convertir geometrías PostGIS a GeoJSON
