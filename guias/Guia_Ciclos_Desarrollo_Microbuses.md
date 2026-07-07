# Guía de Ciclos de Desarrollo — Sistema de Microbuses SIG
### Santa Cruz de la Sierra · Flutter + Python FastAPI + PostgreSQL/PostGIS

> Cada ciclo produce algo **funcional y verificable**. Al terminar cada uno tenés un sistema que corre, no código suelto sin poder probar. Los ciclos están ordenados por dependencia: no podés hacer el 3 sin el 2, ni el 5 sin el 4.

---

## Resumen de los 7 ciclos

| Ciclo | Nombre | Qué queda funcionando al terminar |
|---|---|---|
| **1** | Fundación | BD creada, backend levanta, conexión verificada |
| **2** | Conductores y Auth | Registro de conductor, login, JWT funcional |
| **3** | Microbuses y Líneas | Registro de microbús, carga de líneas con rutas geo |
| **4** | Telemetría en vivo | Conductor inicia recorrido y envía GPS cada 30s |
| **5** | App Usuario — Mapas | Usuario ve rutas de líneas en el mapa |
| **6** | Líneas cercanas y ETA | "Qué pasa aquí" y tiempo estimado de llegada |
| **7** | Tiempo real y cierre | WebSocket, "Esperando microbús", pulido final |

---

## CICLO 1 — Fundación del sistema
**Duración estimada: 3–5 días**

### Objetivo
Que el backend levante, la base de datos exista con su estructura completa y ambos se conecten correctamente. Sin esto no se puede hacer nada más.

### Tareas — Base de Datos (PostgreSQL + PostGIS)

- [ ] Instalar PostgreSQL 14+ y la extensión PostGIS en el servidor/máquina local
- [ ] Crear la base de datos `microbuses_sig`
- [ ] Ejecutar el script SQL completo (`base_de_datos_microbuses.sql`) para crear todas las tablas, índices, tipos enumerados, triggers y funciones
- [ ] Verificar que PostGIS esté activo: `SELECT PostGIS_Version();`
- [ ] Verificar que los índices GIST (espaciales) se crearon correctamente

### Tareas — Backend Python (FastAPI)

- [ ] Crear el entorno virtual Python: `python -m venv venv`
- [ ] Instalar todas las dependencias del `requirements.txt`
- [ ] Crear el archivo `app/core/config.py` con las variables de entorno (URL de la BD, JWT secret, etc.)
- [ ] Crear `app/core/database.py` con la sesión de SQLAlchemy y la conexión a PostgreSQL
- [ ] Crear los modelos ORM (SQLAlchemy) para las 6 tablas: `conductores`, `lineas`, `microbuses`, `microbuses_fotos`, `recorridos`, `telemetria`
- [ ] Configurar Alembic y generar la primera migración
- [ ] Crear `main.py` con la app FastAPI básica (sin routers aún)
- [ ] Levantar el servidor: `uvicorn main:app --reload`
- [ ] Verificar que `/docs` (Swagger UI) abre en el navegador

### Verificación del ciclo ✅
- PostgreSQL corre y acepta conexiones
- Las tablas existen con sus constraints y tipos geoespaciales
- FastAPI levanta sin errores en `uvicorn main:app --reload`
- Swagger UI visible en `http://localhost:8000/docs`
- SQLAlchemy conecta a la BD sin errores en los logs

### Archivos que existen al terminar
```
backend/
├── main.py
├── requirements.txt
├── .env
├── alembic.ini
├── alembic/versions/001_initial.py
└── app/
    ├── core/
    │   ├── config.py
    │   └── database.py
    └── models/
        ├── conductor.py
        ├── microbus.py
        ├── linea.py
        ├── recorrido.py
        └── telemetria.py
```

---

## CICLO 2 — Registro de conductor y autenticación
**Duración estimada: 4–6 días**

### Objetivo
Un conductor puede registrarse por primera vez y luego iniciar sesión. El sistema devuelve un JWT que se usará en todos los ciclos siguientes. También se construye la pantalla de registro en Flutter.

### Dependencia
Ciclo 1 completado.

### Tareas — Backend Python

- [ ] Crear `app/core/security.py`: función para hashear contraseñas (bcrypt) y crear/verificar tokens JWT
- [ ] Crear `app/schemas/conductor.py`: modelos Pydantic para entrada y salida del conductor
- [ ] Crear `app/routers/auth.py` con el endpoint `POST /auth/login`
  - Recibe `{email, password}`
  - Verifica credenciales contra la BD
  - Devuelve `{access_token, token_type}`
