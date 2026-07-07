"""
importar_red_postgis.py
-----------------------
Carga las líneas de microbús a la tabla `lineas` de PostgreSQL/PostGIS
LEYENDO DIRECTAMENTE el archivo DatosLineas.xls (datos del ingeniero).

Este script reemplaza al inexistente "importar_red_postgis.py" que mencionaban
las guías y resuelve la incompatibilidad con importar_arcgis.py:
  - importar_arcgis.py espera DOS shapefiles (ida/vuelta) con campo NUMERO.
  - La guía armar_red produce UN solo rutas.shp (campo NombreLinea, IdRuta 1/2).
Aquí no hace falta pasar por ArcGIS: armamos las geometrías LINESTRING
directamente desde las hojas del Excel, que ya están verificadas y limpias.

Cómo arma cada recorrido:
  hoja Puntos       -> IdPunto = (Longitud, Latitud)   [WGS84 / EPSG:4326]
  hoja LineasPuntos -> para cada IdLineaRuta, la secuencia ordenada de IdPunto (campo Orden)
  hoja LineaRuta    -> IdLineaRuta -> (IdLinea, IdRuta)   (IdRuta 1=ida, 2=vuelta)
  hoja Lineas       -> IdLinea -> NombreLinea (ej. "L001")  ->  lineas.numero

Requisitos (ya presentes en el venv del backend):
    pip install xlrd psycopg2-binary python-dotenv

Uso:
    cd Backend
    python -X utf8 scripts/importar_red_postgis.py
    python -X utf8 scripts/importar_red_postgis.py --dry-run   # no escribe en BD, solo valida

La conexión se toma de DATABASE_URL (Backend/.env) — NO hay credenciales en duro.
"""

import os
import sys
import argparse

import xlrd
import psycopg2
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────
# Rutas (relativas a la carpeta Backend/)
# ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../Backend
RUTA_XLS = os.path.join(BASE_DIR, "Datos_Lineas", "DatosLineas.xls")
RUTA_ENV = os.path.join(BASE_DIR, ".env")

# Valores de IdRuta en la hoja LineaRuta
ID_RUTA_IDA = 1
ID_RUTA_VUELTA = 2


def _col(sheet):
    """Devuelve {nombre_columna: indice} a partir de la fila de encabezados."""
    return {str(sheet.cell_value(0, c)).strip(): c for c in range(sheet.ncols)}


def _as_int(v):
    """Convierte una celda Excel (float) a int de forma segura."""
    if v is None or v == "":
        return None
    return int(round(float(v)))


def leer_xls(ruta):
    """Lee las 4 hojas y devuelve las estructuras necesarias para armar las líneas."""
    book = xlrd.open_workbook(ruta)

    # --- Puntos: IdPunto -> (lon, lat) ---
    sp = book.sheet_by_name("Puntos")
    cp = _col(sp)
    puntos = {}
    for r in range(1, sp.nrows):
        idp = _as_int(sp.cell_value(r, cp["IdPunto"]))
        lon = float(sp.cell_value(r, cp["Longitud"]))
        lat = float(sp.cell_value(r, cp["Latitud"]))
        puntos[idp] = (lon, lat)

    # --- LineasPuntos: IdLineaRuta -> [(Orden, IdPunto), ...] ---
    slp = book.sheet_by_name("LineasPuntos")
    clp = _col(slp)
    secuencias = {}
    for r in range(1, slp.nrows):
        idlr = _as_int(slp.cell_value(r, clp["IdLineaRuta"]))
        idp = _as_int(slp.cell_value(r, clp["IdPunto"]))
        orden = float(slp.cell_value(r, clp["Orden"]))
        secuencias.setdefault(idlr, []).append((orden, idp))

    # --- LineaRuta: IdLineaRuta -> (IdLinea, IdRuta) ---
    slr = book.sheet_by_name("LineaRuta")
    cr = _col(slr)
    ruta_meta = {}
    for r in range(1, slr.nrows):
        idlr = _as_int(slr.cell_value(r, cr["IdLineaRuta"]))
        idlinea = _as_int(slr.cell_value(r, cr["IdLinea"]))
        idruta = _as_int(slr.cell_value(r, cr["IdRuta"]))
        ruta_meta[idlr] = (idlinea, idruta)

    # --- Lineas: IdLinea -> NombreLinea ---
    sl = book.sheet_by_name("Lineas")
    cl = _col(sl)
    nombres = {}
    for r in range(1, sl.nrows):
        idlinea = _as_int(sl.cell_value(r, cl["IdLinea"]))
        nombres[idlinea] = str(sl.cell_value(r, cl["NombreLinea"])).strip()

    return puntos, secuencias, ruta_meta, nombres


