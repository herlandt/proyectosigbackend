# C6 · Parte 1 — Schemas: líneas cercanas, microbuses activos y ETA

## Objetivo
Definir los schemas Pydantic de los tres endpoints nuevos del Ciclo 6:
- `GET /lineas/cercanas` → líneas dentro de un radio con su distancia
- `GET /lineas/{id}/microbuses-activos` → snapshot de posiciones actuales
- `GET /lineas/{id}/eta` → tiempo estimado de llegada del microbús más cercano

## Archivos a modificar
```
app/schemas/linea.py    ← agregar 3 schemas nuevos
```

---

## 1. Agregar al final de `app/schemas/linea.py`

```python
# ── Salida: línea cercana a un punto (GET /lineas/cercanas) ───────────────────
class LineaCercanaResponse(BaseModel):
    linea_id: uuid.UUID
    numero: str
    nombre: str
    distancia_minima_m: float   # metros hasta el punto dado
    pasa_ida: bool
    pasa_vuelta: bool


# ── Salida: microbús activo con posición (GET /lineas/{id}/microbuses-activos) ─
class MicrobusActivoResponse(BaseModel):
    microbus_id: uuid.UUID
    placa: str
    numero_interno: str
    longitud: float
    latitud: float
    velocidad: float
    ultima_actualizacion: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Salida: ETA del microbús más cercano (GET /lineas/{id}/eta) ───────────────
class EtaResponse(BaseModel):
    microbus_id: uuid.UUID
    placa: str
    numero_interno: str
    longitud: float
    latitud: float
    distancia_metros: float
    velocidad_kmh: float
    eta_minutos: float          # tiempo estimado de llegada en minutos
```

También agregar el import que falta al inicio del archivo:

```python
from datetime import datetime   # agregar junto a los otros imports
```

---

## Verificación

```bash
.\venv\Scripts\python -c "
from app.schemas.linea import LineaCercanaResponse, MicrobusActivoResponse, EtaResponse
print('schemas C6 OK')
"
```

---

## Siguiente paso
→ **C6_P2_geo_service_cercanas.md** — Consulta geoespacial de líneas cercanas
