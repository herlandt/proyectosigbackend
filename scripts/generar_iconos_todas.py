"""
generar_iconos_todas.py
-----------------------
Genera iconos PNG de micro (256px) + marcador (96px) para TODAS las lineas reales
de Santa Cruz halladas en OpenStreetMap, con una paleta de colores distinguibles.

Si se pasa --colores ruta.json (dict {"numero": "#hex"}), usa esos colores reales
para las lineas indicadas y la paleta automatica para el resto.

Salida: mobile/assets/icons/lineas/micro_<n>.png y marker_<n>.png
Uso:    python -X utf8 scripts/generar_iconos_todas.py
"""
import argparse
import colorsys
import json
import os

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROYECTO = os.path.dirname(BASE_DIR)
SALIDA = os.path.join(PROYECTO, "mobile", "assets", "icons", "lineas")

# Lineas reales de SCZ con recorrido en OpenStreetMap
LINEAS_OSM = ["1", "2", "3", "4", "5", "10", "16", "20", "21", "23", "24", "25",
              "27", "30", "31", "32", "33", "34", "35", "37", "38", "41", "42",
              "45", "48", "51", "58", "60", "65", "72", "73", "74", "75", "76",
              "79", "90", "110", "112", "119", "121", "127"]


def paleta(n, i):
    """Color HSV distribuido para tener n colores bien distinguibles."""
    h = (i / max(1, n)) % 1.0
    s = 0.72 if i % 2 == 0 else 0.85
    v = 0.85 if i % 3 else 0.70
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def color_texto(rgb):
    brillo = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.886 * rgb[2]
    return (20, 20, 20) if brillo > 150 else (255, 255, 255)


def fuente(tam):
    for n in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "segoeuib.ttf"):
        try:
            return ImageFont.truetype(n, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def hex_a_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def bus(size, etiqueta, rgb):
    oscuro = tuple(int(c * 0.65) for c in rgb)
    txt = color_texto(rgb)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = int(size * 0.10)
    rad = int(size * 0.14)
    d.rounded_rectangle([m, int(size * 0.20), size - m, int(size * 0.80)],
                        radius=rad, fill=rgb, outline=oscuro, width=max(2, size // 64))
    d.rounded_rectangle([m + rad // 2, int(size * 0.27), size - m - rad // 2, int(size * 0.43)],
                        radius=rad // 2, fill=(255, 255, 255, 230))
    rw = int(size * 0.07)
    for wx in (int(size * 0.30), int(size * 0.70)):
        d.ellipse([wx - rw, int(size * 0.80) - rw, wx + rw, int(size * 0.80) + rw], fill=(30, 30, 30))
    f = fuente(int(size * (0.26 if len(etiqueta) <= 2 else 0.20)))
    bb = d.textbbox((0, 0), etiqueta, font=f)
    d.text(((size - (bb[2] - bb[0])) / 2 - bb[0], int(size * 0.50) - bb[1]), etiqueta, font=f, fill=txt)
    return img


def marker(size, etiqueta, rgb):
    txt = color_texto(rgb)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, size - 2, size - 2], fill=rgb, outline=(255, 255, 255), width=max(2, size // 24))
    f = fuente(int(size * (0.46 if len(etiqueta) <= 2 else 0.34)))
    bb = d.textbbox((0, 0), etiqueta, font=f)
    d.text(((size - (bb[2] - bb[0])) / 2 - bb[0], (size - (bb[3] - bb[1])) / 2 - bb[1]), etiqueta, font=f, fill=txt)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--colores", help="JSON {numero: #hex} con colores reales")
    args = ap.parse_args()
    reales = {}
    if args.colores and os.path.exists(args.colores):
        reales = json.load(open(args.colores, encoding="utf-8"))

    os.makedirs(SALIDA, exist_ok=True)
    n = len(LINEAS_OSM)
    for i, num in enumerate(LINEAS_OSM):
        rgb = hex_a_rgb(reales[num]) if num in reales else paleta(n, i)
        bus(256, num, rgb).save(os.path.join(SALIDA, f"micro_{num}.png"))
        marker(96, num, rgb).save(os.path.join(SALIDA, f"marker_{num}.png"))
    print(f"OK: {n*2} archivos ({n} lineas) en {SALIDA}")
    print(f"Lineas: {', '.join(LINEAS_OSM)}")
    if reales:
        print(f"Con color real: {len(reales)} lineas")


if __name__ == "__main__":
    main()
