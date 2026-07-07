# C5 · Parte 3 — Pantalla principal del usuario (lista de líneas)

## Objetivo
Crear la pantalla de inicio de la app del usuario que muestra la lista
de líneas disponibles. Al tocar una línea navega al selector de sentido
y luego al mapa. Se implementa con Riverpod para manejar el estado.

## Archivos a crear
```
lib/shared/providers/lineas_provider.dart
lib/features/usuario/recorrido_linea/pantalla_lista_lineas.dart
lib/app/routes.dart
lib/app/app.dart
lib/main.dart
```

---

## 1. `lib/shared/providers/lineas_provider.dart`

```dart
// lib/shared/providers/lineas_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/linea.dart';
import '../../data/services/api_service_usuario.dart';

final apiServiceUsuarioProvider = Provider<ApiServiceUsuario>(
  (ref) => ApiServiceUsuario(),
);

/// Provider que carga la lista de líneas activas
final lineasProvider = FutureProvider<List<LineaResumen>>((ref) async {
  final api = ref.read(apiServiceUsuarioProvider);
  final data = await api.getLineas();
  return data.map((j) => LineaResumen.fromJson(j)).toList();
});

/// Provider que carga el detalle de una línea por ID
final lineaDetalleProvider = FutureProvider.family<LineaDetalle, String>(
  (ref, lineaId) async {
    final api = ref.read(apiServiceUsuarioProvider);
    final data = await api.getLineaDetalle(lineaId);
    return LineaDetalle.fromJson(data);
  },
);
```

---

## 2. `lib/features/usuario/recorrido_linea/pantalla_lista_lineas.dart`

```dart
// lib/features/usuario/recorrido_linea/pantalla_lista_lineas.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/providers/lineas_provider.dart';

class PantallaListaLineas extends ConsumerWidget {
  const PantallaListaLineas({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lineasAsync = ref.watch(lineasProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Líneas de Microbús'),
        backgroundColor: Colors.blue[800],
        foregroundColor: Colors.white,
      ),
      body: lineasAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.wifi_off, size: 64, color: Colors.grey),
              const SizedBox(height: 16),
              const Text('No se pudo cargar las líneas'),
              const SizedBox(height: 8),
              ElevatedButton(
                onPressed: () => ref.refresh(lineasProvider),
                child: const Text('Reintentar'),
              ),
            ],
          ),
        ),
        data: (lineas) => RefreshIndicator(
          onRefresh: () => ref.refresh(lineasProvider.future),
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: lineas.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final linea = lineas[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: Colors.blue[800],
                  child: Text(
                    linea.numero,
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
                title: Text(linea.nombre),
                subtitle: linea.descripcion != null
                    ? Text(linea.descripcion!, maxLines: 1,
                        overflow: TextOverflow.ellipsis)
                    : null,
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.push(
                  '/usuario/recorrido/${linea.id}',
                  extra: linea,
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
```

---

## 3. `lib/app/routes.dart`

```dart
// lib/app/routes.dart
import 'package:go_router/go_router.dart';
import 'package:flutter/material.dart';

import '../features/usuario/recorrido_linea/pantalla_lista_lineas.dart';
import '../features/usuario/recorrido_linea/pantalla_selector_sentido.dart';
import '../features/usuario/recorrido_linea/pantalla_mapa_recorrido.dart';
import '../data/models/linea.dart';

final router = GoRouter(
  initialLocation: '/usuario',
  routes: [
    // ── App Usuario ──────────────────────────────────────────
    GoRoute(
      path: '/usuario',
      builder: (_, __) => const PantallaListaLineas(),
    ),
    GoRoute(
      path: '/usuario/recorrido/:lineaId',
      builder: (context, state) {
        final linea = state.extra as LineaResumen;
        return PantallaSelectorSentido(linea: linea);
      },
    ),
    GoRoute(
      path: '/usuario/mapa/:lineaId',
      builder: (context, state) {
        final extra = state.extra as Map<String, dynamic>;
        return PantallaMapaRecorrido(
          lineaId: state.pathParameters['lineaId']!,
          sentido: extra['sentido'] as String,
          lineaNombre: extra['nombre'] as String,
        );
      },
    ),

    // ── App Conductor (se implementó en C2/C3/C4) ────────────
    // GoRoute(path: '/login', ...),
    // GoRoute(path: '/conductor/menu', ...),
  ],
);
```

---

## 4. `lib/app/app.dart`

```dart
// lib/app/app.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'routes.dart';

class MicrobusesApp extends ConsumerWidget {
  const MicrobusesApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'Microbuses SCZ',
      routerConfig: router,
      theme: ThemeData(
        colorSchemeSeed: Colors.blue,
        useMaterial3: true,
      ),
      debugShowCheckedModeBanner: false,
    );
  }
}
```

---

## 5. `lib/main.dart`

```dart
// lib/main.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app/app.dart';

void main() {
  runApp(const ProviderScope(child: MicrobusesApp()));
}
```

---

## Siguiente paso
→ **C5_P4_mapa_widget.md** — Widget reutilizable de flutter_map
