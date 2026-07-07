-- ============================================================================
-- BASE DE DATOS: Sistema de Información Geográfica para Microbuses
-- Ciudad: Santa Cruz de la Sierra, Bolivia
-- Motor: PostgreSQL 14+ con extensión PostGIS
-- Compatible con: Supabase (recomendado)
-- ============================================================================

-- ============================================================================
-- 1. EXTENSIONES NECESARIAS
-- ============================================================================

-- PostGIS para datos geoespaciales (líneas, puntos, distancias, radios)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Generación de UUIDs (identificadores únicos)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 2. TIPOS ENUMERADOS
-- ============================================================================

-- Sexo del conductor
CREATE TYPE sexo_enum AS ENUM ('M', 'F');

-- Categoría de licencia de conducir (Bolivia)
CREATE TYPE categoria_licencia_enum AS ENUM ('A', 'B', 'C', 'P', 'M');

-- Sentido del recorrido
CREATE TYPE sentido_enum AS ENUM ('ida', 'vuelta');

-- Tipo de finalización del recorrido
CREATE TYPE tipo_finalizacion_enum AS ENUM ('normal', 'fuerza_mayor');

-- ============================================================================
-- 3. TABLAS PRINCIPALES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 3.1 CONDUCTORES
-- ----------------------------------------------------------------------------
CREATE TABLE conductores (
    id                    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    documento_identidad   VARCHAR(20)     NOT NULL UNIQUE,
    nombre                VARCHAR(150)    NOT NULL,
    fecha_nacimiento      DATE            NOT NULL,
    sexo                  sexo_enum       NOT NULL,
    telefono              VARCHAR(20)     NOT NULL,
    email                 VARCHAR(150)    NOT NULL UNIQUE,
    categoria_licencia    categoria_licencia_enum NOT NULL,
    foto_url              TEXT            NOT NULL,
    activo                BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_email_formato CHECK (email LIKE '%@%.%'),
    CONSTRAINT chk_fecha_nac_valida CHECK (fecha_nacimiento < CURRENT_DATE)
);

COMMENT ON TABLE conductores IS 'Conductores registrados en el sistema (registro único por persona)';
COMMENT ON COLUMN conductores.foto_url IS 'URL de la foto en el Storage (Supabase Storage o similar)';

-- Índices
CREATE INDEX idx_conductores_documento ON conductores(documento_identidad);
CREATE INDEX idx_conductores_email ON conductores(email);

