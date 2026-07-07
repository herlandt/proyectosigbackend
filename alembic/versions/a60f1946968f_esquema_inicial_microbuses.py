"""esquema inicial microbuses

Crea el esquema completo del SIG de microbuses (PostgreSQL + PostGIS):
extensiones, tipos ENUM, tablas, índices, funciones, triggers y la vista
`vw_microbuses_activos`.

Notas:
- El esquema se reconcilia con los MODELOS ORM (que son el contrato real de la app);
  incluye `conductores.password_hash`, ausente en el .sql de guía.
- NO se incluyen las políticas RLS de Supabase (usan `auth.uid()`, que no existe en
  PostgreSQL plano y, además, el backend accede con conexión de servicio que las
  ignoraría) ni los datos de ejemplo. Si se despliega en Supabase, agregar la RLS
  en una migración aparte.

Revision ID: a60f1946968f
Revises:
Create Date: 2026-06-24 10:17:51.216035
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a60f1946968f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EXTENSIONES_Y_ENUMS = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE sexo_enum AS ENUM ('M', 'F');
CREATE TYPE categoria_licencia_enum AS ENUM ('A', 'B', 'C', 'P', 'M');
CREATE TYPE sentido_enum AS ENUM ('ida', 'vuelta');
CREATE TYPE tipo_finalizacion_enum AS ENUM ('normal', 'fuerza_mayor');
"""

TABLAS = """
CREATE TABLE conductores (
    id                    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    documento_identidad   VARCHAR(20)     NOT NULL UNIQUE,
    nombre                VARCHAR(150)    NOT NULL,
    fecha_nacimiento      DATE            NOT NULL,
    sexo                  sexo_enum       NOT NULL,
    telefono              VARCHAR(20)     NOT NULL,
    email                 VARCHAR(150)    NOT NULL UNIQUE,
    password_hash         VARCHAR(255)    NOT NULL,
    categoria_licencia    categoria_licencia_enum NOT NULL,
    foto_url              TEXT            NOT NULL,
    activo                BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_email_formato CHECK (POSITION('@' IN email) > 1 AND POSITION('.' IN email) > 3),
    CONSTRAINT chk_fecha_nac_valida CHECK (fecha_nacimiento < CURRENT_DATE)
);

CREATE TABLE lineas (
    id                    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero                VARCHAR(20)     NOT NULL UNIQUE,
    nombre                VARCHAR(150)    NOT NULL,
    descripcion           TEXT,
    recorrido_ida         GEOMETRY(LineString, 4326) NOT NULL,
    recorrido_vuelta      GEOMETRY(LineString, 4326) NOT NULL,
    punto_partida_ida     GEOMETRY(Point, 4326),
    punto_llegada_ida     GEOMETRY(Point, 4326),
    punto_partida_vuelta  GEOMETRY(Point, 4326),
    punto_llegada_vuelta  GEOMETRY(Point, 4326),
    activa                BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE microbuses (
    id                    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    placa                 VARCHAR(20)     NOT NULL UNIQUE,
    modelo                VARCHAR(100)    NOT NULL,
    cantidad_asientos     INTEGER         NOT NULL,
    conductor_id          UUID            NOT NULL REFERENCES conductores(id) ON DELETE RESTRICT,
    linea_id              UUID            NOT NULL REFERENCES lineas(id) ON DELETE RESTRICT,
    numero_interno        VARCHAR(20)     NOT NULL,
    fecha_asignacion      DATE            NOT NULL DEFAULT CURRENT_DATE,
    fecha_baja            DATE,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_asientos_positivos CHECK (cantidad_asientos > 0),
    CONSTRAINT chk_fecha_baja_valida CHECK (fecha_baja IS NULL OR fecha_baja >= fecha_asignacion),
    CONSTRAINT uq_numero_interno_linea UNIQUE (numero_interno, linea_id)
);

CREATE TABLE microbuses_fotos (
    id                    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    microbus_id           UUID            NOT NULL REFERENCES microbuses(id) ON DELETE CASCADE,
    foto_url              TEXT            NOT NULL,
    orden                 INTEGER         NOT NULL DEFAULT 0,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE recorridos (
    id                    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    microbus_id           UUID            NOT NULL REFERENCES microbuses(id) ON DELETE RESTRICT,
    conductor_id          UUID            NOT NULL REFERENCES conductores(id) ON DELETE RESTRICT,
    linea_id              UUID            NOT NULL REFERENCES lineas(id) ON DELETE RESTRICT,
    sentido               sentido_enum    NOT NULL,
    fecha_inicio          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    fecha_fin             TIMESTAMPTZ,
    tipo_finalizacion     tipo_finalizacion_enum,
    motivo_salida         TEXT,
    ubicacion_inicio      GEOMETRY(Point, 4326) NOT NULL,
    ubicacion_fin         GEOMETRY(Point, 4326),
    distancia_total_km    DECIMAL(10, 3),
    tiempo_total_seg      INTEGER,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_motivo_si_fuerza_mayor CHECK (
        (tipo_finalizacion IS NULL) OR
        (tipo_finalizacion = 'normal') OR
        (tipo_finalizacion = 'fuerza_mayor' AND motivo_salida IS NOT NULL AND LENGTH(TRIM(motivo_salida)) > 0)
    ),
    CONSTRAINT chk_fecha_fin_valida CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio),
    CONSTRAINT chk_finalizacion_completa CHECK (
        (fecha_fin IS NULL AND tipo_finalizacion IS NULL) OR
        (fecha_fin IS NOT NULL AND tipo_finalizacion IS NOT NULL)
    )
);

CREATE TABLE telemetria (
    id                    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    recorrido_id          UUID            NOT NULL REFERENCES recorridos(id) ON DELETE CASCADE,
    ubicacion             GEOMETRY(Point, 4326) NOT NULL,
    fecha                 DATE            NOT NULL,
    hora                  TIME            NOT NULL,
    timestamp_evento      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    velocidad             DECIMAL(6, 2)   NOT NULL DEFAULT 0,
    distancia_recorrida   DECIMAL(10, 3)  NOT NULL DEFAULT 0,
    tiempo_transcurrido   INTEGER         NOT NULL DEFAULT 0,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_velocidad_no_negativa CHECK (velocidad >= 0),
    CONSTRAINT chk_distancia_no_negativa CHECK (distancia_recorrida >= 0),
    CONSTRAINT chk_tiempo_no_negativo CHECK (tiempo_transcurrido >= 0)
);
"""