- [ ] Crear `app/routers/conductores.py` con los endpoints:
  - `POST /conductores/registro`: crea el conductor, sube la foto, guarda en BD
  - `GET /conductores/me`: devuelve los datos del conductor autenticado (requiere JWT)
- [ ] Crear `app/services/storage_service.py` para subir la foto a Cloudinary o MinIO
- [ ] Registrar los routers en `main.py`
- [ ] Probar todos los endpoints en Swagger UI

### Tareas — Flutter (App Conductor)

- [ ] Configurar `pubspec.yaml` con todos los paquetes del proyecto
- [ ] Crear `core/constants/api_endpoints.dart` con las URLs base y de cada endpoint
- [ ] Crear `data/services/api_service.dart`: cliente HTTP con `dio`, configurado con la URL base y el interceptor que agrega el JWT al header
- [ ] Crear `data/services/auth_service.dart`: login y guardado del token en `flutter_secure_storage`
- [ ] Crear la pantalla de **Registro de Conductor** (Pantalla 2):
  - Formulario con todos los campos requeridos
  - `image_picker` para seleccionar la foto
  - Llamada a `POST /conductores/registro`
- [ ] Crear la pantalla de **Login**:
  - Campos email y contraseña
  - Llamada a `POST /auth/login`, guarda el JWT
  - Redirige al menú principal del conductor al autenticarse
- [ ] Configurar `go_router` con las rutas iniciales: `/login`, `/registro`, `/conductor/menu`

### Verificación del ciclo ✅
- `POST /conductores/registro` crea el registro en la BD con la foto subida
- `POST /auth/login` devuelve un JWT válido
- `GET /conductores/me` con JWT devuelve los datos correctos
- `GET /conductores/me` sin JWT devuelve error 401
- En Flutter: el conductor puede registrarse, iniciar sesión y quedar autenticado
- El token JWT se guarda de forma segura y persiste al cerrar la app

---

## CICLO 3 — Microbuses y carga de líneas
**Duración estimada: 4–6 días**

### Objetivo
El conductor puede registrar su microbús. Las líneas de microbús con sus recorridos geográficos existen en la base de datos y la API las expone. Es el ciclo donde se trabaja por primera vez con datos geoespaciales.

### Dependencia
Ciclo 2 completado.

### Tareas — Backend Python

- [ ] Crear `app/schemas/microbus.py` y `app/schemas/linea.py`
- [ ] Crear `app/routers/microbuses.py` con los endpoints:
  - `POST /microbuses/registro`: registra el microbús con sus fotos (requiere JWT)
  - `GET /microbuses/mis-microbuses`: lista los microbuses del conductor autenticado
- [ ] Crear `app/routers/lineas.py` con los endpoints:
  - `GET /lineas`: lista todas las líneas activas
  - `GET /lineas/{id}`: devuelve una línea con sus recorridos en formato **GeoJSON** (listo para `flutter_map`)
- [ ] Crear `app/services/geo_service.py` con la función para serializar geometrías PostGIS a GeoJSON usando GeoAlchemy2
- [ ] Cargar datos de prueba: insertar al menos 5 líneas reales de Santa Cruz de la Sierra con sus coordenadas de recorrido de ida y vuelta

### Tareas — Flutter (App Conductor)

- [ ] Crear la pantalla de **Registro de Microbús**:
  - Formulario con todos los campos requeridos
  - `image_picker` para seleccionar múltiples fotos
  - Selector de línea (consume `GET /lineas`)
  - Llamada a `POST /microbuses/registro`
- [ ] Crear el **menú principal del conductor** con accesos a: Registrar microbús, Iniciar recorrido (deshabilitado hasta el ciclo 4)

### Tareas — Flutter (App Usuario) — inicio

- [ ] Crear `data/services/api_service.dart` en la app de usuario (sin auth, solo GET públicos)
- [ ] Crear la pantalla principal del usuario (Pantalla 1): lista de líneas consumiendo `GET /lineas`

### Verificación del ciclo ✅
- `POST /microbuses/registro` guarda el microbús y sus fotos correctamente
- `GET /lineas` devuelve la lista de líneas
- `GET /lineas/{id}` devuelve el recorrido en GeoJSON válido
- En Flutter Conductor: el conductor puede registrar su microbús
- En Flutter Usuario: la lista de líneas se muestra en pantalla

