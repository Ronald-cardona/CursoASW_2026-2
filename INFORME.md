1. Información General

Nombre del proyecto: Taller #2 
Integrantes: RONALD ALEJANDRO CARDONA CARVAJAL
Asignatura: APLICACION Y SERVICIOS WEB 
Fecha: 9/10/2026

Sensor asignado: GAS-002
Tópico MQTT utilizado: MQTT_TOPIC=iot/sensors/GAS-002/data

2. ## Descripción del Sistema

Magnitudes: ch4, temperature, humidity. 



## 1. Problema resuelto

Los sensores IoT publican sus mediciones por MQTT como mensajes JSON. Sin un sistema que las
procese, esos datos no se validan, no se almacenan y no se pueden consultar. Además, el servicio
puede publicar mensajes inválidos de forma intencional, que no deben guardarse.

El sistema resuelve cuatro cosas:

- **Consume** los mensajes del tópico MQTT asignado.
- **Valida** cada mensaje (estructura, tipos, timestamp, sensor, estado, magnitud y unidad) y
  **almacena únicamente** los que superan todas las validaciones.
- **Guarda** las mediciones en PostgreSQL conservando la referencia UTC del timestamp.
- **Expone** los datos mediante una API REST que devuelve las fechas en hora de Colombia (UTC-5) y
  permite consultas históricas con filtros combinables.

## 2. Arquitectura implementada

```text
 Sensor ──► Broker MQTT ──► mqtt/client.py ──► mqtt/ingesta.py ──► crud/ ──► PostgreSQL
            (EMQX)           (recepción)        (validación)                      ▲
                                                                                  │
 Cliente HTTP ──► FastAPI (api/) ──► crud/ ───────────────────────────────────────┘
                       │
                       └─► schemas/ (respuestas con hora de Colombia)
```

**Tecnologías:** Python 3.11, FastAPI, SQLAlchemy 2.0 (ORM), Pydantic v2, PostgreSQL, paho-mqtt.

**Broker y tópico:** `<broker:puerto>` — tópico `<tópico exacto de los mensajes recibidos>`.

### Capas

| Capa | Archivos | Responsabilidad |
|---|---|---|
| Conexión | `database/connection.py` | Engine, sesión y `get_db()` |
| Modelos | `models/` | Tablas, claves foráneas, restricciones e índices |
| Schemas | `schemas/` | Validación y formato de datos (Pydantic), payload MQTT, hora de Colombia |
| Acceso a datos | `crud/` | Consultas y escrituras en la base de datos |
| API | `api/` | Endpoints FastAPI y códigos HTTP |
| Integración MQTT | `mqtt/client.py`, `mqtt/ingesta.py` | Recepción y validación del mensaje |
| Ensamble | `main.py` | Crea la app y registra los routers |

### Modelo de datos

`sensores` 1:N `sensor_magnitudes` 1:N `mediciones`. Las claves foráneas usan
`ON UPDATE CASCADE ON DELETE RESTRICT`, de modo que no se puede borrar un sensor con magnitudes
ni una magnitud con mediciones.

### Flujo de un mensaje MQTT

1. `mqtt/client.py` recibe el mensaje y lo registra.
2. `schemas/payload_mqtt.py` valida estructura, campos obligatorios, tipos y formato del timestamp.
3. `mqtt/ingesta.py` valida contra la base de datos: existencia y estado del sensor, relación
   sensor-magnitud, correspondencia de la unidad y consistencia de claves foráneas.
4. Si todas las magnitudes son válidas, se guarda **un registro por magnitud**, todos con el
   mismo `timestamp_utc`, en una sola transacción. Si alguna falla, no se guarda nada.
5. Los rechazos quedan en `ingesta.log` y no se almacenan.

### Manejo del tiempo

El timestamp llega en UTC, se valida como texto ISO 8601 con zona horaria y se almacena en
`TIMESTAMPTZ`. Las respuestas GET lo convierten a hora de Colombia con el formato
`AAAA-MM-DD HH:MM:SS (UTC-05:00)`. En los filtros `desde` y `hasta`, una fecha sin zona se
interpreta como hora de Colombia.

### Endpoints principales

- `GET /sensores`, `GET /sensores/{id}`, `GET /sensores/por-codigo/{codigo}`
- `GET /sensores/{id}/magnitudes`, `GET /sensor-magnitudes/{id}`
- `GET /mediciones/{id}`
- `GET /sensores/{id}/mediciones` con `magnitud`, `desde`, `hasta` y `limit`
- `GET /sensores/{id}/ultima-medicion`


