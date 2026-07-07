"""
recalibrar_velocidades.py
-------------------------
Recalibra los tiempos del grafo de ruta óptima (`red_aristas.tiempo_seg`).
El seeder los carga con 25 km/h uniforme; este script los reemplaza por
velocidades más realistas. Tres modos:

  telemetria (default) : velocidad MEDIANA observada por línea+sentido en la
      telemetría real (solo fixes en movimiento >= 5 km/h, con buena precisión
      GPS y en ruta). Necesita --min-puntos por grupo; si un sentido no llega,
      cae al agregado de la línea; si tampoco, no se toca.
  --heuristica         : sin datos aún — anillos alrededor de la plaza
      24 de Septiembre: < 2 km => 15 km/h (casco viejo), < 5 km => 20 km/h,
      resto => 25 km/h. Puente hasta acumular telemetría.
  --uniforme KMH       : vuelve todo a una velocidad fija (deshacer).

Solo toca líneas reales (numero NOT LIKE 'L%'), que son las que usa la ruta
óptima. OJO: re-ejecutar el seeder vuelve a dejar 25 km/h — correr esto después.

Uso:
  cd Backend
  python -X utf8 scripts/recalibrar_velocidades.py --heuristica --dry-run
  python -X utf8 scripts/recalibrar_velocidades.py --heuristica
  python -X utf8 scripts/recalibrar_velocidades.py                # con telemetría
  python -X utf8 scripts/recalibrar_velocidades.py --uniforme 25  # reset
"""
import argparse
import os
import sys

import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_ENV = os.path.join(BASE_DIR, ".env")

PLAZA = (-63.1812, -17.7838)     # plaza 24 de Septiembre
ANILLOS = [(2000, 15.0), (5000, 20.0)]  # (radio_m, km/h); más lejos: VEL_BORDE
VEL_BORDE = 25.0
VEL_MIN, VEL_MAX = 8.0, 45.0     # clamp de lo que diga la telemetría
MIN_PUNTOS = 30                  # fixes en movimiento para confiar en un grupo


def velocidades_desde_telemetria(cur, min_puntos=MIN_PUNTOS):
    """Mediana de velocidad observada. Devuelve {(numero, sentido): kmh} usando
    línea+sentido cuando hay datos suficientes, o el agregado de la línea."""
    cur.execute("""
        SELECT l.numero, r.sentido::text,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY t.velocidad) AS mediana,
               count(*) AS n
        FROM telemetria t
        JOIN recorridos r ON r.id = t.recorrido_id
        JOIN lineas l     ON l.id = r.linea_id
        WHERE t.velocidad >= 5                                  -- en movimiento
          AND (t.precision_m   IS NULL OR t.precision_m   <= 35) -- fix confiable
          AND (t.desvio_ruta_m IS NULL OR t.desvio_ruta_m <= 100) -- en ruta
          AND l.numero NOT LIKE 'L%%'
        GROUP BY l.numero, r.sentido
    """)
    por_sentido = {}
    por_linea = {}   # numero -> [suma_ponderada, n_total]
    for numero, sentido, mediana, n in cur.fetchall():
        por_sentido[(numero, sentido)] = (float(mediana), int(n))
        acc = por_linea.setdefault(numero, [0.0, 0])
        acc[0] += float(mediana) * int(n)
        acc[1] += int(n)

    velocidades = {}
    for (numero, sentido), (mediana, n) in por_sentido.items():
        if n >= min_puntos:
            vel = mediana
        elif por_linea[numero][1] >= min_puntos:
            vel = por_linea[numero][0] / por_linea[numero][1]
        else:
            continue  # datos insuficientes: no tocar
        velocidades[(numero, sentido)] = min(VEL_MAX, max(VEL_MIN, vel))
    return velocidades


