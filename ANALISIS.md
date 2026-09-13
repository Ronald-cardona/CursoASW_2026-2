# Tabla de correspondencias — Proveedores vs. Contrato institucional

| Campo contrato   | Proveedor A  (JSON )             | Proveedor B    (CSV)  |
|------------------|--------------------------------- |---------------------- |
| `ciudad`         | `station.city_name`              | `municipality`        |
| `pais`           | `station.country_code`           | `country`             |
| `latitud`        | `location.lat`                   | `latitude_deg`        |
| `longitud`       | `location.lon`                   | `longitude_deg`       |
| `temperatura_c`  | `measurements.temperature_f`     | `temp_celsius`        |
| `humedad`        | `measurements.relative_humidity` | `humidity_pct`        |
| `viento_kmh`     | `measurements.wind_speed_ms`     | `wind_kmh`            |
| `fecha_hora`     | `observed_at`                    | `measurement_time`    |
| `origen`         | `source` / `provider`            | `origin_code`         |

##  2 Detalle por campo

### `ciudad`
- Tipo: string · Unidad: — · Formato: texto libre en ambos
- Transformación: renombrar/extraer (A viene anidado en `station`)

### `pais`
- Tipo: string · Unidad: — · Formato: código ISO ("CO") en ambos
- Transformación: renombrar; definir si el contrato espera código ISO o nombre completo (no está aclarado en el contrato)

### `latitud`
- Tipo: number · Unidad: grados decimales · Formato: ambos ya en grados decimales
- Transformación: renombrar/extraer; validar rango -90 a 90

### `longitud`
- Tipo: number · Unidad: grados decimales · Formato: ambos ya en grados decimales
- Transformación: renombrar/extraer; validar rango -180 a 180

### `temperatura_c`
- Tipo: number · Unidad: °C · Formato: A en Fahrenheit, B ya en Celsius
- Transformación: A → convertir con `(f - 32) * 5/9`. B → castear a número

### `humedad`
- Tipo: number · Unidad: % (0–100) · Formato: ambos ya en porcentaje
- Transformación: renombrar/extraer; B viene como texto en CSV → castear a número

### `viento_kmh`
- Tipo: number · Unidad: km/h · Formato: A en m/s, B ya en km/h
- Transformación: A → convertir con `× 3.6`. B → castear a número

### `fecha_hora`
- Tipo: string (ISO 8601) · Unidad: ISO 8601 · Formato: A en ISO 8601 con offset (`2026-09-01T00:00:00-05:00`), B en `DD/MM/YYYY HH:MM`
- Transformación: A → parsear/validar. B → parsear con `strptime("%d/%m/%Y %H:%M")`, asumir offset `-05:00`, formatear con `.isoformat()`

### `origen`
- Tipo: string (valor permitido por el contrato) · Unidad: — · Formato: A usa `source` (ej. `"weather_provider_a"`), B usa `origin_code` (ej. `"PB"`)
- **El contrato institucional sí define los valores permitidos: `proveedor_a` y `proveedor_b`.**
- Transformación: se mapea cada valor crudo a su equivalente institucional:
  - `"weather_provider_a"` → `"proveedor_a"`
  - `"PB"` → `"proveedor_b"`
  - Cualquier valor de `origen` que no esté en este mapeo se considera un **error de normalización**.

## 3. Campos sin correspondencia en el contrato

- **Proveedor A:** `provider_record_id`, `station.code`, `generated_at` (metadatos no exigidos por el contrato)
- **Proveedor B:** `record_code`

Estos campos no se envían a la API, pero se usan como base para la trazabilidad interna (ver sección 6).

## 4. Reglas de validación local

Una vez normalizado, cada registro se valida contra las restricciones del contrato:

| Campo           |  Regla                                 |
|-----------------|----------------------------------------|
| `ciudad`        | No vacío                               |
| `pais`          | No vacío                               |
| `latitud`       | Entre -90 y 90                         |
| `longitud`      | Entre -180 y 180                       |
| `temperatura_c` | Debe ser numérico                      |
| `humedad`       | Entre 0 y 100                          |
| `viento_kmh`    | Mayor o igual a 0                      |
| `fecha_hora`    | No vacío (ya en ISO 8601)              |
| `origen`        | Debe ser `proveedor_a` o `proveedor_b` |

## 5. Error de normalización vs. registro rechazado localmente

Es importante distinguir dos situaciones distintas que pueden ocurrir con un registro:

- **`error_normalizacion`**: el registro **no pudo convertirse** a la representación exigida por el contrato institucional (por ejemplo, un campo numérico que no se puede castear, una fecha con formato irreconocible, o un valor de `origen` que no aparece en el mapeo de valores conocidos). Estos registros **no** se incluyen en `salida/normalizadas.json` ni se envían a la API, pero sí quedan identificados en el reporte final.

- **`rechazado_localmente`**: el registro **sí pudo normalizarse** correctamente al formato del contrato (tipos y estructura correctos), pero **incumple una regla de negocio** (por ejemplo, una humedad de 150%, fuera del rango permitido). Estos registros **sí** se incluyen en `salida/normalizadas.json` (porque su conversión fue exitosa), pero no se envían a la API, y quedan identificados en el reporte.

En resumen: `error_normalizacion` es un problema de **forma** (no se pudo representar), mientras que `rechazado_localmente` es un problema de **contenido** (se representó bien, pero el valor no cumple una regla).

## 6. Trazabilidad (`id_origen`)

Cada registro conserva un identificador interno de trazabilidad, usado únicamente para evidencias y reporte (nunca se envía en el body de la API):

- Si el registro trae un identificador propio del proveedor (`provider_record_id` en A, `record_code` en B), se usa ese.
- Si no lo trae, se genera uno propio a partir de la fuente y la posición del registro, con el formato `proveedor_a#<índice>` o `proveedor_b#<índice>`.

