"""telemetria: precision_m (accuracy GPS) + map-matching (ubicacion_ruta, desvio_ruta_m)

- precision_m: accuracy del fix GPS en metros (lo manda la app del conductor).
- ubicacion_ruta: posición proyectada sobre el recorrido de la línea
  (ST_ClosestPoint); NULL si el micro estaba a más de ~100 m de la ruta.
- desvio_ruta_m: distancia entre el punto crudo y la ruta.
- vw_microbuses_activos pasa a exponer la posición proyectada cuando existe
  (COALESCE), así el mapa de pasajeros y el ETA ven al micro sobre su calle.

Revision ID: b7c2f4d81e03
Revises: 0131d865ca12
Create Date: 2026-07-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = 'b7c2f4d81e03'
down_revision: Union[str, Sequence[str], None] = '0131d865ca12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Vista con map-matching: usa la posición proyectada a la ruta si existe.
VISTA_SNAP = """
CREATE VIEW vw_microbuses_activos AS
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
    COALESCE(t.ubicacion_ruta, t.ubicacion)        AS ubicacion,
    ST_X(COALESCE(t.ubicacion_ruta, t.ubicacion))  AS longitud,
    ST_Y(COALESCE(t.ubicacion_ruta, t.ubicacion))  AS latitud,
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
"""

# Vista original (para downgrade).
VISTA_ORIGINAL = """
CREATE VIEW vw_microbuses_activos AS
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
"""


def upgrade() -> None:
    op.add_column(
        "telemetria",
        sa.Column("precision_m", sa.Numeric(6, 1), nullable=True),
    )
    op.add_column(
        "telemetria",
        sa.Column(
            "ubicacion_ruta",
            Geometry("POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
    )
    op.add_column(
        "telemetria",
        sa.Column("desvio_ruta_m", sa.Numeric(8, 1), nullable=True),
    )
    # DROP + CREATE (no OR REPLACE): cambia la expresión de columnas de la vista.
    op.execute("DROP VIEW IF EXISTS vw_microbuses_activos;")
    op.execute(VISTA_SNAP)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_microbuses_activos;")
    op.execute(VISTA_ORIGINAL)
    op.drop_column("telemetria", "desvio_ruta_m")
    op.drop_column("telemetria", "ubicacion_ruta")
    op.drop_column("telemetria", "precision_m")
