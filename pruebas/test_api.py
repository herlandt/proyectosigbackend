"""
Pruebas completas del backend Microbuses SIG
Cubre: auth, conductores, microbuses, lineas, recorridos, telemetria, websocket
"""

import asyncio
import io
import json
import sys
import time
import uuid
from pathlib import Path

import requests
import websockets
from PIL import Image

BASE = "http://localhost:8000"
OK   = "\033[92mOK\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def titulo(texto):
    print(f"\n{'-'*55}")
    print(f"  {texto}")
    print(f"{'-'*55}")

def ok(msg):
    print(f"  {OK}  {msg}")

def fallo(msg, detalle=""):
    print(f"  {FAIL}  {msg}", end="")
    if detalle:
        print(f"  →  {detalle}", end="")
    print()

def advertencia(msg):
    print(f"  {WARN}  {msg}")

def imagen_fake() -> bytes:
    """Genera un PNG mínimo en memoria (no necesita archivo real)."""
    img = Image.new("RGB", (100, 100), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

resultados = {"ok": 0, "fail": 0}

def afirmar(condicion, msg_ok, msg_fail, detalle=""):
    if condicion:
        ok(msg_ok)
        resultados["ok"] += 1
    else:
        fallo(msg_fail, detalle)
        resultados["fail"] += 1
    return condicion


# --------------------------------------------------------------------------- #
# 0. Health check
# --------------------------------------------------------------------------- #

def test_health():
    titulo("0 · Health check")
    try:
        r = requests.get(f"{BASE}/", timeout=5)
        afirmar(r.status_code == 200, "GET / → 200 OK", "GET / falló", str(r.status_code))
        data = r.json()
        afirmar(data.get("status") == "ok", "Respuesta tiene status=ok", "status != ok", str(data))
    except Exception as e:
        fallo("No se pudo conectar al backend", str(e))
        resultados["fail"] += 1
        sys.exit(1)


# --------------------------------------------------------------------------- #
# 1. Registro de conductor
# --------------------------------------------------------------------------- #

TOKEN = None
CONDUCTOR_ID = None
SUFFIX = str(uuid.uuid4())[:8]   # único por ejecución

def test_registro_conductor():
    global TOKEN, CONDUCTOR_ID
    titulo("1 · Registro de conductor")

    img_bytes = imagen_fake()

    r = requests.post(
        f"{BASE}/conductores/registro",
        data={
            "nombre": f"Test Conductor {SUFFIX}",
            "documento_identidad": f"CI{SUFFIX}",
            "fecha_nacimiento": "1990-06-15",
            "sexo": "M",
            "email": f"conductor_{SUFFIX}@test.com",
            "password": "Test1234!",
            "telefono": "77712345",
            "categoria_licencia": "C",
        },
        files={"foto": (f"foto_{SUFFIX}.png", img_bytes, "image/png")},
        timeout=30,
    )
    ok_reg = afirmar(
        r.status_code == 201,
        f"POST /conductores/registro → 201 Created",
        "Registro falló",
        f"{r.status_code} {r.text[:200]}",
    )
    if ok_reg:
        data = r.json()
        CONDUCTOR_ID = data.get("id")
        afirmar(bool(CONDUCTOR_ID), "Respuesta tiene id", "Sin id en respuesta")
        afirmar(
            data.get("email") == f"conductor_{SUFFIX}@test.com",
            "Email coincide",
            "Email no coincide",
        )


# --------------------------------------------------------------------------- #
# 2. Login
# --------------------------------------------------------------------------- #

def test_login():
    global TOKEN
    titulo("2 · Login")

    r = requests.post(
        f"{BASE}/auth/login",
        json={"email": f"conductor_{SUFFIX}@test.com", "password": "Test1234!"},
        timeout=10,
    )
    ok_login = afirmar(
        r.status_code == 200,
        "POST /auth/login → 200 OK",
        "Login falló",
        f"{r.status_code} {r.text[:200]}",
    )
    if ok_login:
        data = r.json()
        TOKEN = data.get("access_token")
        afirmar(bool(TOKEN), "Recibió access_token", "Sin access_token")
        afirmar(data.get("token_type") == "bearer", "token_type=bearer", "token_type incorrecto")


def headers():
    return {"Authorization": f"Bearer {TOKEN}"}


# --------------------------------------------------------------------------- #
# 3. Perfil del conductor
# --------------------------------------------------------------------------- #

def test_perfil():
    titulo("3 · Perfil del conductor")
    r = requests.get(f"{BASE}/conductores/me", headers=headers(), timeout=10)
    afirmar(r.status_code == 200, "GET /conductores/me → 200", "Falló", f"{r.status_code}")
    if r.status_code == 200:
        data = r.json()
        afirmar(data.get("id") == CONDUCTOR_ID, "ID coincide con el registrado", "ID no coincide")


# --------------------------------------------------------------------------- #
# 4. Registro de microbús
# --------------------------------------------------------------------------- #

MICROBUS_ID = None
LINEA_ID    = None

def test_registro_microbus():
    global MICROBUS_ID, LINEA_ID

    titulo("4 · Registro de microbús")

    # Primero necesitamos una linea_id real
    r_lineas = requests.get(f"{BASE}/lineas", timeout=10)
    if r_lineas.status_code != 200 or not r_lineas.json():
        advertencia("No hay líneas en la BD — omitiendo registro de microbús")
        advertencia("Ejecuta el SQL de datos de prueba (C3_P4) en pgAdmin primero")
        resultados["fail"] += 1
        return

    lineas = r_lineas.json()
    LINEA_ID = lineas[0]["id"]
    ok(f"Usando línea: {lineas[0]['numero']} — {lineas[0]['nombre']} (id={LINEA_ID[:8]}...)")

    img_bytes = imagen_fake()

    r = requests.post(
        f"{BASE}/microbuses/registro",
        data={
            "placa": f"PL{SUFFIX[:4]}",
            "numero_interno": f"N{SUFFIX[:4]}",
            "modelo": "Toyota Coaster 2020",
            "cantidad_asientos": "25",
            "fecha_asignacion": "2024-01-15",
            "linea_id": LINEA_ID,
        },
        files=[
            ("fotos", (f"foto1_{SUFFIX}.png", img_bytes, "image/png")),
            ("fotos", (f"foto2_{SUFFIX}.png", img_bytes, "image/png")),
        ],
        headers=headers(),
        timeout=30,
    )
    ok_mb = afirmar(
        r.status_code == 201,
        "POST /microbuses/registro → 201 Created",
        "Registro microbús falló",
        f"{r.status_code} {r.text[:300]}",
    )
    if ok_mb:
        data = r.json()
        MICROBUS_ID = data.get("id")
        afirmar(bool(MICROBUS_ID), "Respuesta tiene id", "Sin id")
        afirmar(len(data.get("fotos", [])) == 2, "2 fotos guardadas", "Fotos incorrectas")


# --------------------------------------------------------------------------- #
# 5. Listado de microbuses propios
# --------------------------------------------------------------------------- #

def test_mis_microbuses():
    titulo("5 · Mis microbuses")
    r = requests.get(f"{BASE}/microbuses/mis-microbuses", headers=headers(), timeout=10)
    afirmar(r.status_code == 200, "GET /microbuses/mis-microbuses → 200", "Falló", str(r.status_code))
    if r.status_code == 200:
        lista = r.json()
        afirmar(isinstance(lista, list), "Respuesta es lista", "No es lista")
        if MICROBUS_ID:
            ids = [m["id"] for m in lista]
            afirmar(MICROBUS_ID in ids, "Microbús recién creado aparece en lista", "No aparece")


# --------------------------------------------------------------------------- #
# 6. Endpoints de líneas
# --------------------------------------------------------------------------- #

def test_lineas():
    titulo("6 · Endpoints de líneas")

    # GET /lineas
    r = requests.get(f"{BASE}/lineas", timeout=10)
    ok_lista = afirmar(r.status_code == 200, "GET /lineas → 200", "Falló", str(r.status_code))

    if not ok_lista or not LINEA_ID:
        advertencia("Sin líneas — saltando pruebas de detalle")
        return

    lineas = r.json()
    afirmar(len(lineas) > 0, f"Hay {len(lineas)} líneas", "Lista vacía")

    # GET /lineas/{id}
    r2 = requests.get(f"{BASE}/lineas/{LINEA_ID}", timeout=10)
    ok_det = afirmar(r2.status_code == 200, "GET /lineas/{id} → 200", "Falló", str(r2.status_code))
    if ok_det:
        det = r2.json()
        tiene_geo = (
            "recorrido_ida" in det and isinstance(det["recorrido_ida"], dict)
        )
        afirmar(tiene_geo, "recorrido_ida es GeoJSON dict", "Sin GeoJSON", str(type(det.get("recorrido_ida"))))

    # GET /lineas/cercanas  (Santa Cruz centro)
    r3 = requests.get(
        f"{BASE}/lineas/cercanas",
        params={"lon": -63.1822, "lat": -17.7834, "radio": 5000},
        timeout=10,
    )
    afirmar(r3.status_code == 200, "GET /lineas/cercanas → 200", "Falló", f"{r3.status_code} {r3.text[:200]}")
    if r3.status_code == 200:
        cercanas = r3.json()
        afirmar(isinstance(cercanas, list), f"Cercanas devuelve lista ({len(cercanas)} resultados)", "No es lista")

    # GET /lineas/{id}/microbuses-activos
    r4 = requests.get(
        f"{BASE}/lineas/{LINEA_ID}/microbuses-activos",
        params={"sentido": "ida"},
        timeout=10,
    )
    afirmar(r4.status_code == 200, "GET /lineas/{id}/microbuses-activos → 200", "Falló", f"{r4.status_code} {r4.text[:200]}")

    # GET /lineas/{id}/eta  (200 si hay buses activos, 404 si no — ambos son correctos)
    r5 = requests.get(
        f"{BASE}/lineas/{LINEA_ID}/eta",
        params={"lon": -63.1822, "lat": -17.7834, "sentido": "ida"},
        timeout=10,
    )
    afirmar(
        r5.status_code in (200, 404),
        f"GET /lineas/{{id}}/eta → {r5.status_code} (200=hay buses / 404=sin buses activos)",
        "ETA devolvio error inesperado",
        f"{r5.status_code} {r5.text[:200]}",
    )
    if r5.status_code == 200:
        eta_data = r5.json()
        ok(f"ETA calculado: {eta_data}")
    else:
        advertencia("Sin microbuses activos ahora — ETA 404 es correcto")


# --------------------------------------------------------------------------- #
# 7. Flujo de recorrido completo
# --------------------------------------------------------------------------- #

RECORRIDO_ID = None

def test_recorrido_iniciar():
    global RECORRIDO_ID
    titulo("7 · Iniciar recorrido")

    if not MICROBUS_ID:
        advertencia("Sin microbús — saltando prueba de recorrido")
        resultados["fail"] += 1
        return

    r = requests.post(
        f"{BASE}/recorridos/iniciar",
        json={
            "microbus_id": MICROBUS_ID,
            "sentido": "ida",
            "latitud": -17.7834,
            "longitud": -63.1822,
        },
        headers=headers(),
        timeout=10,
    )
    ok_ini = afirmar(
        r.status_code == 201,
        "POST /recorridos/iniciar → 201 Created",
        "Falló",
        f"{r.status_code} {r.text[:300]}",
    )
    if ok_ini:
        RECORRIDO_ID = r.json().get("recorrido_id")
        afirmar(bool(RECORRIDO_ID), "Respuesta tiene recorrido_id", "Sin recorrido_id")

    # Intentar iniciar otro (debe dar 409)
    r2 = requests.post(
        f"{BASE}/recorridos/iniciar",
        json={
            "microbus_id": MICROBUS_ID,
            "sentido": "ida",
            "latitud": -17.7834,
            "longitud": -63.1822,
        },
        headers=headers(),
        timeout=10,
    )
    afirmar(r2.status_code == 409, "Segundo iniciar → 409 Conflict (correcto)", "No devolvió 409", str(r2.status_code))


def test_telemetria():
    titulo("8 · Enviar telemetría")

    if not RECORRIDO_ID:
        advertencia("Sin recorrido activo — saltando telemetría")
        resultados["fail"] += 1
        return

    puntos = [
        (-17.7834, -63.1822, 0.0),
        (-17.7840, -63.1830, 0.12),
        (-17.7850, -63.1840, 0.25),
    ]
    for i, (lat, lon, dist) in enumerate(puntos):
        r = requests.post(
            f"{BASE}/recorridos/{RECORRIDO_ID}/telemetria",
            json={
                "latitud": lat,
                "longitud": lon,
                "velocidad": 25.0 + i * 2,
                "distancia_recorrida": dist,
                "tiempo_transcurrido": i * 30,
                "fecha": "2026-05-05",
                "hora": f"14:0{i}:00",
            },
            headers=headers(),
            timeout=10,
        )
        afirmar(
            r.status_code == 200,
            f"Telemetría punto {i+1} → 200",
            f"Telemetría {i+1} falló",
            f"{r.status_code} {r.text[:200]}",
        )


def test_terminar_recorrido():
    titulo("9 · Terminar recorrido")

    if not RECORRIDO_ID:
        advertencia("Sin recorrido — saltando")
        resultados["fail"] += 1
        return

    r = requests.post(
        f"{BASE}/recorridos/{RECORRIDO_ID}/terminar",
        json={"latitud": -17.7850, "longitud": -63.1840},
        headers=headers(),
        timeout=10,
    )
    ok_term = afirmar(
        r.status_code == 200,
        "POST /recorridos/{id}/terminar → 200",
        "Falló",
        f"{r.status_code} {r.text[:300]}",
    )
    if ok_term:
        data = r.json()
        afirmar(data.get("tipo_finalizacion") == "normal", "tipo_finalizacion=normal", "Incorrecto")
        afirmar(data.get("fecha_fin") is not None, "Tiene fecha_fin", "Sin fecha_fin")

    # Intentar terminar de nuevo → debe dar 409
    r2 = requests.post(
        f"{BASE}/recorridos/{RECORRIDO_ID}/terminar",
        json={"latitud": -17.7850, "longitud": -63.1840},
        headers=headers(),
        timeout=10,
    )
    afirmar(r2.status_code == 409, "Terminar ya finalizado → 409 (correcto)", "No devolvió 409", str(r2.status_code))


def test_salir_fuerza_mayor():
    titulo("10 · Flujo salir por fuerza mayor")

    if not MICROBUS_ID:
        advertencia("Sin microbús — saltando")
        resultados["fail"] += 1
        return

    # Iniciar un recorrido nuevo
    r = requests.post(
        f"{BASE}/recorridos/iniciar",
        json={
            "microbus_id": MICROBUS_ID,
            "sentido": "vuelta",
            "latitud": -17.7834,
            "longitud": -63.1822,
        },
        headers=headers(),
        timeout=10,
    )
    if r.status_code != 201:
        fallo("No se pudo iniciar recorrido para fuerza mayor", f"{r.status_code} {r.text[:200]}")
        resultados["fail"] += 1
        return
    rec_id = r.json()["recorrido_id"]

    # Salir sin motivo → debe dar 422
    r2 = requests.post(
        f"{BASE}/recorridos/{rec_id}/salir",
        json={"latitud": -17.7834, "longitud": -63.1822, "motivo_salida": ""},
        headers=headers(),
        timeout=10,
    )
    afirmar(r2.status_code == 422, "Salir sin motivo → 422 Unprocessable (correcto)", "No validó motivo vacío", str(r2.status_code))

    # Salir con motivo válido
    r3 = requests.post(
        f"{BASE}/recorridos/{rec_id}/salir",
        json={
            "latitud": -17.7834,
            "longitud": -63.1822,
            "motivo_salida": "Problema mecánico en el motor",
        },
        headers=headers(),
        timeout=10,
    )
    ok_salir = afirmar(
        r3.status_code == 200,
        "POST /recorridos/{id}/salir con motivo → 200",
        "Falló",
        f"{r3.status_code} {r3.text[:300]}",
    )
    if ok_salir:
        data = r3.json()
        afirmar(data.get("tipo_finalizacion") == "fuerza_mayor", "tipo=fuerza_mayor", "Tipo incorrecto")
        afirmar(
            "Problema mecánico" in (data.get("motivo_salida") or ""),
            "Motivo guardado correctamente",
            "Motivo no coincide",
        )


# --------------------------------------------------------------------------- #
# 11. WebSocket
# --------------------------------------------------------------------------- #

async def _ws_test():
    uri = f"ws://localhost:8000/ws/lineas/{LINEA_ID or 'test-linea'}/posiciones"
    try:
        async with websockets.connect(uri, open_timeout=5) as ws:
            return True, "Conexión WebSocket establecida"
    except Exception as e:
        return False, str(e)

def test_websocket():
    titulo("11 · WebSocket")
    if not LINEA_ID:
        advertencia("Sin linea_id — usando ID ficticio para probar el endpoint")

    success, msg = asyncio.run(_ws_test())
    afirmar(success, f"WS /ws/lineas/{{id}}/posiciones → {msg}", "WebSocket falló", msg)


# --------------------------------------------------------------------------- #
# 12. Errores de autenticación
# --------------------------------------------------------------------------- #

def test_auth_errors():
    titulo("12 · Validación de autenticación")

    # Token inválido
    r = requests.get(
        f"{BASE}/conductores/me",
        headers={"Authorization": "Bearer token_falso_12345"},
        timeout=5,
    )
    afirmar(r.status_code == 401, "Token inválido → 401 Unauthorized", "No devolvió 401", str(r.status_code))

    # Sin token
    r2 = requests.get(f"{BASE}/conductores/me", timeout=5)
    afirmar(r2.status_code == 401, "Sin token → 401 Unauthorized", "No devolvió 401", str(r2.status_code))

    # Login con contraseña incorrecta
    r3 = requests.post(
        f"{BASE}/auth/login",
        json={"email": f"conductor_{SUFFIX}@test.com", "password": "WrongPass999"},
        timeout=5,
    )
    afirmar(r3.status_code == 401, "Contraseña incorrecta → 401", "No devolvió 401", str(r3.status_code))

    # Login con email inexistente
    r4 = requests.post(
        f"{BASE}/auth/login",
        json={"email": "noexiste@test.com", "password": "cualquiera"},
        timeout=5,
    )
    afirmar(r4.status_code == 401, "Email inexistente → 401", "No devolvió 401", str(r4.status_code))


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  PRUEBAS BACKEND — Microbuses SIG")
    print("  http://localhost:8000")
    print("=" * 55)

    test_health()
    test_registro_conductor()
    test_login()
    test_perfil()
    test_registro_microbus()
    test_mis_microbuses()
    test_lineas()
    test_recorrido_iniciar()
    test_telemetria()
    test_terminar_recorrido()
    test_salir_fuerza_mayor()
    test_websocket()
    test_auth_errors()

    total = resultados["ok"] + resultados["fail"]
    print(f"\n{'='*55}")
    print(f"  Resultado: {resultados['ok']}/{total} pruebas pasaron")
    if resultados["fail"] == 0:
        print(f"  {OK}  Todo correcto OK")
    else:
        print(f"  {FAIL}  {resultados['fail']} prueba(s) fallaron")
    print("=" * 55 + "\n")

    sys.exit(0 if resultados["fail"] == 0 else 1)
