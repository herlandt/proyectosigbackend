-- ============================================================================
-- AMPLIACIÓN DEL ESQUEMA: Red de transporte (paradas + grafo para Dijkstra)
-- Proyecto: Microbuses SIG — Santa Cruz de la Sierra
-- Motor: PostgreSQL 18 + PostGIS
--
-- Este script es ADITIVO. No modifica las tablas existentes
-- (conductores, lineas, microbuses, recorridos, telemetria).
-- Agrega lo necesario para el requisito "Ruta óptima (Dijkstra)" del
-- Alcance VER2, usando los datos reales de DatosLineas.xls.
--
-- Ejecutar DESPUÉS de base_de_datos_microbuses.sql.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. PARADAS  (los 106 puntos con Stop = 'S' del dataset)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paradas (
    id            UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_externo    INTEGER         UNIQUE,        -- IdPunto del .xls (para el import / joins)
    codigo        VARCHAR(30),                   -- Descripcion del .xls, ej "S-2"
    nombre        VARCHAR(150),
    ubicacion     GEOMETRY(Point, 4326) NOT NULL,
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE paradas IS 'Paradas oficiales de microbús (puntos Stop=S del dataset ArcGIS)';
COMMENT ON COLUMN paradas.id_externo IS 'IdPunto original del .xls, usado solo en la importación';

CREATE INDEX IF NOT EXISTS idx_paradas_ubicacion ON paradas USING GIST(ubicacion);

-- ----------------------------------------------------------------------------
-- 2. RED_ARISTAS  (grafo dirigido: tramo de una línea entre dos paradas consecutivas)
--    Cada arista es un "salto" de bus de una parada a la siguiente sobre una
--    línea y sentido concretos. La impedancia para Dijkstra es tiempo_seg.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS red_aristas (
    id              BIGSERIAL       PRIMARY KEY,
    linea_id        UUID            NOT NULL REFERENCES lineas(id) ON DELETE CASCADE,
    sentido         sentido_enum    NOT NULL,
    parada_origen   UUID            NOT NULL REFERENCES paradas(id) ON DELETE CASCADE,
    parada_destino  UUID            NOT NULL REFERENCES paradas(id) ON DELETE CASCADE,
    orden           INTEGER         NOT NULL,           -- posición del tramo dentro de la ruta
    distancia_m     DOUBLE PRECISION NOT NULL,
    tiempo_seg      DOUBLE PRECISION NOT NULL,
    geom            GEOMETRY(LineString, 4326),         -- forma del tramo (con puntos intermedios)
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_arista_distinta CHECK (parada_origen <> parada_destino),
    CONSTRAINT chk_arista_costos   CHECK (distancia_m >= 0 AND tiempo_seg >= 0)
);

COMMENT ON TABLE red_aristas IS 'Aristas del grafo de transporte: tramo de bus parada→parada de una línea/sentido';
COMMENT ON COLUMN red_aristas.tiempo_seg IS 'Impedancia principal para Dijkstra (tiempo de viaje del tramo)';

CREATE INDEX IF NOT EXISTS idx_aristas_origen  ON red_aristas(parada_origen);
CREATE INDEX IF NOT EXISTS idx_aristas_destino ON red_aristas(parada_destino);
CREATE INDEX IF NOT EXISTS idx_aristas_linea   ON red_aristas(linea_id, sentido);
CREATE INDEX IF NOT EXISTS idx_aristas_geom    ON red_aristas USING GIST(geom);

-- ----------------------------------------------------------------------------
-- 3. RED_TRANSBORDOS  (aristas de caminata entre paradas cercanas de DISTINTAS líneas)
--    Permiten que Dijkstra encuentre rutas con trasbordo (cambiar de micro).
--    Se generan automáticamente con la función de la sección 5.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS red_transbordos (
    id              BIGSERIAL       PRIMARY KEY,
    parada_origen   UUID            NOT NULL REFERENCES paradas(id) ON DELETE CASCADE,
    parada_destino  UUID            NOT NULL REFERENCES paradas(id) ON DELETE CASCADE,
    distancia_m     DOUBLE PRECISION NOT NULL,
    tiempo_seg      DOUBLE PRECISION NOT NULL,           -- caminata: distancia / velocidad peatonal
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_transbordo_distinto CHECK (parada_origen <> parada_destino),
    CONSTRAINT uq_transbordo UNIQUE (parada_origen, parada_destino)
);

COMMENT ON TABLE red_transbordos IS 'Aristas de caminata entre paradas cercanas (para rutas con trasbordo)';

CREATE INDEX IF NOT EXISTS idx_transbordos_origen ON red_transbordos(parada_origen);

-- ----------------------------------------------------------------------------
-- 4. VISTA UNIFICADA DEL GRAFO  (lo que consume el servicio Dijkstra en Python)
--    Une aristas de bus + aristas de caminata en una sola lista de aristas.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_grafo_aristas AS
    SELECT
        'bus'::text         AS tipo,
        a.linea_id::text    AS linea_id,
        a.sentido::text     AS sentido,
        a.parada_origen     AS origen,
        a.parada_destino    AS destino,
        a.distancia_m,
        a.tiempo_seg
    FROM red_aristas a
    UNION ALL
    SELECT
        'caminata'::text    AS tipo,
        NULL                AS linea_id,
        NULL                AS sentido,
        t.parada_origen     AS origen,
        t.parada_destino    AS destino,
        t.distancia_m,
        t.tiempo_seg
    FROM red_transbordos t;

COMMENT ON VIEW vw_grafo_aristas IS 'Aristas combinadas (bus + caminata) para el algoritmo de ruta óptima';

-- ----------------------------------------------------------------------------
-- 5. FUNCIÓN: generar transbordos entre paradas cercanas
--    Crea aristas de caminata entre paradas a <= p_radio_m metros que NO
--    pertenezcan exactamente a la misma posición. Velocidad peatonal ~5 km/h.
--    Uso:  SELECT fn_generar_transbordos(150);   -- 150 metros
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_generar_transbordos(p_radio_m INTEGER DEFAULT 150)
RETURNS INTEGER AS $$
DECLARE
    v_insertadas INTEGER;
    v_vel_peatonal_mps CONSTANT DOUBLE PRECISION := 1.39;  -- 5 km/h en m/s
BEGIN
    DELETE FROM red_transbordos;

    INSERT INTO red_transbordos (parada_origen, parada_destino, distancia_m, tiempo_seg)
    SELECT
        p1.id,
        p2.id,
        ST_Distance(p1.ubicacion::geography, p2.ubicacion::geography) AS dist,
        ST_Distance(p1.ubicacion::geography, p2.ubicacion::geography) / v_vel_peatonal_mps AS t
    FROM paradas p1
    JOIN paradas p2
      ON p1.id <> p2.id
     AND ST_DWithin(p1.ubicacion::geography, p2.ubicacion::geography, p_radio_m);

    GET DIAGNOSTICS v_insertadas = ROW_COUNT;
    RETURN v_insertadas;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fn_generar_transbordos IS 'Genera aristas de caminata entre paradas dentro del radio dado (metros)';

-- ----------------------------------------------------------------------------
-- 6. FUNCIÓN: paradas más cercanas a un punto (para resolver A y B de Dijkstra)
--    El usuario toca un punto en el mapa; el servicio busca las paradas
--    más cercanas para usarlas como nodos de origen/destino.
--    Uso:  SELECT * FROM fn_paradas_cercanas(-63.18, -17.78, 300, 5);
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_paradas_cercanas(
    p_longitud      DOUBLE PRECISION,
    p_latitud       DOUBLE PRECISION,
    p_radio_m       INTEGER DEFAULT 400,
    p_limite        INTEGER DEFAULT 5
)
RETURNS TABLE (
    parada_id        UUID,
    codigo           VARCHAR,
    nombre           VARCHAR,
    longitud         DOUBLE PRECISION,
    latitud          DOUBLE PRECISION,
    distancia_m      DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.codigo,
        p.nombre,
        ST_X(p.ubicacion),
        ST_Y(p.ubicacion),
        ST_Distance(p.ubicacion::geography,
                    ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography) AS d
    FROM paradas p
    WHERE ST_DWithin(p.ubicacion::geography,
                     ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography,
                     p_radio_m)
    ORDER BY d ASC
    LIMIT p_limite;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fn_paradas_cercanas IS 'Paradas más cercanas a un punto (origen/destino para ruta óptima)';

-- ============================================================================
-- FIN DEL SCRIPT — verificación rápida
-- ============================================================================
-- SELECT COUNT(*) AS paradas       FROM paradas;
-- SELECT COUNT(*) AS aristas_bus   FROM red_aristas;
-- SELECT fn_generar_transbordos(150) AS transbordos_creados;
-- SELECT tipo, COUNT(*) FROM vw_grafo_aristas GROUP BY tipo;
