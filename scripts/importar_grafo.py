"""
importar_grafo.py
-----------------
Carga el GRAFO de la ruta óptima en las tablas EXISTENTES `paradas` y `red_aristas`
a partir de DatosLineas.xls.

Esquema de destino (el que ya está en la base):
  paradas(id, id_externo, codigo, nombre, ubicacion, created_at)
  red_aristas(id, linea_id, sentido, parada_origen, parada_destino, orden,
              distancia_m, tiempo_seg, geom, created_at)

Como LineasPuntos trae Distancia/Tiempo en 0, los costos se CALCULAN:
- distancia = suma de distancias haversine entre puntos consecutivos del recorrido
  (incluye los puntos intermedios 'N' entre dos paradas).
- tiempo   = distancia / velocidad media (25 km/h).
- geom     = LINESTRING del tramo entre paradas (para dibujarlo si se quiere).

linea_id se resuelve buscando en `lineas` por `numero` (= NombreLinea del .xls),
así que primero hay que correr `importar_red_postgis.py`.

Uso:
    cd Backend
    python -X utf8 scripts/importar_grafo.py --dry-run
    python -X utf8 scripts/importar_grafo.py
"""

import argparse
import math
import os
import sys

import psycopg2
import xlrd
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_XLS = os.path.join(BASE_DIR, "Datos_Lineas", "DatosLineas.xls")
RUTA_ENV = os.path.join(BASE_DIR, ".env")

VEL_MEDIA_KMH = 25.0
VEL_MEDIA_MS = VEL_MEDIA_KMH * 1000.0 / 3600.0


