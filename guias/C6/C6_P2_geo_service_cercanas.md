# C6 · Parte 2 — Geo Service: líneas cercanas y microbuses activos

## Objetivo
Extender `app/services/geo_service.py` con dos funciones:
1. `obtener_lineas_cercanas` → llama a `fn_lineas_cercanas` de PostGIS
2. `obtener_microbuses_activos` → consulta la vista `vw_microbuses_activos`

Ambas ya tienen la lógica geoespacial implementada en la BD (C1).
El servicio solo las llama y convierte el resultado a los schemas.

## Archivos a modificar
```
app/services/geo_service.py    ← agregar dos funciones nuevas
```

---

## 1. Agregar en `app/services/geo_service.py`

Al inicio del archivo agregar el import que falta:
```python
from sqlalchemy import text
```

Luego agregar las dos funciones al final:

```python
def obtener_lineas_cercanas(
    db: Session,
    longitud: float,
    latitud: float,
    radio_metros: int = 500,
) -> list[LineaCercanaResponse]:
    """
    Devuelve las líneas activas dentro del radio especificado alrededor
    del punto dado. Usa la función PostGIS fn_lineas_cercanas de la BD.
    Ordenadas de menor a mayor distancia.
    """
    filas = db.execute(
        text("SELECT * FROM fn_lineas_cercanas(:lon, :lat, :radio)"),
        {"lon": longitud, "lat": latitud, "radio": radio_metros},
    ).mappings().all()

    return [
        LineaCercanaResponse(
            linea_id=fila["linea_id"],
            numero=fila["numero"],
            nombre=fila["nombre"],
            distancia_minima_m=float(fila["distancia_minima_m"]),
            pasa_ida=fila["pasa_ida"],
            pasa_vuelta=fila["pasa_vuelta"],
        )
        for fila in filas
    ]


def obtener_microbuses_activos(
    db: Session,
    linea_id: uuid.UUID,
    sentido: str,
) -> list[MicrobusActivoResponse]:
    """
    Devuelve los microbuses en servicio de una línea con su última posición GPS.
    Usa la función PostGIS fn_microbuses_linea_activos de la BD.
    """
    filas = db.execute(
        text("""
            SELECT microbus_id, placa, numero_interno,
                   longitud, latitud, velocidad, ultima_actualizacion
            FROM fn_microbuses_linea_activos(:linea_id, :sentido::sentido_enum)
        """),
        {"linea_id": str(linea_id), "sentido": sentido},
    ).mappings().all()

    return [
        MicrobusActivoResponse(
            microbus_id=fila["microbus_id"],
            placa=fila["placa"],
            numero_interno=fila["numero_interno"],
            longitud=float(fila["longitud"]) if fila["longitud"] else 0.0,
            latitud=float(fila["latitud"]) if fila["latitud"] else 0.0,
            velocidad=float(fila["velocidad"]) if fila["velocidad"] else 0.0,
            ultima_actualizacion=fila["ultima_actualizacion"],
        )
        for fila in filas
    ]
```

También agregar los imports de los nuevos schemas al inicio del archivo:

```python
from app.schemas.linea import (
    LineaCercanaResponse,
    LineaDetalle,
    LineaResumen,
    MicrobusActivoResponse,
    PuntoGeo,
)
```

---

## 2. Cómo funciona `fn_lineas_cercanas`

La función ya existe en la BD desde el script SQL del C1. Recibe:
- `p_longitud`, `p_latitud` — coordenadas del punto del usuario
- `p_radio_metros` — radio de búsqueda (default 500 m)

Internamente usa `ST_DWithin` con cast a `geography` para que la distancia
sea en metros reales (no grados). Devuelve:

| Columna | Tipo | Descripción |
|---|---|---|
| `linea_id` | UUID | ID de la línea |
| `numero` | varchar | Número de la línea |
| `nombre` | varchar | Nombre |
| `distancia_minima_m` | float | Distancia mínima al recorrido en metros |
| `pasa_ida` | bool | Si el recorrido de ida pasa dentro del radio |
| `pasa_vuelta` | bool | Si el recorrido de vuelta pasa dentro del radio |

---

## 3. Por qué `::sentido_enum` en la función de microbuses

PostgreSQL requiere el cast explícito `:sentido::sentido_enum` porque el
parámetro llega como string desde Python y la función espera el tipo ENUM
definido en la BD. Sin el cast PostgreSQL lanza:

```
ERROR: function fn_microbuses_linea_activos(uuid, text) does not exist
```

---

## Verificación

Prueba rápida con la BD (necesita al menos una línea cargada del C3):

```bash
.\venv\Scripts\python -c "
from app.core.database import SessionLocal
from app.services.geo_service import obtener_lineas_cercanas

db = SessionLocal()
# Plaza 24 de Septiembre — centro de Santa Cruz
resultado = obtener_lineas_cercanas(db, lon=-63.1822, lat=-17.7834, radio_metros=1000)
for r in resultado:
    print(f'Línea {r.numero}: {r.distancia_minima_m:.0f}m')
db.close()
"
```

Si las líneas del C3 están cargadas, debe mostrar las que pasan cerca del centro.

---

## Siguiente paso
→ **C6_P3_eta_service.md** — Cálculo del tiempo estimado de llegada
