# C2 · Parte 1 — Schemas Pydantic y dependencia de autenticación

## Objetivo
Definir los contratos de entrada/salida del conductor con Pydantic, y crear la
dependencia `get_current_conductor` que todos los endpoints protegidos usarán
para extraer el conductor del JWT.

## Archivos a crear
```
app/schemas/conductor.py
app/core/dependencies.py
```

---

## 1. `app/schemas/conductor.py`

Los schemas Pydantic validan los datos que entran y salen de la API.
Se necesitan tres grupos:

| Schema | Uso |
|---|---|
| `ConductorCreate` | Cuerpo del `POST /conductores/registro` |
| `ConductorResponse` | Lo que devuelve la API (sin contraseña) |
| `LoginRequest` | Cuerpo del `POST /auth/login` |
| `TokenResponse` | Lo que devuelve el login |

```python
# app/schemas/conductor.py
import uuid
from datetime import date
from enum import Enum

from pydantic import BaseModel, EmailStr, field_validator


class SexoEnum(str, Enum):
    M = "M"
    F = "F"


class CategoriaLicenciaEnum(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    P = "P"
    M = "M"


# ── Entrada: registro ──────────────────────────────────────────────────────────
class ConductorCreate(BaseModel):
    documento_identidad: str
    nombre: str
    fecha_nacimiento: date
    sexo: SexoEnum
    telefono: str
    email: EmailStr
    password: str               # se recibe, se hashea, nunca se devuelve
    categoria_licencia: CategoriaLicenciaEnum

    @field_validator("documento_identidad", "nombre", "telefono")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El campo no puede estar vacío")
        return v.strip()


# ── Salida: datos del conductor ────────────────────────────────────────────────
class ConductorResponse(BaseModel):
    id: uuid.UUID
    documento_identidad: str
    nombre: str
    fecha_nacimiento: date
    sexo: SexoEnum
    telefono: str
    email: str
    categoria_licencia: CategoriaLicenciaEnum
    foto_url: str
    activo: bool

    model_config = {"from_attributes": True}


# ── Auth ───────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

> **Nota sobre `password`**: el campo solo existe en `ConductorCreate`.
> `ConductorResponse` no lo tiene, así que nunca se filtra al cliente.

---

## 2. `app/core/dependencies.py`

Esta dependencia se inyecta con `Depends(get_current_conductor)` en cualquier
endpoint que requiera JWT. Lee el token del header `Authorization: Bearer <token>`,
lo decodifica y devuelve el objeto `Conductor` de la base de datos.

```python
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
```

> **Cómo funciona el flujo**:
> 1. El cliente envía `Authorization: Bearer <token>`
> 2. `oauth2_scheme` extrae el token del header
> 3. `decode_access_token` verifica la firma y la expiración
> 4. Se busca el conductor en la BD y se devuelve al endpoint

---

## Verificación de esta parte

Antes de continuar con la Parte 2, verificar que:

- [ ] `app/schemas/conductor.py` no tiene errores de sintaxis (importar y ejecutar)
- [ ] `app/core/dependencies.py` importa correctamente desde `security` y `database`
- [ ] El servidor sigue levantando sin errores tras agregar los archivos

```bash
# Verificación rápida de sintaxis desde la raíz del proyecto
.\venv\Scripts\python -c "from app.schemas.conductor import ConductorCreate; print('OK')"
.\venv\Scripts\python -c "from app.core.dependencies import get_current_conductor; print('OK')"
```

---

## Siguiente paso
→ **C2_P2_storage_service.md** — Subida de fotos a Cloudinary
