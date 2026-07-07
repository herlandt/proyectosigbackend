# C2 · Parte 3 — Router de autenticación (`POST /auth/login`)

## Objetivo
Implementar `app/routers/auth.py` con el endpoint de login. El conductor envía
email y contraseña; si son válidos recibe un JWT para usar en el resto de la API.

## Archivos a crear/modificar
```
app/routers/auth.py     ← crear
```

---

## 1. `app/routers/auth.py`

```python
# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.conductor import Conductor
from app.schemas.conductor import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    # 1. Buscar conductor por email
    conductor = db.query(Conductor).filter(Conductor.email == datos.email).first()

    # 2. Verificar que existe y que la contraseña es correcta
    if not conductor or not verify_password(datos.password, conductor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    # 3. Verificar que la cuenta está activa
    if not conductor.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada",
        )

    # 4. Crear y devolver el JWT
    token = create_access_token(data={"sub": str(conductor.id)})
    return TokenResponse(access_token=token)
```

---

## 2. Campo `password_hash` en el modelo `Conductor`

El modelo ORM actual no tiene el campo `password_hash`. Hay que agregarlo
en `app/models/conductor.py`:

```python
# Agregar esta línea dentro de la clase Conductor, junto a los otros campos:
password_hash = Column(String(255), nullable=False)
```

> **Por qué no está en el SQL original**: el script `base_de_datos_microbuses.sql`
> no incluye `password_hash` en la tabla `conductores`. Hay que agregarlo también
> en la base de datos con:
>
> ```sql
> ALTER TABLE conductores ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT '';
> ```
>
> Ejecutar este ALTER en pgAdmin o psql antes de probar el registro.

---

## 3. Flujo completo de login

```
Cliente                     API                         BD
  │                          │                           │
  │  POST /auth/login        │                           │
  │  { email, password }     │                           │
  │ ─────────────────────► │                           │
  │                          │  SELECT * FROM conductores│
  │                          │  WHERE email = ?          │
  │                          │ ────────────────────────► │
  │                          │ ◄──── conductor o None ── │
  │                          │                           │
  │                          │  bcrypt.verify(password,  │
  │                          │    conductor.password_hash)│
  │                          │                           │
  │  { access_token, ... }   │                           │
  │ ◄─────────────────────  │                           │
```

---

## 4. Por qué `sub` en el JWT

El campo `sub` (subject) del JWT almacena el `id` del conductor como string.
Así, en `get_current_conductor` (Parte 1), se puede recuperar el conductor
haciendo `db.query(Conductor).filter(Conductor.id == payload["sub"])`.

No se guarda el email en el JWT para evitar problemas si el conductor cambia
su email en el futuro.

---

## Verificación de esta parte

- [ ] El modelo `Conductor` tiene el campo `password_hash`
- [ ] La tabla en PostgreSQL tiene la columna `password_hash`
- [ ] El archivo `app/routers/auth.py` importa sin errores

```bash
.\venv\Scripts\python -c "from app.routers.auth import router; print('OK')"
```

El endpoint aún no aparece en Swagger porque no está registrado en `main.py`.
Eso se hace en la Parte 5.

---

## Siguiente paso
→ **C2_P4_router_conductores.md** — Endpoints de registro y perfil del conductor
