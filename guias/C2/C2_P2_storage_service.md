# C2 · Parte 2 — Storage Service (subida de fotos)

## Objetivo
Implementar `app/services/storage_service.py` para subir imágenes (foto del
conductor, fotos del microbús) a **Cloudinary** (servicio gratuito, sin servidor
propio). También agregar `cloudinary` al `requirements.txt`.

---

## 1. Agregar dependencia

En `requirements.txt` agregar al final:

```
cloudinary
```

Instalar:
```bash
.\venv\Scripts\pip install cloudinary
```

---

## 2. Variables de entorno en `.env`

Agregar las tres credenciales de Cloudinary al archivo `.env`:

```env
CLOUDINARY_CLOUD_NAME=tu_cloud_name
CLOUDINARY_API_KEY=tu_api_key
CLOUDINARY_API_SECRET=tu_api_secret
```

> Para obtener las credenciales: registrarse gratis en https://cloudinary.com
> → Dashboard → Product Environment Credentials

---

## 3. Actualizar `app/core/config.py`

Agregar los tres campos al `Settings`:

```python
# Agregar dentro de la clase Settings:
CLOUDINARY_CLOUD_NAME: str = ""
CLOUDINARY_API_KEY: str = ""
CLOUDINARY_API_SECRET: str = ""
```

---

## 4. `app/services/storage_service.py`

```python
# app/services/storage_service.py
import cloudinary
import cloudinary.uploader

from app.core.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
)


def subir_imagen(archivo_bytes: bytes, carpeta: str, nombre: str) -> str:
    """
    Sube una imagen a Cloudinary y devuelve la URL pública.

    Args:
        archivo_bytes: contenido binario del archivo
        carpeta: carpeta destino en Cloudinary, ej: "conductores", "microbuses"
        nombre: identificador único del archivo (ej: UUID del conductor)

    Returns:
        URL pública de la imagen subida
    """
    resultado = cloudinary.uploader.upload(
        archivo_bytes,
        folder=f"microbuses_sig/{carpeta}",
        public_id=nombre,
        overwrite=True,
        resource_type="image",
        transformation=[
            {"width": 800, "height": 800, "crop": "limit"},
            {"quality": "auto"},
            {"fetch_format": "auto"},
        ],
    )
    return resultado["secure_url"]


def eliminar_imagen(public_id: str) -> None:
    """Elimina una imagen de Cloudinary por su public_id."""
    cloudinary.uploader.destroy(public_id)
```

> **Qué hace la transformación**:
> - `crop: limit` → reduce si supera 800×800, no agranda imágenes pequeñas
> - `quality: auto` → Cloudinary elige la compresión óptima
> - `fetch_format: auto` → sirve WebP a navegadores que lo soporten
>
> Esto garantiza que ninguna imagen supere el límite de 1 MB del enunciado.

---

## 5. Cómo se usa desde los routers

El router de conductores recibirá el archivo con `UploadFile` de FastAPI:

```python
# Ejemplo de uso (se implementa en Parte 4)
from fastapi import UploadFile
from app.services.storage_service import subir_imagen

async def registro_conductor(foto: UploadFile):
    contenido = await foto.read()
    url = subir_imagen(contenido, carpeta="conductores", nombre=str(conductor_id))
```

---

## Verificación de esta parte

- [ ] `cloudinary` instalado (`pip show cloudinary`)
- [ ] Credenciales de Cloudinary en `.env`
- [ ] El servidor sigue levantando sin errores

```bash
# Verificar que el módulo importa correctamente
.\venv\Scripts\python -c "from app.services.storage_service import subir_imagen; print('OK')"
```

---

## Siguiente paso
→ **C2_P3_router_auth.md** — Endpoint `POST /auth/login`
