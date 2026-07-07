"""
importar_arcgis.py
------------------
Importa rutas de líneas de microbús desde un archivo ArcGIS (.shp o .gdb)
a la tabla `lineas` de PostgreSQL/PostGIS.

Requisitos (instalar solo para este script, no para la API):
    pip install geopandas fiona shapely

Uso:
    python scripts/importar_arcgis.py

Antes de correr, ajusta la sección CONFIGURACIÓN más abajo.
"""

import os
import sys
import uuid
import psycopg2
import geopandas as gpd
from shapely.geometry import mapping
from dotenv import load_dotenv
import json

# ─────────────────────────────────────────────────────────────────
# CONFIGURACIÓN — ajusta estos valores según tu archivo
# ─────────────────────────────────────────────────────────────────

# Ruta al archivo. Puede ser:
#   - Un .shp individual:  r"C:\datos\rutas_ida.shp"
#   - Una .gdb con capas:  r"C:\datos\microbuses.gdb"
ARCHIVO_IDA = r"C:\ruta\al\archivo\rutas_ida.shp"
ARCHIVO_VUELTA = r"C:\ruta\al\archivo\rutas_vuelta.shp"

# Si ambos sentidos están en el MISMO archivo/capa, usa esto en su lugar:
# ARCHIVO_UNICO = r"C:\ruta\al\archivo\rutas.shp"
# CAMPO_SENTIDO = "sentido"      # nombre del campo que dice "ida" / "vuelta"
# VALOR_IDA     = "ida"          # valor exacto que indica sentido ida
# VALOR_VUELTA  = "vuelta"       # valor exacto que indica sentido vuelta

# Si el archivo es .gdb con múltiples capas, especifica el nombre de capa:
# CAPA_IDA    = "RecorridoIda"
# CAPA_VUELTA = "RecorridoVuelta"
# (deja en None si el archivo ya tiene una sola capa)
CAPA_IDA    = None
CAPA_VUELTA = None

# Nombres de los campos en el archivo ArcGIS
# (usa None si el campo no existe o no quieres importarlo)
CAMPO_NUMERO      = "NUMERO"       # número de línea, ej. "21", "105"
CAMPO_NOMBRE      = "NOMBRE"       # nombre largo, ej. "Línea 21 - Norte Sur"
CAMPO_DESCRIPCION = None           # descripción opcional, ej. "DESCRIPCION"

# Conexión a PostgreSQL: se toma de DATABASE_URL en Backend/.env
# (NO escribas credenciales en este archivo).
RUTA_ENV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

# ─────────────────────────────────────────────────────────────────
# FIN DE CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────


def leer_capa(archivo, capa=None):
    """Lee un shapefile o capa de GDB y devuelve un GeoDataFrame en EPSG:4326."""
    kwargs = {"filename": archivo}
    if capa:
        kwargs["layer"] = capa
    gdf = gpd.read_file(**kwargs)
    if gdf.crs is None:
        print(f"  ADVERTENCIA: el archivo no tiene CRS definido. Asumiendo EPSG:4326.")
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        print(f"  Reproyectando de {gdf.crs} a EPSG:4326 ...")
        gdf = gdf.to_crs(epsg=4326)
    return gdf


def geom_a_wkt(geom):
    """Convierte una geometría Shapely a WKT con SRID para PostGIS."""
    if geom is None or geom.is_empty:
        return None
    return f"SRID=4326;{geom.wkt}"


