"""
routing_service.py
------------------
RUTA ÓPTIMA (Dijkstra) sobre la red REAL de microbuses (líneas de OSM).

Características:
- Usa SOLO las líneas reales (excluye las académicas L001…L018) -> opción A.
- Caminata de acceso y de egreso optimizadas: en vez de tomar la parada más
  cercana al origen/destino, considera las K paradas más cercanas y deja que
  Dijkstra elija la combinación (caminar + viajar) de menor tiempo total. Así,
  si un micro te deja cerca del destino, caminar el último tramo puede salir
  más rápido.
- Transbordos a pie entre paradas cercanas (tabla red_transbordos).
- Cada tramo se marca como 'linea' (micro) o 'caminata' (a pie, para dibujar
  punteado en la app).
- Si origen y destino están muy cerca, devuelve "solo caminar".

Dijkstra es Python puro (heapq). El estado es (parada, línea_actual) para
penalizar los transbordos entre líneas (la caminata no penaliza: su tiempo cuenta).
"""

import heapq
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.ruta import ParadaEnRuta, RutaOptimaResponse, TramoRuta

PENAL_TRANSBORDO_SEG = 180.0       # 3 min de penalización por cambiar de línea
VEL_CAMINATA_MS = 1.389            # ~5 km/h
CAMINATA = "CAMINATA"             # marca de arista a pie
ORIGEN, DESTINO = "__ORIGEN__", "__DESTINO__"
REAL_PARADA_MIN = 100000          # las paradas reales (OSM) tienen id_externo >= esto
K_PARADAS = 6                     # paradas candidatas por extremo
RADIO_ACCESO_M = 1200             # radio para buscar paradas de entrada/salida (~15 min a pie)
CAMINATA_DIRECTA_MAX_M = 1800     # si A y B están más cerca que esto, se puede caminar directo

Arista = Tuple[str, str, str, float, float]  # (destino, linea, sentido, tiempo, distancia)
Adyacencia = Dict[str, List[Arista]]


