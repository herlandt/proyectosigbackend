# C5 · Parte 2 — Modelos Dart: Línea y GeoJSON

## Objetivo
Crear las clases Dart que representan los datos de la API:
`LineaResumen` para la lista y `LineaDetalle` para el mapa con GeoJSON.
Estos modelos parsean exactamente lo que devuelve el backend Python.

## Archivos a crear
```
lib/data/models/linea.dart
lib/data/models/punto_geo.dart
```

---

## 1. `lib/data/models/punto_geo.dart`

```dart
// lib/data/models/punto_geo.dart

class PuntoGeo {
  final double longitud;
  final double latitud;

  const PuntoGeo({required this.longitud, required this.latitud});

  factory PuntoGeo.fromJson(Map<String, dynamic> json) => PuntoGeo(
        longitud: (json['longitud'] as num).toDouble(),
        latitud: (json['latitud'] as num).toDouble(),
      );
}
```

---

## 2. `lib/data/models/linea.dart`

```dart
// lib/data/models/linea.dart
import 'package:latlong2/latlong.dart';
import 'punto_geo.dart';

/// Modelo liviano para la lista de líneas (sin geometría)
class LineaResumen {
  final String id;
  final String numero;
  final String nombre;
  final String? descripcion;
  final bool activa;

  const LineaResumen({
    required this.id,
    required this.numero,
    required this.nombre,
    this.descripcion,
    required this.activa,
  });

  factory LineaResumen.fromJson(Map<String, dynamic> json) => LineaResumen(
        id: json['id'] as String,
        numero: json['numero'] as String,
        nombre: json['nombre'] as String,
        descripcion: json['descripcion'] as String?,
        activa: json['activa'] as bool,
      );
}

/// Modelo completo con recorridos GeoJSON para el mapa
class LineaDetalle {
  final String id;
  final String numero;
  final String nombre;
  final String? descripcion;
  final bool activa;

  // Coordenadas de la ruta parseadas a List<LatLng> para flutter_map
  final List<LatLng> recorridoIda;
  final List<LatLng> recorridoVuelta;

  // Puntos extremos para los marcadores verde/rojo
  final PuntoGeo? puntoPartidaIda;
  final PuntoGeo? puntoLlegadaIda;
  final PuntoGeo? puntoPartidaVuelta;
  final PuntoGeo? puntoLlegadaVuelta;

  const LineaDetalle({
    required this.id,
    required this.numero,
    required this.nombre,
    this.descripcion,
    required this.activa,
    required this.recorridoIda,
    required this.recorridoVuelta,
    this.puntoPartidaIda,
    this.puntoLlegadaIda,
    this.puntoPartidaVuelta,
    this.puntoLlegadaVuelta,
  });

  factory LineaDetalle.fromJson(Map<String, dynamic> json) {
    return LineaDetalle(
      id: json['id'] as String,
      numero: json['numero'] as String,
      nombre: json['nombre'] as String,
      descripcion: json['descripcion'] as String?,
      activa: json['activa'] as bool,
      recorridoIda: _parseGeoJson(json['recorrido_ida']),
      recorridoVuelta: _parseGeoJson(json['recorrido_vuelta']),
      puntoPartidaIda: json['punto_partida_ida'] != null
          ? PuntoGeo.fromJson(json['punto_partida_ida'])
          : null,
      puntoLlegadaIda: json['punto_llegada_ida'] != null
          ? PuntoGeo.fromJson(json['punto_llegada_ida'])
          : null,
      puntoPartidaVuelta: json['punto_partida_vuelta'] != null
          ? PuntoGeo.fromJson(json['punto_partida_vuelta'])
          : null,
      puntoLlegadaVuelta: json['punto_llegada_vuelta'] != null
          ? PuntoGeo.fromJson(json['punto_llegada_vuelta'])
          : null,
    );
  }

  /// Parsea un dict GeoJSON LineString a lista de LatLng para flutter_map
  /// El GeoJSON tiene coordenadas en [longitud, latitud]
  /// LatLng de flutter_map espera (latitud, longitud) — orden invertido
  static List<LatLng> _parseGeoJson(dynamic geojson) {
    if (geojson == null) return [];
    final coords = geojson['coordinates'] as List<dynamic>;
    return coords
        .map((c) => LatLng(
              (c[1] as num).toDouble(), // latitud  = índice 1
              (c[0] as num).toDouble(), // longitud = índice 0
            ))
        .toList();
  }

  /// Devuelve el recorrido según el sentido pedido
  List<LatLng> recorridoPorSentido(String sentido) {
    return sentido == 'ida' ? recorridoIda : recorridoVuelta;
  }

  /// Punto de partida según el sentido (para marcador verde)
  PuntoGeo? partidaPorSentido(String sentido) {
    return sentido == 'ida' ? puntoPartidaIda : puntoPartidaVuelta;
  }

  /// Punto de llegada según el sentido (para marcador rojo)
  PuntoGeo? llegadaPorSentido(String sentido) {
    return sentido == 'ida' ? puntoLlegadaIda : puntoLlegadaVuelta;
  }
}
```

---

## 3. Por qué se invierten las coordenadas

El estándar GeoJSON guarda coordenadas como `[longitud, latitud]` (X, Y).
La clase `LatLng` de `latlong2` y `flutter_map` espera `(latitud, longitud)`.
El método `_parseGeoJson` hace esa conversión en `c[1]` (lat) y `c[0]` (lon).

```
GeoJSON:    [-63.14, -17.825]   →  [longitud, latitud]
LatLng:     LatLng(-17.825, -63.14)  →  (latitud, longitud)
```

Este error es muy común y hace que el mapa dibuje las rutas en el lugar
equivocado (espejado). Verificar siempre con el primer punto de una ruta
que caiga dentro de Santa Cruz de la Sierra (aprox. lat -17.7 a -17.9,
lon -63.1 a -63.2).

---

## Siguiente paso
→ **C5_P3_pantalla_principal_usuario.md** — Pantalla con la lista de líneas
