# Proyecto: Sistema de Información Geográfica para Microbuses — Santa Cruz de la Sierra

## 1. Descripción General

El proyecto consiste en el desarrollo de un sistema móvil integrado que sirva como apoyo a los usuarios del transporte público (microbuses) en la ciudad de Santa Cruz de la Sierra. El sistema cumple cuatro funciones principales:

1. Permitir a los conductores registrarse y transmitir su ubicación en tiempo real mientras están en servicio.
2. Permitir a los usuarios conocer la ruta completa de cada línea de microbús.
3. Mostrar qué líneas de microbús pasan por un punto dado de la ciudad.
4. Informar por dónde viene y en qué tiempo llegará el microbús más cercano de una línea en particular.

---

## 2. Arquitectura del Sistema

El sistema se compone de cuatro capas claramente separadas:

- **Aplicación Móvil del Conductor** (Flutter): registra al conductor, inicia recorridos y transmite telemetría GPS al backend cada 30 segundos.
- **Aplicación Móvil del Usuario** (Flutter): consulta rutas, líneas cercanas y posición en tiempo real de los microbuses.
- **Backend / API REST** (Python — FastAPI): recibe y procesa todas las peticiones de ambas apps, contiene la lógica de negocio (cálculo de ETA, consultas geoespaciales, validaciones) y se comunica con la base de datos.
- **Base de Datos Centralizada** (PostgreSQL + PostGIS): almacena toda la información geográfica, de conductores, microbuses y telemetría.

```
App Conductor (Flutter)  ──┐
                           ├──► API REST (Python FastAPI) ──► PostgreSQL + PostGIS
App Usuario    (Flutter)  ──┘         │
                                      └──► WebSockets (tiempo real)
```

La separación entre apps y backend es deliberada: toda la lógica de negocio y los cálculos geoespaciales viven en el backend Python, lo que hace al sistema más fácil de mantener, testear y escalar independientemente de las apps móviles.

### 2.1 Stack Tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Aplicaciones móviles | **Flutter (Dart)** | Un solo código para iOS y Android, alto rendimiento |
| Mapas | **flutter_map** + **OpenStreetMap** | Gratuito sin API key, tiles OSM sin costo |
| GPS y ubicación | **geolocator** + **flutter_background_service** | Captura de ubicación en primer y segundo plano |
| Backend / API REST | **Python — FastAPI** | Moderno, rápido, genera documentación Swagger automática, excelente soporte para geo con Shapely y GeoAlchemy2 |
| ORM y geo | **SQLAlchemy** + **GeoAlchemy2** | Manejo de modelos relacionales y tipos geoespaciales de PostGIS desde Python |
| Tiempo real | **WebSockets** (FastAPI nativo) | Canal persistente para enviar posiciones de microbuses a los usuarios sin polling |
| Base de datos | **PostgreSQL 14+ + PostGIS** | Estándar para datos geoespaciales: radios, distancias, intersecciones de rutas |
| Autenticación | **JWT** (python-jose) | Tokens para autenticar conductores en cada petición |
| Almacenamiento de imágenes | **MinIO** (autoalojado) o **Cloudinary** (gratuito) | Fotos de conductores y microbuses |
| Servidor de producción | **Uvicorn** + **Gunicorn** | Servidor ASGI recomendado para FastAPI |
| Cálculo de ETA | Lógica Python con PostGIS (`ST_Distance`, `ST_DWithin`) | Distancia real sobre la ruta + velocidad promedio del microbús |

### 2.2 Endpoints del Backend (API REST — FastAPI)

