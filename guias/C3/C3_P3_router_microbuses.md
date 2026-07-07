# C3 · Parte 3 — Router de microbuses

## Objetivo
Implementar `app/routers/microbuses.py` con dos endpoints:
- `POST /microbuses/registro` → registra un microbús con múltiples fotos (requiere JWT)
- `GET /microbuses/mis-microbuses` → lista los microbuses del conductor autenticado

## Archivos a crear
```
app/routers/microbuses.py
```

---

## 1. `app/routers/microbuses.py`

```python
# app/routers/microbuses.py
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
    fecha_asignacion: str = Form(...),           # "YYYY-MM-DD"
    fotos: List[UploadFile] = File(...),         # una o varias fotos
    conductor: Conductor = Depends(get_current_conductor),
    db: Session = Depends(get_db),
):
    # 1. Validar que la línea existe
    linea = db.query(Linea).filter(Linea.id == linea_id, Linea.activa == True).first()
    if not linea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Línea no encontrada o inactiva",
        )

    # 2. Verificar placa única
    if db.query(Microbus).filter(Microbus.placa == placa.upper()).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La placa ya está registrada",
        )

    # 3. Verificar número interno único dentro de la línea
    if db.query(Microbus).filter(
        Microbus.numero_interno == numero_interno,
        Microbus.linea_id == linea_id,
    ).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El número interno ya existe en esta línea",
        )

    # 4. Validar tipos de archivo de todas las fotos
    for foto in fotos:
        if foto.content_type not in TIPOS_PERMITIDOS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Archivo '{foto.filename}' no es una imagen válida (JPEG, PNG o WebP)",
            )

    # 5. Crear el microbús
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
    db.flush()  # obtener el id sin hacer commit aún

    # 6. Subir fotos y guardar registros
    for orden, foto in enumerate(fotos):
        contenido = await foto.read()
        foto_url = subir_imagen(
            archivo_bytes=contenido,
            carpeta="microbuses",
            nombre=f"{microbus_id}_{orden}",
        )
        db.add(Microbusfoto(
            microbus_id=microbus_id,
            foto_url=foto_url,
            orden=orden,
        ))

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
```

---

## 2. Notas importantes

### `db.flush()` vs `db.commit()`
Se usa `flush()` después de agregar el microbús para que SQLAlchemy asigne
el `id` en memoria y poder usarlo en los registros de fotos, **sin** hacer
commit todavía. Si la subida de alguna foto falla, el `commit()` nunca se
ejecuta y no queda un microbús sin fotos en la BD.

### Múltiples fotos con `List[UploadFile]`
FastAPI acepta múltiples archivos con el mismo nombre de campo (`fotos`).
Desde Flutter se envían así:
```dart
for (final path in rutasFotos) {
  request.files.add(await http.MultipartFile.fromPath('fotos', path));
}
```

---

## Verificación de esta parte

```bash
.\venv\Scripts\python -c "
from app.routers.microbuses import router
print('router microbuses OK')
"
```

---

## Siguiente paso
→ **C3_P4_router_lineas_y_datos.md** — Endpoints de líneas + datos de prueba para Santa Cruz
