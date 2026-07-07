# C5 · Parte 4 — Widget de mapa reutilizable (`mapa_widget.dart`)

## Objetivo
Crear un widget Flutter que encapsula `flutter_map` con OpenStreetMap.
Recibe las polilíneas, marcadores y configuración como parámetros.
Se reutiliza en "Recorrido de Línea", "Líneas cercanas" y "Esperando microbús".

## Archivos a crear
```
lib/shared/widgets/mapa_widget.dart
```

---

## 1. `lib/shared/widgets/mapa_widget.dart`

```dart
// lib/shared/widgets/mapa_widget.dart
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class MapaWidget extends StatelessWidget {
  final LatLng centroInicial;
  final double zoomInicial;
  final List<Polyline> polilineas;
  final List<Marker> marcadores;
  final MapController? controlador;

  const MapaWidget({
    super.key,
    this.centroInicial = const LatLng(-17.7834, -63.1822), // Plaza 24 de Septiembre
    this.zoomInicial = 13.0,
    this.polilineas = const [],
    this.marcadores = const [],
    this.controlador,
  });

  @override
  Widget build(BuildContext context) {
    return FlutterMap(
      mapController: controlador,
      options: MapOptions(
        initialCenter: centroInicial,
        initialZoom: zoomInicial,
        minZoom: 10,
        maxZoom: 18,
      ),
      children: [
        // Capa de tiles OpenStreetMap (gratuita, sin API key)
        TileLayer(
          urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          userAgentPackageName: 'com.microbuses.sig',
          maxNativeZoom: 19,
        ),
        // Capa de polilíneas (rutas)
        if (polilineas.isNotEmpty)
          PolylineLayer(polylines: polilineas),
        // Capa de marcadores (inicio, fin, microbuses)
        if (marcadores.isNotEmpty)
          MarkerLayer(markers: marcadores),
      ],
    );
  }
}
```

---

## 2. Funciones auxiliares de marcadores

Crear un archivo de utilidades para los marcadores estándar del sistema:

```dart
// lib/shared/widgets/marcadores_mapa.dart
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

/// Marcador verde para el punto de partida de una ruta
Marker marcadorPartida(LatLng punto) => Marker(
      point: punto,
      width: 36,
      height: 36,
      child: const Icon(Icons.location_on, color: Colors.green, size: 36),
    );

/// Marcador rojo para el punto de llegada de una ruta
Marker marcadorLlegada(LatLng punto) => Marker(
      point: punto,
      width: 36,
      height: 36,
      child: const Icon(Icons.location_on, color: Colors.red, size: 36),
    );

/// Marcador azul para la posición actual del usuario
Marker marcadorUsuario(LatLng punto) => Marker(
      point: punto,
      width: 20,
      height: 20,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.blue,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 3),
          boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 4)],
        ),
      ),
    );

/// Marcador amarillo con ícono de bus para un microbús activo
Marker marcadorMicrobus(LatLng punto, String etiqueta) => Marker(
      point: punto,
      width: 48,
      height: 56,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            decoration: BoxDecoration(
              color: Colors.amber[700],
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(etiqueta,
                style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
          ),
          const Icon(Icons.directions_bus, color: Colors.amber, size: 28),
        ],
      ),
    );
```

---

## 3. Cómo dibujar flechas de dirección en la ruta

El enunciado pide flechas indicando el sentido del recorrido. Se implementa
colocando marcadores de flecha a intervalos regulares sobre la polilínea:

```dart
// lib/shared/widgets/flechas_ruta.dart
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

/// Genera marcadores de flecha cada [intervaloMetros] metros a lo largo de la ruta
List<Marker> generarFlechas(List<LatLng> puntos, {double intervaloMetros = 300}) {
  if (puntos.length < 2) return [];

  final flechas = <Marker>[];
  double distanciaAcumulada = 0;

  for (int i = 1; i < puntos.length; i++) {
    final p1 = puntos[i - 1];
    final p2 = puntos[i];

    // Distancia aproximada entre dos puntos (en metros)
    final dist = const Distance().as(LengthUnit.Meter, p1, p2);
    distanciaAcumulada += dist;

    if (distanciaAcumulada >= intervaloMetros) {
      distanciaAcumulada = 0;

      // Ángulo de la flecha en grados
      final angulo = _calcularAngulo(p1, p2);
      final mitad = LatLng(
        (p1.latitude + p2.latitude) / 2,
        (p1.longitude + p2.longitude) / 2,
      );

      flechas.add(Marker(
        point: mitad,
        width: 20,
        height: 20,
        child: Transform.rotate(
          angle: angulo * pi / 180,
          child: const Icon(Icons.arrow_upward, color: Colors.white, size: 16),
        ),
      ));
    }
  }
  return flechas;
}

double _calcularAngulo(LatLng p1, LatLng p2) {
  final dy = p2.latitude - p1.latitude;
  final dx = p2.longitude - p1.longitude;
  return atan2(dx, dy) * 180 / pi;
}
```

---

## Siguiente paso
→ **C5_P5_pantalla_recorrido_y_verificacion.md** — Pantalla del mapa de recorrido y verificación final