### Estructura

| Campo | Tipo | Descripción | Destino en la base de datos |
|---|---|---|---|
| `sensor_id` | string | Código del sensor | `sensores.codigo` (no es el `id` numérico) |
| `timestamp` | string ISO 8601, UTC | Instante de la medición | `mediciones.timestamp_utc` |
| `measurements` | objeto | Una clave por magnitud | una fila por clave en `mediciones` |
| `measurements.<magnitud>.value` | número | Valor medido | `mediciones.valor` |
| `measurements.<magnitud>.unit` | string | Unidad | se compara con `sensor_magnitudes.unidad` |

3. ## Configuración del entorno

### Requisitos previos

- Python 3.11 o superior
- PostgreSQL con las tablas `sensores`, `sensor_magnitudes` y `mediciones`
- Acceso a un broker MQTT

### 1. Crear el entorno virtual

Desde la raíz del proyecto, en PowerShell:

```powershell
python -m venv venv
```



### 2. Activarlo

```powershell
.\venv\Scripts\activate
```

Debe verse `(venv)` al inicio de la línea. Si PowerShell bloquea el script, ejecuta una vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 3. Instalar las dependencias

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. `requirements.txt`

Lista las librerías que necesita el proyecto, para reproducir el entorno en cualquier equipo.

| Librería | Para qué se usa |
|---|---|
| `fastapi` | Framework de la API REST |
| `uvicorn[standard]` | Servidor que ejecuta la API |
| `sqlalchemy` | ORM para acceder a PostgreSQL |
| `pydantic` | Validación de datos y del payload MQTT |
| `psycopg2-binary` | Driver de PostgreSQL |
| `python-dotenv` | Lee las variables del archivo `.env` |
| `paho-mqtt` | Cliente MQTT para consumir el tópico |
| `tzdata` | Zonas horarias (`America/Bogota`); necesaria en Windows |
| `httpx` | Requerida por `TestClient` en `evidencias/generar_evidencias.py` |

Para regenerarlo con las versiones exactas instaladas:

```powershell
pip freeze | Out-File requirements.txt -Encoding ascii
```

### 5. Variables de entorno

Se definen en un archivo `.env` en la raíz del proyecto. 


El archivo `.env` está en `.gitignore` y **no se sube** al repositorio.

| Variable | Obligatoria | Valor por defecto | Descripción | Sensible |
|---|---|---|---|---|
| `POSTGRES_HOST` | Sí | — | Servidor de PostgreSQL | No |
| `POSTGRES_PORT` | No | `3002` (según `database/connection.py`) | Puerto de PostgreSQL | No |
| `POSTGRES_DB` | Sí | — | Nombre de la base de datos | No |
| `POSTGRES_USER` | Sí | — | Usuario de la base de datos | Sí |
| `POSTGRES_PASSWORD` | Sí | — | Contraseña de la base de datos | **Sí** |
| `MQTT_BROKER` | Sí | — | Host del broker MQTT | No |
| `MQTT_PORT` | No | `1883` | Puerto del broker | No |
| `MQTT_TOPIC` | No | `iot/sensors/AQ-005/data` | Tópico asignado | No |
| `MQTT_USERNAME` | No | vacío | Usuario del broker, si lo pide | Sí |
| `MQTT_PASSWORD` | No | vacío | Contraseña del broker, si la pide | **Sí** |
| `MQTT_KEEPALIVE` | No | `60` | Segundos de keepalive de la conexión | No |
| `LOG_PAYLOADS` | No | `0` | `1` guarda cada mensaje crudo en `payloads_recibidos.jsonl` | No |

4. 
## Base de datos

### 1. Conexión

El proyecto usa PostgreSQL a través de SQLAlchemy 2.0 con el driver `psycopg2`. La conexión está
en `database/connection.py` y exporta sus elementos desde `database/__init__.py`.



**Quién usa la conexión**

- **API:** cada endpoint recibe su sesión con `Depends(get_db)`.
- **Consumidor MQTT:** `mqtt/ingesta.py` abre una sesión por cada mensaje con `with SessionLocal() as db`.

**Transacciones:** `crud/comun.py` → `guardar()` hace `commit` y, si PostgreSQL rechaza la operación
(`IntegrityError`), hace `rollback` y propaga el error. Las mediciones de un mismo mensaje MQTT se
insertan en una sola transacción (`crud/medicion.py` → `crear_mediciones_lote()`): se guardan todas
o ninguna.

