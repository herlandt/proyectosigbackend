import uuid
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_conductor
from app.models.conductor import Conductor
from app.models.linea import Linea
from app.models.microbus import Microbus, Microbusfoto
from app.schemas.microbus import MicrobusResponse
from app.services.storage_service import subir_imagen

router = APIRouter(prefix="/microbuses", tags=["Microbuses"])

TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}


@router.post(
	"/registro",
	response_model=MicrobusResponse,
	status_code=status.HTTP_201_CREATED,
)
async def registro_microbus(
	placa: str = Form(...),
	modelo: str = Form(...),
	cantidad_asientos: int = Form(...),
	linea_id: uuid.UUID = Form(...),
	numero_interno: str = Form(...),
	fecha_asignacion: str = Form(...),
	fotos: List[UploadFile] = File(...),
	conductor: Conductor = Depends(get_current_conductor),
	db: Session = Depends(get_db),
):
	linea = db.query(Linea).filter(Linea.id == linea_id, Linea.activa == True).first()
	if not linea:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Linea no encontrada o inactiva",
		)

	if db.query(Microbus).filter(Microbus.placa == placa.upper()).first():
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="La placa ya esta registrada",
		)

	if db.query(Microbus).filter(
		Microbus.numero_interno == numero_interno,
		Microbus.linea_id == linea_id,
	).first():
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="El numero interno ya existe en esta linea",
		)

	for foto in fotos:
		if foto.content_type not in TIPOS_PERMITIDOS:
			raise HTTPException(
				status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
				detail=(
					f"Archivo '{foto.filename}' no es una imagen valida "
					"(JPEG, PNG o WebP)"
				),
			)

	microbus_id = uuid.uuid4()
	nuevo_microbus = Microbus(
		id=microbus_id,
		placa=placa.strip().upper(),
		modelo=modelo.strip(),
		cantidad_asientos=cantidad_asientos,
		conductor_id=conductor.id,
		linea_id=linea_id,
		numero_interno=numero_interno.strip(),
		fecha_asignacion=date.fromisoformat(fecha_asignacion),
	)
	db.add(nuevo_microbus)
	db.flush()

	for orden, foto in enumerate(fotos):
		contenido = await foto.read()
		foto_url = subir_imagen(
			archivo_bytes=contenido,
			carpeta="microbuses",
			nombre=f"{microbus_id}_{orden}",
		)
		db.add(
			Microbusfoto(
				microbus_id=microbus_id,
				foto_url=foto_url,
				orden=orden,
			)
		)

	db.commit()
	db.refresh(nuevo_microbus)
	return nuevo_microbus


@router.get("/mis-microbuses", response_model=list[MicrobusResponse])
def mis_microbuses(
	conductor: Conductor = Depends(get_current_conductor),
	db: Session = Depends(get_db),
):
	return (
		db.query(Microbus)
		.filter(Microbus.conductor_id == conductor.id)
		.order_by(Microbus.fecha_asignacion.desc())
		.all()
	)