| Método | Endpoint | Descripción | Quién lo usa |
|---|---|---|---|
| `POST` | `/auth/login` | Autenticación del conductor, devuelve JWT | App Conductor |
| `POST` | `/conductores/registro` | Registro de un nuevo conductor | App Conductor |
| `GET` | `/conductores/me` | Datos del conductor autenticado | App Conductor |
| `POST` | `/microbuses/registro` | Registro de un nuevo microbús | App Conductor |
| `GET` | `/microbuses/mis-microbuses` | Lista de microbuses del conductor | App Conductor |
| `POST` | `/recorridos/iniciar` | Inicia un recorrido, devuelve el ID de sesión | App Conductor |
| `POST` | `/recorridos/{id}/telemetria` | Envía un punto GPS cada 30 segundos | App Conductor |
| `POST` | `/recorridos/{id}/terminar` | Finaliza el recorrido normalmente | App Conductor |
| `POST` | `/recorridos/{id}/salir` | Finaliza por fuerza mayor (requiere motivo) | App Conductor |
| `GET` | `/lineas` | Lista completa de líneas disponibles | App Usuario |
| `GET` | `/lineas/{id}` | Datos de una línea (recorrido ida/vuelta en GeoJSON) | App Usuario |
| `GET` | `/lineas/cercanas` | Líneas dentro de un radio de un punto (`?lon=&lat=&radio=`) | App Usuario |
| `GET` | `/lineas/{id}/microbuses-activos` | Posición de microbuses en servicio de una línea (`?sentido=`) | App Usuario |
| `GET` | `/lineas/{id}/eta` | ETA del microbús más cercano (`?lon=&lat=&sentido=`) | App Usuario |
| `WS` | `/ws/lineas/{id}/posiciones` | WebSocket: stream de posiciones en tiempo real | App Usuario |

### 2.3 Paquetes Python del Backend

| Paquete | Función |
|---|---|
| `fastapi` | Framework principal del backend |
| `uvicorn` | Servidor ASGI para correr FastAPI |
| `sqlalchemy` | ORM para manejo de modelos y consultas |
| `geoalchemy2` | Extensión de SQLAlchemy para tipos PostGIS (Geometry, Geography) |
| `psycopg2-binary` | Driver de conexión a PostgreSQL |
| `python-jose[cryptography]` | Generación y validación de tokens JWT |
| `passlib[bcrypt]` | Hash de contraseñas |
| `python-multipart` | Recepción de archivos (fotos) en formularios |
| `shapely` | Cálculos geométricos en Python (distancias, buffers) |
| `pydantic` | Validación de datos de entrada/salida (incluido en FastAPI) |
| `alembic` | Migraciones de base de datos |
| `pytest` + `httpx` | Testing de los endpoints |

### 2.4 Paquetes Flutter principales

| Paquete | Función |
|---|---|
| `flutter_map` | Renderizado de mapas con tiles de OpenStreetMap |
| `latlong2` | Manejo de coordenadas geográficas |
| `geolocator` | Acceso al GPS del dispositivo |
| `flutter_background_service` | Envío de telemetría en segundo plano (app del conductor) |
| `dio` | Cliente HTTP para consumir la API REST del backend |
| `web_socket_channel` | Conexión WebSocket para posiciones en tiempo real |
| `flutter_secure_storage` | Almacenamiento seguro del token JWT |
| `image_picker` | Captura de fotos para registro de conductor y microbús |
| `flutter_polyline_points` | Dibujo de rutas como polilíneas sobre el mapa |
| `riverpod` | Gestión de estado |
| `go_router` | Navegación y rutas de la app |

---

## 3. Requerimientos Funcionales

### 3.1 Aplicación Móvil — CONDUCTOR

#### 3.1.1 Registro de Conductor (único, una sola vez)

La aplicación debe permitir a cada conductor registrarse una sola vez en el sistema. El módulo de registro debe almacenar en la base de datos los siguientes campos:

| Campo | Tipo | Obligatorio |
|---|---|---|
| Documento de identidad | Texto | Sí |
| Nombre completo | Texto | Sí |
| Fecha de nacimiento | Fecha | Sí |
| Sexo | Selección (M/F) | Sí |
| Teléfono | Texto | Sí |
| Correo electrónico | Texto | Sí |
| Categoría de licencia | Selección (A, B, C, P, M, etc.) | Sí |
| Foto del conductor | Imagen | Sí |