-- ----------------------------------------------------------------------------
-- 3.2 LÍNEAS DE MICROBÚS
-- ----------------------------------------------------------------------------
CREATE TABLE lineas (
    id                    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero                VARCHAR(20)     NOT NULL UNIQUE,
    nombre                VARCHAR(150)    NOT NULL,
    descripcion           TEXT,
    -- Recorridos como LineString en SRID 4326 (WGS84 - estándar GPS)
    recorrido_ida         GEOMETRY(LineString, 4326) NOT NULL,
    recorrido_vuelta      GEOMETRY(LineString, 4326) NOT NULL,
    -- Puntos de partida y llegada calculados (para mostrar marcas verde/rojo)
    punto_partida_ida     GEOMETRY(Point, 4326),
    punto_llegada_ida     GEOMETRY(Point, 4326),
    punto_partida_vuelta  GEOMETRY(Point, 4326),
    punto_llegada_vuelta  GEOMETRY(Point, 4326),
    activa                BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE lineas IS 'Líneas de microbús con sus recorridos de ida y vuelta';
COMMENT ON COLUMN lineas.numero IS 'Identificador público de la línea, ej: "10", "23", "100"';
COMMENT ON COLUMN lineas.recorrido_ida IS 'Geometría del recorrido en sentido de ida (LineString en WGS84)';

-- Índices espaciales (GIST) para consultas de radio y proximidad
CREATE INDEX idx_lineas_recorrido_ida ON lineas USING GIST(recorrido_ida);
CREATE INDEX idx_lineas_recorrido_vuelta ON lineas USING GIST(recorrido_vuelta);
CREATE INDEX idx_lineas_numero ON lineas(numero);

-- ----------------------------------------------------------------------------
-- 3.3 MICROBUSES
-- ----------------------------------------------------------------------------
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

COMMENT ON TABLE microbuses IS 'Microbuses asignados a líneas con su conductor';
COMMENT ON COLUMN microbuses.fecha_baja IS 'Si es NULL, el microbús está activo';

CREATE INDEX idx_microbuses_conductor ON microbuses(conductor_id);
CREATE INDEX idx_microbuses_linea ON microbuses(linea_id);
CREATE INDEX idx_microbuses_placa ON microbuses(placa);
CREATE INDEX idx_microbuses_activos ON microbuses(linea_id) WHERE fecha_baja IS NULL;

-- ----------------------------------------------------------------------------
-- 3.4 FOTOS DE MICROBUSES (relación 1:N)
-- ----------------------------------------------------------------------------
CREATE TABLE microbuses_fotos (
    id                    UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    microbus_id           UUID            NOT NULL REFERENCES microbuses(id) ON DELETE CASCADE,
    foto_url              TEXT            NOT NULL,
    orden                 INTEGER         NOT NULL DEFAULT 0,
    created_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE microbuses_fotos IS 'Múltiples fotos por microbús';

CREATE INDEX idx_fotos_microbus ON microbuses_fotos(microbus_id);

-- ----------------------------------------------------------------------------
-- 3.5 RECORRIDOS (sesiones de viaje del conductor)
-- ----------------------------------------------------------------------------
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

COMMENT ON TABLE recorridos IS 'Sesiones de viaje. Si fecha_fin es NULL, el recorrido está activo';
COMMENT ON COLUMN recorridos.motivo_salida IS 'OBLIGATORIO cuando tipo_finalizacion = fuerza_mayor';

CREATE INDEX idx_recorridos_microbus ON recorridos(microbus_id);
CREATE INDEX idx_recorridos_linea ON recorridos(linea_id);
CREATE INDEX idx_recorridos_activos ON recorridos(linea_id, sentido) WHERE fecha_fin IS NULL;
CREATE INDEX idx_recorridos_fecha ON recorridos(fecha_inicio DESC);

-- ----------------------------------------------------------------------------
-- 3.6 TELEMETRÍA (puntos GPS enviados cada 30 segundos)
-- ----------------------------------------------------------------------------
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

COMMENT ON TABLE telemetria IS 'Puntos GPS enviados cada 30 segundos durante el recorrido';
COMMENT ON COLUMN telemetria.velocidad IS 'Velocidad en km/h';
COMMENT ON COLUMN telemetria.distancia_recorrida IS 'Distancia acumulada en km desde inicio del recorrido';
COMMENT ON COLUMN telemetria.tiempo_transcurrido IS 'Segundos transcurridos desde inicio del recorrido';

-- Índice espacial para consultas de proximidad (microbuses cercanos a un punto)
CREATE INDEX idx_telemetria_ubicacion ON telemetria USING GIST(ubicacion);
CREATE INDEX idx_telemetria_recorrido ON telemetria(recorrido_id);
CREATE INDEX idx_telemetria_timestamp ON telemetria(timestamp_evento DESC);
CREATE INDEX idx_telemetria_recorrido_ts ON telemetria(recorrido_id, timestamp_evento DESC);

-- ============================================================================
-- 4. FUNCIONES AUXILIARES
-- ============================================================================

-- Trigger para actualizar updated_at automáticamente
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

-- Calcular automáticamente puntos de partida y llegada al insertar/actualizar líneas
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

-- ============================================================================
-- 5. VISTAS ÚTILES
-- ============================================================================

-- Vista: microbuses activos con su última posición conocida
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

COMMENT ON VIEW vw_microbuses_activos IS 'Microbuses actualmente en servicio con su última posición GPS';

-- ============================================================================
-- 6. FUNCIONES DE NEGOCIO (CONSULTAS GEOESPACIALES)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 6.1 ¿Qué líneas de microbús pasan por un punto dentro de un radio?
-- Uso desde Flutter:
--   SELECT * FROM fn_lineas_cercanas(-63.1822, -17.7834, 500);
-- ----------------------------------------------------------------------------
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
        l.id,
        l.numero,
        l.nombre,
        LEAST(
            ST_Distance(l.recorrido_ida::geography,    ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography),
            ST_Distance(l.recorrido_vuelta::geography, ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography)
        ) AS distancia_minima_m,
        ST_DWithin(
            l.recorrido_ida::geography,
            ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography,
            p_radio_metros
        ) AS pasa_ida,
        ST_DWithin(
            l.recorrido_vuelta::geography,
            ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography,
            p_radio_metros
        ) AS pasa_vuelta
    FROM lineas l
    WHERE l.activa = TRUE
      AND (
          ST_DWithin(l.recorrido_ida::geography,    ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography, p_radio_metros) OR
          ST_DWithin(l.recorrido_vuelta::geography, ST_SetSRID(ST_MakePoint(p_longitud, p_latitud), 4326)::geography, p_radio_metros)
      )
    ORDER BY distancia_minima_m ASC;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- 6.2 Microbuses activos de una línea (para "Esperando microbús")
-- Uso desde Flutter:
--   SELECT * FROM fn_microbuses_linea_activos('uuid-de-la-linea', 'ida');
-- ----------------------------------------------------------------------------
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
    SELECT
        v.microbus_id,
        v.placa,
        v.numero_interno,
        v.longitud,
        v.latitud,
        v.velocidad,
        v.ultima_actualizacion
    FROM vw_microbuses_activos v
    WHERE v.linea_id = p_linea_id
      AND v.sentido  = p_sentido;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- 6.3 ETA (Estimated Time of Arrival) — microbús más cercano de una línea
-- Calcula el tiempo estimado de llegada del microbús más cercano al punto
-- del usuario, asumiendo velocidad promedio de 25 km/h o la real si está disponible.
-- Uso desde Flutter:
--   SELECT * FROM fn_eta_microbus_cercano('uuid-linea', 'ida', -63.18, -17.78);
-- ----------------------------------------------------------------------------
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
        v.microbus_id,
        v.placa,
        v.numero_interno,
        v.longitud,
        v.latitud,
        ST_Distance(v.ubicacion::geography, v_punto_usuario) AS distancia_metros,
        v.velocidad,
        -- ETA: distancia (km) / velocidad (km/h) * 60 = minutos
        -- Si velocidad < 5 km/h, usar 25 km/h como promedio (microbús detenido o muy lento)
        ROUND(
            (ST_Distance(v.ubicacion::geography, v_punto_usuario) / 1000.0) /
            CASE WHEN v.velocidad < 5 THEN 25 ELSE v.velocidad END * 60,
            1
        )::DECIMAL AS eta_minutos
    FROM vw_microbuses_activos v
    WHERE v.linea_id = p_linea_id
      AND v.sentido  = p_sentido
    ORDER BY distancia_metros ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. POLÍTICAS DE SEGURIDAD (Row Level Security para Supabase)
-- ============================================================================

-- Habilitar RLS en tablas sensibles
ALTER TABLE conductores      ENABLE ROW LEVEL SECURITY;
ALTER TABLE microbuses       ENABLE ROW LEVEL SECURITY;
ALTER TABLE recorridos       ENABLE ROW LEVEL SECURITY;
ALTER TABLE telemetria       ENABLE ROW LEVEL SECURITY;

-- Líneas son públicas (cualquier usuario puede leerlas)
ALTER TABLE lineas ENABLE ROW LEVEL SECURITY;
CREATE POLICY pol_lineas_lectura_publica ON lineas
    FOR SELECT USING (TRUE);

-- Conductores: solo pueden leer/editar su propio registro
-- (asume que el auth.uid() de Supabase coincide con conductores.id)
CREATE POLICY pol_conductor_lectura_propia ON conductores
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY pol_conductor_edicion_propia ON conductores
    FOR UPDATE USING (auth.uid() = id);

-- Microbuses: el conductor solo ve sus propios microbuses asignados
CREATE POLICY pol_microbus_propio ON microbuses
    FOR SELECT USING (auth.uid() = conductor_id);

-- Recorridos: el conductor solo gestiona los suyos
CREATE POLICY pol_recorrido_propio ON recorridos
    FOR ALL USING (auth.uid() = conductor_id);

-- Telemetría: el conductor solo escribe en sus recorridos
CREATE POLICY pol_telemetria_insertar ON telemetria
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM recorridos r
            WHERE r.id = telemetria.recorrido_id
            AND r.conductor_id = auth.uid()
        )
    );