def importar(conn, gdf_ida, gdf_vuelta):
    """
    Inserta las líneas en la tabla `lineas`.

    Empareja ida y vuelta por el valor del campo CAMPO_NUMERO.
    Si una línea solo tiene ida o solo vuelta, la omite con advertencia.
    """
    cur = conn.cursor()

    # Normalizar nombres de columnas a minúsculas
    gdf_ida.columns = [c.lower() for c in gdf_ida.columns]
    gdf_vuelta.columns = [c.lower() for c in gdf_vuelta.columns]

    campo_num = CAMPO_NUMERO.lower()
    campo_nom = CAMPO_NOMBRE.lower()
    campo_desc = CAMPO_DESCRIPCION.lower() if CAMPO_DESCRIPCION else None

    # Construir índice por número de línea
    ida_por_numero = {
        str(row[campo_num]).strip(): row
        for _, row in gdf_ida.iterrows()
        if row[campo_num] is not None
    }
    vuelta_por_numero = {
        str(row[campo_num]).strip(): row
        for _, row in gdf_vuelta.iterrows()
        if row[campo_num] is not None
    }

    todos_los_numeros = set(ida_por_numero) | set(vuelta_por_numero)
    insertadas = 0
    omitidas = 0

    for numero in sorted(todos_los_numeros):
        fila_ida = ida_por_numero.get(numero)
        fila_vuelta = vuelta_por_numero.get(numero)

        if fila_ida is None:
            print(f"  OMITIDA línea {numero}: no tiene recorrido de ida")
            omitidas += 1
            continue
        if fila_vuelta is None:
            print(f"  OMITIDA línea {numero}: no tiene recorrido de vuelta")
            omitidas += 1
            continue

        nombre = str(fila_ida[campo_nom]).strip() if campo_nom in fila_ida.index else f"Línea {numero}"
        descripcion = str(fila_ida[campo_desc]).strip() if campo_desc and campo_desc in fila_ida.index else None

        wkt_ida = geom_a_wkt(fila_ida.geometry)
        wkt_vuelta = geom_a_wkt(fila_vuelta.geometry)

        if wkt_ida is None or wkt_vuelta is None:
            print(f"  OMITIDA línea {numero}: geometría nula o vacía")
            omitidas += 1
            continue

        linea_id = str(uuid.uuid4())

        cur.execute(
            """
            INSERT INTO lineas (id, numero, nombre, descripcion, recorrido_ida, recorrido_vuelta, activa)
            VALUES (
                %s, %s, %s, %s,
                ST_GeomFromEWKT(%s),
                ST_GeomFromEWKT(%s),
                TRUE
            )
            ON CONFLICT (numero) DO UPDATE SET
                nombre        = EXCLUDED.nombre,
                descripcion   = EXCLUDED.descripcion,
                recorrido_ida = EXCLUDED.recorrido_ida,
                recorrido_vuelta = EXCLUDED.recorrido_vuelta,
                updated_at    = NOW()
            """,
            (linea_id, numero, nombre, descripcion, wkt_ida, wkt_vuelta)
        )
        print(f"  OK  línea {numero} — {nombre}")
        insertadas += 1

    conn.commit()
    cur.close()
    return insertadas, omitidas


def inspeccionar(archivo, capa=None):
    """Muestra los campos disponibles en el archivo para ayudar a configurar el script."""
    print(f"\n=== Inspeccionando: {archivo} (capa: {capa or 'primera'}) ===")
    gdf = leer_capa(archivo, capa)
    print(f"  CRS: {gdf.crs}")
    print(f"  Features: {len(gdf)}")
    print(f"  Tipo de geometría: {gdf.geometry.geom_type.unique()}")
    print(f"  Campos disponibles:")
    for col in gdf.columns:
        if col == "geometry":
            continue
        vals = gdf[col].dropna().unique()[:3]
        print(f"    {col:30s} → {list(vals)}")
    print()


def main():
    # Modo inspección: corre primero para ver los campos del archivo
    # Descomenta las siguientes líneas cuando tengas el archivo:
    # inspeccionar(ARCHIVO_IDA, CAPA_IDA)
    # inspeccionar(ARCHIVO_VUELTA, CAPA_VUELTA)
    # return

    print("Leyendo capas ...")
    gdf_ida     = leer_capa(ARCHIVO_IDA, CAPA_IDA)
    gdf_vuelta  = leer_capa(ARCHIVO_VUELTA, CAPA_VUELTA)
    print(f"  Ida:    {len(gdf_ida)} features")
    print(f"  Vuelta: {len(gdf_vuelta)} features")

    print("\nConectando a PostgreSQL (DATABASE_URL del .env) ...")
    load_dotenv(RUTA_ENV)
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit(f"ERROR: falta DATABASE_URL (revisá {RUTA_ENV})")
    conn = psycopg2.connect(database_url)

    print("\nImportando líneas ...")
    insertadas, omitidas = importar(conn, gdf_ida, gdf_vuelta)
    conn.close()

    print(f"\n{'─'*40}")
    print(f"  Insertadas/actualizadas: {insertadas}")
    print(f"  Omitidas:               {omitidas}")
    print(f"{'─'*40}")


if __name__ == "__main__":
    main()
