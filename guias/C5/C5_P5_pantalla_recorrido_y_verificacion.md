# C5 · Parte 5 — Pantallas de recorrido y verificación final del Ciclo 5

## Objetivo
Implementar las dos pantallas finales del flujo "Recorrido de Línea":
- **`PantallaSelectorSentido`** (Pantalla 4) — el usuario elige ida / vuelta / ambos
- **`PantallaMapaRecorrido`** (Pantalla 3) — mapa con la ruta, marcadores y flechas

## Archivos a crear
```
lib/features/usuario/recorrido_linea/pantalla_selector_sentido.dart
lib/features/usuario/recorrido_linea/pantalla_mapa_recorrido.dart
```

---

## 1. `pantalla_selector_sentido.dart`

```dart
// lib/features/usuario/recorrido_linea/pantalla_selector_sentido.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../data/models/linea.dart';

class PantallaSelectorSentido extends StatelessWidget {
  final LineaResumen linea;
  const PantallaSelectorSentido({super.key, required this.linea});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Línea ${linea.numero}'),
        backgroundColor: Colors.blue[800],
        foregroundColor: Colors.white,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(linea.nombre,
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center),
            if (linea.descripcion != null) ...[
              const SizedBox(height: 8),
              Text(linea.descripcion!,
                  style: const TextStyle(color: Colors.grey),
                  textAlign: TextAlign.center),
            ],
            const SizedBox(height: 48),
            const Text('¿Qué sentido deseas ver?',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
            const SizedBox(height: 20),
            _BotonSentido(
              icono: Icons.arrow_forward,
              texto: 'Ida',
              color: Colors.blue[700]!,
              onTap: () => _ir(context, 'ida'),
            ),
            const SizedBox(height: 12),
            _BotonSentido(
              icono: Icons.arrow_back,
              texto: 'Vuelta',
              color: Colors.orange[700]!,
              onTap: () => _ir(context, 'vuelta'),
            ),
            const SizedBox(height: 12),
            _BotonSentido(
              icono: Icons.compare_arrows,
              texto: 'Ambos sentidos',
              color: Colors.purple[700]!,
              onTap: () => _ir(context, 'ambos'),
            ),
          ],
        ),
      ),
    );
  }

  void _ir(BuildContext context, String sentido) {
    context.push('/usuario/mapa/${linea.id}', extra: {
      'sentido': sentido,
      'nombre': '${linea.numero} — ${linea.nombre}',
    });
  }
}

class _BotonSentido extends StatelessWidget {
  final IconData icono;
  final String texto;
  final Color color;
  final VoidCallback onTap;

  const _BotonSentido({
    required this.icono,
    required this.texto,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: onTap,
      icon: Icon(icono),
      label: Text(texto, style: const TextStyle(fontSize: 16)),
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}
```

---

## 2. `pantalla_mapa_recorrido.dart`

