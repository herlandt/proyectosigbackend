"""
osm_a_geojson.py
----------------
Convierte la respuesta de la Overpass API (OSM JSON con 'out geom') de las rutas
de micro de Santa Cruz de la Sierra a GeoJSON listo para ArcGIS / QGIS / PostGIS.

Cada relación route=bus se convierte en un Feature MultiLineString (un tramo por
cada way miembro) con propiedades ref / name / network / osm_id.

Genera DOS archivos en Datos_OSM/:
  - rutas_micros_scz_osm.geojson            (todas las rutas de bus encontradas)
  - rutas_micros_scz_osm_proyecto.geojson   (solo las líneas de tu proyecto: 1,2,5,8,9,10,11,16,17,18)

Fuente de datos: OpenStreetMap, licencia ODbL — requiere atribución
("© OpenStreetMap contributors") si se publica.

Uso:
    python -X utf8 scripts/osm_a_geojson.py <ruta_al_osm.json>
"""

import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # Backend/
PROYECTO = os.path.dirname(BASE_DIR)                                     # Proyecto SIG/
SALIDA_DIR = os.path.join(PROYECTO, "Datos_OSM")

# Números de línea de tu proyecto (NombreLinea L001.. -> 1,2,5,...)
LINEAS_PROYECTO = {"1", "2", "5", "8", "9", "10", "11", "16", "17", "18"}


def relacion_a_feature(rel):
    """Construye un Feature MultiLineString a partir de una relación route=bus."""
    tramos = []
    for m in rel.get("members", []):
        if m.get("type") == "way" and "geometry" in m:
            linea = [[p["lon"], p["lat"]] for p in m["geometry"]]
            if len(linea) >= 2:
                tramos.append(linea)
    if not tramos:
        return None
    tags = rel.get("tags", {})
    return {
        "type": "Feature",
        "geometry": {"type": "MultiLineString", "coordinates": tramos},
        "properties": {
            "osm_id": rel.get("id"),
            "ref": tags.get("ref"),
            "name": tags.get("name"),
            "network": tags.get("network"),
            "operator": tags.get("operator"),
            "from": tags.get("from"),
            "to": tags.get("to"),
        },
    }


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python scripts/osm_a_geojson.py <ruta_al_osm.json>")
    ruta = sys.argv[1]

    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = []
    for el in data.get("elements", []):
        if el.get("type") == "relation":
            feat = relacion_a_feature(el)
            if feat:
                features.append(feat)

    os.makedirs(SALIDA_DIR, exist_ok=True)
    fc = {"type": "FeatureCollection",
          "attribution": "© OpenStreetMap contributors (ODbL)",
          "features": features}

    salida_todas = os.path.join(SALIDA_DIR, "rutas_micros_scz_osm.geojson")
    with open(salida_todas, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)

    proyecto = [ft for ft in features if (ft["properties"].get("ref") or "") in LINEAS_PROYECTO]
    fc_proy = {"type": "FeatureCollection",
               "attribution": "© OpenStreetMap contributors (ODbL)",
               "features": proyecto}
    salida_proy = os.path.join(SALIDA_DIR, "rutas_micros_scz_osm_proyecto.geojson")
    with open(salida_proy, "w", encoding="utf-8") as f:
        json.dump(fc_proy, f, ensure_ascii=False)

    print(f"Rutas totales convertidas: {len(features)}")
    refs = sorted({(ft['properties'].get('ref') or '?') for ft in features},
                  key=lambda s: (len(s), s))
    print(f"Refs encontrados: {', '.join(refs)}")
    print(f"\nLíneas del proyecto encontradas en OSM: {len(proyecto)}")
    for ft in proyecto:
        p = ft["properties"]
        print(f"  Línea {p.get('ref')}: {p.get('name')}  ({len(ft['geometry']['coordinates'])} tramos)")
    print(f"\nArchivos generados en {SALIDA_DIR}:")
    print(f"  - {os.path.basename(salida_todas)}")
    print(f"  - {os.path.basename(salida_proy)}")


if __name__ == "__main__":
    main()
