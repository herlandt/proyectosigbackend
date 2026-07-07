"""
pulir_geometrias.py
-------------------
PULE las geometrías de las líneas: las relaciones de OSM a veces vienen con
HUECOS y el recorrido salta en línea recta entre dos puntos lejanos (se ve como
una diagonal cruzando la manzana, p. ej. la ida de la línea 72). Este script:

  1. Arma ida/vuelta por línea igual que el seeder (incluye vueltas OSRM).
  2. Detecta saltos rectos > UMBRAL_SALTO_M entre puntos consecutivos.
  3. Rellena cada salto con la ruta real por calles (OSRM driving) y valida:
     - los extremos de lo devuelto quedan cerca de los puntos originales, y
     - el largo no es absurdo (ratio <= 8x el salto recto).
     Si el "salto" era una avenida recta legítima, OSRM devuelve casi la misma
     recta y no cambia nada visible; si era un hueco, ahora sigue las calles.
  4. Guarda TODO en Datos_OSM/rutas_pulidas.geojson (una Feature por
     ref+sentido). El seeder lo usa con prioridad máxima si existe.

Re-ejecutable: reescribe el archivo completo en cada corrida.

Uso:
  cd Backend
  python -X utf8 scripts/pulir_geometrias.py            # todas
  python -X utf8 scripts/pulir_geometrias.py --refs 72  # solo algunas
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generar_vueltas_osrm import pedir_osrm  # noqa: E402
from seed_lineas_osm import (  # noqa: E402
    DIR_OSM,
    cargar_vueltas_osrm,
    haversine,
    ida_vuelta,
    recorridos_por_ref,
)

SALIDA = os.path.join(DIR_OSM, "rutas_pulidas.geojson")
UMBRAL_SALTO_M = 200      # segmentos rectos más largos que esto se revisan
TOLERANCIA_EXTREMO_M = 120  # lo devuelto debe empezar/terminar cerca del salto
RATIO_MAX = 8.0           # relleno no puede ser > 8x el salto recto
PAUSA_SEG = 0.7           # cortesía con el servidor demo de OSRM


def _valido(ruta, a, b, salto_m):
    if not ruta or len(ruta) < 2:
        return False
    if haversine(ruta[0][0], ruta[0][1], a[0], a[1]) > TOLERANCIA_EXTREMO_M:
        return False
    if haversine(ruta[-1][0], ruta[-1][1], b[0], b[1]) > TOLERANCIA_EXTREMO_M:
        return False
    largo = sum(haversine(ruta[i - 1][0], ruta[i - 1][1], ruta[i][0], ruta[i][1])
                for i in range(1, len(ruta)))
    return largo <= salto_m * RATIO_MAX


def pulir(coords):
    """Rellena los saltos > UMBRAL_SALTO_M con la ruta OSRM por calles.
    Devuelve (coords_pulidas, saltos_rellenados, saltos_mantenidos)."""
    out = [coords[0]]
    rellenados = mantenidos = 0
    for i in range(1, len(coords)):
        a, b = coords[i - 1], coords[i]
        d = haversine(a[0], a[1], b[0], b[1])
        if d > UMBRAL_SALTO_M:
            try:
                ruta = pedir_osrm([a, b])
            except Exception:  # noqa: BLE001 (red caída => se mantiene la recta)
                ruta = None
            time.sleep(PAUSA_SEG)
            if _valido(ruta, a, b, d):
                out.extend(ruta[1:-1])  # puntos intermedios por la calle real
                rellenados += 1
            else:
                mantenidos += 1
        out.append(b)
    return out, rellenados, mantenidos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", help="solo estas líneas (separadas por coma)")
    args = ap.parse_args()
    solo = set(args.refs.split(",")) if args.refs else None

    rutas = recorridos_por_ref()
    overrides = cargar_vueltas_osrm()

    # Con --refs se conserva lo ya pulido de las demás líneas (re-ejecutable).
    features = {}
    if solo is not None and os.path.exists(SALIDA):
        gj = json.load(open(SALIDA, encoding="utf-8"))
        features = {(f["properties"]["ref"], f["properties"]["sentido"]): f
                    for f in gj.get("features", [])
                    if f["properties"]["ref"] not in solo}

    tot_rell = tot_mant = 0
    for ref in sorted(rutas, key=lambda r: (len(r), r)):
        if solo is not None and ref not in solo:
            continue
        ida, vuelta = ida_vuelta(rutas[ref])
        circular = vuelta == ida
        if not circular and ref in overrides and vuelta == list(reversed(ida)):
            vuelta = overrides[ref]

        resultados = {}
        resultados["ida"] = pulir(ida)
        # Circular: la vuelta ES la ida — se reutiliza el pulido (sin OSRM extra).
        resultados["vuelta"] = resultados["ida"] if circular else pulir(vuelta)

        for sentido, (pulida, rell, mant) in resultados.items():
            if sentido == "vuelta" and circular:
                rell = mant = 0  # ya contados en la ida
            tot_rell += rell
            tot_mant += mant
            if rell or mant:
                print(f"  {ref:>4} {sentido:<6}: {rell} saltos rellenados, "
                      f"{mant} mantenidos (rectas legítimas o sin ruta)")
            features[(ref, sentido)] = {
                "type": "Feature",
                "properties": {"ref": ref, "sentido": sentido,
                               "saltos_rellenados": rell},
                "geometry": {"type": "LineString",
                             "coordinates": [[round(c[0], 6), round(c[1], 6)]
                                             for c in pulida]},
            }

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection",
                   "features": list(features.values())}, f, ensure_ascii=False)
    print(f"\nGuardado {SALIDA}: {len(features)} geometrías, "
          f"{tot_rell} saltos rellenados, {tot_mant} mantenidos.")
    print("Siguiente paso: python -X utf8 scripts/seed_lineas_osm.py")


if __name__ == "__main__":
    main()