-- Telemetría: lectura pública para "Esperando microbús" (los usuarios necesitan ver dónde están los micros)
CREATE POLICY pol_telemetria_lectura_publica ON telemetria
    FOR SELECT USING (TRUE);

-- ============================================================================
-- 8. DATOS DE EJEMPLO (para testing)
-- ============================================================================

-- Línea de ejemplo en Santa Cruz de la Sierra
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES
(
    '10',
    'Línea 10',
    'Plan 3000 - Centro',
    ST_GeomFromText('LINESTRING(
        -63.140000 -17.825000,
        -63.150000 -17.815000,
        -63.165000 -17.800000,
        -63.180000 -17.785000,
        -63.182000 -17.783400
    )', 4326),
    ST_GeomFromText('LINESTRING(
        -63.182000 -17.783400,
        -63.180000 -17.785000,
        -63.165000 -17.800000,
        -63.150000 -17.815000,
        -63.140000 -17.825000
    )', 4326)
);

-- Conductor de ejemplo
INSERT INTO conductores (
    documento_identidad, nombre, fecha_nacimiento, sexo,
    telefono, email, categoria_licencia, foto_url
) VALUES (
    '12345678',
    'Juan Pérez Gutiérrez',
    '1985-03-15',
    'M',
    '+59170000000',
    'juan.perez@example.com',
    'C',
    'https://storage.example.com/conductores/juan.jpg'
);

