# C6 · Parte 3 — ETA Service: tiempo estimado de llegada

## Objetivo
Implementar `app/services/eta_service.py` que calcula en cuántos minutos
llegará el microbús más cercano al punto del usuario. Usa la función
`fn_eta_microbus_cercano` ya definida en la BD.

## Archivos a crear
```
app/services/eta_service.py
```

---

## 1. `app/services/eta_service.py`

```python
# app/services/eta_service.py
import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.linea import EtaResponse


def calcular_eta(
    db: Session,
    linea_id: uuid.UUID,
    sentido: str,
    longitud: float,
    latitud: float,
) -> Optional[EtaResponse]:
    """
    Devuelve el ETA del microbús más cercano al punto del usuario.
    Retorna None si no hay microbuses activos en esa línea/sentido.

    El cálculo usa fn_eta_microbus_cercano de PostGIS:
    - distancia real en metros entre el microbús y el usuario
    - velocidad del microbús (o 25 km/h si está detenido)
    - ETA = (distancia_km / velocidad_kmh) * 60 minutos
    """
    filas = db.execute(
        text("""
            SELECT microbus_id, placa, numero_interno,
                   longitud, latitud,
                   distancia_metros, velocidad_kmh, eta_minutos
            FROM fn_eta_microbus_cercano(
                :linea_id,
                :sentido::sentido_enum,
                :lon,
                :lat
            )
            LIMIT 1
        """),
        {
            "linea_id": str(linea_id),
            "sentido": sentido,
            "lon": longitud,
            "lat": latitud,
        },
    ).mappings().all()

    if not filas:
        return None

    fila = filas[0]
    return EtaResponse(
        microbus_id=fila["microbus_id"],
        placa=fila["placa"],
        numero_interno=fila["numero_interno"],
        longitud=float(fila["longitud"]) if fila["longitud"] else 0.0,
        latitud=float(fila["latitud"]) if fila["latitud"] else 0.0,
        distancia_metros=float(fila["distancia_metros"]),
        velocidad_kmh=float(fila["velocidad_kmh"]),
        eta_minutos=float(fila["eta_minutos"]),
    )
```

---

## 2. Cómo funciona `fn_eta_microbus_cercano`

La función SQL del C1 hace esto en un solo query:

```sql
-- Para cada microbús activo de la línea:
distancia = ST_Distance(ubicacion_microbus::geography, punto_usuario::geography)

eta = (distancia / 1000.0) / CASE
          WHEN velocidad < 5 THEN 25   -- usa 25 km/h si está casi detenido
          ELSE velocidad
      END * 60
```

**Resultado**: microbuses ordenados por `distancia_metros` ASC.
El `LIMIT 1` en el servicio toma solo el más cercano.

---

## 3. Caso sin microbuses activos

Si no hay ningún conductor transmitiendo en esa línea/sentido,
la función devuelve 0 filas → el servicio retorna `None`.

El endpoint debe manejar esto y devolver una respuesta clara:

```json
{
  "detail": "No hay microbuses activos en esta línea en este momento"
}
```

---

## 4. Limitaciones del cálculo

| Limitación | Por qué existe | Solución futura |
|---|---|---|
| Distancia en línea recta | No calcula distancia sobre la ruta | Usar `ST_LineLocatePoint` para proyectar sobre el recorrido |
| No considera semáforos ni tráfico | Solo usa velocidad actual | ETA es estimado, no exacto |
| Velocidad 0 → usa 25 km/h | El microbús puede estar parado en un semáforo | Aceptable para la precisión del sistema |

El enunciado pide un ETA estimado, no una predicción exacta. El cálculo
actual es suficiente para el alcance del proyecto.

---

## Verificación

```bash
.\venv\Scripts\python -c "
from app.services.eta_service import calcular_eta
print('eta_service OK')
"
```

Para probar con datos reales necesitas un conductor activo (C4).
Si no hay ninguno, `calcular_eta` devuelve `None` — eso es correcto.

---

## Siguiente paso
→ **C6_P4_router_lineas_nuevos_endpoints.md** — Agregar /cercanas, /eta y /microbuses-activos al router
