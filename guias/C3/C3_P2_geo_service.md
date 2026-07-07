# C3 · Parte 2 — Geo Service (PostGIS → GeoJSON)

## Objetivo
Implementar `app/services/geo_service.py` con las funciones que convierten
geometrías PostGIS (WKB) a dicts GeoJSON y extraen coordenadas de puntos.
Este servicio es la base de todo lo geoespacial en el proyecto.

## Archivos a crear
```
app/services/geo_service.py
```

---

## 1. Contexto: cómo devuelve geometrías SQLAlchemy + GeoAlchemy2

Cuando haces `db.query(Linea).first()`, los campos `recorrido_ida`,
`punto_partida_ida`, etc. vienen como objetos `WKBElement` de GeoAlchemy2,
no como GeoJSON. Hay que convertirlos.

La forma más directa es usar `ST_AsGeoJSON` de PostGIS en la misma consulta
SQL para que la BD haga la conversión y devuelva el string JSON directamente.

---

## 2. `app/services/geo_service.py`

```python
# app/services/geo_service.py
import json
from typing import Any, Optional

from geoalchemy2.functions import ST_AsGeoJSON, ST_X, ST_Y
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.linea import Linea
from app.schemas.linea import LineaDetalle, LineaResumen, PuntoGeo


def geojson_a_dict(wkb_element) -> Optional[Any]:
    """
    Convierte un WKBElement de GeoAlchemy2 a dict GeoJSON.
    Devuelve None si el elemento es None.
    """
    if wkb_element is None:
        return None
    # ST_AsGeoJSON devuelve un string JSON; lo parseamos a dict
    from geoalchemy2.functions import ST_AsGeoJSON as fn
    from sqlalchemy import select, literal
    geojson_str = func.ST_AsGeoJSON(wkb_element).compile(compile_kwargs={"literal_binds": True})
    # Usamos shapely para la conversión local sin necesitar una sesión de BD
    from shapely import wkb as shapely_wkb
    from shapely.geometry import mapping
    shape = shapely_wkb.loads(bytes(wkb_element.data), hex=False)
    return mapping(shape)


def punto_a_coordenadas(wkb_element) -> Optional[PuntoGeo]:
    """
    Extrae longitud y latitud de un WKBElement POINT.
    Devuelve None si el elemento es None.
    """
    if wkb_element is None:
        return None
    from shapely import wkb as shapely_wkb
    shape = shapely_wkb.loads(bytes(wkb_element.data), hex=False)
    return PuntoGeo(longitud=shape.x, latitud=shape.y)


def obtener_lineas_activas(db: Session) -> list[LineaResumen]:
    """Devuelve todas las líneas activas (sin geometría, para la lista)."""
    lineas = db.query(Linea).filter(Linea.activa == True).order_by(Linea.numero).all()
    return [LineaResumen.model_validate(l) for l in lineas]


def obtener_linea_detalle(db: Session, linea_id) -> Optional[LineaDetalle]:
    """
    Devuelve una línea con sus recorridos en formato GeoJSON
    y los puntos extremos para los marcadores verde/rojo.
    """
    linea = db.query(Linea).filter(Linea.id == linea_id, Linea.activa == True).first()
    if not linea:
        return None

    return LineaDetalle(
        id=linea.id,
        numero=linea.numero,
        nombre=linea.nombre,
        descripcion=linea.descripcion,
        activa=linea.activa,
        recorrido_ida=geojson_a_dict(linea.recorrido_ida),
        recorrido_vuelta=geojson_a_dict(linea.recorrido_vuelta),
        punto_partida_ida=punto_a_coordenadas(linea.punto_partida_ida),
        punto_llegada_ida=punto_a_coordenadas(linea.punto_llegada_ida),
        punto_partida_vuelta=punto_a_coordenadas(linea.punto_partida_vuelta),
        punto_llegada_vuelta=punto_a_coordenadas(linea.punto_llegada_vuelta),
    )
```

> **Por qué usar Shapely en lugar de hacer un SELECT con ST_AsGeoJSON**:
> Con Shapely la conversión es local (sin round-trip a la BD), más rápida
> para campos que ya están cargados en el objeto ORM.
> El objeto `WKBElement` de GeoAlchemy2 expone `.data` como bytes que
> Shapely puede leer directamente con `wkb.loads`.

---

## 3. Alternativa más simple (si Shapely da problemas)

Si `wkb_element.data` falla, usar directamente una query SQL con `ST_AsGeoJSON`:

```python
from sqlalchemy import text

def obtener_geojson_linea(db: Session, linea_id):
    row = db.execute(text("""
        SELECT
            ST_AsGeoJSON(recorrido_ida)::json      AS ida,
            ST_AsGeoJSON(recorrido_vuelta)::json   AS vuelta,
            ST_X(punto_partida_ida)  AS lon_partida_ida,
            ST_Y(punto_partida_ida)  AS lat_partida_ida,
            ST_X(punto_llegada_ida)  AS lon_llegada_ida,
            ST_Y(punto_llegada_ida)  AS lat_llegada_ida,
            ST_X(punto_partida_vuelta) AS lon_partida_vuelta,
            ST_Y(punto_partida_vuelta) AS lat_partida_vuelta,
            ST_X(punto_llegada_vuelta) AS lon_llegada_vuelta,
            ST_Y(punto_llegada_vuelta) AS lat_llegada_vuelta
        FROM lineas
        WHERE id = :linea_id AND activa = TRUE
    """), {"linea_id": str(linea_id)}).mappings().first()
    return row
```

> Esta alternativa delega todo a PostGIS y evita depender de Shapely para la
> serialización. Si hay errores de conversión WKB en la alternativa principal,
> usar esta.

---

## Verificación de esta parte

```bash
.\venv\Scripts\python -c "
from app.services.geo_service import obtener_lineas_activas, obtener_linea_detalle
print('geo_service OK')
"
```

---

## Siguiente paso
→ **C3_P3_router_microbuses.md** — Endpoints de registro y listado de microbuses