INDICES = """
CREATE INDEX idx_conductores_documento ON conductores(documento_identidad);
CREATE INDEX idx_conductores_email ON conductores(email);

CREATE INDEX idx_lineas_recorrido_ida ON lineas USING GIST(recorrido_ida);
CREATE INDEX idx_lineas_recorrido_vuelta ON lineas USING GIST(recorrido_vuelta);
CREATE INDEX idx_lineas_numero ON lineas(numero);

CREATE INDEX idx_microbuses_conductor ON microbuses(conductor_id);
CREATE INDEX idx_microbuses_linea ON microbuses(linea_id);
CREATE INDEX idx_microbuses_placa ON microbuses(placa);
CREATE INDEX idx_microbuses_activos ON microbuses(linea_id) WHERE fecha_baja IS NULL;

CREATE INDEX idx_fotos_microbus ON microbuses_fotos(microbus_id);

CREATE INDEX idx_recorridos_microbus ON recorridos(microbus_id);
CREATE INDEX idx_recorridos_linea ON recorridos(linea_id);
CREATE INDEX idx_recorridos_activos ON recorridos(linea_id, sentido) WHERE fecha_fin IS NULL;
CREATE INDEX idx_recorridos_fecha ON recorridos(fecha_inicio DESC);

CREATE INDEX idx_telemetria_ubicacion ON telemetria USING GIST(ubicacion);
CREATE INDEX idx_telemetria_recorrido ON telemetria(recorrido_id);
CREATE INDEX idx_telemetria_timestamp ON telemetria(timestamp_evento DESC);
CREATE INDEX idx_telemetria_recorrido_ts ON telemetria(recorrido_id, timestamp_evento DESC);
"""

