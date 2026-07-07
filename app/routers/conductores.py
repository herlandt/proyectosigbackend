import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_conductor
from app.core.security import hash_password
from app.models.conductor import Conductor, CategoriaLicenciaEnum, SexoEnum
from app.schemas.conductor import ConductorResponse
from app.services.storage_service import subir_imagen

router = APIRouter(prefix="/conductores", tags=["Conductores"])

TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}


@router.post(
	"/registro",
	response_model=ConductorResponse,
	status_code=status.HTTP_201_CREATED,
)
async def registro_conductor(
	documento_identidad: str = Form(...),
	nombre: str = Form(...),
	fecha_nacimiento: str = Form(...),
	sexo: SexoEnum = Form(...),
	telefono: str = Form(...),
	email: str = Form(...),
	password: str = Form(...),
	categoria_licencia: CategoriaLicenciaEnum = Form(...),
	foto: UploadFile = File(...),
	db: Session = Depends(get_db),
):
	if db.query(Conductor).filter(Conductor.email == email).first():
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="El email ya está registrado",
		)
	if db.query(Conductor).filter(
		Conductor.documento_identidad == documento_identidad
	).first():
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="El documento de identidad ya está registrado",
		)

	contenido_foto = await foto.read()
	if foto.content_type not in TIPOS_PERMITIDOS:
		raise HTTPException(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			detail="Solo se permiten imágenes JPEG, PNG o WebP",
		)

	conductor_id = uuid.uuid4()
	foto_url = subir_imagen(
		archivo_bytes=contenido_foto,
		carpeta="conductores",
		nombre=str(conductor_id),
	)

	nuevo_conductor = Conductor(
		id=conductor_id,
		documento_identidad=documento_identidad.strip(),
		nombre=nombre.strip(),
		fecha_nacimiento=date.fromisoformat(fecha_nacimiento),
		sexo=sexo,
		telefono=telefono.strip(),
		email=email.strip().lower(),
		password_hash=hash_password(password),
		categoria_licencia=categoria_licencia,
		foto_url=foto_url,
	)

	db.add(nuevo_conductor)
	db.commit()
	db.refresh(nuevo_conductor)

	return nuevo_conductor


@router.get("/me", response_model=ConductorResponse)
def obtener_perfil(
	conductor: Conductor = Depends(get_current_conductor),
):
	return conductor
