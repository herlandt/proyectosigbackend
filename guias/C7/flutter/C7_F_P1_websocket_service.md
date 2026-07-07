# C7 · Flutter · Parte 1 — WebSocket Service

## Objetivo
Crear `websocket_service.dart` que mantiene la conexión al endpoint
`WS /ws/lineas/{id}/posiciones` y expone un `Stream` de posiciones
que las pantallas pueden escuchar. Incluye reconexión automática.

## Archivos a crear
```
lib/data/services/websocket_service.dart
lib/data/models/posicion_microbus.dart
```

---

## 1. `lib/data/models/posicion_microbus.dart`

```dart
// lib/data/models/posicion_microbus.dart
import 'package:latlong2/latlong.dart';

class PosicionMicrobus {
  final String microbusId;
  final String placa;
  final String numeroInterno;
  final double longitud;
  final double latitud;
  final double velocidad;
  final String sentido;

  const PosicionMicrobus({
    required this.microbusId,
    required this.placa,
    required this.numeroInterno,
    required this.longitud,
    required this.latitud,
    required this.velocidad,
    required this.sentido,
  });

  factory PosicionMicrobus.fromJson(Map<String, dynamic> json) =>
      PosicionMicrobus(
        microbusId:    json['microbus_id'] as String,
        placa:         json['placa'] as String,
        numeroInterno: json['numero_interno'] as String,
        longitud:      (json['longitud'] as num).toDouble(),
        latitud:       (json['latitud'] as num).toDouble(),
        velocidad:     (json['velocidad'] as num).toDouble(),
        sentido:       json['sentido'] as String,
      );

  /// LatLng para usar directamente en flutter_map
  LatLng get coordenadas => LatLng(latitud, longitud);
}
```

---

## 2. `lib/data/services/websocket_service.dart`

```dart
// lib/data/services/websocket_service.dart
import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../core/constants/api_endpoints.dart';
import '../models/posicion_microbus.dart';

class WebSocketService {
  final String lineaId;

  WebSocketChannel? _channel;
  StreamController<PosicionMicrobus>? _controller;
  bool _activo = false;
  int _intentosReconexion = 0;
  static const int _maxIntentos = 5;

  WebSocketService({required this.lineaId});

  /// Stream de posiciones — la pantalla escucha este stream
  Stream<PosicionMicrobus> get posiciones {
    _controller ??= StreamController<PosicionMicrobus>.broadcast();
    return _controller!.stream;
  }

  /// Conectar al WebSocket del backend
  Future<void> conectar() async {
    _activo = true;
    _intentosReconexion = 0;
    await _conectar();
  }

  Future<void> _conectar() async {
    if (!_activo) return;

    try {
      final uri = Uri.parse(ApiEndpoints.wsPosiciones(lineaId));
      _channel = WebSocketChannel.connect(uri);

      _channel!.stream.listen(
        (mensaje) {
          _intentosReconexion = 0; // reset al recibir datos
          try {
            final json = jsonDecode(mensaje as String) as Map<String, dynamic>;
            final posicion = PosicionMicrobus.fromJson(json);
            _controller?.add(posicion);
          } catch (e) {
            debugPrint('WebSocket: error parseando mensaje: $e');
          }
        },
        onError: (error) {
          debugPrint('WebSocket error: $error');
          _reconectar();
        },
        onDone: () {
          debugPrint('WebSocket cerrado');
          _reconectar();
        },
      );
    } catch (e) {
      debugPrint('WebSocket: no se pudo conectar: $e');
      _reconectar();
    }
  }

  Future<void> _reconectar() async {
    if (!_activo || _intentosReconexion >= _maxIntentos) return;

    _intentosReconexion++;
    final espera = Duration(seconds: _intentosReconexion * 2); // backoff
    debugPrint('WebSocket: reconectando en ${espera.inSeconds}s '
        '(intento $_intentosReconexion/$_maxIntentos)');

    await Future.delayed(espera);
    await _conectar();
  }

  /// Cerrar la conexión — llamar en dispose() de la pantalla
  Future<void> desconectar() async {
    _activo = false;
    await _channel?.sink.close();
    await _controller?.close();
    _channel = null;
    _controller = null;
  }
}
```

---

## 3. Provider de Riverpod para el WebSocket

```dart
// Agregar en lib/shared/providers/lineas_provider.dart

import '../../data/services/websocket_service.dart';
import '../../data/models/posicion_microbus.dart';

/// Provider del servicio WebSocket para una línea específica
final websocketServiceProvider =
    Provider.family.autoDispose<WebSocketService, String>(
  (ref, lineaId) {
    final service = WebSocketService(lineaId: lineaId);
    // Se limpia automáticamente al salir de la pantalla
    ref.onDispose(() => service.desconectar());
    return service;
  },
);

/// Stream provider de posiciones para una línea
final posicionesStreamProvider =
    StreamProvider.family<PosicionMicrobus, String>(
  (ref, lineaId) {
    final service = ref.watch(websocketServiceProvider(lineaId));
    service.conectar();
    return service.posiciones;
  },
);
```

---

## Siguiente paso
→ **C7_F_P2_pantalla_esperando_microbus.md** — Pantallas 8 y 9: mapa en tiempo real
