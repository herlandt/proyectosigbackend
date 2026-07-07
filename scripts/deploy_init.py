"""
deploy_init.py
--------------
Inicialización de datos que corre en CADA deploy de Render, DESPUÉS de
`alembic upgrade head` y ANTES de arrancar uvicorn (ver render.yaml).

Deja la base en su estado "fijo" y reproducible:
  1. seed_lineas_osm  -> líneas reales + paradas + grafo (idempotente: borra lo
     que generó antes y lo rehace, así no duplica en redeploys sucesivos).
  2. recalibrar_velocidades --heuristica -> tiempos por anillos (el seed deja
     25 km/h uniforme; esto lo ajusta).

Es BEST-EFFORT: si algo falla (p. ej. la BD tarda en aceptar conexiones), se
loguea el error pero NO se aborta, para que la API arranque igual. Las
migraciones sí son obligatorias y se corren aparte, con && en el startCommand.
"""
import os
import runpy
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(BASE_DIR, "scripts")


def _esperar_bd(intentos=10, espera=3):
    """La BD de Render puede tardar unos segundos en aceptar conexiones tras el
    build. Reintenta un SELECT 1 antes de sembrar."""
    import psycopg2
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("[deploy_init] SIN DATABASE_URL — no se puede sembrar.", flush=True)
        return False
    for i in range(1, intentos + 1):
        try:
            conn = psycopg2.connect(url, connect_timeout=5)
            conn.close()
            return True
        except Exception as e:  # noqa: BLE001
            print(f"[deploy_init] BD no lista (intento {i}/{intentos}): {e}", flush=True)
            time.sleep(espera)
    return False


def _correr(nombre_script, argv):
    """Ejecuta scripts/<nombre_script> como si fuera __main__, con sus args."""
    ruta = os.path.join(SCRIPTS, nombre_script)
    argv_previo = sys.argv
    try:
        sys.argv = [ruta, *argv]
        print(f"[deploy_init] -> {nombre_script} {' '.join(argv)}", flush=True)
        runpy.run_path(ruta, run_name="__main__")
        print(f"[deploy_init] OK {nombre_script}", flush=True)
        return True
    except SystemExit as e:  # los scripts pueden llamar sys.exit
        if e.code in (None, 0):
            print(f"[deploy_init] OK {nombre_script}", flush=True)
            return True
        print(f"[deploy_init] {nombre_script} terminó con código {e.code}", flush=True)
        return False
    except Exception as e:  # noqa: BLE001
        print(f"[deploy_init] ERROR en {nombre_script}: {e}", flush=True)
        return False
    finally:
        sys.argv = argv_previo


def main():
    if not _esperar_bd():
        print("[deploy_init] BD no disponible; se omite el seed (la API arranca igual).",
              flush=True)
        return
    if _correr("seed_lineas_osm.py", []):
        _correr("recalibrar_velocidades.py", ["--heuristica"])
    print("[deploy_init] Inicialización de datos finalizada.", flush=True)


if __name__ == "__main__":
    main()
