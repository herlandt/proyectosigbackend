"""
Reimporta a la base lo editado en ArcGIS/QGIS por `exportar_arcgis.py`:
- paradas: nueva ubicación por `pid`.
- rutas:   nueva geometría de `recorrido_ida`/`recorrido_vuelta` por `lid`+`sentido`.

Prefiere los GeoJSON (paradas.geojson / rutas.geojson); si no existen usa los
Shapefile. Actualiza por id: lo agregado o borrado en el editor se ignora.

Uso:
    venv/Scripts/python.exe scripts/reimportar_arcgis.py            # paradas + rutas
    venv/Scripts/python.exe scripts/reimportar_arcgis.py --aristas  # + recalcular red

Con --aristas recalcula red_aristas y red_transbordos (distancia/tiempo/geom)
a partir de las nuevas posiciones de las paradas, preservando la velocidad
original de cada arista (escala el tiempo proporcionalmente).
"""
import json
import sys
from pathlib import Path

import shapefile  # pyshp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "arcgis_edicion"
EPS = 1e-7  # ~1 cm: umbral para considerar que una parada se movió


# ---------- lectura de archivos editados ----------
def leer_paradas():
    """-> list[(pid, lon, lat)]"""
    gj = CARPETA / "paradas.geojson"
    if gj.exists():
        data = json.loads(gj.read_text(encoding="utf-8"))
        out = []
        for f in data["features"]:
            lon, lat = f["geometry"]["coordinates"][:2]
            out.append((f["properties"]["pid"], float(lon), float(lat)))
        return out
    r = shapefile.Reader(str(CARPETA / "paradas"))
    out = []
    for sr in r.shapeRecords():
        x, y = sr.shape.points[0]
        out.append((sr.record["pid"], float(x), float(y)))
    return out


def _partes_de_shape(shape):
    pts = shape.points
    parts = list(shape.parts) + [len(pts)]
    return [pts[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]


def leer_rutas():
    """-> list[(lid, sentido, geojson_geom)]"""
    gj = CARPETA / "rutas.geojson"
    if gj.exists():
        data = json.loads(gj.read_text(encoding="utf-8"))
        return [(f["properties"]["lid"], f["properties"]["sentido"], f["geometry"])
                for f in data["features"]]
    r = shapefile.Reader(str(CARPETA / "rutas"))
    out = []
    for sr in r.shapeRecords():
        partes = _partes_de_shape(sr.shape)
        if len(partes) == 1:
            geom = {"type": "LineString",
                    "coordinates": [[float(x), float(y)] for x, y in partes[0]]}
        else:
            geom = {"type": "MultiLineString",
                    "coordinates": [[[float(x), float(y)] for x, y in p] for p in partes]}
        out.append((sr.record["lid"], sr.record["sentido"], geom))
    return out


# ---------- escritura a la base ----------
def importar_paradas(db):
    actuales = {str(r[0]): (r[1], r[2]) for r in db.execute(text(
        "SELECT id::text, ST_X(ubicacion), ST_Y(ubicacion) FROM paradas "
        "WHERE ubicacion IS NOT NULL")).fetchall()}
    movidas = 0
    for pid, lon, lat in leer_paradas():
        cur = actuales.get(pid)
        if cur is None:
            continue
        if abs(cur[0] - lon) < EPS and abs(cur[1] - lat) < EPS:
            continue
        db.execute(text(
            "UPDATE paradas SET ubicacion = ST_SetSRID(ST_MakePoint(:lon,:lat),4326) "
            "WHERE id = :pid"), {"lon": lon, "lat": lat, "pid": pid})
        movidas += 1
    return movidas


def importar_rutas(db):
    col = {"ida": "recorrido_ida", "vuelta": "recorrido_vuelta"}
    n = 0
    for lid, sentido, geom in leer_rutas():
        c = col.get(sentido)
        if c is None:
            continue
        db.execute(text(
            f"UPDATE lineas SET {c} = ST_SetSRID(ST_GeomFromGeoJSON(:g),4326), "
            f"updated_at = now() WHERE id = :lid"),
            {"g": json.dumps(geom), "lid": lid})
        n += 1
    return n


def recalcular_red(db):
    """Recalcula distancia/tiempo/geom de la red desde las paradas y rutas
    actuales, preservando la velocidad original de cada arista (escala el
    tiempo). Cada arista se re-snapea a la CURVA de su recorrido (ST_LineSubstring
    entre las proyecciones de sus paradas), no a una recta, así conserva la forma
    real de la calle. Los transbordos (caminata parada→parada) sí van rectos."""
    db.execute(text("""
        UPDATE red_aristas a SET
            geom = sub.g,
            distancia_m = ST_Length(sub.g::geography),
            tiempo_seg = CASE WHEN a.distancia_m > 0 AND ST_Length(sub.g::geography) > 0
                              THEN a.tiempo_seg * ST_Length(sub.g::geography) / a.distancia_m
                              ELSE a.tiempo_seg END
        FROM (
            SELECT a2.id,
                   ST_LineSubstring(rec.line,
                       least(ST_LineLocatePoint(rec.line, po.ubicacion),
                             ST_LineLocatePoint(rec.line, pd.ubicacion)),
                       greatest(ST_LineLocatePoint(rec.line, po.ubicacion),
                                ST_LineLocatePoint(rec.line, pd.ubicacion))) AS g
            FROM red_aristas a2
            JOIN paradas po ON po.id = a2.parada_origen
            JOIN paradas pd ON pd.id = a2.parada_destino
            JOIN LATERAL (
                SELECT ST_LineMerge(
                    CASE WHEN a2.sentido = 'ida' THEN l.recorrido_ida
                         ELSE l.recorrido_vuelta END) AS line
                FROM lineas l WHERE l.id = a2.linea_id
            ) rec ON true
            WHERE rec.line IS NOT NULL
              AND GeometryType(rec.line) = 'LINESTRING'
        ) sub
        WHERE a.id = sub.id
          AND sub.g IS NOT NULL
          AND ST_Length(sub.g::geography) > 0
    """))
    db.execute(text("""
        UPDATE red_transbordos t SET
            distancia_m = nd.d,
            tiempo_seg = CASE WHEN t.distancia_m > 0
                              THEN t.tiempo_seg * nd.d / t.distancia_m
                              ELSE t.tiempo_seg END
        FROM (
            SELECT t2.id,
                   ST_Distance(po.ubicacion::geography, pd.ubicacion::geography) AS d
            FROM red_transbordos t2
            JOIN paradas po ON po.id = t2.parada_origen
            JOIN paradas pd ON pd.id = t2.parada_destino
        ) nd
        WHERE t.id = nd.id
    """))


def main():
    if not CARPETA.exists():
        print(f"No existe {CARPETA}. Corré primero exportar_arcgis.py")
        return
    rebuild = "--aristas" in sys.argv
    db = SessionLocal()
    try:
        movidas = importar_paradas(db)
        rutas = importar_rutas(db)
        if rebuild:
            recalcular_red(db)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"ERROR (rollback): {e}")
        raise
    finally:
        db.close()
    print(f"OK  paradas movidas: {movidas}  |  rutas actualizadas: {rutas}"
          + ("  |  red recalculada" if rebuild else ""))


if __name__ == "__main__":
    main()