-- ============================================================================
-- 9. QUERIES DE EJEMPLO PARA EL DESARROLLO
-- ============================================================================

/*

-- Q1: ¿Qué líneas pasan dentro de 500 metros de la Plaza 24 de Septiembre?
SELECT * FROM fn_lineas_cercanas(-63.1822, -17.7834, 500);

-- Q2: Microbuses activos de la línea 10 en sentido de ida
SELECT * FROM fn_microbuses_linea_activos(
    (SELECT id FROM lineas WHERE numero = '10'),
    'ida'
);

-- Q3: ETA del microbús más cercano de la línea 10 (sentido ida) a la ubicación del usuario
SELECT * FROM fn_eta_microbus_cercano(
    (SELECT id FROM lineas WHERE numero = '10'),
    'ida',
    -63.1822,
    -17.7834
);

-- Q4: Recorrido completo de una línea (ida + vuelta) en formato GeoJSON para el mapa
SELECT
    numero,
    nombre,
    ST_AsGeoJSON(recorrido_ida)    AS geojson_ida,
    ST_AsGeoJSON(recorrido_vuelta) AS geojson_vuelta,
    ST_AsGeoJSON(punto_partida_ida)  AS partida_ida,
    ST_AsGeoJSON(punto_llegada_ida)  AS llegada_ida
FROM lineas
WHERE numero = '10';

-- Q5: Iniciar un recorrido (lo hace el conductor desde la app)
INSERT INTO recorridos (microbus_id, conductor_id, linea_id, sentido, ubicacion_inicio)
VALUES (
    'uuid-microbus',
    'uuid-conductor',
    'uuid-linea',
    'ida',
    ST_SetSRID(ST_MakePoint(-63.140, -17.825), 4326)
)
RETURNING id;

-- Q6: Insertar telemetría (cada 30 segundos desde la app del conductor)
INSERT INTO telemetria (
    recorrido_id, ubicacion, fecha, hora,
    velocidad, distancia_recorrida, tiempo_transcurrido
) VALUES (
    'uuid-recorrido',
    ST_SetSRID(ST_MakePoint(-63.155, -17.810), 4326),
    CURRENT_DATE,
    CURRENT_TIME,
    35.5,
    2.350,
    240
);

-- Q7: Terminar recorrido normal
UPDATE recorridos
SET fecha_fin           = NOW(),
    tipo_finalizacion   = 'normal',
    ubicacion_fin       = ST_SetSRID(ST_MakePoint(-63.182, -17.7834), 4326)
WHERE id = 'uuid-recorrido';

-- Q8: Salir del recorrido por fuerza mayor
UPDATE recorridos
SET fecha_fin           = NOW(),
    tipo_finalizacion   = 'fuerza_mayor',
    motivo_salida       = 'Falla mecánica en el motor',
    ubicacion_fin       = ST_SetSRID(ST_MakePoint(-63.165, -17.800), 4326)
WHERE id = 'uuid-recorrido';

*/

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
