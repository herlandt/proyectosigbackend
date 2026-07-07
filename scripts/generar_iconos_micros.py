"""
generar_iconos_micros.py
------------------------
Genera un ícono PNG de microbús por cada línea, coloreado y numerado.
Sirve para poblar el campo `ImagenMicrobus` / los marcadores del mapa de la app,
en reemplazo del placeholder "img_l045.png" (todas las líneas hoy usan el mismo
color #FF0000, lo cual es incorrecto).

Genera dos tamaños por línea en mobile/assets/icons/lineas/:
  - micro_<numero>.png    (256x256, ícono de bus para listas/galería)
  - marker_<numero>.png   (96x96, marcador compacto para el mapa)

Colores: paleta distinguible por línea. El único color "real" confirmado de SCZ
en esta lista es la Línea 16 ≈ azul; el resto son colores por defecto, fáciles
de ajustar editando el diccionario LINEAS.

Requisitos: pip install pillow  (ya presente en el venv).
Uso:        python -X utf8 scripts/generar_iconos_micros.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))            # Backend/
PROYECTO = os.path.dirname(BASE_DIR)                                              # Proyecto SIG/
SALIDA = os.path.join(PROYECTO, "mobile", "assets", "icons", "lineas")

# numero (= NombreLinea del XLS) -> color principal
LINEAS = {
    "L001": "#E53935",  # rojo
    "L002": "#43A047",  # verde
    "L005": "#FB8C00",  # naranja
    "L008": "#8E24AA",  # violeta
    "L009": "#00897B",  # teal
    "L010": "#6D4C41",  # marrón
    "L011": "#D81B60",  # rosa
    "L016": "#1E88E5",  # azul  (color real confirmado de la Línea 16)
    "L017": "#3949AB",  # índigo
    "L018": "#F9A825",  # ámbar
}


def hex_a_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mas_oscuro(rgb, f=0.65):
    return tuple(int(c * f) for c in rgb)


def color_texto(rgb):
    """Negro o blanco según el brillo del fondo, para máximo contraste."""
    brillo = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.886 * rgb[2]
    return (20, 20, 20) if brillo > 150 else (255, 255, 255)


def cargar_fuente(tam):
    for nombre in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "segoeuib.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def dibujar_bus(size, numero, color_hex):
    """Dibuja un ícono de bus con el número de la línea centrado."""
    rgb = hex_a_rgb(color_hex)
    oscuro = mas_oscuro(rgb)
    txt = color_texto(rgb)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    m = int(size * 0.10)                 # margen
    body = [m, int(size * 0.20), size - m, int(size * 0.80)]
    rad = int(size * 0.14)
    d.rounded_rectangle(body, radius=rad, fill=rgb, outline=oscuro, width=max(2, size // 64))

    # franja de ventanas
    vh = int(size * 0.16)
    vy = int(size * 0.27)
    d.rounded_rectangle([m + rad // 2, vy, size - m - rad // 2, vy + vh],
                        radius=rad // 2, fill=(255, 255, 255, 230))

    # ruedas
    rw = int(size * 0.07)
    wy = int(size * 0.80)
    for wx in (int(size * 0.30), int(size * 0.70)):
        d.ellipse([wx - rw, wy - rw, wx + rw, wy + rw], fill=(30, 30, 30))

    # número de línea (debajo de las ventanas)
    etiqueta = numero[1:].lstrip("0") or numero  # "L001" -> "1"
    fuente = cargar_fuente(int(size * 0.26))
    bbox = d.textbbox((0, 0), etiqueta, font=fuente)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = int(size * 0.50) - bbox[1]
    d.text((tx, ty), etiqueta, font=fuente, fill=txt)
    return img


def dibujar_marker(size, numero, color_hex):
    """Marcador circular compacto con el número, para el mapa."""
    rgb = hex_a_rgb(color_hex)
    txt = color_texto(rgb)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, size - 2, size - 2], fill=rgb, outline=(255, 255, 255), width=max(2, size // 24))
    etiqueta = numero[1:].lstrip("0") or numero
    fuente = cargar_fuente(int(size * 0.46))
    bbox = d.textbbox((0, 0), etiqueta, font=fuente)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), etiqueta, font=fuente, fill=txt)
    return img


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for numero, color in LINEAS.items():
        dibujar_bus(256, numero, color).save(os.path.join(SALIDA, f"micro_{numero}.png"))
        dibujar_marker(96, numero, color).save(os.path.join(SALIDA, f"marker_{numero}.png"))
        print(f"  OK  {numero}  ({color})  -> micro_{numero}.png + marker_{numero}.png")
    print(f"\nGenerados {len(LINEAS) * 2} archivos en:\n  {SALIDA}")
    print("Recordá: en pubspec.yaml ya está 'assets/icons/' — agregá 'assets/icons/lineas/' si hace falta.")


if __name__ == "__main__":
    main()