---

## CICLO 4 — Telemetría: el conductor transmite su posición
**Duración estimada: 5–7 días**

### Objetivo
El conductor puede iniciar un recorrido, y desde ese momento la app envía automáticamente su posición GPS al backend cada 30 segundos, incluso con la pantalla apagada. El conductor puede terminar el recorrido normalmente o salir por fuerza mayor.

### Dependencia
Ciclo 3 completado.

### Tareas — Backend Python

- [ ] Crear `app/schemas/recorrido.py` y `app/schemas/telemetria.py`
- [ ] Crear `app/routers/recorridos.py` con los endpoints:
  - `POST /recorridos/iniciar`: crea la sesión de recorrido, registra ubicación inicial, devuelve `{recorrido_id}`
  - `POST /recorridos/{id}/telemetria`: inserta un punto GPS en la tabla `telemetria`; valida que el recorrido pertenezca al conductor del JWT
  - `POST /recorridos/{id}/terminar`: marca `fecha_fin`, `tipo_finalizacion = 'normal'`, guarda ubicación final
  - `POST /recorridos/{id}/salir`: marca `tipo_finalizacion = 'fuerza_mayor'`, exige el campo `motivo_salida` (error 422 si viene vacío)

### Tareas — Flutter (App Conductor)

- [ ] Crear `data/services/location_service.dart`: acceso al GPS con `geolocator`, calcula velocidad y distancia acumulada
- [ ] Crear `data/services/background_service.dart`: servicio con `flutter_background_service` que corre un `Timer.periodic` de 30 segundos para enviar telemetría aunque la app esté en segundo plano
- [ ] Crear la pantalla **Iniciar Recorrido** (Pantalla 10):
  - Selector de sentido (ida / vuelta)
  - Botón "Iniciar recorrido" → llama `POST /recorridos/iniciar`, guarda el `recorrido_id`
  - Activa el servicio de telemetría en segundo plano
  - Muestra información del recorrido en curso (tiempo, distancia, velocidad)
- [ ] Crear la pantalla **Terminar Recorrido** (Pantalla 11):
  - Resumen del recorrido
  - Botón "Terminar" → llama `POST /recorridos/{id}/terminar`, detiene el servicio de fondo
- [ ] Crear la pantalla **Salir del Recorrido** (Pantalla 12):
  - Campo de texto obligatorio para el motivo
  - Botón "Salir" → llama `POST /recorridos/{id}/salir`, detiene el servicio de fondo
  - Validación local: no permite enviar con el campo vacío

### Verificación del ciclo ✅
- El conductor puede iniciar un recorrido y el registro aparece en la tabla `recorridos`
- Cada 30 segundos se insertan filas en la tabla `telemetria` con posición real del dispositivo
- Al minimizar la app, el envío continúa (verificar en la BD que siguen llegando filas)
- Terminar recorrido cierra la sesión correctamente
- Salir del recorrido sin motivo devuelve error 422 desde el backend
- Salir con motivo cierra la sesión y guarda el motivo en la BD

---

## CICLO 5 — App Usuario: visualización de rutas en el mapa
**Duración estimada: 4–6 días**

### Objetivo
El usuario puede ver en el mapa la ruta completa de cualquier línea (ida, vuelta o ambas), con el marcador verde en la partida, rojo en la llegada y flechas indicando el sentido. Es el primer ciclo puramente visual del lado usuario.

### Dependencia
Ciclo 3 completado (las líneas con GeoJSON deben existir).

### Tareas — Flutter (App Usuario)

- [ ] Crear `shared/widgets/mapa_widget.dart`: widget reutilizable que envuelve `flutter_map` con tiles de OpenStreetMap configurados
- [ ] Implementar la funcionalidad **Recorrido de Línea** (Pantallas 3 y 4):
  - Lista de líneas → el usuario selecciona una
  - Selector de sentido: ida / vuelta / ambos
  - Llamada a `GET /lineas/{id}` para obtener el GeoJSON
  - Dibujar la polilínea del recorrido sobre el mapa con `flutter_map`
  - Marcador **verde** en el punto de partida (`ST_StartPoint`, ya viene en la respuesta)
  - Marcador **rojo** en el punto de llegada (`ST_EndPoint`, ya viene en la respuesta)
  - Flechas sobre la polilínea indicando el sentido (íconos de flecha pequeños cada N metros)
