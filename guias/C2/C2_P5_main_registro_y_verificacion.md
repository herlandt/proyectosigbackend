# C2 · Parte 5 — Registrar routers en main.py y verificación final del Ciclo 2

## Objetivo
Conectar los routers de `auth` y `conductores` a la app FastAPI principal, y
ejecutar todas las verificaciones del Ciclo 2 para confirmar que el backend
está completo y funcionando.

---

## 1. Actualizar `main.py`

Agregar los dos imports y los dos `include_router`:

```python
# main.py  (versión final del Ciclo 2)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, conductores

app = FastAPI(
    title="Sistema de Información Geográfica — Microbuses Santa Cruz",
    description="API REST para el sistema de microbuses de Santa Cruz de la Sierra, Bolivia.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conductores.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "Microbuses SIG API"}
```

---

## 2. Ejecutar el ALTER TABLE en PostgreSQL

Antes de probar, asegurarse de que la columna `password_hash` existe en la BD:

```sql
-- Ejecutar en pgAdmin o psql
ALTER TABLE conductores
    ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NOT NULL DEFAULT '';
```

> El `DEFAULT ''` es temporal para que el ALTER no falle con filas existentes.
> Los conductores reales siempre tendrán su hash del registro.

---

## 3. Levantar el servidor

```bash
.\venv\Scripts\uvicorn main:app --reload
```

Abrir `http://localhost:8000/docs` — deben aparecer las secciones:
- **Autenticación** → `POST /auth/login`
- **Conductores** → `POST /conductores/registro`, `GET /conductores/me`

---

## 4. Checklist de verificación del Ciclo 2

### 4.1 Registro de conductor

En Swagger UI (`/docs`) o con curl/Postman:

```bash
# Con curl (ajustar ruta de foto)
curl -X POST http://localhost:8000/conductores/registro \
  -F "documento_identidad=12345678" \
  -F "nombre=Juan Pérez" \
  -F "fecha_nacimiento=1985-03-15" \
  -F "sexo=M" \
  -F "telefono=+59170000000" \
  -F "email=juan@ejemplo.com" \
  -F "password=mipassword123" \
  -F "categoria_licencia=C" \
  -F "foto=@/ruta/a/foto.jpg"
```

**Resultado esperado**: `201 Created` con el JSON del conductor (sin `password_hash`).

Verificar en pgAdmin que el registro existe en la tabla `conductores`.

---

### 4.2 Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@ejemplo.com", "password": "mipassword123"}'
```

**Resultado esperado**: `200 OK` con `{"access_token": "eyJ...", "token_type": "bearer"}`.

---

### 4.3 Obtener perfil (con JWT)

```bash
# Reemplazar <TOKEN> con el access_token recibido en el login
curl -X GET http://localhost:8000/conductores/me \
  -H "Authorization: Bearer <TOKEN>"
```

**Resultado esperado**: `200 OK` con los datos del conductor.

---

### 4.4 Acceso sin JWT

```bash
curl -X GET http://localhost:8000/conductores/me
```

**Resultado esperado**: `401 Unauthorized`.

---

### 4.5 Casos de error a verificar

| Escenario | Código esperado |
|---|---|
| Login con email inexistente | `401` |
| Login con contraseña incorrecta | `401` |
| Registro con email duplicado | `409` |
| Registro con documento duplicado | `409` |
| `/conductores/me` sin token | `401` |
| `/conductores/me` con token expirado/inválido | `401` |

---

## 5. Estado del proyecto al terminar el Ciclo 2

```
backend/
├── main.py                   ✅ routers auth + conductores registrados
├── .env                      ✅ DATABASE_URL + JWT + Cloudinary
├── requirements.txt          ✅ cloudinary agregado
└── app/
    ├── core/
    │   ├── config.py         ✅ Settings con Cloudinary
    │   ├── database.py       ✅
    │   ├── security.py       ✅
    │   └── dependencies.py   ✅ get_current_conductor
    ├── models/
    │   └── conductor.py      ✅ con password_hash
    ├── schemas/
    │   └── conductor.py      ✅ Create / Response / Login / Token
    ├── routers/
    │   ├── auth.py           ✅ POST /auth/login
    │   └── conductores.py    ✅ POST /registro, GET /me
    └── services/
        └── storage_service.py ✅ subir_imagen()
```

---

## Siguiente ciclo
Ciclo 2 completado ✅ → **Ciclo 3 — Microbuses y carga de líneas geoespaciales**