def haversine(lon1, lat1, lon2, lat2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _col(sheet):
    return {str(sheet.cell_value(0, c)).strip(): c for c in range(sheet.ncols)}


def _as_int(v):
    return int(round(float(v))) if v not in (None, "") else None


def leer_xls(ruta):
    book = xlrd.open_workbook(ruta)

    sp = book.sheet_by_name("Puntos")
    cp = _col(sp)
    puntos = {}  # idp -> (lon, lat, stop, descripcion)
    for r in range(1, sp.nrows):
        idp = _as_int(sp.cell_value(r, cp["IdPunto"]))
        puntos[idp] = (
            float(sp.cell_value(r, cp["Longitud"])),
            float(sp.cell_value(r, cp["Latitud"])),
            str(sp.cell_value(r, cp["Stop"])).strip(),
            str(sp.cell_value(r, cp["Descripcion"])).strip(),
        )

    slp = book.sheet_by_name("LineasPuntos")
    clp = _col(slp)
    secuencias = {}
    for r in range(1, slp.nrows):
        idlr = _as_int(slp.cell_value(r, clp["IdLineaRuta"]))
        idp = _as_int(slp.cell_value(r, clp["IdPunto"]))
        orden = float(slp.cell_value(r, clp["Orden"]))
        secuencias.setdefault(idlr, []).append((orden, idp))

    slr = book.sheet_by_name("LineaRuta")
    cr = _col(slr)
    ruta_meta = {}
    for r in range(1, slr.nrows):
        idlr = _as_int(slr.cell_value(r, cr["IdLineaRuta"]))
        idlinea = _as_int(slr.cell_value(r, cr["IdLinea"]))
        idruta = _as_int(slr.cell_value(r, cr["IdRuta"]))
        ruta_meta[idlr] = (idlinea, "ida" if idruta == 1 else "vuelta")

    sl = book.sheet_by_name("Lineas")
    cl = _col(sl)
    nombres = {}
    for r in range(1, sl.nrows):
        idlinea = _as_int(sl.cell_value(r, cl["IdLinea"]))
        nombres[idlinea] = str(sl.cell_value(r, cl["NombreLinea"])).strip()

    return puntos, secuencias, ruta_meta, nombres


def construir_grafo(puntos, secuencias, ruta_meta, nombres):
    """paradas: idp -> (lon, lat, codigo). aristas: lista de dicts con el tramo."""
    paradas = {}
    aristas = []

    for idlr, seq in secuencias.items():
        idlinea, sentido = ruta_meta.get(idlr, (None, None))
        numero = nombres.get(idlinea)
        if numero is None:
            continue

        seq_ord = sorted(seq, key=lambda t: t[0])
        ult = None
        acc = 0.0
        path = []
        prev = None
        orden = 0
        for _o, idp in seq_ord:
            if idp not in puntos:
                continue
            lon, lat, stop, desc = puntos[idp]
            if prev is not None:
                acc += haversine(prev[0], prev[1], lon, lat)
            prev = (lon, lat)
            path.append((lon, lat))
            if stop == "S":
                paradas[idp] = (lon, lat, desc)
                if ult is not None and idp != ult and len(path) >= 2:
                    orden += 1
                    aristas.append({
                        "origen": ult,
                        "destino": idp,
                        "numero": numero,
                        "sentido": sentido,
                        "distancia": acc,
                        "tiempo": acc / VEL_MEDIA_MS if VEL_MEDIA_MS else 0.0,
                        "orden": orden,
                        "path": list(path),
                    })
                ult = idp
                acc = 0.0
                path = [(lon, lat)]

    return paradas, aristas


def _wkt_linestring(path):
    # Quita puntos consecutivos repetidos
    limpio = []
    for p in path:
        if not limpio or limpio[-1] != p:
            limpio.append(p)
    if len(limpio) < 2:
        return None
    cuerpo = ", ".join(f"{lon} {lat}" for lon, lat in limpio)
    return f"SRID=4326;LINESTRING({cuerpo})"


def cargar_bd(paradas, aristas):
    load_dotenv(RUTA_ENV)
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(f"ERROR: falta DATABASE_URL (revisá {RUTA_ENV})")
    conn = psycopg2.connect(url)
    cur = conn.cursor()

    # linea numero -> uuid
    cur.execute("SELECT numero, id FROM lineas")
    linea_id_de = {fila[0]: fila[1] for fila in cur.fetchall()}

    faltantes = {a["numero"] for a in aristas if a["numero"] not in linea_id_de}
    if faltantes:
        conn.close()
        sys.exit(f"ERROR: estas líneas no están en la tabla 'lineas' "
                 f"(corré importar_red_postgis.py primero): {sorted(faltantes)}")

    # El grafo es derivado: se regenera completo.
    cur.execute("TRUNCATE red_aristas, red_transbordos, paradas RESTART IDENTITY CASCADE")

    # Paradas
    for idp, (lon, lat, codigo) in paradas.items():
        cur.execute(
            """
            INSERT INTO paradas (id_externo, codigo, nombre, ubicacion)
            VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            """,
            (idp, codigo, codigo, lon, lat),
        )

    cur.execute("SELECT id_externo, id FROM paradas")
    parada_id_de = {fila[0]: fila[1] for fila in cur.fetchall()}

    # Aristas
    for a in aristas:
        cur.execute(
            """
            INSERT INTO red_aristas
                (linea_id, sentido, parada_origen, parada_destino, orden,
                 distancia_m, tiempo_seg, geom)
            VALUES (%s, %s::sentido_enum, %s, %s, %s, %s, %s, ST_GeomFromEWKT(%s))
            """,
            (
                linea_id_de[a["numero"]],
                a["sentido"],
                parada_id_de[a["origen"]],
                parada_id_de[a["destino"]],
                a["orden"],
                round(a["distancia"], 2),
                round(a["tiempo"], 2),
                _wkt_linestring(a["path"]),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--xls", default=RUTA_XLS)
    args = parser.parse_args()

    print(f"Leyendo {args.xls} ...")
    puntos, secuencias, ruta_meta, nombres = leer_xls(args.xls)
    paradas, aristas = construir_grafo(puntos, secuencias, ruta_meta, nombres)

    total_m = sum(a["distancia"] for a in aristas)
    print("\nGrafo construido:")
    print(f"  Paradas (nodos):  {len(paradas)}")
    print(f"  Aristas (tramos): {len(aristas)}")
    print(f"  Distancia total:  {total_m / 1000:.1f} km")

    if args.dry_run:
        print("\n[--dry-run] No se escribió en la base de datos.")
        return

    print("\nCargando a PostgreSQL (DATABASE_URL del .env) ...")
    cargar_bd(paradas, aristas)
    print(f"  OK: {len(paradas)} paradas y {len(aristas)} aristas cargadas.")


if __name__ == "__main__":
    main()