```dart
// lib/features/usuario/recorrido_linea/pantalla_mapa_recorrido.dart
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../../data/models/linea.dart';
import '../../../shared/providers/lineas_provider.dart';
import '../../../shared/widgets/mapa_widget.dart';
import '../../../shared/widgets/marcadores_mapa.dart';
import '../../../shared/widgets/flechas_ruta.dart';

class PantallaMapaRecorrido extends ConsumerWidget {
  final String lineaId;
  final String sentido;       // 'ida', 'vuelta' o 'ambos'
  final String lineaNombre;

  const PantallaMapaRecorrido({
    super.key,
    required this.lineaId,
    required this.sentido,
    required this.lineaNombre,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lineaAsync = ref.watch(lineaDetalleProvider(lineaId));

    return Scaffold(
      appBar: AppBar(
        title: Text(lineaNombre),
        backgroundColor: Colors.blue[800],
        foregroundColor: Colors.white,
      ),
      body: lineaAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
        data: (linea) => _MapaConRuta(linea: linea, sentido: sentido),
      ),
    );
  }
}

class _MapaConRuta extends StatelessWidget {
  final LineaDetalle linea;
  final String sentido;

  const _MapaConRuta({required this.linea, required this.sentido});

  @override
  Widget build(BuildContext context) {
    final polilineas = <Polyline>[];
    final marcadores = <Marker>[];

    // Agregar recorrido de ida
    if (sentido == 'ida' || sentido == 'ambos') {
      if (linea.recorridoIda.isNotEmpty) {
        polilineas.add(Polyline(
          points: linea.recorridoIda,
          color: Colors.blue[700]!,
          strokeWidth: 4,
        ));

        // Marcador verde en partida
        if (linea.puntoPartidaIda != null) {
          marcadores.add(marcadorPartida(LatLng(
            linea.puntoPartidaIda!.latitud,
            linea.puntoPartidaIda!.longitud,
          )));
        }

        // Marcador rojo en llegada
        if (linea.puntoLlegadaIda != null) {
          marcadores.add(marcadorLlegada(LatLng(
            linea.puntoLlegadaIda!.latitud,
            linea.puntoLlegadaIda!.longitud,
          )));
        }

        // Flechas de dirección
        marcadores.addAll(generarFlechas(linea.recorridoIda));
      }
    }

    // Agregar recorrido de vuelta
    if (sentido == 'vuelta' || sentido == 'ambos') {
      if (linea.recorridoVuelta.isNotEmpty) {
        polilineas.add(Polyline(
          points: linea.recorridoVuelta,
          color: Colors.orange[700]!,
          strokeWidth: 4,
          isDotted: sentido == 'ambos', // punteado para distinguir en "ambos"
        ));

        if (linea.puntoPartidaVuelta != null) {
          marcadores.add(marcadorPartida(LatLng(
            linea.puntoPartidaVuelta!.latitud,
            linea.puntoPartidaVuelta!.longitud,
          )));
        }

        if (linea.puntoLlegadaVuelta != null) {
          marcadores.add(marcadorLlegada(LatLng(
            linea.puntoLlegadaVuelta!.latitud,
            linea.puntoLlegadaVuelta!.longitud,
          )));
        }

        if (sentido == 'vuelta') {
          marcadores.addAll(generarFlechas(linea.recorridoVuelta));
        }
      }
    }

    // Centro del mapa: primer punto del recorrido visible
    final puntosCentro = sentido == 'vuelta'
        ? linea.recorridoVuelta
        : linea.recorridoIda;
    final centro = puntosCentro.isNotEmpty
        ? puntosCentro[puntosCentro.length ~/ 2]
        : const LatLng(-17.7834, -63.1822);

    return Stack(
      children: [
        MapaWidget(
          centroInicial: centro,
          zoomInicial: 13,
          polilineas: polilineas,
          marcadores: marcadores,
        ),
        // Leyenda de colores
        Positioned(
          bottom: 16,
          left: 16,
          child: _Leyenda(sentido: sentido),
        ),
      ],
    );
  }
}

class _Leyenda extends StatelessWidget {
  final String sentido;
  const _Leyenda({required this.sentido});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.9),
        borderRadius: BorderRadius.circular(8),
        boxShadow: [BoxShadow(color: Colors.black26, blurRadius: 4)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (sentido == 'ida' || sentido == 'ambos')
            _ItemLeyenda(color: Colors.blue[700]!, texto: 'Ida'),
          if (sentido == 'vuelta' || sentido == 'ambos')
            _ItemLeyenda(color: Colors.orange[700]!, texto: 'Vuelta'),
          _ItemLeyenda(color: Colors.green, texto: 'Partida'),
          _ItemLeyenda(color: Colors.red, texto: 'Llegada'),
        ],
      ),
    );
  }
}

class _ItemLeyenda extends StatelessWidget {
  final Color color;
  final String texto;
  const _ItemLeyenda({required this.color, required this.texto});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 16, height: 4, color: color),
          const SizedBox(width: 8),
          Text(texto, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}
```

---

## 3. Verificación del Ciclo 5

### Checklist visual

- [ ] La lista de líneas aparece al abrir la app
- [ ] Al tocar una línea aparece el selector de sentido (Pantalla 4)
- [ ] Al elegir "Ida" se muestra la ruta en **azul** con marcadores verde/rojo
- [ ] Al elegir "Vuelta" se muestra la ruta en **naranja** con marcadores verde/rojo
- [ ] Al elegir "Ambos" se superponen azul (sólido) y naranja (punteado)
- [ ] Las flechas apuntan en la dirección correcta del recorrido
- [ ] El marcador verde está en el punto de inicio de la ruta
- [ ] El marcador rojo está en el punto final de la ruta
- [ ] El mapa se puede mover y hacer zoom sin problemas
- [ ] Si el backend no responde, aparece el botón "Reintentar"

### Verificar coordenadas con la BD

```sql
-- Confirmar que los puntos están en Santa Cruz de la Sierra
SELECT numero,
       ST_Y(punto_partida_ida) AS lat_inicio,   -- debe ser ~-17.825
       ST_X(punto_partida_ida) AS lon_inicio,   -- debe ser ~-63.140
       ST_Y(punto_llegada_ida) AS lat_fin,      -- debe ser ~-17.783
       ST_X(punto_llegada_ida) AS lon_fin       -- debe ser ~-63.182
FROM lineas WHERE numero = '10';
```

---

## 4. Estado del proyecto al terminar el Ciclo 5

```
flutter_app/lib/
├── main.dart                         ✅ C5
├── app/
│   ├── app.dart                      ✅ C5
│   └── routes.dart                   ✅ C5
├── core/constants/
│   └── api_endpoints.dart            ✅ C5
├── data/
│   ├── models/
│   │   ├── linea.dart                ✅ C5
│   │   └── punto_geo.dart            ✅ C5
│   └── services/
│       └── api_service_usuario.dart  ✅ C5
├── shared/
│   ├── providers/
│   │   └── lineas_provider.dart      ✅ C5
│   └── widgets/
│       ├── mapa_widget.dart          ✅ C5
│       ├── marcadores_mapa.dart      ✅ C5
│       └── flechas_ruta.dart         ✅ C5
└── features/usuario/recorrido_linea/
    ├── pantalla_lista_lineas.dart    ✅ C5
    ├── pantalla_selector_sentido.dart ✅ C5
    └── pantalla_mapa_recorrido.dart  ✅ C5
```

---

## Siguiente ciclo
Ciclo 5 completado ✅ → **Ciclo 6 — Líneas cercanas y cálculo de ETA**

> El Ciclo 6 agrega endpoints nuevos al **backend** (`/lineas/cercanas` y
> `/lineas/{id}/eta`) y las pantallas Flutter de "Qué líneas pasan aquí".
