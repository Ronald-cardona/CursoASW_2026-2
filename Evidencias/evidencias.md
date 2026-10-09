1. Recepción MQTT

resultado obtenido:
2026-10-09 09:02:29,187 INFO client: Conectando a emqx.coriotlab.co:1883...
2026-10-09 09:02:29,433 INFO client: Conectado al broker emqx.coriotlab.co:1883
2026-10-09 09:02:29,433 INFO client: Suscrito al tópico: iot/sensors/GAS-002/data. Presiona Ctrl+C para finalizar.
2026-10-09 09:02:33,820 WARNING ingesta: Payload de 'GAS-002' rechazado, no se guarda nada: unidad de 'ch4': llegó 'INVALID_UNIT' y la registrada es 'ppm'
[2026-10-09 09:02:33] iot/sensors/GAS-002/data -> 0 mediciones en este mensaje | TOTAL: recibidos=1 almacenados=0 rechazados=1

ESTE REGISTRO FUE RECHAZADO 

¿En qué archivo está implementado?

Elemento                                          Ubicación

Conexión y suscripción	                          mqtt/client.py — main() y on_connect()

Recepción del mensaje                             mqtt/client.py — on_message()

Procesamiento y validación                        mqtt/ingesta.py — guardar_mensaje() y procesar_payload()

Registro de ejecución                             ingesta.log, cuando se generan los registros configurados

Recepción MQTT: Se verificó la conexión al broker MQTT y la recepción de mensajes a través del tópico asignado.

2. Medición válida

Resultado obtenido:
{
    "id": 12786,
    "sensor_magnitud_id": 13,
    "valor": "58.9100",
    "timestamp_local": "2026-10-09 09:14:17 (UTC-05:00)",
    "fecha_recepcion_local": "2026-10-09 09:14:18 (UTC-05:00)",
    "magnitud": "humidity",
    "unidad": "%"
  },
  {
    "id": 12785,
    "sensor_magnitud_id": 14,
    "valor": "21.8400",
    "timestamp_local": "2026-10-09 09:14:17 (UTC-05:00)",
    "fecha_recepcion_local": "2026-10-09 09:14:18 (UTC-05:00)",
    "magnitud": "temperature",
    "unidad": "C"
  },
  {
    "id": 12784,
    "sensor_magnitud_id": 15,
    "valor": "971.4500",
    "timestamp_local": "2026-10-09 09:14:17 (UTC-05:00)",
    "fecha_recepcion_local": "2026-10-09 09:14:18 (UTC-05:00)",
    "magnitud": "ch4",
    "unidad": "ppm"
  },

  Esta prueba depende de 3 archivos principales: 

  mqtt/ingesta.py: valida el mensaje y decide si se guarda.

 crud/medicion.py: realiza el almacenamiento de las mediciones.

 models/medicion.py: define el modelo de la tabla de mediciones.

 Medición válida: Se verifica que una medición válida sea procesada correctamente y almacenada en la base de datos PostgreSQL.

EVIDENCIAS DE 3 A 7 

Sensor inexistente: 
2026-10-08 22:14:33,481 WARNING ingesta: Payload de 'GAS-002' rechazado, no se guarda nada: la magnitud 'co2' no está registrada para el sensor 'GAS-002'

Unidad incorrecta:
2026-10-08 21:55:33,348 WARNING ingesta: Payload de 'GAS-002' rechazado, no se guarda nada: unidad de 'ch4': llegó 'INVALID_UNIT' y la registrada es 'ppm'

Tipo de dato incorrecto:
2026-10-08 21:56:43,095 WARNING ingesta: Payload rechazado por estructura: measurements.humidity.value: Value error, value debe ser un número (int o float)

Magnitud incorrecta:
2026-10-08 22:02:28,387 WARNING ingesta: [GAS-002] humidity: valor 999999.0000 fuera del rango [0.0000, 100.0000] (se guarda igual)

Timestamp inválido:
2026-10-08 22:04:18,136 WARNING ingesta: Payload rechazado por estructura: timestamp: Value error, timestamp debe ser texto ISO 8601 con zona horaria, ej. 2026-10-07T16:25:30Z

DEPENDE DE VARIOS ARCHIVOS

ingesta.py --> funcion validar_reglas_negocio
errores.py

se verifica que los datos que no sean correctos para las reglas del negocio, sean rechazados. 

8. Consulta por ID existente:

Code	Details
200	
Response body
Download
{
  "codigo": "GAS-002",
  "nombre": "Sensor de metano",
  "categoria": "GAS",
  "ubicacion": "Laboratorio de energía",
  "activo": true,
  "id": 5,
  "fecha_registro_local": "2026-10-07 11:42:11 (UTC-05:00)"
}
 
El archivo donde se encuentra es: 
- api/sensores.py 
- api/mediciones.py
- api/sensor_magnitudes.py

se verifica que si el ID del sensor existe aparazca junto con sus caracteristicas

9. Consulta por ID no existente:


Code	Details
404
Undocumented
Error: Not Found

Response body
Download
{
  "detail": "Sensor no encontrado"
}  

se verifica que si el id del sensor no existe aparezca un error 404


10. Consulta histórica:

Entrada. Primero necesitamos el id del sensor. En Swagger ejecutamos GET /sensores/por-codigo/{codigo} con el codigo (por ejemplo GAS-005) y anotamos el id. Luego ejecutamos GET /sensores/{sensor_id}/mediciones con ese id, sin más parámetros.
 
Archivo y función: 

api/sensores.py → listar_mediciones_del_sensor()
crud/consultas.py → buscar_mediciones()

Explicación: La consulta une mediciones con sensor_magnitudes para filtrar por sensor y ordena por timestamp_utc descendente. Devuelve datos guardados en PostgreSQL, no datos simulados.