def construir_wkt(idlr, secuencias, puntos):
    """Arma un WKT LINESTRING(lon lat, ...) para una ruta, ordenado por Orden."""
    seq = sorted(secuencias.get(idlr, []), key=lambda t: t[0])
    coords = []
    ult = None
    for _orden, idp in seq:
        if idp not in puntos:
            continue
        c = puntos[idp]
        if c != ult:          # evita vértices duplicados consecutivos (geometría inválida)
            coords.append(c)
            ult = c
    if len(coords) < 2:
        return None, len(coords)
    cuerpo = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    return f"SRID=4326;LINESTRING({cuerpo})", len(coords)


def agrupar_lineas(secuencias, ruta_meta, nombres, puntos):
    """Devuelve [(numero, nombre, wkt_ida, wkt_vuelta), ...] listo para insertar."""
    # IdLinea -> {'ida': idlr, 'vuelta': idlr}
    por_linea = {}
    for idlr, (idlinea, idruta) in ruta_meta.items():
        d = por_linea.setdefault(idlinea, {})
        if idruta == ID_RUTA_IDA:
            d["ida"] = idlr
        elif idruta == ID_RUTA_VUELTA:
            d["vuelta"] = idlr

    resultado = []
    for idlinea in sorted(por_linea):
        numero = nombres.get(idlinea, f"L{idlinea:03d}")
        d = por_linea[idlinea]
        if "ida" not in d or "vuelta" not in d:
            print(f"  OMITIDA {numero}: falta ida o vuelta")
            continue
        wkt_ida, n_ida = construir_wkt(d["ida"], secuencias, puntos)
        wkt_vuelta, n_vuelta = construir_wkt(d["vuelta"], secuencias, puntos)
        if not wkt_ida or not wkt_vuelta:
            print(f"  OMITIDA {numero}: geometría insuficiente (ida={n_ida}, vuelta={n_vuelta} pts)")
            continue
        resultado.append((numero, f"Línea {numero}", wkt_ida, wkt_vuelta, n_ida, n_vuelta))
    return resultado


def obtener_database_url():
    load_dotenv(RUTA_ENV)
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(f"ERROR: no se encontró DATABASE_URL (ni en entorno ni en {RUTA_ENV})")
    return url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Valida y arma las geometrías sin escribir en la base de datos")
    parser.add_argument("--xls", default=RUTA_XLS, help="Ruta a DatosLineas.xls")
    args = parser.parse_args()

    print(f"Leyendo {args.xls} ...")
    puntos, secuencias, ruta_meta, nombres = leer_xls(args.xls)
    print(f"  Puntos: {len(puntos)} | Rutas: {len(ruta_meta)} | Líneas: {len(nombres)}")

    lineas = agrupar_lineas(secuencias, ruta_meta, nombres, puntos)
    print(f"\nLíneas listas para cargar: {len(lineas)}")
    for numero, _nombre, _i, _v, n_ida, n_vuelta in lineas:
        print(f"  {numero}: ida={n_ida} vértices, vuelta={n_vuelta} vértices")

    if args.dry_run:
        print("\n[--dry-run] No se escribió en la base de datos.")
        return

    print("\nConectando a PostgreSQL (DATABASE_URL del .env) ...")
    conn = psycopg2.connect(obtener_database_url())
    cur = conn.cursor()

    insertadas = 0
    for numero, nombre, wkt_ida, wkt_vuelta, _ni, _nv in lineas:
        cur.execute(
            """
            INSERT INTO lineas (numero, nombre, recorrido_ida, recorrido_vuelta, activa)
            VALUES (%s, %s, ST_GeomFromEWKT(%s), ST_GeomFromEWKT(%s), TRUE)
            ON CONFLICT (numero) DO UPDATE SET
                nombre           = EXCLUDED.nombre,
                recorrido_ida    = EXCLUDED.recorrido_ida,
                recorrido_vuelta = EXCLUDED.recorrido_vuelta,
                updated_at       = NOW()
            """,
            (numero, nombre, wkt_ida, wkt_vuelta),
        )
        print(f"  OK  {numero} — {nombre}")
        insertadas += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n{'─' * 40}")
    print(f"  Insertadas/actualizadas: {insertadas}")
    print(f"{'─' * 40}")
    print("Verificá con:  GET http://localhost:8000/lineas")


if __name__ == "__main__":
    main()