### 2. Tablas utilizadas



**`sensores`**

| Campo | Tipo | Nulo | Restricción |
|---|---|---|---|
| `id` | SERIAL | No | PK |
| `codigo` | VARCHAR(20) | No | UNIQUE |
| `nombre` | VARCHAR(100) | No | |
| `categoria` | VARCHAR(30) | No | CHECK: `AIRE`, `GAS`, `AGUA` o `AMBIENTE` |
| `ubicacion` | VARCHAR(100) | No | |
| `activo` | BOOLEAN | No | DEFAULT TRUE |
| `fecha_registro` | TIMESTAMPTZ | No | DEFAULT NOW() |

**`sensor_magnitudes`**

| Campo | Tipo | Nulo | Restricción |
|---|---|---|---|
| `id` | SERIAL | No | PK |
| `sensor_id` | INTEGER | No | FK → `sensores(id)` |
| `magnitud` | VARCHAR(50) | No | UNIQUE junto con `sensor_id` |
| `unidad` | VARCHAR(20) | No | |
| `valor_minimo` | NUMERIC(12,4) | No | CHECK `valor_minimo < valor_maximo` |
| `valor_maximo` | NUMERIC(12,4) | No | |

**`mediciones`**

| Campo | Tipo | Nulo | Restricción |
|---|---|---|---|
| `id` | BIGSERIAL | No | PK |
| `sensor_magnitud_id` | INTEGER | No | FK → `sensor_magnitudes(id)` |
| `valor` | NUMERIC(12,4) | No | |
| `timestamp_utc` | TIMESTAMPTZ | No | Instante de la medición, en UTC |
| `fecha_recepcion` | TIMESTAMPTZ | No | DEFAULT NOW() |



### 3. Relaciones implementadas

```text
sensores 1 ───< N sensor_magnitudes 1 ───< N mediciones
```


### 4. Correspondencia con `data-model.md`

| Elemento de `data-model.md` | Implementación | Archivo |
|---|---|---|
| Tabla `sensores` y sus 7 campos | Clase `Sensor`, mismos tipos y nulos | `models/sensor.py` |
| `codigo` UNIQUE | `unique=True` | `models/sensor.py` |
| `categoria` CHECK (4 valores) | `CheckConstraint("categoria IN (...)")` y `Enum CategoriaSensor` en Pydantic | `models/sensor.py`, `schemas/sensor.py` |
| `activo` DEFAULT TRUE | `server_default=text("TRUE")` | `models/sensor.py` |
| `fecha_registro` DEFAULT NOW() | `server_default=func.now()` | `models/sensor.py` |
| Tabla `sensor_magnitudes` y sus 6 campos | Clase `SensorMagnitud` | `models/sensor_magnitud.py` |
| `UNIQUE(sensor_id, magnitud)` | `UniqueConstraint(..., name="uq_sensor_magnitud")` | `models/sensor_magnitud.py` |
| `CHECK (valor_minimo < valor_maximo)` | `CheckConstraint(..., name="ck_magnitud_rango")` y validador Pydantic | `models/sensor_magnitud.py`, `schemas/sensor_magnitud.py` |
| FK `sensor_id` con `ON UPDATE CASCADE ON DELETE RESTRICT` | `ForeignKey("sensores.id", onupdate="CASCADE", ondelete="RESTRICT")` | `models/sensor_magnitud.py` |
| Tabla `mediciones` y sus 5 campos | Clase `Medicion` (`id` como `BigInteger`) | `models/medicion.py` |
| FK `sensor_magnitud_id` con `ON UPDATE CASCADE ON DELETE RESTRICT` | `ForeignKey("sensor_magnitudes.id", ...)` | `models/medicion.py` |
| `fecha_recepcion` DEFAULT NOW() | `server_default=func.now()` | `models/medicion.py` |
| Los 3 índices de `mediciones` | `Index("idx_mediciones_sensor_magnitud", ...)`, `Index("idx_mediciones_timestamp_utc", ...)`, `Index("idx_mediciones_magnitud_timestamp", ...)` | `models/medicion.py` |
| Relaciones 1:N | `relationship()` bidireccional | los tres modelos |

5. ## Organización del código

El proyecto se divide en capas. Cada carpeta tiene una sola responsabilidad y solo depende de las
capas que tiene por debajo, de modo que un cambio en una parte no obliga a tocar las demás.


