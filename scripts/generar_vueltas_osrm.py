"""
generar_vueltas_osrm.py
-----------------------
Calcula el recorrido de VUELTA real (por las calles correctas, respetando
sentidos de circulación) para las líneas donde OSM solo trae la ida y el
seeder usaba `reversed(ida)` — que dibuja al micro yendo contramano.

Cómo: por cada línea afectada se toman waypoints de la ida invertida (cada
~800 m) y se pide a OSRM (perfil driving) la ruta que los une. Donde la calle
es doble vía, OSRM devuelve la misma calle; donde es mano única, devuelve la
paralela legal de retorno. El resultado se valida:
  - largo entre 0.8x y 1.45x del largo de la ida (si OSRM hizo loops por
    waypoints mal ubicados, se reintenta con menos waypoints), y
  - al menos 80% de los puntos a < ~430 m del corredor de la ida (evita que
    OSRM se escape por una avenida totalmente distinta).

Salida: Datos_OSM/vueltas_osrm.geojson (una Feature por línea, properties.ref).
El seeder (seed_lineas_osm.py) usa ese archivo como override de la vuelta.

Uso:
  cd Backend
  python -X utf8 scripts/generar_vueltas_osrm.py            # todas las afectadas
  python -X utf8 scripts/generar_vueltas_osrm.py --refs 10,4  # solo algunas
"""
import argparse
import json
import os
import sys
import time

import requests
from shapely.geometry import LineString, Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed_lineas_osm import (  # noqa: E402
    DIR_OSM,
    es_circular,
    haversine,
    ida_vuelta,
    recorridos_por_ref,
)

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"
SALIDA = os.path.join(DIR_OSM, "vueltas_osrm.geojson")
ESPACIADOS_M = [800, 1500, 3000, None]  # None = solo extremos
RATIO_OK = (0.80, 1.45)      # largo aceptable vs largo de la ida
RATIO_LIMITE = (0.70, 1.80)  # fuera de esto se descarta el candidato
CORREDOR_DEG = 0.004         # ~430 m: qué tan cerca de la ida debe ir la vuelta
FRACCION_EN_CORREDOR = 0.80
PAUSA_SEG = 1.0              # cortesía con el servidor demo de OSRM


def largo_m(coords):
    return sum(haversine(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
               for i in range(1, len(coords)))


def muestrear(coords, espaciado):
    """Puntos de la línea cada `espaciado` metros (incluye extremos).
    Con espaciado None devuelve solo los extremos."""
    if espaciado is None:
        return [coords[0], coords[-1]]
    pts = [coords[0]]
    acc = 0.0
    for i in range(1, len(coords)):
        acc += haversine(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
        if acc >= espaciado:
            pts.append(coords[i])
            acc = 0.0
    if pts[-1] != coords[-1]:
        pts.append(coords[-1])
    return pts


def pedir_osrm(waypoints):
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in waypoints)
    url = (OSRM_URL + coords +
           "?overview=full&geometries=geojson&alternatives=false&steps=false")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        return None
    return [(c[0], c[1]) for c in data["routes"][0]["geometry"]["coordinates"]]


def en_corredor(vuelta, ida):
    """Fracción de puntos de la vuelta que quedan cerca del corredor de la ida."""
    linea_ida = LineString(ida)
    cerca = sum(1 for c in vuelta if linea_ida.distance(Point(c)) <= CORREDOR_DEG)
    return cerca / max(1, len(vuelta))


def calcular_vuelta(ida):
    """Devuelve (coords, ratio, espaciado) del mejor candidato OSRM, o None."""
    objetivo = list(reversed(ida))
    len_ida = largo_m(ida)
    candidatos = []
    for esp in ESPACIADOS_M:
        try:
            ruta = pedir_osrm(muestrear(objetivo, esp))
        except requests.RequestException:
            ruta = None
        time.sleep(PAUSA_SEG)
        if not ruta or len(ruta) < 2:
            continue
        ratio = largo_m(ruta) / len_ida
        if not (RATIO_LIMITE[0] <= ratio <= RATIO_LIMITE[1]):
            continue
        if en_corredor(ruta, ida) < FRACCION_EN_CORREDOR:
            continue
        candidatos.append((ruta, ratio, esp))
        if RATIO_OK[0] <= ratio <= RATIO_OK[1]:
            break  # suficientemente bueno: waypoints más densos = más fiel
    if not candidatos:
        return None
    return min(candidatos, key=lambda c: abs(c[1] - 1.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", help="solo estas líneas (separadas por coma)")
    args = ap.parse_args()
    solo = set(args.refs.split(",")) if args.refs else None

    rutas = recorridos_por_ref()
    afectadas = []
    circulares = set()
    for ref, comps in rutas.items():
        ida = comps[0]
        if es_circular(ida):
            circulares.add(ref)  # sin vuelta: el lazo va siempre en un sentido
            continue
        tiene_vuelta_real = (len(comps) >= 2 and
                             LineString(comps[1]).length >= 0.5 * LineString(ida).length)
        if not tiene_vuelta_real and (solo is None or ref in solo):
            afectadas.append(ref)
    afectadas.sort(key=lambda r: (len(r), r))
    print(f"Líneas con vuelta = reversed(ida): {len(afectadas)} "
          f"| circulares (sin vuelta): {sorted(circulares)}")

    # Conserva lo ya calculado en corridas anteriores (re-ejecutable),
    # PERO descarta vueltas de líneas circulares (eran un artefacto).
    previas = {}
    if os.path.exists(SALIDA):
        gj = json.load(open(SALIDA, encoding="utf-8"))
        previas = {f["properties"]["ref"]: f for f in gj.get("features", [])
                   if f["properties"]["ref"] not in circulares}

    features = dict(previas)
    ok = sin_ruta = 0
    for ref in afectadas:
        ida, _ = ida_vuelta(rutas[ref])
        res = calcular_vuelta(ida)
        if res is None:
            print(f"  {ref:>4}: OSRM no dio una vuelta válida — se mantiene reversed(ida)")
            sin_ruta += 1
            continue
        coords, ratio, esp = res
        features[ref] = {
            "type": "Feature",
            "properties": {"ref": ref, "fuente": "osrm",
                           "ratio_vs_ida": round(ratio, 3),
                           "espaciado_waypoints_m": esp},
            "geometry": {"type": "LineString",
                         "coordinates": [[round(c[0], 6), round(c[1], 6)] for c in coords]},
        }
        print(f"  {ref:>4}: OK (largo {ratio:.2f}x de la ida, waypoints cada {esp} m)")
        ok += 1

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection",
                   "features": list(features.values())}, f, ensure_ascii=False)
    print(f"\nGuardado {SALIDA}: {ok} vueltas nuevas, {sin_ruta} sin solución, "
          f"{len(features)} en total.")
    print("Siguiente paso: python -X utf8 scripts/seed_lineas_osm.py")


if __name__ == "__main__":
    main()