def _haversine(lon1, lat1, lon2, lat2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ──────────────────────────────────────────────────────────────────
# Dijkstra (puro)
# ──────────────────────────────────────────────────────────────────
def _dijkstra(adyacencia, origen, destino, penal_transbordo=PENAL_TRANSBORDO_SEG, prohibidas=None):
    if origen == destino:
        return [], 0.0
    inicio = (origen, None)
    dist = {inicio: 0.0}
    prev = {}
    pq = [(0.0, origen, None)]
    while pq:
        costo, nodo, linea = heapq.heappop(pq)
        estado = (nodo, linea)
        if costo > dist.get(estado, float("inf")):
            continue
        if nodo == destino:
            return _reconstruir(prev, estado), costo
        for (vecino, l_arista, sentido, t, d) in adyacencia.get(nodo, []):
            if prohibidas and l_arista in prohibidas:
                continue
            # La caminata no penaliza (su tiempo ya cuenta); solo penaliza cambiar de línea.
            es_cambio = (linea is not None and linea != CAMINATA
                         and l_arista != CAMINATA and l_arista != linea)
            extra = penal_transbordo if es_cambio else 0.0
            nuevo = costo + t + extra
            ne = (vecino, l_arista)
            if nuevo < dist.get(ne, float("inf")):
                dist[ne] = nuevo
                prev[ne] = (estado, {"origen": nodo, "destino": vecino, "linea": l_arista,
                                     "sentido": sentido, "tiempo": t, "distancia": d})
                heapq.heappush(pq, (nuevo, vecino, l_arista))
    return None, float("inf")


def _reconstruir(prev, estado):
    aristas = []
    while estado in prev:
        estado_prev, arista = prev[estado]
        aristas.append(arista)
        estado = estado_prev
    aristas.reverse()
    return aristas


# ──────────────────────────────────────────────────────────────────
# Agrupar en tramos (linea / caminata)
# ──────────────────────────────────────────────────────────────────
def _agrupar_en_tramos(camino, info):
    tramos = []
    actual = None

    def pr(pid):
        p = info.get(pid, {})
        return ParadaEnRuta(id_punto=p.get("id_punto"), descripcion=p.get("descripcion"),
                            longitud=p.get("lon", 0.0), latitud=p.get("lat", 0.0))

    for a in camino:
        es_cam = a["linea"] == CAMINATA
        clave = ("caminata",) if es_cam else ("linea", a["linea"], a["sentido"])
        if actual is None or actual["clave"] != clave:
            if actual is not None:
                tramos.append(_cerrar(actual, pr))
            actual = {"clave": clave, "es_cam": es_cam, "linea": a["linea"],
                      "sentido": a["sentido"], "tiempo": 0.0, "distancia": 0.0,
                      "paradas": [a["origen"]]}
        actual["tiempo"] += a["tiempo"]
        actual["distancia"] += a["distancia"]
        actual["paradas"].append(a["destino"])

    if actual is not None:
        tramos.append(_cerrar(actual, pr))
    return tramos


def _cerrar(t, pr):
    es_cam = t["es_cam"]
    return TramoRuta(
        tipo="caminata" if es_cam else "linea",
        linea_numero="Caminata" if es_cam else t["linea"],
        sentido="" if es_cam else t["sentido"],
        tiempo_seg=round(t["tiempo"], 1),
        distancia_m=round(t["distancia"], 1),
        paradas=[pr(pid) for pid in t["paradas"]],
    )


# ──────────────────────────────────────────────────────────────────
# Acceso a datos
# ──────────────────────────────────────────────────────────────────
def cargar_grafo(db: Session) -> Tuple[Adyacencia, Dict[str, dict]]:
    adyacencia: Adyacencia = {}
    # Tramos de viaje SOLO de líneas reales (excluye L001…L018)
    filas = db.execute(text(
        "SELECT a.parada_origen::text AS o, a.parada_destino::text AS d, "
        "l.numero AS linea, a.sentido::text AS sentido, a.distancia_m, a.tiempo_seg "
        "FROM red_aristas a JOIN lineas l ON l.id = a.linea_id "
        "WHERE l.numero NOT LIKE 'L%'"
    )).mappings().all()
    for f in filas:
        adyacencia.setdefault(f["o"], []).append(
            (f["d"], f["linea"], f["sentido"], float(f["tiempo_seg"]), float(f["distancia_m"]))
        )

    # Transbordos a pie entre paradas cercanas
    trans = db.execute(text(
        "SELECT parada_origen::text AS o, parada_destino::text AS d, distancia_m, tiempo_seg "
        "FROM red_transbordos"
    )).mappings().all()
    for f in trans:
        adyacencia.setdefault(f["o"], []).append(
            (f["d"], CAMINATA, "caminata", float(f["tiempo_seg"]), float(f["distancia_m"]))
        )

    info: Dict[str, dict] = {}
    paradas = db.execute(text(
        "SELECT id::text AS id, id_externo, codigo, ST_X(ubicacion) AS lon, ST_Y(ubicacion) AS lat "
        "FROM paradas WHERE id_externo >= :min"
    ), {"min": REAL_PARADA_MIN}).mappings().all()
    for p in paradas:
        info[p["id"]] = {"id_punto": p["id_externo"], "descripcion": p["codigo"],
                         "lon": float(p["lon"]), "lat": float(p["lat"])}
    return adyacencia, info


def paradas_cercanas(db: Session, lon: float, lat: float,
                     k: int = K_PARADAS, radio: int = RADIO_ACCESO_M):
    """Las k paradas reales más cercanas dentro del radio. [(id, distancia_m), ...]."""
    rows = db.execute(text("""
        SELECT id::text AS id,
               ST_Distance(ubicacion::geography,
                           ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS dist
        FROM paradas
        WHERE id_externo >= :min
          AND ST_DWithin(ubicacion::geography,
                         ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radio)
        ORDER BY ubicacion <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
        LIMIT :k
    """), {"lon": lon, "lat": lat, "radio": radio, "k": k, "min": REAL_PARADA_MIN}).mappings().all()
    return [(r["id"], float(r["dist"])) for r in rows]


# ──────────────────────────────────────────────────────────────────
# Caso de uso
# ──────────────────────────────────────────────────────────────────
def _tramo_caminata(o_lon, o_lat, d_lon, d_lat, dist, desc_o="Origen", desc_d="Destino"):
    return TramoRuta(
        tipo="caminata", linea_numero="Caminata", sentido="",
        tiempo_seg=round(dist / VEL_CAMINATA_MS, 1), distancia_m=round(dist, 1),
        paradas=[ParadaEnRuta(longitud=o_lon, latitud=o_lat, descripcion=desc_o),
                 ParadaEnRuta(longitud=d_lon, latitud=d_lat, descripcion=desc_d)],
    )


def _respuesta_solo_caminata(o_lon, o_lat, d_lon, d_lat, dist):
    t = _tramo_caminata(o_lon, o_lat, d_lon, d_lat, dist)
    return RutaOptimaResponse(
        tiempo_total_seg=t.tiempo_seg, tiempo_total_min=round(t.tiempo_seg / 60.0, 1),
        distancia_total_m=t.distancia_m, transbordos=0,
        caminata_origen_m=t.distancia_m, caminata_destino_m=0.0, tramos=[t],
    )


def _preparar(db, o_lon, o_lat, d_lon, d_lat):
    """Arma el grafo con los nodos virtuales ORIGEN/DESTINO y las caminatas de
    acceso/egreso. Devuelve (adyacencia, info, dist_directa) o (None, None, dist)."""
    cand_o = paradas_cercanas(db, o_lon, o_lat)
    cand_d = paradas_cercanas(db, d_lon, d_lat)
    dist_directa = _haversine(o_lon, o_lat, d_lon, d_lat)
    if not cand_o or not cand_d:
        return None, None, dist_directa

    ady, info = cargar_grafo(db)
    info[ORIGEN] = {"id_punto": None, "descripcion": "Origen", "lon": o_lon, "lat": o_lat}
    info[DESTINO] = {"id_punto": None, "descripcion": "Destino", "lon": d_lon, "lat": d_lat}
    for sid, dist in cand_o:
        ady.setdefault(ORIGEN, []).append((sid, CAMINATA, "caminata", dist / VEL_CAMINATA_MS, dist))
    for sid, dist in cand_d:
        ady.setdefault(sid, []).append((DESTINO, CAMINATA, "caminata", dist / VEL_CAMINATA_MS, dist))
    if dist_directa <= CAMINATA_DIRECTA_MAX_M:
        ady.setdefault(ORIGEN, []).append((DESTINO, CAMINATA, "caminata", dist_directa / VEL_CAMINATA_MS, dist_directa))
    return ady, info, dist_directa


def _en_servicio(ahora: datetime) -> bool:
    def _min(s):
        h, m = s.split(":")
        return int(h) * 60 + int(m)
    t = ahora.hour * 60 + ahora.minute
    return _min(settings.SERVICIO_INICIO) <= t <= _min(settings.SERVICIO_FIN)


def _construir(camino, info) -> RutaOptimaResponse:
    tramos = _agrupar_en_tramos(camino, info)
    # Espera del próximo micro: con frecuencia F, la espera promedio en una parada es F/2.
    espera_unit_seg = (settings.FRECUENCIA_MIN * 60.0) / 2.0
    espera_total = 0.0
    for t in tramos:
        if t.tipo == "linea":
            t.espera_min = round(espera_unit_seg / 60.0, 1)
            espera_total += espera_unit_seg

    viaje_seg = sum(t.tiempo_seg for t in tramos)   # micros + caminatas
    total_seg = viaje_seg + espera_total
    total_m = sum(t.distancia_m for t in tramos)
    rides = [t for t in tramos if t.tipo == "linea"]
    cam_ini = tramos[0].distancia_m if tramos and tramos[0].tipo == "caminata" else 0.0
    cam_fin = tramos[-1].distancia_m if tramos and tramos[-1].tipo == "caminata" else 0.0
    return RutaOptimaResponse(
        tiempo_total_seg=round(total_seg, 1),
        tiempo_total_min=round(total_seg / 60.0, 1),
        distancia_total_m=round(total_m, 1),
        transbordos=max(0, len(rides) - 1),
        caminata_origen_m=round(cam_ini, 1),
        caminata_destino_m=round(cam_fin, 1),
        espera_total_min=round(espera_total / 60.0, 1),
        frecuencia_min=settings.FRECUENCIA_MIN,
        en_servicio=_en_servicio(datetime.now()),
        tramos=tramos,
    )


def calcular_rutas_optimas(db, o_lon, o_lat, d_lon, d_lat, max_rutas: int = 4):
    """Devuelve VARIAS alternativas (estilo Moovit), ordenadas con la de MENOS
    transbordos primero (y a igualdad, la más rápida)."""
    ady, info, dist_directa = _preparar(db, o_lon, o_lat, d_lon, d_lat)
    if ady is None:
        if dist_directa <= CAMINATA_DIRECTA_MAX_M:
            return [_respuesta_solo_caminata(o_lon, o_lat, d_lon, d_lat, dist_directa)]
        return []

    rutas: List[RutaOptimaResponse] = []
    firmas = set()

    def intentar(penal, prohibidas):
        camino, _ = _dijkstra(ady, ORIGEN, DESTINO, penal_transbordo=penal, prohibidas=prohibidas)
        if not camino:
            return
        r = _construir(camino, info)
        firma = tuple(t.linea_numero for t in r.tramos if t.tipo == "linea")
        if firma in firmas:
            return
        firmas.add(firma)
        rutas.append(r)

    intentar(3000.0, None)                 # opción de mínimos transbordos
    intentar(PENAL_TRANSBORDO_SEG, None)   # opción más rápida

    # Alternativas: prohibir, de a una, las líneas ya usadas → rutas diversas
    usadas = [ln for r in list(rutas) for t in r.tramos if t.tipo == "linea"
              for ln in [t.linea_numero]]
    for L in dict.fromkeys(usadas):        # sin repetir, en orden
        if len(rutas) >= max_rutas + 2:
            break
        intentar(PENAL_TRANSBORDO_SEG, {L})

    rutas.sort(key=lambda r: (r.transbordos, r.tiempo_total_seg))
    return rutas[:max_rutas]


def calcular_ruta_optima(db, o_lon, o_lat, d_lon, d_lat):
    """Compatibilidad: la mejor ruta (la primera de calcular_rutas_optimas)."""
    rutas = calcular_rutas_optimas(db, o_lon, o_lat, d_lon, d_lat, max_rutas=1)
    return rutas[0] if rutas else None
