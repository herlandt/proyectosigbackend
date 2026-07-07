# C5 · Parte 1 — pubspec.yaml y API Service del usuario

## Objetivo
Configurar las dependencias Flutter del proyecto y crear el cliente HTTP
de la app del usuario (sin autenticación, solo peticiones GET públicas).

> El Ciclo 5 es **puramente Flutter**. El backend no necesita cambios;
> solo se verifica que `GET /lineas/{id}` devuelve el GeoJSON correcto.

---

## 1. `pubspec.yaml`

```yaml
name: microbuses_sig
description: Sistema de Información Geográfica para Microbuses - Santa Cruz de la Sierra

publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter

  # Mapas y coordenadas
  flutter_map: ^7.0.0
  latlong2: ^0.9.0
  flutter_polyline_points: ^2.0.0

  # GPS
  geolocator: ^12.0.0

  # HTTP y WebSocket
  dio: ^5.7.0
  web_socket_channel: ^3.0.0

  # Almacenamiento seguro del JWT
  flutter_secure_storage: ^9.2.0

  # Captura de fotos
  image_picker: ^1.1.0

  # Estado (Riverpod)
  flutter_riverpod: ^2.5.0

  # Navegación
  go_router: ^14.0.0

  # Servicio en segundo plano (telemetría del conductor)
  flutter_background_service: ^5.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^4.0.0

flutter:
  uses-material-design: true
  assets:
    - assets/icons/
```

Instalar dependencias:
```bash
flutter pub get
```

Crear la carpeta de assets:
```bash
mkdir assets/icons
```

---

## 2. `lib/core/constants/api_endpoints.dart`

```dart
// lib/core/constants/api_endpoints.dart

class ApiEndpoints {
  // Cambiar por la IP real del servidor durante desarrollo
  // En Android Emulator: 10.0.2.2 apunta al localhost de la PC
  // En dispositivo físico: usar la IP local de la PC (ej: 192.168.1.100)
  static const String baseUrl = 'http://10.0.2.2:8000';

  // Autenticación
  static const String login = '$baseUrl/auth/login';

  // Conductores
  static const String registroConductor = '$baseUrl/conductores/registro';
  static const String perfilConductor   = '$baseUrl/conductores/me';

  // Microbuses
  static const String registroMicrobus  = '$baseUrl/microbuses/registro';
  static const String misMicrobuses     = '$baseUrl/microbuses/mis-microbuses';

  // Recorridos (conductor)
  static const String iniciarRecorrido  = '$baseUrl/recorridos/iniciar';
  static String telemetria(String id)   => '$baseUrl/recorridos/$id/telemetria';
  static String terminarRecorrido(String id) => '$baseUrl/recorridos/$id/terminar';
  static String salirRecorrido(String id)    => '$baseUrl/recorridos/$id/salir';

  // Líneas (usuario)
  static const String lineas            = '$baseUrl/lineas';
  static String lineaDetalle(String id) => '$baseUrl/lineas/$id';
  static String lineasCercanas          = '$baseUrl/lineas/cercanas';
  static String microbusesActivos(String id) => '$baseUrl/lineas/$id/microbuses-activos';
  static String etaLinea(String id)     => '$baseUrl/lineas/$id/eta';

  // WebSocket (usuario)
  static String wsPosiciones(String id) =>
      'ws://10.0.2.2:8000/ws/lineas/$id/posiciones';
}
```

---

## 3. `lib/data/services/api_service_usuario.dart`

El servicio del usuario no necesita JWT. Solo hace peticiones GET públicas.

```dart
// lib/data/services/api_service_usuario.dart
import 'package:dio/dio.dart';
import '../../../core/constants/api_endpoints.dart';

class ApiServiceUsuario {
  late final Dio _dio;

  ApiServiceUsuario() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiEndpoints.baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
    ));

    // Interceptor para logging en desarrollo
    _dio.interceptors.add(LogInterceptor(
      requestBody: false,
      responseBody: false,
      logPrint: (o) => debugPrint(o.toString()),
    ));
  }

  /// Lista todas las líneas activas
  Future<List<dynamic>> getLineas() async {
    final response = await _dio.get('/lineas');
    return response.data as List<dynamic>;
  }

  /// Detalle de una línea con GeoJSON
  Future<Map<String, dynamic>> getLineaDetalle(String lineaId) async {
    final response = await _dio.get('/lineas/$lineaId');
    return response.data as Map<String, dynamic>;
  }

  /// Líneas dentro de un radio (se usa en C6)
  Future<List<dynamic>> getLineasCercanas({
    required double lon,
    required double lat,
    int radioMetros = 500,
  }) async {
    final response = await _dio.get('/lineas/cercanas', queryParameters: {
      'lon': lon,
      'lat': lat,
      'radio': radioMetros,
    });
    return response.data as List<dynamic>;
  }

  /// ETA del microbús más cercano (se usa en C6)
  Future<Map<String, dynamic>?> getEta({
    required String lineaId,
    required double lon,
    required double lat,
    required String sentido,
  }) async {
    final response = await _dio.get(
      '/lineas/$lineaId/eta',
      queryParameters: {'lon': lon, 'lat': lat, 'sentido': sentido},
    );
    final lista = response.data as List<dynamic>;
    return lista.isNotEmpty ? lista.first as Map<String, dynamic> : null;
  }
}
```

---

## Verificación de esta parte

1. `flutter pub get` sin errores
2. Los imports de `ApiServiceUsuario` se resuelven correctamente
3. El backend en `localhost:8000` responde a `GET /lineas`

```bash
# Verificar que el backend responde
curl http://localhost:8000/lineas
```

---

## Siguiente paso
→ **C5_P2_modelo_linea_dart.md** — Modelo Dart para parsear la respuesta del API
