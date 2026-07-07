"""grafo paradas y red_aristas

Revision ID: 0131d865ca12
Revises: a60f1946968f
Create Date: 2026-06-24 10:33:01.437690

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0131d865ca12'
down_revision: Union[str, Sequence[str], None] = 'a60f1946968f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GRAFO = """
CREATE TABLE paradas (
    id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_externo    INTEGER,
    codigo        VARCHAR(50),
    nombre        VARCHAR(150),
    ubicacion     GEOMETRY(Point, 4326) NOT NULL,
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_paradas_ubicacion ON paradas USING GIST(ubicacion);
CREATE UNIQUE INDEX uq_paradas_id_externo ON paradas(id_externo);

CREATE TABLE red_aristas (
    id             BIGSERIAL       PRIMARY KEY,
    linea_id       UUID            NOT NULL REFERENCES lineas(id) ON DELETE CASCADE,
    sentido        sentido_enum    NOT NULL,
    parada_origen  UUID            NOT NULL REFERENCES paradas(id) ON DELETE CASCADE,
    parada_destino UUID            NOT NULL REFERENCES paradas(id) ON DELETE CASCADE,
    orden          INTEGER         NOT NULL,
    distancia_m    DOUBLE PRECISION NOT NULL,
    tiempo_seg     DOUBLE PRECISION NOT NULL,
    geom           GEOMETRY(LineString, 4326),
    created_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_red_aristas_origen ON red_aristas(parada_origen);
CREATE INDEX idx_red_aristas_destino ON red_aristas(parada_destino);
CREATE INDEX idx_red_aristas_linea ON red_aristas(linea_id);

CREATE TABLE red_transbordos (
    id             BIGSERIAL       PRIMARY KEY,
    parada_origen  UUID            NOT NULL REFERENCES paradas(id) ON DELETE CASCADE,
    parada_destino UUID            NOT NULL REFERENCES paradas(id) ON DELETE CASCADE,
    distancia_m    DOUBLE PRECISION NOT NULL,
    tiempo_seg     DOUBLE PRECISION NOT NULL,
    created_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
"""

DROP_GRAFO = """
DROP TABLE IF EXISTS red_transbordos CASCADE;
DROP TABLE IF EXISTS red_aristas CASCADE;
DROP TABLE IF EXISTS paradas CASCADE;
"""


def upgrade() -> None:
    """Crea las tablas del grafo de ruta óptima."""
    op.execute(GRAFO)


def downgrade() -> None:
    op.execute(DROP_GRAFO)
