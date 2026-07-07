# C2 · Parte 4 — Router de conductores (registro y perfil)

## Objetivo
Implementar `app/routers/conductores.py` con dos endpoints:
- `POST /conductores/registro` → crea el conductor, sube su foto, guarda en BD
- `GET /conductores/me` → devuelve los datos del conductor autenticado (requiere JWT)

## Archivos a crear
```
app/routers/conductores.py
```

---

## 1. `app/routers/conductores.py`

```python
# app/routers/conductores.py
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_conductor
from app.core.security import hash_password
from app.models.conductor import Conductor, CategoriaLicenciaEnum, SexoEnum
from app.schemas.conductor import ConductorResponse
from app.services.storage_service import subir_imagen

router = APIRouter(prefix="/conductores", tags=["Conductores"])


@router.post(
    "/registro",
    response_model=ConductorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def registro_conductor(
    # Campos del formulario (Form + File porque enviamos foto)
    documento_identidad: str = Form(...),
    nombre: str = Form(...),
    fecha_nacimiento: str = Form(...),          # "YYYY-MM-DD"
    sexo: SexoEnum = Form(...),
    telefono: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    categoria_licencia: CategoriaLicenciaEnum = Form(...),
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1. Verificar que el email y documento no estén ya registrados
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

    # 2. Subir foto a Cloudinary
    conductor_id = uuid.uuid4()
    contenido_foto = await foto.read()
    foto_url = subir_imagen(
        archivo_bytes=contenido_foto,
        carpeta="conductores",
        nombre=str(conductor_id),
    )

    # 3. Crear el objeto conductor
    from datetime import date
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

    # 4. Guardar en BD
    db.add(nuevo_conductor)
    db.commit()
    db.refresh(nuevo_conductor)

    return nuevo_conductor


@router.get("/me", response_model=ConductorResponse)
def obtener_perfil(
    conductor: Conductor = Depends(get_current_conductor),
):
    return conductor
```

---

## 2. Por qué se usa `Form(...)` en lugar de `BaseModel`

Cuando un endpoint recibe **archivos** (`UploadFile`) junto con datos de texto,
FastAPI requiere que los campos de texto también vengan como `Form(...)`.
No se puede mezclar `Body` (JSON) con `File` en el mismo request.

En la app Flutter, esto significa que el registro se enviará como
`multipart/form-data`, no como JSON:

```dart
// En Flutter (referencia para la Parte Flutter)
final request = http.MultipartRequest('POST', uri);
request.fields['nombre'] = 'Juan Pérez';
request.fields['email'] = 'juan@ejemplo.com';
// ...
request.files.add(await http.MultipartFile.fromPath('foto', fotoPath));
```

---

## 3. Validación de tipo de archivo (mejora de seguridad)

Agregar validación del tipo MIME de la foto antes de subirla:

```python
# Agregar después de leer el contenido de la foto:
TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
if foto.content_type not in TIPOS_PERMITIDOS:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Solo se permiten imágenes JPEG, PNG o WebP",
    )
```

---

## 4. Flujo completo de registro

```
Flutter                     API                         BD / Cloudinary
  │                          │                           │
  │  POST /conductores/registro                          │
  │  (multipart/form-data)   │                           │
  │ ─────────────────────► │                           │
  │                          │  ¿email duplicado?        │
  │                          │ ────────────────────────► │
  │                          │  ¿documento duplicado?    │
  │                          │ ────────────────────────► │
  │                          │                           │
  │                          │  subir_imagen()           │
  │                          │ ──────────────────────────► Cloudinary
  │                          │ ◄────────── foto_url ────── │
  │                          │                           │
  │                          │  INSERT INTO conductores  │
  │                          │ ────────────────────────► │
  │                          │                           │
  │  201 { conductor data }  │                           │
  │ ◄─────────────────────  │                           │
```

---

## Verificación de esta parte

- [ ] `app/routers/conductores.py` importa sin errores
- [ ] La dependencia `get_current_conductor` se inyecta correctamente en `/me`

```bash
.\venv\Scripts\python -c "from app.routers.conductores import router; print('OK')"
```

---

## Siguiente paso
→ **C2_P5_main_registro_y_verificacion.md** — Registrar routers en main.py y verificación final