FUNCIONES_TRIGGERS_VISTA = """
CREATE OR REPLACE FUNCTION actualizar_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_conductores_updated_at
    BEFORE UPDATE ON conductores
    FOR EACH ROW EXECUTE FUNCTION actualizar_updated_at();

CREATE TRIGGER trg_lineas_updated_at
    BEFORE UPDATE ON lineas
    FOR EACH ROW EXECUTE FUNCTION actualizar_updated_at();

CREATE TRIGGER trg_microbuses_updated_at
    BEFORE UPDATE ON microbuses
    FOR EACH ROW EXECUTE FUNCTION actualizar_updated_at();

CREATE TRIGGER trg_recorridos_updated_at
    BEFORE UPDATE ON recorridos
    FOR EACH ROW EXECUTE FUNCTION actualizar_updated_at();

CREATE OR REPLACE FUNCTION calcular_puntos_extremos_linea()
RETURNS TRIGGER AS $$
BEGIN
    NEW.punto_partida_ida    = ST_StartPoint(NEW.recorrido_ida);
    NEW.punto_llegada_ida    = ST_EndPoint(NEW.recorrido_ida);
    NEW.punto_partida_vuelta = ST_StartPoint(NEW.recorrido_vuelta);
    NEW.punto_llegada_vuelta = ST_EndPoint(NEW.recorrido_vuelta);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lineas_puntos_extremos
    BEFORE INSERT OR UPDATE OF recorrido_ida, recorrido_vuelta ON lineas
    FOR EACH ROW EXECUTE FUNCTION calcular_puntos_extremos_linea();

CREATE OR REPLACE VIEW vw_microbuses_activos AS
SELECT
    m.id                  AS microbus_id,
    m.placa,
    m.numero_interno,
    m.linea_id,
    l.numero              AS linea_numero,
    l.nombre              AS linea_nombre,
    r.id                  AS recorrido_id,
    r.sentido,
    r.fecha_inicio,
    c.id                  AS conductor_id,
    c.nombre              AS conductor_nombre,
    t.ubicacion,
    ST_X(t.ubicacion)     AS longitud,
    ST_Y(t.ubicacion)     AS latitud,
    t.velocidad,
    t.distancia_recorrida,
    t.tiempo_transcurrido,
    t.timestamp_evento    AS ultima_actualizacion
FROM microbuses m
INNER JOIN lineas l       ON l.id = m.linea_id
INNER JOIN conductores c  ON c.id = m.conductor_id
INNER JOIN recorridos r   ON r.microbus_id = m.id AND r.fecha_fin IS NULL
LEFT JOIN LATERAL (
    SELECT *
    FROM telemetria t2
    WHERE t2.recorrido_id = r.id
    ORDER BY t2.timestamp_evento DESC
    LIMIT 1
) t ON TRUE
WHERE m.fecha_baja IS NULL;

-- Funciones de consulta geoespacial (usadas por geo_service / eta_service)
CREATE OR REPLACE FUNCTION fn_lineas_cercanas(
    p_longitud      DOUBLE PRECISION,
    p_latitud       DOUBLE PRECISION,
    p_radio_metros  INTEGER DEFAULT 500
)
RETURNS TABLE (
    linea_id              UUID,
    numero                VARCHAR,
    nombre                VARCHAR,
    distancia_minima_m    DOUBLE PRECISION,
    pasa_ida              BOOLEAN,
    pasa_vuelta           BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id, l.numero, l.nombre,
        LEAST(
            ST_Distance(l.recorrido_ida::geography,    ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography),
            ST_Distance(l.recorrido_vuelta::geography, ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography)
        ),
        ST_DWithin(l.recorrido_ida::geography,    ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography, p_radio_metros),
        ST_DWithin(l.recorrido_vuelta::geography, ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography, p_radio_metros)
    FROM lineas l
    WHERE l.activa = TRUE
      AND (
          ST_DWithin(l.recorrido_ida::geography,    ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography, p_radio_metros) OR
          ST_DWithin(l.recorrido_vuelta::geography, ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography, p_radio_metros)
      )
    ORDER BY distancia_minima_m ASC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_microbuses_linea_activos(
    p_linea_id  UUID,
    p_sentido   sentido_enum
)
RETURNS TABLE (
    microbus_id           UUID,
    placa                 VARCHAR,
    numero_interno        VARCHAR,
    longitud              DOUBLE PRECISION,
    latitud               DOUBLE PRECISION,
    velocidad             DECIMAL,
    ultima_actualizacion  TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT v.microbus_id, v.placa, v.numero_interno, v.longitud, v.latitud, v.velocidad, v.ultima_actualizacion
    FROM vw_microbuses_activos v
    WHERE v.linea_id = p_linea_id AND v.sentido = p_sentido;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_eta_microbus_cercano(
    p_linea_id   UUID,
    p_sentido    sentido_enum,
    p_longitud   DOUBLE PRECISION,
    p_latitud    DOUBLE PRECISION
)
RETURNS TABLE (
    microbus_id           UUID,
    placa                 VARCHAR,
    numero_interno        VARCHAR,
    longitud              DOUBLE PRECISION,
    latitud               DOUBLE PRECISION,
    distancia_metros      DOUBLE PRECISION,
    velocidad_kmh         DECIMAL,
    eta_minutos           DECIMAL
) AS $$
DECLARE
    v_punto_usuario GEOGRAPHY;
BEGIN
    v_punto_usuario := ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography;
    RETURN QUERY
    SELECT
        v.microbus_id, v.placa, v.numero_interno, v.longitud, v.latitud,
        ST_Distance(v.ubicacion::geography, v_punto_usuario),
        v.velocidad,
        ROUND(
            (ST_Distance(v.ubicacion::geography, v_punto_usuario) / 1000.0) /
            CASE WHEN v.velocidad < 5 THEN 25 ELSE v.velocidad END * 60, 1
        )::DECIMAL
    FROM vw_microbuses_activos v
    WHERE v.linea_id = p_linea_id AND v.sentido = p_sentido
    ORDER BY distancia_metros ASC;
END;
$$ LANGUAGE plpgsql;
"""

