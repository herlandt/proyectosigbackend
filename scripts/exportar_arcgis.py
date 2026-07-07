"""
Exporta paradas y recorridos a Shapefile + GeoJSON (WGS84 / EPSG:4326) para
editarlos en ArcGIS/QGIS: mover paradas, corregir vértices de las rutas y, sobre
todo, separar las avenidas de un sentido a su calle real.

Salida (carpeta `arcgis_edicion/` en la raíz del proyecto):
    paradas.shp/.shx/.dbf/.prj  +  paradas.geojson
    rutas.shp/.shx/.dbf/.prj    +  rutas.geojson
    LEEME.md  (instrucciones de edición y reimportación)

Cada feature conserva su `id` (uuid) para que `importar_arcgis.py` sepa a qué
fila volver. NO cambies ese campo al editar.

Uso:
    venv/Scripts/python.exe scripts/exportar_arcgis.py
"""
import json
import sys
from pathlib import Path

import shapefile  # pyshp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.database import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "arcgis_edicion"

# WKT de WGS84 para el archivo .prj (lo que espera ArcGIS).
PRJ_WGS84 = (
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",'
    '6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]]'
)


def _parsear_codigo(codigo: str):
    """De 'L5-i3' -> ('5','ida'); de 'L110-v2' -> ('110','vuelta'); si no, ('', '')."""
    if not codigo or not codigo.startswith("L") or "-" not in codigo:
        return "", ""
    izq, der = codigo.split("-", 1)
    linea = izq[1:]
    sent = "ida" if der[:1] == "i" else ("vuelta" if der[:1] == "v" else "")
    return linea, sent


def exportar_paradas(db, carpeta: Path):
    filas = db.execute(text("""
        SELECT id::text, COALESCE(id_externo, 0), COALESCE(codigo, ''),
               COALESCE(nombre, ''), ST_X(ubicacion), ST_Y(ubicacion)
        FROM paradas
        WHERE ubicacion IS NOT NULL
        ORDER BY id_externo
    """)).fetchall()

    # Shapefile
    w = shapefile.Writer(str(carpeta / "paradas"), shapeType=shapefile.POINT)
    w.field("pid", "C", size=40)
    w.field("id_ext", "N", decimal=0)
    w.field("codigo", "C", size=30)
    w.field("nombre", "C", size=80)
    w.field("linea", "C", size=10)
    w.field("sentido", "C", size=10)

    features = []
    for pid, idext, codigo, nombre, lon, lat in filas:
        linea, sent = _parsear_codigo(codigo)
        w.point(lon, lat)
        w.record(pid, idext, codigo, nombre, linea, sent)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"pid": pid, "id_ext": idext, "codigo": codigo,
                           "nombre": nombre, "linea": linea, "sentido": sent},
        })
    w.close()
    (carpeta / "paradas.prj").write_text(PRJ_WGS84, encoding="utf-8")
    (carpeta / "paradas.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8")
    return len(filas)


def _coords_de_geojson(geo: dict):
    """Devuelve lista de partes [[ (lon,lat), ... ], ...] para LineString/Multi."""
    if geo["type"] == "LineString":
        return [geo["coordinates"]]
    if geo["type"] == "MultiLineString":
        return geo["coordinates"]
    return []


def exportar_rutas(db, carpeta: Path):
    filas = db.execute(text("""
        SELECT id::text, COALESCE(numero, ''), COALESCE(nombre, ''),
               'ida'  AS sentido, ST_AsGeoJSON(recorrido_ida)
        FROM lineas WHERE recorrido_ida IS NOT NULL
        UNION ALL
        SELECT id::text, COALESCE(numero, ''), COALESCE(nombre, ''),
               'vuelta', ST_AsGeoJSON(recorrido_vuelta)
        FROM lineas WHERE recorrido_vuelta IS NOT NULL
        ORDER BY 2, 4
    """)).fetchall()

    w = shapefile.Writer(str(carpeta / "rutas"), shapeType=shapefile.POLYLINE)
    w.field("lid", "C", size=40)
    w.field("numero", "C", size=10)
    w.field("nombre", "C", size=80)
    w.field("sentido", "C", size=10)

    features = []
    for lid, numero, nombre, sentido, geojson_txt in filas:
        if not geojson_txt:
            continue
        geo = json.loads(geojson_txt)
        partes = _coords_de_geojson(geo)
        if not partes:
            continue
        # pyshp: lista de partes, cada parte lista de [x, y]
        w.line([[[float(x), float(y)] for x, y in parte] for parte in partes])
        w.record(lid, numero, nombre, sentido)
        features.append({
            "type": "Feature",
            "geometry": geo,
            "properties": {"lid": lid, "numero": numero,
                           "nombre": nombre, "sentido": sentido},
        })
    w.close()
    (carpeta / "rutas.prj").write_text(PRJ_WGS84, encoding="utf-8")
    (carpeta / "rutas.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8")
    return len(features)


LEEME = """# Edición de paradas y rutas en ArcGIS / QGIS

Estos archivos están en **WGS84 (EPSG:4326)**, listos para abrir y editar.

## Capas
- **paradas** (puntos): mové cada parada a su ubicación real sobre la calle.
- **rutas** (líneas): un registro por línea y `sentido` (ida/vuelta). Acá se
  corrige el caso de **avenidas de un solo sentido**: si la vuelta debe ir por
  otra calle, mové los vértices de la línea de ese `sentido` a su avenida real.

## Reglas importantes
1. **NO cambies** los campos `pid` (paradas) ni `lid`+`sentido` (rutas): son la
   clave para reimportar a la base. Podés mover geometría y editar `nombre`.
2. No borres ni agregues features si vas a reimportar (la reimportación
   actualiza por id; lo nuevo/eliminado se ignora).
3. Guardá manteniendo el mismo nombre de archivo y la proyección WGS84.

## Recomendado para corregir un par de un sentido
- Cargá de fondo un mapa base (OSM/Imagery) en ArcGIS.
- Editá la línea `sentido = vuelta` (o ida) y arrastrá sus vértices a la calle
  correcta. Hacé lo mismo con las paradas de esa mano.

## Reimportar a la base
    venv/Scripts/python.exe scripts/reimportar_arcgis.py            # paradas + rutas
    venv/Scripts/python.exe scripts/reimportar_arcgis.py --aristas  # + recalcular la red

Podés editar el **GeoJSON** o el **Shapefile**: el importador prefiere el
GeoJSON si existe, y si no usa el Shapefile.
"""


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        n_par = exportar_paradas(db, SALIDA)
        n_rutas = exportar_rutas(db, SALIDA)
    finally:
        db.close()
    (SALIDA / "LEEME.md").write_text(LEEME, encoding="utf-8")
    print(f"OK -> {SALIDA}")
    print(f"   paradas: {n_par}  (paradas.shp + paradas.geojson)")
    print(f"   rutas:   {n_rutas}  (rutas.shp + rutas.geojson)")
    print("   LEEME.md con instrucciones de edicion/reimportacion")


if __name__ == "__main__":
    main()
