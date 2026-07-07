"""fn_eta_microbus_cercano: ETA por distancia SOBRE LA RUTA (no línea recta)

Antes: distancia en línea recta micro→usuario / velocidad. Eso da ETA falsos
(un micro que ya pasó tu parada, o uno a 300 m en línea recta pero a 3 km por
el recorrido, parecían "cerca").

Ahora:
- Se proyectan micro y parada del usuario sobre el recorrido de la línea con
  ST_LineLocatePoint (fracción 0..1) y la distancia es la diferencia de
  fracciones por el largo real de la ruta.
- Solo se devuelven micros que AÚN NO pasaron la parada (con ~30 m de
  tolerancia por ruido GPS).
- Mismas columnas de salida: eta_service no cambia.

Revision ID: d4e8a29c6f15
Revises: b7c2f4d81e03
Create Date: 2026-07-06
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e8a29c6f15'
down_revision: Union[str, Sequence[str], None] = 'b7c2f4d81e03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FN_ETA_RUTA = """
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
    v_ruta     GEOMETRY;
    v_largo_m  DOUBLE PRECISION;
    v_frac_par DOUBLE PRECISION;  -- posición de la parada del usuario en la ruta (0..1)
BEGIN
    SELECT CASE WHEN p_sentido = 'ida' THEN l.recorrido_ida ELSE l.recorrido_vuelta END
    INTO v_ruta
    FROM lineas l WHERE l.id = p_linea_id;

    IF v_ruta IS NULL THEN
        RETURN;
    END IF;

    v_largo_m  := ST_Length(v_ruta::geography);
    v_frac_par := ST_LineLocatePoint(
        v_ruta, ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326));

    RETURN QUERY
    SELECT
        v.microbus_id, v.placa, v.numero_interno, v.longitud, v.latitud,
        GREATEST(f.dist_m, 0.0),
        v.velocidad,
        ROUND(
            ((GREATEST(f.dist_m, 0.0) / 1000.0) /
             CASE WHEN v.velocidad < 5 THEN 25 ELSE v.velocidad END * 60)::numeric, 1
        )::DECIMAL
    FROM vw_microbuses_activos v
    CROSS JOIN LATERAL (
        SELECT (v_frac_par - ST_LineLocatePoint(v_ruta, v.ubicacion)) * v_largo_m AS dist_m
    ) f
    WHERE v.linea_id = p_linea_id
      AND v.sentido = p_sentido
      AND v.ubicacion IS NOT NULL
      AND f.dist_m >= -30    -- tolerancia GPS: "recién pasó" cuenta como en la parada
    ORDER BY f.dist_m ASC;
END;
$$ LANGUAGE plpgsql;
"""

# Versión original (línea recta), para downgrade.
FN_ETA_RECTA = """
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


def upgrade() -> None:
    op.execute(FN_ETA_RUTA)


def downgrade() -> None:
    op.execute(FN_ETA_RECTA)