def aplicar_telemetria(cur, min_puntos, dry_run):
    velocidades = velocidades_desde_telemetria(cur, min_puntos)
    if not velocidades:
        print(f"Sin grupos con >= {min_puntos} fixes en movimiento: no se cambió nada.")
        print("(Acumulá recorridos reales con la app y volvé a correr esto.)")
        return
    print(f"{len(velocidades)} grupos línea+sentido con datos suficientes:")
    for (numero, sentido), vel in sorted(velocidades.items()):
        print(f"  línea {numero:>4} {sentido:<6} -> {vel:.1f} km/h")
        if not dry_run:
            cur.execute("""
                UPDATE red_aristas a
                SET tiempo_seg = round((a.distancia_m / (%s / 3.6))::numeric, 2)
                FROM lineas l
                WHERE l.id = a.linea_id AND l.numero = %s AND a.sentido::text = %s
            """, (vel, numero, sentido))


def aplicar_heuristica(cur, dry_run):
    # La expresión de distancia va inline en el CASE: el FROM de un UPDATE no
    # puede tener un LATERAL que referencie a la tabla que se actualiza.
    dist = (f"ST_Distance(ST_Centroid(a.geom)::geography, "
            f"ST_SetSRID(ST_MakePoint({PLAZA[0]}, {PLAZA[1]}), 4326)::geography)")
    casos = " ".join(f"WHEN {dist} < {radio} THEN {kmh}" for radio, kmh in ANILLOS)
    if dry_run:
        cur.execute(f"""
            SELECT CASE {casos} ELSE {VEL_BORDE} END AS kmh, count(*)
            FROM red_aristas a
            JOIN lineas l ON l.id = a.linea_id
            WHERE l.numero NOT LIKE 'L%%'
            GROUP BY 1 ORDER BY 1
        """)
        for kmh, n in cur.fetchall():
            print(f"  {n:>5} aristas quedarían a {kmh:.0f} km/h")
        return
    cur.execute(f"""
        UPDATE red_aristas a
        SET tiempo_seg = round((a.distancia_m /
            ((CASE {casos} ELSE {VEL_BORDE} END) / 3.6))::numeric, 2)
        FROM lineas l
        WHERE l.id = a.linea_id AND l.numero NOT LIKE 'L%%'
    """)
    print(f"  {cur.rowcount} aristas recalibradas por anillos "
          f"({', '.join(f'<{r}m={k:.0f}' for r, k in ANILLOS)}, resto={VEL_BORDE:.0f} km/h)")


def aplicar_uniforme(cur, kmh, dry_run):
    if dry_run:
        cur.execute("""
            SELECT count(*) FROM red_aristas a JOIN lineas l ON l.id = a.linea_id
            WHERE l.numero NOT LIKE 'L%%'
        """)
        print(f"  {cur.fetchone()[0]} aristas quedarían a {kmh} km/h")
        return
    cur.execute("""
        UPDATE red_aristas a
        SET tiempo_seg = round((a.distancia_m / (%s / 3.6))::numeric, 2)
        FROM lineas l
        WHERE l.id = a.linea_id AND l.numero NOT LIKE 'L%%'
    """, (kmh,))
    print(f"  {cur.rowcount} aristas a {kmh} km/h uniforme")


def main():
    ap = argparse.ArgumentParser()
    modo = ap.add_mutually_exclusive_group()
    modo.add_argument("--heuristica", action="store_true")
    modo.add_argument("--uniforme", type=float, metavar="KMH")
    ap.add_argument("--min-puntos", type=int, default=MIN_PUNTOS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_dotenv(RUTA_ENV)
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(f"ERROR: falta DATABASE_URL (revisá {RUTA_ENV})")
    conn = psycopg2.connect(url)
    cur = conn.cursor()

    if args.uniforme:
        aplicar_uniforme(cur, args.uniforme, args.dry_run)
    elif args.heuristica:
        aplicar_heuristica(cur, args.dry_run)
    else:
        aplicar_telemetria(cur, args.min_puntos, args.dry_run)

    if args.dry_run:
        conn.rollback()
        print("[--dry-run] No se escribió en la base de datos.")
    else:
        conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
