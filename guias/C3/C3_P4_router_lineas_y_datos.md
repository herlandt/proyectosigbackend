# C3 · Parte 4 — Router de líneas y datos de prueba

## Objetivo
Implementar `app/routers/lineas.py` con los endpoints de listado y detalle,
e insertar 5 líneas reales de Santa Cruz de la Sierra con recorridos
georeferenciados para poder probar la app.

## Archivos a crear
```
app/routers/lineas.py
guias/C3/datos_prueba_lineas.sql   ← script SQL con las 5 líneas
```

---

## 1. `app/routers/lineas.py`

```python
# app/routers/lineas.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.linea import LineaDetalle, LineaResumen
from app.services.geo_service import obtener_linea_detalle, obtener_lineas_activas

router = APIRouter(prefix="/lineas", tags=["Líneas"])


@router.get("", response_model=list[LineaResumen])
def listar_lineas(db: Session = Depends(get_db)):
    """Lista todas las líneas activas (sin geometría)."""
    return obtener_lineas_activas(db)


@router.get("/{linea_id}", response_model=LineaDetalle)
def detalle_linea(linea_id: uuid.UUID, db: Session = Depends(get_db)):
    """Devuelve una línea con recorridos GeoJSON y puntos de partida/llegada."""
    linea = obtener_linea_detalle(db, linea_id)
    if not linea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Línea no encontrada",
        )
    return linea
```

> Los endpoints `GET /lineas/cercanas` y `GET /lineas/{id}/microbuses-activos`
> se implementan en el Ciclo 6. Por ahora solo se necesitan estos dos.

---

## 2. Datos de prueba — 5 líneas de Santa Cruz de la Sierra

Ejecutar este script SQL en pgAdmin o psql **después** de que la tabla
`lineas` exista (el script de la BD ya la creó).

```sql
-- ============================================================
-- DATOS DE PRUEBA: 5 líneas de microbús — Santa Cruz de la Sierra
-- Coordenadas aproximadas basadas en rutas reales
-- ============================================================

-- Limpiar datos de prueba anteriores si los hay
DELETE FROM lineas WHERE numero IN ('10','17','24','51','87');

-- ── Línea 10: Plan 3000 ↔ Centro ────────────────────────────
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '10', 'Línea 10 — Plan 3000', 'Plan 3000 - 4to Anillo - Centro',
  ST_GeomFromText('LINESTRING(
    -63.1400 -17.8250,
    -63.1480 -17.8180,
    -63.1560 -17.8100,
    -63.1640 -17.8020,
    -63.1720 -17.7950,
    -63.1800 -17.7870,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1800 -17.7870,
    -63.1720 -17.7950,
    -63.1640 -17.8020,
    -63.1560 -17.8100,
    -63.1480 -17.8180,
    -63.1400 -17.8250
  )', 4326)
);

-- ── Línea 17: Equipetrol ↔ Centro ───────────────────────────
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '17', 'Línea 17 — Equipetrol', 'Barrio Equipetrol - 3er Anillo - Plaza Principal',
  ST_GeomFromText('LINESTRING(
    -63.2100 -17.7700,
    -63.2020 -17.7720,
    -63.1950 -17.7750,
    -63.1880 -17.7790,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1880 -17.7790,
    -63.1950 -17.7750,
    -63.2020 -17.7720,
    -63.2100 -17.7700
  )', 4326)
);

-- ── Línea 24: Villa 1ro de Mayo ↔ Centro ────────────────────
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '24', 'Línea 24 — Villa 1ro de Mayo', 'Villa 1ro de Mayo - Av. Roca y Coronado - Centro',
  ST_GeomFromText('LINESTRING(
    -63.1300 -17.7600,
    -63.1380 -17.7650,
    -63.1460 -17.7700,
    -63.1550 -17.7750,
    -63.1650 -17.7790,
    -63.1750 -17.7810,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1750 -17.7810,
    -63.1650 -17.7790,
    -63.1550 -17.7750,
    -63.1460 -17.7700,
    -63.1380 -17.7650,
    -63.1300 -17.7600
  )', 4326)
);

-- ── Línea 51: Pampa de la Isla ↔ Centro ─────────────────────
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '51', 'Línea 51 — Pampa de la Isla', 'Pampa de la Isla - Av. Alemana - 2do Anillo - Centro',
  ST_GeomFromText('LINESTRING(
    -63.1900 -17.7400,
    -63.1880 -17.7480,
    -63.1860 -17.7560,
    -63.1845 -17.7640,
    -63.1835 -17.7720,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1835 -17.7720,
    -63.1845 -17.7640,
    -63.1860 -17.7560,
    -63.1880 -17.7480,
    -63.1900 -17.7400
  )', 4326)
);

-- ── Línea 87: Urbarí ↔ Centro ───────────────────────────────
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '87', 'Línea 87 — Urbarí', 'Urbarí - Av. Busch - 1er Anillo - Centro',
  ST_GeomFromText('LINESTRING(
    -63.1600 -17.8050,
    -63.1660 -17.8000,
    -63.1700 -17.7950,
    -63.1740 -17.7900,
    -63.1780 -17.7860,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1780 -17.7860,
    -63.1740 -17.7900,
    -63.1700 -17.7950,
    -63.1660 -17.8000,
    -63.1600 -17.8050
  )', 4326)
);

-- Verificar inserción
SELECT numero, nombre, ST_NumPoints(recorrido_ida) AS puntos_ida FROM lineas ORDER BY numero;
```

### Dónde ejecutar
1. Abrir **pgAdmin 4** → conectar a `microbuses_sig`
2. Abrir Query Tool (ícono de llave)
3. Pegar el SQL completo y ejecutar (F5)
4. Verificar que devuelve 5 filas en la consulta final

---

## 3. Verificar que los puntos extremos se calcularon

El trigger `trg_lineas_puntos_extremos` del script original de la BD calcula
automáticamente `punto_partida_ida`, `punto_llegada_ida`, etc. al insertar.
Verificar:

```sql
SELECT numero,
       ST_AsText(punto_partida_ida)  AS partida_ida,
       ST_AsText(punto_llegada_ida)  AS llegada_ida
FROM lineas
ORDER BY numero;
```

Debe mostrar las coordenadas de inicio y fin de cada ruta.

---

## Verificación del router

```bash
.\venv\Scripts\python -c "
from app.routers.lineas import router
print('router lineas OK')
"
```

---

## Siguiente paso
→ **C3_P5_main_y_verificacion.md** — Registrar routers y verificación final del Ciclo 3
