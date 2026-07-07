from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.conductor import Conductor
from app.schemas.conductor import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
	conductor = db.query(Conductor).filter(Conductor.email == datos.email).first()

	if not conductor or not verify_password(datos.password, conductor.password_hash):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Email o contraseña incorrectos",
		)

	if not conductor.activo:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Cuenta desactivada",
		)

	token = create_access_token(data={"sub": str(conductor.id)})
	return TokenResponse(access_token=token)