Taller-2/
├── api/          Endpoints HTTP
├── crud/         Acceso a datos
├── schemas/      Validación y formato de datos
├── models/       Tablas de la base de datos
├── database/     Conexión a PostgreSQL
├── mqtt/         Consumo y procesamiento de mensajes MQTT
├── evidencias/   Pruebas y evidencias
└── main.py       Ensamble de la aplicación

### `schemas/` — validación y formato de datos

Define cómo entran y cómo salen los datos, con Pydantic.

### `models/` — tablas

Describe la estructura de la base de datos con SQLAlchemy (ORM).

### `crud/` — acceso a datos

Contiene todas las consultas y escrituras en la base de datos. Cada función recibe una sesión y
devuelve objetos del ORM.

### `api/` — endpoints HTTP

Expone los datos mediante FastAPI y decide los códigos de respuesta.

### `mqtt/` — integración con el broker

Consume los mensajes de los sensores y guarda solo los válidos.

### `database/` — conexión

Prepara el acceso a PostgreSQL y nada más.

6. ## Endpoints implementados


### Sensores (`api/sensores.py`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/sensores` | Lista los sensores. Filtros: `categoria`, `activo`, `skip`, `limit` |
| GET | `/sensores/por-codigo/{codigo}` | Obtiene un sensor por su código (el `sensor_id` que llega por MQTT) |
| GET | `/sensores/{sensor_id}` | Obtiene un sensor por su id |
| GET | `/sensores/{sensor_id}/magnitudes` | Lista las magnitudes que mide el sensor, con su unidad y rango |
| GET | `/sensores/{sensor_id}/mediciones` | Historial de mediciones del sensor, de la más reciente a la más antigua. Filtros combinables: `magnitud`, `desde`, `hasta`, `limit`, `skip` |
| GET | `/sensores/{sensor_id}/ultima-medicion` | Medición más reciente de cada magnitud del sensor. Filtro opcional: `magnitud` |
| POST | `/sensores` | Crea un sensor |
| PUT | `/sensores/{sensor_id}` | Reemplaza todos los datos de un sensor |
| PATCH | `/sensores/{sensor_id}` | Actualiza parcialmente un sensor |
| DELETE | `/sensores/{sensor_id}` | Elimina un sensor. Falla si tiene magnitudes asociadas |

### Magnitudes de sensor (`api/sensor_magnitudes.py`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/sensor-magnitudes` | Lista las magnitudes. Filtros: `sensor_id`, `magnitud`, `unidad`, `skip`, `limit` |
| GET | `/sensor-magnitudes/{magnitud_id}` | Obtiene una magnitud por su id |
| GET | `/sensor-magnitudes/{magnitud_id}/mediciones` | Historial de mediciones de esa magnitud. Filtros: `desde`, `hasta`, `limit`, `skip` |
| GET | `/sensor-magnitudes/{magnitud_id}/ultima-medicion` | Medición más reciente de esa magnitud |
| POST | `/sensor-magnitudes` | Registra una magnitud para un sensor |
| PUT | `/sensor-magnitudes/{magnitud_id}` | Reemplaza todos los datos de una magnitud |
| PATCH | `/sensor-magnitudes/{magnitud_id}` | Actualiza parcialmente una magnitud |
| DELETE | `/sensor-magnitudes/{magnitud_id}` | Elimina una magnitud. Falla si tiene mediciones asociadas |

### Mediciones (`api/mediciones.py`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/mediciones` | Busca mediciones con filtros combinables: `sensor_id`, `sensor_magnitud_id`, `magnitud`, `desde`, `hasta`, `limit`, `skip` |
| GET | `/mediciones/{medicion_id}` | Obtiene una medición por su id, con el nombre y la unidad de su magnitud |
| POST | `/mediciones` | Registra una medición manualmente |
| PUT | `/mediciones/{medicion_id}` | Reemplaza todos los datos de una medición |
| PATCH | `/mediciones/{medicion_id}` | Actualiza parcialmente una medición |
| DELETE | `/mediciones/{medicion_id}` | Elimina una medición |

### Parámetros de consulta

| Parámetro | Descripción |
|---|---|
| `limit` | Cantidad máxima de resultados (1 a 1000 en mediciones, 1 a 500 en sensores y magnitudes). Como el historial va de la más reciente a la más antigua, `limit=N` devuelve las últimas N mediciones |
| `skip` | Número de resultados a saltar, para paginar |
| `desde`, `hasta` | Rango de fechas, ambos inclusivos. Sin zona horaria se interpretan como hora de Colombia; también se aceptan con `Z` (UTC) o con desfase (`-05:00`). Si `desde` es posterior a `hasta`, responde 400 |
| `magnitud` | Nombre exacto de la magnitud, por ejemplo `temperature` |

