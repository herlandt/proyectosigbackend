# C7 · Flutter · Parte 3 — Pulido, permisos GPS y APK final

## Objetivo
Completar el sistema con: permisos de GPS declarados en los manifiestos,
manejo de errores consistente, y generación del APK para prueba en
dispositivo real.

---

## 1. Permisos de GPS — Android

Editar `android/app/src/main/AndroidManifest.xml`:

```xml
<!-- Agregar dentro de <manifest>, ANTES de <application> -->
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>

<!-- Solo para la app del CONDUCTOR (telemetría en segundo plano) -->
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION"/>
```

Para la app del conductor también agregar dentro de `<application>`:

```xml
<service
    android:name="id.flutter.flutter_background_service.BackgroundService"
    android:foregroundServiceType="location"
    android:exported="false"/>
```

---

## 2. Permisos de GPS — iOS

Editar `ios/Runner/Info.plist` y agregar dentro de `<dict>`:

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>Necesitamos tu ubicación para mostrarte los microbuses cercanos.</string>

<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>Necesitamos tu ubicación en segundo plano para enviar telemetría mientras conduces.</string>

<key>NSLocationAlwaysUsageDescription</key>
<string>La app del conductor envía tu ubicación mientras el recorrido está activo.</string>

<key>UIBackgroundModes</key>
<array>
    <string>location</string>
    <string>fetch</string>
</array>
```

---

## 3. Manejo de errores global en Flutter

Agregar un widget de error genérico reutilizable:

```dart
// lib/shared/widgets/error_widget.dart
import 'package:flutter/material.dart';

class ErrorVista extends StatelessWidget {
  final String mensaje;
  final VoidCallback? onReintentar;

  const ErrorVista({super.key, required this.mensaje, this.onReintentar});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.wifi_off_rounded, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(mensaje,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.grey)),
            if (onReintentar != null) ...[
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: onReintentar,
                icon: const Icon(Icons.refresh),
                label: const Text('Reintentar'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

---

## 4. Manejo de errores en Dio (errores HTTP)

Agregar un interceptor de errores en `ApiServiceUsuario`:

```dart
// Agregar en el constructor de ApiServiceUsuario:
_dio.interceptors.add(InterceptorsWrapper(
  onError: (DioException error, handler) {
    String mensaje;
    switch (error.response?.statusCode) {
      case 404: mensaje = 'No encontrado'; break;
      case 401: mensaje = 'No autorizado'; break;
      case 422: mensaje = 'Datos inválidos'; break;
      case 500: mensaje = 'Error del servidor'; break;
      default:  mensaje = 'Sin conexión al servidor';
    }
    handler.reject(DioException(
      requestOptions: error.requestOptions,
      message: mensaje,
    ));
  },
));
```

---

## 5. Generar APK para prueba en dispositivo

```bash
# APK de debug (más rápido, para pruebas)
flutter build apk --debug

# APK de release (optimizado, para entregar)
flutter build apk --release

# El archivo queda en:
# build/app/outputs/flutter-apk/app-debug.apk
# build/app/outputs/flutter-apk/app-release.apk
```

Instalar en dispositivo conectado por USB:
```bash
flutter install
```

---

## 6. Checklist final del sistema completo

### Backend ✅
- [ ] 15 endpoints REST + 1 WebSocket funcionando
- [ ] PostgreSQL/PostGIS con 5+ líneas de Santa Cruz cargadas
- [ ] JWT, bcrypt, Cloudinary configurados
- [ ] Swagger UI accesible en `/docs`

### App Conductor ✅
- [ ] Registro de conductor con foto
- [ ] Login y token JWT guardado
- [ ] Registro de microbús con fotos
- [ ] Iniciar recorrido → GPS activo en background cada 30s
- [ ] Indicador visual del servicio de fondo activo
- [ ] Terminar recorrido → resumen mostrado
- [ ] Salir por fuerza mayor → motivo obligatorio

### App Usuario ✅
- [ ] Lista de líneas activas
- [ ] Recorrido de línea con polilínea, marcadores verde/rojo y flechas
- [ ] Ida / vuelta / ambos sentidos
- [ ] Líneas cercanas a la ubicación del usuario
- [ ] Esperando microbús → microbuses moviéndose en tiempo real
- [ ] ETA actualizado con cada nueva posición
- [ ] Mensaje claro cuando no hay microbuses activos

---

## 7. Estructura final del proyecto Flutter

```
flutter_app/lib/
├── main.dart
├── app/
│   ├── app.dart
│   └── routes.dart
├── core/constants/
│   └── api_endpoints.dart
├── data/
│   ├── models/
│   │   ├── linea.dart
│   │   ├── punto_geo.dart
│   │   └── posicion_microbus.dart       ← C7
│   └── services/
│       ├── api_service_usuario.dart
│       └── websocket_service.dart       ← C7
├── shared/
│   ├── providers/
│   │   └── lineas_provider.dart         ← + websocket providers C7
│   └── widgets/
│       ├── mapa_widget.dart
│       ├── marcadores_mapa.dart
│       ├── flechas_ruta.dart
│       └── error_widget.dart            ← C7
└── features/usuario/
    ├── recorrido_linea/
    │   ├── pantalla_lista_lineas.dart
    │   ├── pantalla_selector_sentido.dart
    │   └── pantalla_mapa_recorrido.dart
    └── esperando_microbus/              ← C7
        ├── pantalla_selector_linea_espera.dart
        └── pantalla_esperando_microbus.dart
```

**Sistema completo ✅**
