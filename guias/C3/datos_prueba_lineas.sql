-- ============================================================
-- DATOS DE PRUEBA: 5 lineas de microbus - Santa Cruz de la Sierra
-- Coordenadas aproximadas basadas en rutas reales
-- ============================================================

-- Limpiar datos de prueba anteriores si los hay
DELETE FROM lineas WHERE numero IN ('10','17','24','51','87');

-- Linea 10: Plan 3000 <-> Centro
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '10', 'Linea 10 - Plan 3000', 'Plan 3000 - 4to Anillo - Centro',
  ST_GeomFromText('LINESTRING(
    -63.1400 -17.8250,
    -63.1480 -17.8180,
    -63.1560 -17.8100,
    -63.1640 -17.8020,
    -63.1720 -17.7950,
    -63.1800 -17.7870,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1800 -17.7870,
    -63.1720 -17.7950,
    -63.1640 -17.8020,
    -63.1560 -17.8100,
    -63.1480 -17.8180,
    -63.1400 -17.8250
  )', 4326)
);

-- Linea 17: Equipetrol <-> Centro
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '17', 'Linea 17 - Equipetrol', 'Barrio Equipetrol - 3er Anillo - Plaza Principal',
  ST_GeomFromText('LINESTRING(
    -63.2100 -17.7700,
    -63.2020 -17.7720,
    -63.1950 -17.7750,
    -63.1880 -17.7790,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1880 -17.7790,
    -63.1950 -17.7750,
    -63.2020 -17.7720,
    -63.2100 -17.7700
  )', 4326)
);

-- Linea 24: Villa 1ro de Mayo <-> Centro
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '24', 'Linea 24 - Villa 1ro de Mayo', 'Villa 1ro de Mayo - Av. Roca y Coronado - Centro',
  ST_GeomFromText('LINESTRING(
    -63.1300 -17.7600,
    -63.1380 -17.7650,
    -63.1460 -17.7700,
    -63.1550 -17.7750,
    -63.1650 -17.7790,
    -63.1750 -17.7810,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1750 -17.7810,
    -63.1650 -17.7790,
    -63.1550 -17.7750,
    -63.1460 -17.7700,
    -63.1380 -17.7650,
    -63.1300 -17.7600
  )', 4326)
);

-- Linea 51: Pampa de la Isla <-> Centro
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '51', 'Linea 51 - Pampa de la Isla', 'Pampa de la Isla - Av. Alemana - 2do Anillo - Centro',
  ST_GeomFromText('LINESTRING(
    -63.1900 -17.7400,
    -63.1880 -17.7480,
    -63.1860 -17.7560,
    -63.1845 -17.7640,
    -63.1835 -17.7720,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1835 -17.7720,
    -63.1845 -17.7640,
    -63.1860 -17.7560,
    -63.1880 -17.7480,
    -63.1900 -17.7400
  )', 4326)
);

-- Linea 87: Urbari <-> Centro
INSERT INTO lineas (numero, nombre, descripcion, recorrido_ida, recorrido_vuelta) VALUES (
  '87', 'Linea 87 - Urbari', 'Urbari - Av. Busch - 1er Anillo - Centro',
  ST_GeomFromText('LINESTRING(
    -63.1600 -17.8050,
    -63.1660 -17.8000,
    -63.1700 -17.7950,
    -63.1740 -17.7900,
    -63.1780 -17.7860,
    -63.1820 -17.7834
  )', 4326),
  ST_GeomFromText('LINESTRING(
    -63.1820 -17.7834,
    -63.1780 -17.7860,
    -63.1740 -17.7900,
    -63.1700 -17.7950,
    -63.1660 -17.8000,
    -63.1600 -17.8050
  )', 4326)
);

-- Verificar insercion
SELECT numero, nombre, ST_NumPoints(recorrido_ida) AS puntos_ida FROM lineas ORDER BY numero;