### Códigos de respuesta

| Código | Cuándo |
|---|---|
| 200 | Consulta o actualización correcta |
| 201 | Recurso creado (POST) |
| 204 | Recurso eliminado (DELETE) |
| 400 | El rango de fechas es incoherente (`desde` posterior a `hasta`) |
| 404 | El recurso solicitado, o el padre referenciado, no existe |
| 409 | Conflicto: dato duplicado, o borrado bloqueado por una relación (`ON DELETE RESTRICT`) |
| 422 | Parámetro o cuerpo que no cumple el formato esperado |

### Formato de las fechas en las respuestas

Las fechas se guardan en UTC y las respuestas las muestran en hora de Colombia con el formato
`AAAA-MM-DD HH:MM:SS (UTC-05:00)`, en los campos `timestamp_local`, `fecha_recepcion_local` y
`fecha_registro_local`.

7. Evidencias de Funcionamiento

LAS EVIDENCIAS DE FUNCIONAMIENTO SE ENCUENTRAN EN LA CARPETA "Evidencias"

## CONCLUSIONES




### Principales aprendizajes

- **Separar el código por capas ayuda mucho.** Dividir el proyecto en `models`, `schemas`, `crud`,
  `api`, `mqtt` y `database` me pareció exagerado al comienzo. Pero cuando aparecía un error ya sabía
  en qué carpeta buscar, y la API y el consumidor MQTT reutilizan las mismas funciones de `crud`,
  así que no tuve que repetir código.
- **Hay dos niveles de validación.** Pydantic revisa que el mensaje tenga la forma correcta
  (campos, tipos y timestamp), pero no sabe si el sensor existe o si la unidad coincide. Eso hay que
  comprobarlo contra la base de datos. Entendí que son validaciones distintas y que se necesitan las dos.
- **Un mensaje se guarda completo o no se guarda.** Si un payload trae varias magnitudes y una falla,
  es mejor descartarlo entero que dejar datos a medias. Para lograrlo usé una sola transacción.
- **El tiempo se guarda en UTC y se muestra en hora local.** Aprendí a usar `TIMESTAMPTZ` y a
  convertir a la hora de Colombia solo al responder. También que en Windows hace falta instalar
  `tzdata` para trabajar con zonas horarias.
- **La base de datos también protege los datos.** Con las claves foráneas `ON DELETE RESTRICT` no se
  puede borrar un sensor con magnitudes ni una magnitud con mediciones, incluso si la API tuviera
  un error.
- **Cada código HTTP significa algo distinto.** Diferencié el 400 (petición incoherente, como
  `desde` mayor que `hasta`), el 404 (no existe), el 409 (conflicto con la base de datos) y el 422
  (el formato no cumple lo declarado, que FastAPI genera solo).
- **MQTT funciona distinto a HTTP.** El cliente se queda escuchando un tópico y los mensajes llegan
  cuando el sensor publica. Además, el servicio puede mandar mensajes inválidos a propósito, así que
  el consumidor nunca debe asumir que todo viene bien.

### Dificultades encontradas

1. **El entorno.** `sqlalchemy` y `psycopg2` no estaban instalados en el entorno virtual, y VS Code
   subrayaba los imports en amarillo porque estaba usando otro intérprete.
2. **El tópico del broker.** El cliente se conectaba y se suscribía, pero llevaba varios minutos sin
   recibir ningún mensaje.
3. **La hora de inicio "mal".** El resumen de la recolección mostraba `01:43` cuando en mi reloj
   eran las 20:43.




### Soluciones aplicadas

1. Activé el entorno virtual, instalé las dependencias con `pip` y elegí el intérprete correcto con
   *Python: Select Interpreter*. Después armé un `requirements.txt` para no repetir el proceso.

2. El profesor me dio el sensor que realmente necesitaba 
3. Me di cuenta de que la hora estaba bien, pero en UTC. Cambié el resumen para mostrarla en hora de
   Colombia.


### Conclusión final

El sistema cumple con lo pedido: consume el tópico asignado, almacena solo los mensajes que superan
todas las validaciones y permite consultar el histórico por sensor, magnitud y rango de fechas, con
las horas en Colombia. 