DROP_TODO = """
DROP VIEW IF EXISTS vw_microbuses_activos;

DROP TABLE IF EXISTS telemetria CASCADE;
DROP TABLE IF EXISTS recorridos CASCADE;
DROP TABLE IF EXISTS microbuses_fotos CASCADE;
DROP TABLE IF EXISTS microbuses CASCADE;
DROP TABLE IF EXISTS lineas CASCADE;
DROP TABLE IF EXISTS conductores CASCADE;

DROP FUNCTION IF EXISTS fn_eta_microbus_cercano(UUID, sentido_enum, DOUBLE PRECISION, DOUBLE PRECISION);
DROP FUNCTION IF EXISTS fn_microbuses_linea_activos(UUID, sentido_enum);
DROP FUNCTION IF EXISTS fn_lineas_cercanas(DOUBLE PRECISION, DOUBLE PRECISION, INTEGER);
DROP FUNCTION IF EXISTS calcular_puntos_extremos_linea();
DROP FUNCTION IF EXISTS actualizar_updated_at();

DROP TYPE IF EXISTS tipo_finalizacion_enum;
DROP TYPE IF EXISTS sentido_enum;
DROP TYPE IF EXISTS categoria_licencia_enum;
DROP TYPE IF EXISTS sexo_enum;
"""


def upgrade() -> None:
    """Crea el esquema completo."""
    op.execute(EXTENSIONES_Y_ENUMS)
    op.execute(TABLAS)
    op.execute(INDICES)
    op.execute(FUNCIONES_TRIGGERS_VISTA)


def downgrade() -> None:
    """Elimina el esquema (no borra las extensiones postgis/uuid-ossp)."""
    op.execute(DROP_TODO)
