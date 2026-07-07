"""
seed_lineas_osm.py
------------------
SEEDER de líneas reales de Santa Cruz a partir de OpenStreetMap. Por cada línea
deja la información COMPLETA en la base de datos:

  1. lineas        : recorrido_ida / recorrido_vuelta (geometría real de OSM)
  2. paradas       : generadas cada ESPACIADO_M metros sobre el recorrido real
  3. red_aristas   : tramos parada→parada (grafo para la ruta óptima)
  4. red_transbordos: conexiones a pie entre paradas generadas cercanas

Es IDEMPOTENTE: se puede re-ejecutar (borra lo que generó antes y lo rehace).
NO toca las líneas académicas L001…L018 ni sus paradas reales (id_externo < OFFSET).

Datos de entrada:
  - Datos_OSM/rutas_micros_scz_osm.geojson   (recorridos)
  - Datos_OSM/catalogo_lineas_scz.csv         (nombre / origen-destino)
  - Datos_OSM/colores_lineas.json             (color por línea, opcional)

Uso:
  cd Backend
  python -X utf8 scripts/seed_lineas_osm.py --dry-run   # valida sin escribir
  python -X utf8 scripts/seed_lineas_osm.py             # carga a la BD
"""
import argparse
import csv
import json
import math
import os
import sys

import psycopg2
from dotenv import load_dotenv
from shapely.geometry import LineString
from shapely.ops import linemerge

# ── Configuración ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROYECTO = os.path.dirname(BASE_DIR)
RUTA_ENV = os.path.join(BASE_DIR, ".env")
DIR_OSM = os.path.join(PROYECTO, "Datos_OSM")
GEOJSON = os.path.join(DIR_OSM, "rutas_micros_scz_osm.geojson")
CATALOGO = os.path.join(DIR_OSM, "catalogo_lineas_scz.csv")
COLORES = os.path.join(DIR_OSM, "colores_lineas.json")
# Vueltas reales calculadas con OSRM (scripts/generar_vueltas_osrm.py) para las
# líneas donde OSM no trae el sentido de retorno; reemplazan al reversed(ida).
VUELTAS_OSRM = os.path.join(DIR_OSM, "vueltas_osrm.geojson")

ESPACIADO_M = 400.0          # distancia entre paradas generadas
VEL_MEDIA_MS = 25 * 1000 / 3600.0   # 25 km/h
VEL_CAMINATA_MS = 1.389      # ~5 km/h
RADIO_TRANSBORDO_M = 120     # paradas a pie si están a < 120 m
ID_EXTERNO_OFFSET = 100000   # marca las paradas generadas (las reales son < 100000)


