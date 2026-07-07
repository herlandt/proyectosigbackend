# C7 · Flutter · Parte 2 — Pantallas "Esperando Microbús" (Pantallas 8 y 9)

## Objetivo
Implementar el flujo completo de "Esperando Microbús":
- **Pantalla 8** — el usuario selecciona la línea
- **Pantalla 9** — mapa en tiempo real con microbuses moviéndose y ETA actualizado

## Archivos a crear
```
lib/features/usuario/esperando_microbus/pantalla_selector_linea_espera.dart
lib/features/usuario/esperando_microbus/pantalla_esperando_microbus.dart
```

---

## 1. `pantalla_selector_linea_espera.dart` (Pantalla 8)

```dart
// lib/features/usuario/esperando_microbus/pantalla_selector_linea_espera.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../shared/providers/lineas_provider.dart';

class PantallaSelectorLineaEspera extends ConsumerWidget {
  const PantallaSelectorLineaEspera({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lineasAsync = ref.watch(lineasProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Esperando Microbús'),
        backgroundColor: Colors.green[800],
        foregroundColor: Colors.white,
      ),
      body: lineasAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (lineas) => Column(
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                '¿Qué línea estás esperando?',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
              ),
            ),
            Expanded(
              child: ListView.separated(
                itemCount: lineas.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, i) {
                  final linea = lineas[i];
                  return ListTile(
                    leading: CircleAvatar(
                      backgroundColor: Colors.green[800],
                      child: Text(linea.numero,
                          style: const TextStyle(color: Colors.white,
                              fontSize: 12, fontWeight: FontWeight.bold)),
                    ),
                    title: Text(linea.nombre),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push(
                      '/usuario/esperando/${linea.id}',
                      extra: linea,
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 2. `pantalla_esperando_microbus.dart` (Pantalla 9)

```dart
// lib/features/usuario/esperando_microbus/pantalla_esperando_microbus.dart
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import '../../../data/models/linea.dart';
import '../../../data/models/posicion_microbus.dart';
import '../../../data/services/api_service_usuario.dart';
import '../../../shared/providers/lineas_provider.dart';
import '../../../shared/widgets/mapa_widget.dart';
import '../../../shared/widgets/marcadores_mapa.dart';

class PantallaEsperandoMicrobus extends ConsumerStatefulWidget {
  final LineaResumen linea;
  const PantallaEsperandoMicrobus({super.key, required this.linea});

  @override
  ConsumerState<PantallaEsperandoMicrobus> createState() =>
      _PantallaEsperandoMicrobusState();
}