- [ ] Crear `data/models/linea.dart` que parsea el GeoJSON recibido del backend
- [ ] Conectar la pantalla principal del usuario (lista de líneas) con el mapa de recorrido

### Tareas — Backend Python (ajustes menores)

- [ ] Verificar que `GET /lineas/{id}` devuelve en la respuesta:
  - GeoJSON del recorrido de ida
  - GeoJSON del recorrido de vuelta
  - Coordenadas del punto de partida y llegada de cada sentido (para los marcadores verde/rojo)

### Verificación del ciclo ✅
- El usuario puede seleccionar una línea desde la lista
- Elegir "ida" muestra solo el recorrido de ida con marcadores correctos
- Elegir "vuelta" muestra solo el recorrido de vuelta
- Elegir "ambos" superpone ambos recorridos en el mapa
- El marcador verde está exactamente en el inicio de la ruta
- El marcador rojo está exactamente en el final de la ruta
- Las flechas indican el sentido de circulación

---

## CICLO 6 — Líneas cercanas y cálculo de ETA
**Duración estimada: 5–7 días**

### Objetivo
El usuario puede tocar un punto en el mapa (o usar su ubicación actual) y ver qué líneas de microbús pasan cerca. Al seleccionar una línea, también puede ver en cuántos minutos llegará el microbús más cercano. Este es el ciclo más intensivo en lógica geoespacial.

### Dependencia
Ciclos 4 y 5 completados (necesita microbuses activos transmitiendo para probar el ETA).

### Tareas — Backend Python

- [ ] En `app/services/geo_service.py` implementar la consulta que usa la función SQL `fn_lineas_cercanas(lon, lat, radio)` ya definida en la BD
- [ ] En `app/routers/lineas.py` agregar:
  - `GET /lineas/cercanas?lon=&lat=&radio=`: llama al geo_service y devuelve la lista de líneas con su distancia mínima y si pasa en ida/vuelta
- [ ] En `app/services/eta_service.py` implementar el cálculo de ETA:
  - Obtiene todos los microbuses activos de la línea con su última posición (usa `vw_microbuses_activos`)
  - Para cada uno, calcula la distancia al punto del usuario en metros (PostGIS)
  - Usa la velocidad real del microbús (o 25 km/h si está detenido) para estimar minutos
  - Devuelve el microbús más cercano con su ETA
- [ ] En `app/routers/lineas.py` agregar:
  - `GET /lineas/{id}/eta?lon=&lat=&sentido=`: llama al eta_service

### Tareas — Flutter (App Usuario)

- [ ] Implementar la funcionalidad **Qué Líneas Pasan Aquí** (Pantallas 5, 6 y 7):
  - Opción 1: usar la ubicación GPS actual del usuario (`geolocator`)
  - Opción 2: el usuario toca un punto en el mapa para definir la ubicación
  - Llamada a `GET /lineas/cercanas` con las coordenadas y el radio
  - Mostrar en el mapa el radio como un círculo
  - Listar las líneas encontradas con su distancia
  - Al seleccionar una línea → navegar al mapa de recorrido (reutilizar el widget del ciclo 5)
- [ ] Implementar la visualización de **ETA**:
  - En la pantalla de líneas cercanas, al seleccionar una línea mostrar el ETA del microbús más cercano
  - Llamada a `GET /lineas/{id}/eta`
  - Mostrar: "El próximo microbús llega en aprox. X minutos"

### Verificación del ciclo ✅
- Con un conductor transmitiendo en ciclo 4, el usuario puede buscar líneas cercanas a su posición
- Las líneas que aparecen son realmente las que pasan dentro del radio indicado
- El ETA es calculado y se muestra en la interfaz
- Si no hay microbuses activos en esa línea, el sistema lo indica claramente (no mostrar ETA falso)
- Al seleccionar una línea cercana se muestra su recorrido completo en el mapa

---

## CICLO 7 — Tiempo real, "Esperando microbús" y cierre
**Duración estimada: 5–7 días**

### Objetivo
El usuario ve en tiempo real dónde están los microbuses de una línea en el mapa, actualizándose sin tocar nada. Se implementa el WebSocket. Se completa el pulido visual, manejo de errores y casos borde de todo el sistema.