def haversine(lon1, lat1, lon2, lat2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cargar_catalogo():
    info = {}
    if os.path.exists(CATALOGO):
        for row in csv.DictReader(open(CATALOGO, encoding="utf-8-sig")):
            info[str(row["numero"]).strip()] = row
    return info


def cargar_colores():
    return json.load(open(COLORES, encoding="utf-8")) if os.path.exists(COLORES) else {}


def _limpiar_texto(s):
    """Reemplaza glifos que se ven mal en el dispositivo (flecha, º, ·, guiones largos) por ASCII."""
    s = (s or "").strip()
    for a, b in [("→", "-"), ("º", "o"), ("°", "o"),
                 ("·", "-"), ("–", "-"), ("—", "-")]:
        s = s.replace(a, b)
    return s.strip()


def recorridos_por_ref():
    """Agrupa las features del GeoJSON por número de línea y devuelve, por ref,
    una lista de componentes (LineStrings) ordenadas de mayor a menor longitud."""
    data = json.load(open(GEOJSON, encoding="utf-8"))
    partes = {}
    for f in data["features"]:
        ref = (f["properties"].get("ref") or "").strip()
        if not ref:
            continue
        geom = f["geometry"]
        coords_sets = (geom["coordinates"] if geom["type"] == "MultiLineString"
                       else [geom["coordinates"]])
        for cs in coords_sets:
            if len(cs) >= 2:
                partes.setdefault(ref, []).append([(c[0], c[1]) for c in cs])

    rutas = {}
    for ref, lista in partes.items():
        lines = [LineString(p) for p in lista if len(p) >= 2]
        if not lines:
            continue
        merged = linemerge(lines) if len(lines) > 1 else lines[0]
        comps = ([merged] if merged.geom_type == "LineString"
                 else sorted(list(merged.geoms), key=lambda g: g.length, reverse=True))
        rutas[ref] = [list(c.coords) for c in comps]
    return rutas


def ida_vuelta(comps):
    """ida = componente más largo. vuelta = 2º componente SOLO si es razonablemente
    completo (>= 50% del largo de ida); si no, se usa el ida invertido."""
    ida = comps[0]
    if len(comps) >= 2 and LineString(comps[1]).length >= 0.5 * LineString(ida).length:
        vuelta = comps[1]
    else:
        vuelta = list(reversed(ida))
    return ida, vuelta


def cargar_vueltas_osrm():
    """Vueltas reales por ref (override del reversed(ida)), si el archivo existe."""
    if not os.path.exists(VUELTAS_OSRM):
        return {}
    gj = json.load(open(VUELTAS_OSRM, encoding="utf-8"))
    return {f["properties"]["ref"]: [(c[0], c[1]) for c in f["geometry"]["coordinates"]]
            for f in gj.get("features", [])
            if f.get("geometry", {}).get("type") == "LineString"}


def wkt_line(coords):
    limpio = []
    for c in coords:
        if not limpio or limpio[-1] != c:
            limpio.append(c)
    if len(limpio) < 2:
        return None
    return "SRID=4326;LINESTRING(" + ", ".join(f"{lon} {lat}" for lon, lat in limpio) + ")"


def generar_paradas_tramos(coords):
    """Coloca paradas cada ESPACIADO_M metros sobre la línea.
    Devuelve (paradas[(lon,lat)], tramos[{path, dist}])."""
    if len(coords) < 2:
        return [], []
    paradas = [coords[0]]
    tramos = []
    cur = [coords[0]]
    acc = 0.0
    objetivo = ESPACIADO_M
    for i in range(1, len(coords)):
        a, b = coords[i - 1], coords[i]
        seg = haversine(a[0], a[1], b[0], b[1])
        while seg > 0 and acc + seg >= objetivo:
            t = (objetivo - acc) / seg
            px = a[0] + (b[0] - a[0]) * t
            py = a[1] + (b[1] - a[1]) * t
            cur.append((px, py))
            paradas.append((px, py))
            tramos.append({"path": cur, "dist": _largo(cur)})
            cur = [(px, py)]
            a = (px, py)
            seg = haversine(a[0], a[1], b[0], b[1])
            acc = objetivo
            objetivo += ESPACIADO_M
        acc += seg
        cur.append(b)
    if len(cur) >= 2 and _largo(cur) > ESPACIADO_M * 0.3:
        paradas.append(coords[-1])
        tramos.append({"path": cur, "dist": _largo(cur)})
    return paradas, tramos


def _largo(path):
    return sum(haversine(path[i - 1][0], path[i - 1][1], path[i][0], path[i][1])
               for i in range(1, len(path)))


def main():
    global ESPACIADO_M
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--espaciado", type=float, default=ESPACIADO_M)
    args = ap.parse_args()
    ESPACIADO_M = args.espaciado

    rutas = recorridos_por_ref()
    catalogo = cargar_catalogo()
    colores = cargar_colores()
    vueltas_osrm = cargar_vueltas_osrm()
    print(f"Líneas con recorrido en OSM: {len(rutas)}"
          + (f" | vueltas OSRM: {len(vueltas_osrm)}" if vueltas_osrm else ""))

    # Pre-cálculo (en memoria) para validar/estadísticas
    plan = []
    for ref in sorted(rutas, key=lambda r: (len(r), r)):
        ida, vuelta = ida_vuelta(rutas[ref])
        if ref in vueltas_osrm and vuelta == list(reversed(ida)):
            vuelta = vueltas_osrm[ref]  # vuelta real por calles legales
        wi, wv = wkt_line(ida), wkt_line(vuelta)
        if not wi or not wv:
            print(f"  OMITIDA {ref}: geometría insuficiente")
            continue
        p_ida, t_ida = generar_paradas_tramos(ida)
        p_vue, t_vue = generar_paradas_tramos(vuelta)
        cat = catalogo.get(ref, {})
        origen = _limpiar_texto(cat.get("origen", ""))
        destino = _limpiar_texto(cat.get("destino", ""))
        nombre = f"Linea {ref}"
        if origen and destino:
            desc = f"{origen} - {destino}"
        else:
            desc = origen or destino or "Recorrido OSM"
        plan.append({"ref": ref, "nombre": nombre, "desc": desc, "wi": wi, "wv": wv,
                     "p_ida": p_ida, "t_ida": t_ida, "p_vue": p_vue, "t_vue": t_vue})

    tot_par = sum(len(x["p_ida"]) + len(x["p_vue"]) for x in plan)
    tot_tra = sum(len(x["t_ida"]) + len(x["t_vue"]) for x in plan)
    print(f"Plan: {len(plan)} líneas | {tot_par} paradas generadas | {tot_tra} tramos")
    for x in plan[:6]:
        print(f"  {x['ref']:>4}: ida {len(x['p_ida'])} paradas / vuelta {len(x['p_vue'])} — {x['desc'][:50]}")

    if args.dry_run:
        print("\n[--dry-run] No se escribió en la base de datos.")
        return

    load_dotenv(RUTA_ENV)
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(f"ERROR: falta DATABASE_URL (revisá {RUTA_ENV})")
    conn = psycopg2.connect(url)
    cur = conn.cursor()

    # Idempotencia: borrar lo generado antes (cascada elimina sus aristas/transbordos)
    cur.execute("DELETE FROM paradas WHERE id_externo >= %s", (ID_EXTERNO_OFFSET,))

    contador_ext = ID_EXTERNO_OFFSET
    n_par = n_ari = 0
    for x in plan:
        # 1) Línea (upsert por numero)
        cur.execute(
            """
            INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta, activa)
            VALUES (%s, %s, %s, ST_GeomFromEWKT(%s), ST_GeomFromEWKT(%s), TRUE)
            ON CONFLICT (numero) DO UPDATE SET
                nombre = EXCLUDED.nombre, descripcion = EXCLUDED.descripcion,
                recorrido_ida = EXCLUDED.recorrido_ida,
                recorrido_vuelta = EXCLUDED.recorrido_vuelta, updated_at = NOW()
            RETURNING id
            """,
            (x["ref"], x["nombre"], x["desc"], x["wi"], x["wv"]),
        )
        linea_id = cur.fetchone()[0]

        for sentido, paradas, tramos in (("ida", x["p_ida"], x["t_ida"]),
                                         ("vuelta", x["p_vue"], x["t_vue"])):
            ids = []
            for j, (lon, lat) in enumerate(paradas):
                contador_ext += 1
                cur.execute(
                    """
                    INSERT INTO paradas (id_externo, codigo, nombre, ubicacion)
                    VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                    RETURNING id
                    """,
                    (contador_ext, f"L{x['ref']}-{sentido[0]}{j}",
                     f"Línea {x['ref']} ({sentido}) parada {j}", lon, lat),
                )
                ids.append(cur.fetchone()[0])
                n_par += 1
            for k, tr in enumerate(tramos):
                if k + 1 >= len(ids):
                    break
                dist = tr["dist"]
                cur.execute(
                    """
                    INSERT INTO red_aristas
                        (linea_id, sentido, parada_origen, parada_destino, orden,
                         distancia_m, tiempo_seg, geom)
                    VALUES (%s, %s::sentido_enum, %s, %s, %s, %s, %s, ST_GeomFromEWKT(%s))
                    """,
                    (linea_id, sentido, ids[k], ids[k + 1], k + 1,
                     round(dist, 2), round(dist / VEL_MEDIA_MS, 2), wkt_line(tr["path"])),
                )
                n_ari += 1

    # 4) Transbordos a pie entre paradas generadas cercanas (en ambos sentidos)
    cur.execute(
        """
        INSERT INTO red_transbordos (parada_origen, parada_destino, distancia_m, tiempo_seg)
        SELECT a.id, b.id, d.dist, d.dist / %s
        FROM paradas a
        JOIN LATERAL (
            SELECT b.id, ST_Distance(a.ubicacion::geography, b.ubicacion::geography) AS dist
            FROM paradas b
            WHERE b.id <> a.id AND b.id_externo >= %s
              AND ST_DWithin(a.ubicacion::geography, b.ubicacion::geography, %s)
        ) b ON TRUE
        CROSS JOIN LATERAL (SELECT b.dist AS dist) d
        WHERE a.id_externo >= %s
        """,
        (VEL_CAMINATA_MS, ID_EXTERNO_OFFSET, RADIO_TRANSBORDO_M, ID_EXTERNO_OFFSET),
    )
    n_trans = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n{'─'*48}")
    print(f"  Líneas cargadas:        {len(plan)}")
    print(f"  Paradas generadas:      {n_par}")
    print(f"  Tramos (red_aristas):   {n_ari}")
    print(f"  Transbordos a pie:      {n_trans}")
    print(f"{'─'*48}")
    print("OJO: los tiempos quedaron a 25 km/h uniforme. Recalibrar con:")
    print("  python -X utf8 scripts/recalibrar_velocidades.py --heuristica")
    print("  (o sin flag, si ya hay telemetría real acumulada)")


if __name__ == "__main__":
    main()