class _PantallaEsperandoMicrobusState
    extends ConsumerState<PantallaEsperandoMicrobus> {
  String _sentido = 'ida';
  LatLng? _posicionUsuario;
  Map<String, PosicionMicrobus> _microbuses = {};   // key: microbus_id
  double? _etaMinutos;
  bool _cargandoEta = false;
  final MapController _mapController = MapController();

  @override
  void initState() {
    super.initState();
    _obtenerUbicacionUsuario();
  }

  Future<void> _obtenerUbicacionUsuario() async {
    try {
      final perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        await Geolocator.requestPermission();
      }
      final pos = await Geolocator.getCurrentPosition();
      setState(() {
        _posicionUsuario = LatLng(pos.latitude, pos.longitude);
      });
      await _actualizarEta();
    } catch (_) {
      // Si falla el GPS usar el centro de Santa Cruz
      setState(() {
        _posicionUsuario = const LatLng(-17.7834, -63.1822);
      });
    }
  }

  Future<void> _actualizarEta() async {
    if (_posicionUsuario == null) return;
    setState(() => _cargandoEta = true);
    try {
      final api = ref.read(apiServiceUsuarioProvider);
      final eta = await api.getEta(
        lineaId: widget.linea.id,
        lon: _posicionUsuario!.longitude,
        lat: _posicionUsuario!.latitude,
        sentido: _sentido,
      );
      setState(() {
        _etaMinutos = eta != null
            ? (eta['eta_minutos'] as num).toDouble()
            : null;
      });
    } catch (_) {
      setState(() => _etaMinutos = null);
    } finally {
      setState(() => _cargandoEta = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Escuchar el WebSocket
    ref.listen(
      posicionesStreamProvider(widget.linea.id),
      (_, next) {
        next.whenData((posicion) {
          if (posicion.sentido == _sentido) {
            setState(() {
              _microbuses[posicion.microbusId] = posicion;
            });
            _actualizarEta(); // recalcular ETA con cada nueva posición
          }
        });
      },
    );

    // Conectar el WebSocket al iniciar
    ref.watch(posicionesStreamProvider(widget.linea.id));

    final lineaAsync = ref.watch(lineaDetalleProvider(widget.linea.id));

    return Scaffold(
      appBar: AppBar(
        title: Text('Esperando Línea ${widget.linea.numero}'),
        backgroundColor: Colors.green[800],
        foregroundColor: Colors.white,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: _SelectorSentido(
            sentido: _sentido,
            onChange: (s) {
              setState(() {
                _sentido = s;
                _microbuses.clear();
                _etaMinutos = null;
              });
              _actualizarEta();
            },
          ),
        ),
      ),
      body: Column(
        children: [
          // Panel de ETA
          _PanelEta(etaMinutos: _etaMinutos, cargando: _cargandoEta),

          // Mapa
          Expanded(
            child: lineaAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Error: $e')),
              data: (linea) => _construirMapa(linea),
            ),
          ),
        ],
      ),
    );
  }

  Widget _construirMapa(LineaDetalle linea) {
    final puntos = _sentido == 'ida' ? linea.recorridoIda : linea.recorridoVuelta;
    final marcadores = <Marker>[];

    // Marcadores de microbuses activos
    for (final mb in _microbuses.values) {
      marcadores.add(marcadorMicrobus(mb.coordenadas, mb.numeroInterno));
    }

    // Marcador del usuario
    if (_posicionUsuario != null) {
      marcadores.add(marcadorUsuario(_posicionUsuario!));
    }

    // Marcadores partida/llegada de la ruta
    final partida = _sentido == 'ida'
        ? linea.puntoPartidaIda
        : linea.puntoPartidaVuelta;
    final llegada = _sentido == 'ida'
        ? linea.puntoLlegadaIda
        : linea.puntoLlegadaVuelta;

    if (partida != null) {
      marcadores.add(marcadorPartida(LatLng(partida.latitud, partida.longitud)));
    }
    if (llegada != null) {
      marcadores.add(marcadorLlegada(LatLng(llegada.latitud, llegada.longitud)));
    }

    return MapaWidget(
      centroInicial: _posicionUsuario ?? const LatLng(-17.7834, -63.1822),
      zoomInicial: 14,
      controlador: _mapController,
      polilineas: puntos.isNotEmpty
          ? [Polyline(points: puntos, color: Colors.green[700]!, strokeWidth: 4)]
          : [],
      marcadores: marcadores,
    );
  }
}

class _SelectorSentido extends StatelessWidget {
  final String sentido;
  final ValueChanged<String> onChange;
  const _SelectorSentido({required this.sentido, required this.onChange});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _Chip(label: 'Ida', activo: sentido == 'ida',
            onTap: () => onChange('ida')),
        const SizedBox(width: 12),
        _Chip(label: 'Vuelta', activo: sentido == 'vuelta',
            onTap: () => onChange('vuelta')),
      ],
    );
  }
}

class _Chip extends StatelessWidget {
  final String label;
  final bool activo;
  final VoidCallback onTap;
  const _Chip({required this.label, required this.activo, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
        decoration: BoxDecoration(
          color: activo ? Colors.white : Colors.green[900],
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(label,
            style: TextStyle(
                color: activo ? Colors.green[800] : Colors.white,
                fontWeight: FontWeight.bold)),
      ),
    );
  }
}

class _PanelEta extends StatelessWidget {
  final double? etaMinutos;
  final bool cargando;
  const _PanelEta({this.etaMinutos, required this.cargando});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: Colors.green[50],
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
      child: cargando
          ? const Center(
              child: SizedBox(height: 20, width: 20,
                  child: CircularProgressIndicator(strokeWidth: 2)))
          : etaMinutos != null
              ? Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.directions_bus, color: Colors.green),
                    const SizedBox(width: 8),
                    Text(
                      'Próximo microbús en ${etaMinutos!.toStringAsFixed(1)} min',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w600),
                    ),
                  ],
                )
              : const Text('No hay microbuses activos en este momento',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey)),
    );
  }
}
```

---

## 3. Agregar rutas en `routes.dart`

```dart
// Agregar en lib/app/routes.dart dentro de la lista de routes:

GoRoute(
  path: '/usuario/esperando',
  builder: (_, __) => const PantallaSelectorLineaEspera(),
),
GoRoute(
  path: '/usuario/esperando/:lineaId',
  builder: (context, state) {
    final linea = state.extra as LineaResumen;
    return PantallaEsperandoMicrobus(linea: linea);
  },
),
```

---

## Siguiente paso
→ **C7_F_P3_pulido_y_cierre.md** — Manejo de errores, permisos GPS y APK final
