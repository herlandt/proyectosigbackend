from pydantic import field_validator
from pydantic_settings import BaseSettings

# Valor placeholder que NO debe usarse nunca (estaba en el .env de ejemplo).
PLACEHOLDER_SECRET = "cambia-esta-clave-secreta-en-produccion-debe-ser-larga-y-aleatoria"


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Entorno y seguridad
    ENVIRONMENT: str = "development"
    # Orígenes permitidos para CORS, separados por coma (ej. "https://app.midominio.com").
    # Vacío => se usan defaults de desarrollo (localhost). Los clientes móviles nativos
    # NO pasan por CORS, así que restringir esto no afecta a la app Flutter.
    ALLOWED_ORIGINS: str = ""
    # Si es True, el WebSocket de posiciones exige un JWT válido (?token=...).
    WS_REQUIRE_AUTH: bool = False

    # Frecuencia de micros (para estimar la espera del próximo micro en la ruta óptima)
    FRECUENCIA_MIN: float = 15.0          # un micro por parada cada ~15 min
    SERVICIO_INICIO: str = "05:30"        # horario de servicio (HH:MM)
    SERVICIO_FIN: str = "23:59"

    # Cloudinary (almacenamiento de imágenes)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("SECRET_KEY")
    @classmethod
    def _validar_secret_key(cls, v: str) -> str:
        """Evita arrancar con una SECRET_KEY insegura (placeholder o muy corta)."""
        if not v or v == PLACEHOLDER_SECRET:
            raise ValueError(
                "SECRET_KEY sin configurar. Generá una con: "
                'python -c "import secrets; print(secrets.token_hex(32))"'
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY demasiado corta (mínimo 32 caracteres).")
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        if self.ALLOWED_ORIGINS.strip():
            return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        # Defaults de desarrollo
        return [
            "http://localhost",
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1",
        ]


settings = Settings()
