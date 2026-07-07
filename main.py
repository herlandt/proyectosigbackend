from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, conductores, lineas, microbuses, recorridos, rutas, websocket

app = FastAPI(
    title="Sistema de Información Geográfica — Microbuses Santa Cruz",
    description="API REST para el sistema de microbuses de Santa Cruz de la Sierra, Bolivia.",
    version="1.0.0",
)

# CORS restringido a orígenes conocidos (configurable vía ALLOWED_ORIGINS en .env).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conductores.router)
app.include_router(microbuses.router)
app.include_router(lineas.router)
app.include_router(recorridos.router)
app.include_router(rutas.router)
app.include_router(websocket.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "Microbuses SIG API"}