11. Consulta por rango de fechas:
Entrada: Eligir dos fechas que estén dentro de lo que devolvió la consulta anterior.

Archivo y función.

api/sensores.py → listar_mediciones_del_sensor()
schemas/tiempo.py → a_utc()
crud/consultas.py → buscar_mediciones()

Explicación: Las fechas sin zona horaria se interpretan como hora de Colombia y se convierten a UTC. Luego se filtra con timestamp_utc >= desde AND timestamp_utc <= hasta.

12. Rango desde > hasta

Code	Details
400
Undocumented
Error: Bad Request

Response body
Download
{
  "detail": "'desde' no puede ser posterior a 'hasta'"
}

archivos donde se encuentran:

- api/sensores.py --> listar_mediciones_del_sensor()
- api/mediciones.py --> _rango_utc(), llamada desde listar()
- api/sensor_magnitudes.py --> _rango_utc(), llamada desde listar_mediciones_de_la_magnitud()


13. Validación HTTP incorrecta

Code	Details
422	
Error: Unprocessable Entity

Response body
Download
{
  "detail": [
    {
      "type": "enum",
      "loc": [
        "body",
        "categoria"
      ],
      "msg": "Input should be 'AIRE', 'GAS', 'AGUA' or 'AMBIENTE'",
      "input": "RADIACION",
      "ctx": {
        "expected": "'AIRE', 'GAS', 'AGUA' or 'AMBIENTE'"
      }
    }
  ]
}

archivos donde se encuentran:

- api/mediciones.py -->  listar(), parámetro limit: int = Query(100, ge=1, le=1000)
- api/sensores.py  -->  obtener(sensor_id: int)
- schemas/sensor.py --> SensorCreate y CategoriaSensor

14. Ultima medicion :

Entrada. Con el id del sensor , ejecutar en Swagger GET /sensores/{sensor_id}/ultima-medicion

Archivo y función.

api/sensores.py → ultima_medicion_del_sensor()
api/sensor_magnitudes.py → ultima_medicion_de_la_magnitud()
crud/consultas.py → ultima_medicion_por_magnitud() y ultima_medicion_de_magnitud()

Explicación. Por cada magnitud del sensor, la consulta ordena sus mediciones por timestamp_utc descendente y toma solo la primera. Por eso el resultado es siempre el registro más reciente.

15. Últimas N mediciones

Entrada. Con el id del sensor, ejecutar en Swagger GET /sensores/{sensor_id}/mediciones y escribir limit en 10

Resultado esperado: Código 200 y exactamente 10 elementos, ordenados de la más reciente a la más antigua. El primero es la medición más reciente del sensor.

Archivo y función.

api/sensores.py → listar_mediciones_del_sensor(), parámetro limit: int = Query(100, ge=1, le=1000)
crud/consultas.py → buscar_mediciones(), línea .order_by(Medicion.timestamp_utc.desc(), Medicion.id.desc()).limit(limit)

Explicación: La consulta ordena por timestamp_utc descendente y luego recorta con LIMIT N. Como el orden va de la más reciente a la más antigua, quedarse con las primeras N equivale a obtener las últimas N mediciones.

16. Filtro por magnitud

Entrada: Anota el campo magnitud de cada elemento, por ejemplo temperature,  luego ejecuta en Swagger

Resultado esperado: Código 200 y una lista en la que todos los elementos tienen "magnitud": "temperature" y la misma unidad. No debe aparecer ninguna otra magnitud, aunque el sensor mande varias en cada mensaje.

Archivo y función:

api/sensores.py → listar_mediciones_del_sensor(), parámetro magnitud
crud/consultas.py → buscar_mediciones(), condición SensorMagnitud.magnitud == magnitud

Explicación: La consulta une mediciones con sensor_magnitudes y filtra por el nombre de la magnitud. Así se obtienen solo las filas de esa variable, ordenadas de la más reciente a la más antigua.

17. Claves foráneas

preparar el sensor de prueba (Swagger)
POST /sensores
json
   {"codigo": "TEST-FK", "nombre": "Sensor prueba FK", "categoria": "AMBIENTE", "ubicacion": "Pruebas", "activo": true}

Responde 201. 

2. POST /sensor-magnitudes (usa ese id en sensor_id)

json
   {"sensor_id": 7, "magnitud": "temperature", "unidad": "C", "valor_minimo": -40, "valor_maximo": 85}

Responde 201. 
3. POST /mediciones

json
   {"sensor_magnitud_id": 12, "valor": 24.5, "timestamp_utc": "2026-10-08T16:25:30Z"}

Responde 201.

Archivo y función
models/sensor_magnitud.py → SensorMagnitud.sensor_id: ForeignKey("sensores.id", onupdate="CASCADE", ondelete="RESTRICT")
models/medicion.py → Medicion.sensor_magnitud_id: ForeignKey("sensor_magnitudes.id", onupdate="CASCADE", ondelete="RESTRICT")
api/sensor_magnitudes.py → _sensor_existe(), usada en crear()
api/mediciones.py → _magnitud_existe(), usada en crear()
api/errores.py → error_integridad(), que convierte el error de PostgreSQL en 409
mqtt/ingesta.py → validar_reglas_negocio() (la magnitud debe pertenecer al sensor) y crud/medicion.py → crear_mediciones_lote() (si la base rechaza, se revierte todo)

La relación es sensores 1:N sensor_magnitudes 1:N mediciones. La API comprueba antes de insertar que el padre exista (404). Aun así, la base de datos es la que garantiza la integridad con las claves foráneas: impide insertar un hijo sin padre y borrar un padre con hijos.

18. Separación de responsabilidades
la separacion de responsabilidades se evidencia en la imagen 