#### 3.1.2 Registro de Microbús

El módulo de registro de microbús debe almacenar en la base de datos la siguiente información:

| Campo | Tipo | Obligatorio |
|---|---|---|
| Fotos del microbús | Imágenes (múltiples) | Sí |
| Placa | Texto | Sí |
| Modelo | Texto | Sí |
| Cantidad de asientos | Numérico | Sí |
| Conductor asignado | Relación (FK a conductor) | Sí |
| Línea | Relación (FK a línea) | Sí |
| Número interno | Texto | Sí |
| Fecha de asignación | Fecha | Sí |
| Fecha de baja | Fecha | No (se llena cuando se da de baja) |

#### 3.1.3 Iniciar Recorrido

Flujo obligatorio en este orden:

1. El conductor **selecciona el sentido del recorrido** de su línea de microbús (ida o vuelta).
2. El conductor presiona **"Iniciar recorrido"**.
3. La interfaz muestra la información del recorrido en curso del microbús.
4. A partir de ese momento, la aplicación captura y envía a la base de datos **cada 30 segundos** la siguiente telemetría:

| Dato de telemetría | Descripción |
|---|---|
| Longitud | Coordenada geográfica |
| Latitud | Coordenada geográfica |
| Fecha | Fecha del registro |
| Hora | Hora del registro |
| Velocidad | Velocidad actual del microbús |
| Distancia recorrida | Distancia acumulada desde el inicio del recorrido |
| Tiempo transcurrido | Tiempo acumulado desde el inicio del recorrido |

El envío debe funcionar en segundo plano incluso si el conductor minimiza la aplicación.

#### 3.1.4 Terminar Recorrido

Esta funcionalidad indica la finalización normal de una ruta. Al activarla, el sistema debe enviar a la base de datos:

- Ubicación final (longitud, latitud)
- Fecha de finalización
- Hora de finalización
- Resumen de la información del recorrido completado

#### 3.1.5 Salir del Recorrido

Esta funcionalidad se utiliza cuando el conductor debe abandonar la ruta por motivos de fuerza mayor. Al activarla, el sistema debe:

- Registrar la ubicación final (longitud, latitud)
- Registrar la fecha y hora de finalización
- **Obligar al conductor a describir textualmente el motivo de la salida** (campo obligatorio)
- Diferenciar en la base de datos este tipo de finalización de una finalización normal

---

### 3.2 Aplicación Móvil — USUARIO

#### 3.2.1 Recorrido de Línea de Microbús

Flujo funcional:

1. El usuario busca y selecciona una línea de microbús desde una **tabla de opciones**.
2. El usuario indica si desea visualizar:
   - Recorrido de **ida**
   - Recorrido de **vuelta**
   - **Ambos** sentidos
3. El sistema muestra en el mapa de la ciudad el recorrido seleccionado con las siguientes indicaciones visuales:
   - **Marca de color verde** en el punto de partida
   - **Marca de color rojo** en el punto de llegada
   - **Flechas** indicando el sentido del recorrido a lo largo de la ruta

#### 3.2.2 Qué Líneas de Microbús Pasan Aquí

Flujo funcional:

1. El sistema identifica la **ubicación actual del usuario** (GPS) o permite al usuario **indicar un punto arbitrario** en el mapa.
2. El sistema muestra en el mapa todas las líneas de microbús que transitan dentro de un **radio determinado** alrededor de ese punto.
3. Al seleccionar una de las líneas resultantes y elegir el sentido del recorrido, se muestra en el mapa la **ruta completa** de dicha línea (con los mismos indicadores visuales del punto 3.2.1).

#### 3.2.3 Esperando Microbús (Tiempo Real)

Flujo funcional:

1. El usuario selecciona una línea de microbús.
2. El usuario elige el sentido del recorrido.
3. El sistema muestra en el mapa:
   - El **recorrido completo** de la línea seleccionada.
   - La **posición en tiempo real** de todos los microbuses activos de esa línea que se encuentren dentro de un radio específico respecto al recorrido.
