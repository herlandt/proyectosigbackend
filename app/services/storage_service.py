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
	Sube una imagen a Cloudinary y devuelve la URL publica.

	Args:
		archivo_bytes: contenido binario del archivo
		carpeta: carpeta destino en Cloudinary, ej: "conductores", "microbuses"
		nombre: identificador unico del archivo (ej: UUID del conductor)

	Returns:
		URL publica de la imagen subida
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
