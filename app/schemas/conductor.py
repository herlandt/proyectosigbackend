# app/schemas/conductor.py

import uuid
from datetime import date
from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum


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
    email: EmailStr
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