4. El sistema debe **calcular y mostrar el tiempo estimado de llegada (ETA)** del microbús más cercano al punto donde se encuentra el usuario.

Requisitos técnicos de esta funcionalidad:

- La actualización de posiciones debe ser en **tiempo real** (mínimo cada 30 segundos, coincidiendo con la frecuencia de envío del conductor).
- La app del usuario se conecta al endpoint WebSocket del backend (`/ws/lineas/{id}/posiciones`) para recibir posiciones sin hacer polling manual.
- Cada vez que el conductor envía telemetría al backend, este redistribuye la nueva posición a todos los usuarios conectados a ese WebSocket.

---

## 4. Pantallas de Referencia (Mockups)

El documento original de alcance incluye **12 pantallas de referencia** que definen el diseño visual mínimo esperado para ambas aplicaciones:

| Pantalla | Aplicación | Funcionalidad |
|---|---|---|
| Pantalla 1 | Usuario | Pantalla principal de la app del usuario |
| Pantalla 2 | Conductor | Pantalla principal de la app del conductor |
| Pantalla 3 | Usuario | Recorrido de línea — mapa con ruta, partida (verde), llegada (rojo) y flechas |
| Pantalla 4 | Usuario | Recorrido de línea — selección de sentido |
| Pantalla 5 | Usuario | Qué líneas pasan aquí — visualización de radio y líneas cercanas |
| Pantalla 6 | Usuario | Qué líneas pasan aquí — selección de línea y sentido |
| Pantalla 7 | Usuario | Visualización de ruta completa de línea seleccionada |
| Pantalla 8 | Usuario | Esperando microbús — selección de línea |
| Pantalla 9 | Usuario | Esperando microbús — selección de sentido |
| Pantalla 10 | Conductor | Iniciar recorrido — información del recorrido en curso y telemetría |
| Pantalla 11 | Conductor | Terminar recorrido — resumen de información del recorrido finalizado |
| Pantalla 12 | Conductor | Salir del recorrido — formulario con motivo obligatorio |

Las pantallas originales con sus capturas se encuentran en el documento `Alcance_del_Proyecto_microbuses_SIG_1_2026_final.docx`.

---

## 5. Estructura de los Proyectos

### 5.1 Backend Python (FastAPI)

```
backend/
├── main.py                   # Punto de entrada, registro de routers
├── requirements.txt
├── alembic/                  # Migraciones de base de datos
│   └── versions/
├── app/
│   ├── core/
│   │   ├── config.py         # Variables de entorno (DB URL, JWT secret, etc.)
│   │   ├── security.py       # JWT: crear y verificar tokens
│   │   └── database.py       # Sesión de SQLAlchemy
│   ├── models/               # Modelos ORM (tablas de la BD)
│   │   ├── conductor.py
│   │   ├── microbus.py
│   │   ├── linea.py
│   │   ├── recorrido.py
│   │   └── telemetria.py
│   ├── schemas/              # Modelos Pydantic (validación de entrada/salida)
│   │   ├── conductor.py
│   │   ├── microbus.py
│   │   ├── linea.py
│   │   ├── recorrido.py
│   │   └── telemetria.py
│   ├── routers/              # Endpoints agrupados por funcionalidad
│   │   ├── auth.py           # POST /auth/login
│   │   ├── conductores.py    # POST /conductores/registro, GET /conductores/me
│   │   ├── microbuses.py     # POST /microbuses/registro
│   │   ├── recorridos.py     # iniciar, telemetría, terminar, salir
│   │   ├── lineas.py         # listado, detalle, cercanas
│   │   └── websocket.py      # WS /ws/lineas/{id}/posiciones
│   └── services/             # Lógica de negocio separada de los routers
│       ├── geo_service.py    # Consultas geoespaciales (PostGIS via GeoAlchemy2)
│       ├── eta_service.py    # Cálculo de tiempo estimado de llegada
│       └── storage_service.py # Subida de imágenes
└── tests/
    ├── test_auth.py
    ├── test_recorridos.py
    └── test_geo.py
```

