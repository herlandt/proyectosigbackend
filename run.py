"""
Lanzador del backend — Microbuses SIG Santa Cruz.

Uso:
    python run.py            # modo desarrollo (recarga automática)
    python run.py --prod     # modo producción (sin reload, varios workers)
    python run.py --port 9000

Levanta la API FastAPI con uvicorn en 0.0.0.0 para que también sea
accesible desde el celular (app Flutter) dentro de la misma red Wi-Fi.
"""

import argparse
import os
import socket
import sys


def _asegurar_venv() -> None:
    """Si se ejecutó con un Python sin las dependencias, relanza con el del venv.

    Permite correr `python run.py` con cualquier intérprete (incluido el botón
    ▶ de VS Code) sin tener que activar el entorno virtual manualmente.
    """
    try:
        import uvicorn  # noqa: F401  (solo para comprobar si está disponible)

        return
    except ModuleNotFoundError:
        pass

    base = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(base, "venv", "Scripts", "python.exe"),  # Windows
        os.path.join(base, "venv", "bin", "python"),           # Linux/Mac
    ]
    venv_py = next((p for p in candidatos if os.path.exists(p)), None)

    if venv_py is None:
        sys.exit(
            "ERROR: No se encontró el entorno virtual 'venv'.\n"
            "Creálo e instalá dependencias con:\n"
            "  python -m venv venv\n"
            "  venv\\Scripts\\pip install -r requirements.txt"
        )

    # Evita un bucle infinito si ya estamos usando el python del venv.
    if os.path.abspath(venv_py) != os.path.abspath(sys.executable):
        print(f"Relanzando con el entorno virtual: {venv_py}")
        # subprocess (no os.execv): en Windows os.execv parte las rutas con espacios.
        import subprocess

        try:
            completado = subprocess.run([venv_py, os.path.abspath(__file__), *sys.argv[1:]])
            sys.exit(completado.returncode)
        except KeyboardInterrupt:
            sys.exit(0)

    sys.exit(
        "ERROR: El venv existe pero le faltan dependencias.\n"
        "Instalálas con:\n"
        "  venv\\Scripts\\pip install -r requirements.txt"
    )


_asegurar_venv()

import uvicorn


def ip_local() -> str:
    """Devuelve la IP de esta PC en la red local (para conectar el celular)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No envía nada; solo se usa para descubrir la interfaz de salida.
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Lanzador del backend Microbuses SIG")
    parser.add_argument("--host", default="0.0.0.0", help="Host de escucha (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Puerto (default: 8000)")
    parser.add_argument("--prod", action="store_true", help="Modo producción (sin reload)")
    parser.add_argument("--workers", type=int, default=1, help="Workers en modo --prod")
    args = parser.parse_args()

    # Posicionarse SIEMPRE en la carpeta del backend, sin importar desde dónde
    # se lance. Necesario para que pydantic encuentre el .env y uvicorn importe
    # 'main:app' y vigile solo esta carpeta en modo reload.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    reload = not args.prod
    ip = ip_local()

    print("=" * 60)
    print("  Microbuses SIG — Backend FastAPI")
    print("=" * 60)
    print(f"  Modo:        {'PRODUCCION' if args.prod else 'DESARROLLO (reload)'}")
    print(f"  Local:       http://127.0.0.1:{args.port}")
    print(f"  Red Wi-Fi:   http://{ip}:{args.port}   <-- usa esta en la app Flutter")
    print(f"  Docs (API):  http://127.0.0.1:{args.port}/docs")
    print("=" * 60)
    print("  Ctrl+C para detener")
    print("=" * 60)

    try:
        uvicorn.run(
            "main:app",
            host=args.host,
            port=args.port,
            reload=reload,
            workers=args.workers if args.prod else 1,
        )
    except KeyboardInterrupt:
        print("\nBackend detenido.")
        sys.exit(0)


if __name__ == "__main__":
    main()