### Dependencia
Ciclos 5 y 6 completados.

### Tareas — Backend Python

- [ ] Crear `app/routers/websocket.py` con el endpoint `WS /ws/lineas/{id}/posiciones`:
  - Mantiene una lista de conexiones activas por `linea_id` (ConnectionManager)
  - Cuando llega telemetría a `POST /recorridos/{id}/telemetria`, el router de recorridos notifica al WebSocket manager para que redistribuya la nueva posición a todos los clientes conectados a esa línea
  - El mensaje enviado por WebSocket es un JSON con `{microbus_id, placa, numero_interno, longitud, latitud, velocidad, sentido}`
- [ ] Agregar en `app/routers/lineas.py`:
  - `GET /lineas/{id}/microbuses-activos?sentido=`: snapshot inicial de posiciones (para cuando el usuario abre la pantalla, antes de conectar el WS)

### Tareas — Flutter (App Usuario)

- [ ] Crear `data/services/websocket_service.dart`:
  - Conecta a `WS /ws/lineas/{id}/posiciones` usando `web_socket_channel`
  - Emite un Stream de posiciones que los widgets pueden escuchar
  - Maneja reconexión automática si se corta la conexión
- [ ] Implementar la funcionalidad **Esperando Microbús** (Pantallas 8 y 9):
  - El usuario selecciona una línea y un sentido
  - Llamada inicial a `GET /lineas/{id}/microbuses-activos` para mostrar posiciones actuales
  - Conexión al WebSocket → los marcadores de los microbuses se mueven en el mapa conforme llegan nuevas posiciones
  - Se muestra el recorrido completo de la línea como fondo
  - Cada microbús se representa con un ícono de microbús sobre el mapa
  - Se actualiza también el ETA al punto del usuario cada vez que llega una posición nueva

### Tareas — Pulido general (ambas apps + backend)

- [ ] Manejo de errores en Flutter: mostrar mensajes claros cuando no hay conexión, cuando el servidor falla, cuando no hay microbuses activos
- [ ] Manejo de errores en el backend: respuestas de error consistentes con código HTTP correcto y mensaje descriptivo
- [ ] Validar que la app del conductor muestra un indicador claro cuando el servicio de telemetría en segundo plano está activo
- [ ] Probar el flujo completo: conductor inicia recorrido → usuario abre "Esperando microbús" → ve el microbús moverse en tiempo real
- [ ] Limpiar conexiones WebSocket cuando el usuario sale de la pantalla (`dispose`)
- [ ] Revisar que los permisos de GPS (Android e iOS) están correctamente declarados en los manifiestos
- [ ] Tests básicos: al menos un test por endpoint crítico en `pytest`
- [ ] Generar el APK de ambas apps para pruebas en dispositivo real

### Verificación del ciclo ✅
- El usuario abre "Esperando microbús", ve los microbuses activos en el mapa
- Cuando el conductor envía su siguiente posición (30s), el marcador en el mapa del usuario se mueve sin recargar la pantalla
- El ETA se recalcula con cada actualización de posición
- Si el conductor termina el recorrido, su marcador desaparece del mapa del usuario
- La app del conductor muestra el estado del servicio de fondo claramente
- Ambas apps funcionan correctamente en un dispositivo Android real

---

## Tabla de dependencias

```
Ciclo 1 ──► Ciclo 2 ──► Ciclo 3 ──► Ciclo 4 ──► Ciclo 7
                                 └──► Ciclo 5 ──► Ciclo 6 ──► Ciclo 7
```

- El Ciclo 7 requiere que el 4, el 5 y el 6 estén todos completos.
- Los ciclos 5 y 6 pueden desarrollarse en paralelo si hay dos personas en el equipo.

---

## Estimación total

| Ciclo | Días estimados |
|---|---|
| 1 — Fundación | 3–5 días |
| 2 — Auth y conductores | 4–6 días |
| 3 — Microbuses y líneas | 4–6 días |
| 4 — Telemetría | 5–7 días |
| 5 — Mapas de rutas | 4–6 días |
| 6 — Líneas cercanas y ETA | 5–7 días |
| 7 — Tiempo real y cierre | 5–7 días |
| **Total** | **30–44 días hábiles** |

> Trabajando a tiempo completo y en equipo de 2 personas (uno backend, uno Flutter), el proyecto puede completarse en **6–8 semanas**.


