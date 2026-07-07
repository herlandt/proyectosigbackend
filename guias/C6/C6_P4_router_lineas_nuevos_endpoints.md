# C6 · Parte 4 — Actualizar router de líneas con los nuevos endpoints

## Objetivo
Agregar tres endpoints nuevos a `app/routers/lineas.py`:
- `GET /lineas/cercanas` — líneas dentro de un radio
- `GET /lineas/{id}/microbuses-activos` — snapshot de posiciones
- `GET /lineas/{id}/eta` — ETA del microbús más cercano

## Archivos a modificar
```
app/routers/lineas.py    ← agregar 3 endpoints nuevos
```

---

## ⚠️ Advertencia de orden de rutas en FastAPI

`GET /lineas/cercanas` debe declararse **ANTES** de `GET /lineas/{linea_id}`.
Si se declara después, FastAPI intenta parsear la string `"cercanas"` como
UUID y devuelve `422 Unprocessable Entity`.

```
# CORRECTO — orden en el archivo:
GET /lineas/cercanas          ← primero (ruta específica)
GET /lineas/{linea_id}        ← después (ruta con parámetro)
```

---

## 1. `app/routers/lineas.py` — versión completa del Ciclo 6

Reemplazar el contenido actual del archivo con esta versión:

```python
# app/routers/lineas.py
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.linea import (
    EtaResponse,
    LineaCercanaResponse,
    LineaDetalle,
    LineaResumen,
    MicrobusActivoResponse,
)
from app.services.eta_service import calcular_eta
from app.services.geo_service import (
    obtener_linea_detalle,
    obtener_lineas_activas,
    obtener_lineas_cercanas,
    obtener_microbuses_activos,
)

router = APIRouter(prefix="/lineas", tags=["Líneas"])


# ── 1. GET /lineas/cercanas  (debe ir ANTES de /{linea_id}) ───────────────────
@router.get("/cercanas", response_model=list[LineaCercanaResponse])
def lineas_cercanas(
    lon: float = Query(..., description="Longitud del punto"),
    lat: float = Query(..., description="Latitud del punto"),
    radio: int = Query(500, ge=50, le=5000, description="Radio de búsqueda en metros"),
    db: Session = Depends(get_db),
):
    """Devuelve las líneas activas que pasan dentro del radio alrededor del punto."""
    return obtener_lineas_cercanas(db, longitud=lon, latitud=lat, radio_metros=radio)


# ── 2. GET /lineas  ───────────────────────────────────────────────────────────
@router.get("", response_model=list[LineaResumen])
def listar_lineas(db: Session = Depends(get_db)):
    """Lista todas las líneas activas (sin geometría)."""
    return obtener_lineas_activas(db)


# ── 3. GET /lineas/{linea_id}  ────────────────────────────────────────────────
@router.get("/{linea_id}", response_model=LineaDetalle)
def detalle_linea(linea_id: uuid.UUID, db: Session = Depends(get_db)):
    """Devuelve una línea con sus recorridos GeoJSON y puntos de partida/llegada."""
    linea = obtener_linea_detalle(db, linea_id)
    if not linea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Línea no encontrada")
    return linea


# ── 4. GET /lineas/{linea_id}/microbuses-activos  ─────────────────────────────
@router.get("/{linea_id}/microbuses-activos", response_model=list[MicrobusActivoResponse])
def microbuses_activos(
    linea_id: uuid.UUID,
    sentido: str = Query(..., pattern="^(ida|vuelta)$"),
    db: Session = Depends(get_db),
):
    """
    Snapshot inicial de posiciones de microbuses activos en una línea.
    Usado por la app del usuario antes de conectar el WebSocket (C7).
    """
    return obtener_microbuses_activos(db, linea_id=linea_id, sentido=sentido)


# ── 5. GET /lineas/{linea_id}/eta  ────────────────────────────────────────────
@router.get("/{linea_id}/eta", response_model=Optional[EtaResponse])
def eta_microbus(
    linea_id: uuid.UUID,
    lon: float = Query(..., description="Longitud del usuario"),
    lat: float = Query(..., description="Latitud del usuario"),
    sentido: str = Query(..., pattern="^(ida|vuelta)$"),
    db: Session = Depends(get_db),
):
    """
    ETA del microbús más cercano al punto del usuario.
    Devuelve null si no hay microbuses activos en esa línea/sentido.
    """
    eta = calcular_eta(
        db,
        linea_id=linea_id,
        sentido=sentido,
        longitud=lon,
        latitud=lat,
    )
    if eta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay microbuses activos en esta línea en este momento",
        )
    return eta
```

---

## 2. `main.py` no necesita cambios

El router de líneas ya está registrado desde el C3. Los nuevos endpoints
se agregan automáticamente al registrar el mismo `router`.

---

## Siguiente paso
→ **C6_P5_verificacion.md** — Verificación completa del Ciclo 6
