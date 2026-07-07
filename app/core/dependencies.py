# app/core/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.conductor import Conductor


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_conductor(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Conductor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    conductor_id: str = payload.get("sub")
    if conductor_id is None:
        raise credentials_exception

    conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
    if conductor is None or not conductor.activo:
        raise credentials_exception

    return conductor