### 5.2 Apps Móviles Flutter

```
flutter_app/
├── pubspec.yaml
├── lib/
│   ├── main.dart
│   ├── app/
│   │   ├── app.dart
│   │   └── routes.dart           # go_router
│   ├── core/
│   │   ├── constants/
│   │   │   └── api_endpoints.dart  # URLs de la API REST
│   │   ├── theme/
│   │   └── utils/
│   ├── data/
│   │   ├── models/               # Clases Dart (conductor, microbús, línea, etc.)
│   │   ├── repositories/         # Lógica de acceso a datos
│   │   └── services/
│   │       ├── api_service.dart       # Cliente HTTP (dio) para la API REST
│   │       ├── auth_service.dart      # Login, guardado del JWT
│   │       ├── location_service.dart  # GPS con geolocator
│   │       ├── background_service.dart # Envío en segundo plano
│   │       └── websocket_service.dart  # Conexión al WS de posiciones
│   ├── features/
│   │   ├── conductor/
│   │   │   ├── registro/
│   │   │   ├── recorrido/        # Iniciar, telemetría, terminar, salir
│   │   │   └── widgets/
│   │   └── usuario/
│   │       ├── recorrido_linea/
│   │       ├── lineas_aqui/
│   │       ├── esperando_microbus/
│   │       └── widgets/
│   └── shared/
│       ├── widgets/
│       │   └── mapa_widget.dart  # flutter_map reutilizable
│       └── providers/            # Riverpod providers globales
```

---

## 6. Requerimientos No Funcionales

| Requisito | Detalle |
|---|---|
| Plataformas móviles | iOS y Android (Flutter, un solo código fuente) |
| Backend | Python 3.11+, FastAPI, corriendo en servidor Linux con Uvicorn + Gunicorn |
| Frecuencia de telemetría | Cada 30 segundos por recorrido activo |
| Funcionamiento en segundo plano | La app del conductor debe seguir enviando telemetría con la pantalla apagada o la app minimizada |
| Tiempo real | Latencia máxima aceptable de actualización de posición: 30-35 segundos vía WebSocket |
| Rendimiento de mapas | Carga fluida de tiles, polilíneas y marcadores sin congelamientos perceptibles |
| Almacenamiento de imágenes | Fotos comprimidas antes de subir desde la app (máx. 1 MB por imagen) |
| Autenticación | JWT firmado con HS256 (python-jose). Cada petición del conductor al backend lleva el token en el header `Authorization: Bearer <token>` |
| Seguridad de datos | El backend valida que un conductor solo pueda operar sobre sus propios recorridos y microbuses (validación en la capa de servicio Python) |
| Sistema de coordenadas | SRID 4326 (WGS84) para toda la información geográfica almacenada en PostGIS |
| Documentación de la API | Swagger UI generada automáticamente por FastAPI, accesible en `/docs` |
| Ciudad objetivo | Santa Cruz de la Sierra, Bolivia |

---

## 7. Entregables del Proyecto

1. **Código fuente del backend Python** (FastAPI) en repositorio Git, con `requirements.txt` y migraciones Alembic.
2. **Código fuente de las apps Flutter** (conductor y usuario) en repositorio Git.
3. **Aplicación del Conductor** compilada para Android (APK) y/o iOS.
4. **Aplicación del Usuario** compilada para Android (APK) y/o iOS.
5. **Base de datos PostgreSQL/PostGIS** configurada con datos de prueba (al menos 5 líneas de microbús con recorridos de ida y vuelta georeferenciados).
6. **Documentación técnica**: instrucciones de instalación del backend (Python + PostgreSQL), configuración de variables de entorno y despliegue en servidor Linux.
7. **Colección de endpoints** (Postman o la Swagger UI de FastAPI) para verificar el funcionamiento de la API.
8. **Manual de usuario** para ambas aplicaciones.