## 7. Supuestos documentados

1. **Zona horaria de `measurement_time` (Proveedor B):** el contrato exige ISO 8601, pero el proveedor B no incluye zona horaria. Se asume que corresponde a hora de Colombia (`-05:00`).
2. **Formato de `pais`:** se asume que el contrato espera el código ISO de 2 letras (ej. `"CO"`), ya que es el formato que entregan ambos proveedores; el contrato no lo especifica explícitamente.
3. **Mapeo de `origen`:** el contrato define los valores institucionales permitidos (`proveedor_a`, `proveedor_b`) pero no indica cómo mapear los valores crudos de cada proveedor a esos valores; el mapeo (`"weather_provider_a"` → `"proveedor_a"`, `"PB"` → `"proveedor_b"`) es una decisión propia del equipo, documentada aquí.

## 8. Resultados de referencia (dataset completo, 400 registros)

| Métrica                   | Valor |
|---------------------------|-------|
| Total procesados          | 400   |
| Normalizados exitosamente | 391   |
| Válidos localmente        | 380   |
| Rechazados localmente     | 11    |
| Errores de normalización  | 9     |

## 9. Validación local frente a validación del servidor

La validación local permitió detectar registros que, aunque podían normalizarse correctamente, incumplían las reglas del contrato institucional. Por esta razón, 11 registros fueron clasificados como `rechazado_localmente` y no fueron enviados a la API.

Sin embargo, superar la validación local no garantiza que el servidor acepte un registro. Durante la ejecución real se encontraron dos respuestas HTTP 409 correspondientes a los registros `A-0001` y `A-0002`. Ambos registros eran válidos localmente, pero ya habían sido registrados previamente durante las pruebas controladas de integración, por lo que el servidor respondió:

```json
{
  "detail": "La medición ya existe"
}```

Los códigos 4xx se consideran errores no transitorios, por lo que estos registros no fueron reintentados. En ambos casos se realizó únicamente 1 intento y el procesamiento continuó con los demás registros.

## 10. Decisión de implementación más importante

La decisión de implementación más importante fue separar claramente las etapas de lectura, normalización, validación local e integración HTTP.

La comunicación con la API únicamente recibe registros que previamente fueron normalizados y clasificados como válidos. Esto permite distinguir si un problema se produjo durante la transformación de los datos, por una regla de validación local o por una respuesta del servidor.

También se conservó `id_origen` únicamente como identificador interno de trazabilidad. Este campo permite relacionar cada resultado con el registro original, pero no se envía en el body porque no pertenece al contrato institucional.

Para los errores transitorios se implementó un máximo de tres intentos por registro: un intento inicial y hasta dos reintentos. Las respuestas 4xx no se reintentan, mientras que los errores 5xx, timeout y pérdida de conexión sí permiten nuevos intentos hasta alcanzar el máximo establecido.

## 11. Evidencia resumida de la ejecución real

La ejecución completa produjo los siguientes resultados:

| Métrica | Resultado |
|---|---:|
| Registros procesados | 400 |
| Registros normalizados | 391 |
| Errores de normalización | 9 |
| Válidos localmente | 380 |
| Rechazados localmente | 11 |
| Enviados a la API | 380 |
| Aceptados por la API | 378 |
| Rechazados por la API | 2 |
| Errores de comunicación | 0 |
| Mediciones registradas después del GET final | 380 |

### Ejemplo de error antes del envío

El registro `A-0040` fue clasificado como `error_normalizacion` debido a la ausencia del campo `observed_at`, por lo que no fue enviado a la API.

También se presentó, por ejemplo, el registro `A-0015`, que pudo normalizarse correctamente pero fue rechazado localmente porque contenía:

```text
humedad = 108.4
```

El motivo registrado fue:

```text
humedad fuera de rango: 108.4
```

Este caso evidencia la diferencia entre un error de normalización y un dato que puede representarse correctamente pero incumple las reglas del contrato.

### Respuesta exitosa de la API

Durante la prueba controlada de integración se obtuvo código HTTP `201` con una respuesta de este tipo:

```json
{
  "id": 4003,
  "estado": "aceptada",
  "mensaje": "Medición registrada correctamente"
}
```

### Rechazos de la API

Durante la ejecución completa se obtuvieron dos rechazos:

| `id_origen` | HTTP | Resultado | Motivo | Intentos |
|---|---:|---|---|---:|
| `A-0001` | 409 | `rechazado_api` | La medición ya existe | 1 |
| `A-0002` | 409 | `rechazado_api` | La medición ya existe | 1 |

Estos dos registros habían sido enviados previamente durante las pruebas controladas. Por esta razón, durante la ejecución completa fueron aceptados 378 registros nuevos.

Los resultados son consistentes:

```text
378 registros nuevos aceptados
+ 2 registros ya existentes
= 380 mediciones únicas almacenadas
```

### Consulta final mediante GET

La consulta final respondió con código HTTP `200` e indicó un total de:

```json
{
  "equipo": "EQUIPO-03-APPSWEB",
  "total": 380
}
```

Por lo tanto, al finalizar el proceso quedaron almacenadas 380 mediciones únicas para el equipo.

## 12. Pruebas automatizadas

Se implementaron 10 pruebas automatizadas independientes de la API real. Estas cubren:

- transformación de datos del proveedor A;
- conversión de Fahrenheit a Celsius;
- conversión de m/s a km/h;
- transformación de fecha y origen del proveedor B;
- registro válido;
- registro inválido;
- valores límite;
- reintentos ante errores 503;
- timeout y pérdida de conexión;
- generación del resumen y procesamiento de varios registros.

La ejecución final de la suite produjo:

```text
10 passed
```