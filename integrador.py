"""
Paso 2: Lectura de datos

Lee datos de proveedores, los normaliza al contrato institucional,
los valida localmente y genera evidencias.
"""

import json
import csv
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta

# =========================
# CONFIGURACIÓN DE LA API
# =========================

URL_BASE = "https://appsweb.quantaiot.co"
EQUIPO = "EQUIPO-03-APPSWEB"

TIMEOUT_SEGUNDOS = 5
MAX_INTENTOS = 3


# =========================
# 1. LECTURA DE DATOS
# =========================

def leer_proveedor_a(ruta: str) -> list[dict]:
    """Lee el archivo JSON del proveedor A y devuelve su lista de registros."""
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["records"]


def leer_proveedor_b(ruta: str) -> list[dict]:
    """Lee el archivo CSV del proveedor B (separado por ;) y devuelve una lista de dicts."""
    with open(ruta, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        return list(reader)


# =========================
# 2. NORMALIZACIÓN
# =========================

OFFSET_COLOMBIA = timezone(timedelta(hours=-5))

ORIGEN_PERMITIDOS = {
    "weather_provider_a": "proveedor_a",
    "PB": "proveedor_b",
}


def normalizar_registro_a(registro: dict) -> dict:
    """Normaliza un registro del proveedor A al contrato institucional."""
    try:
        temp_f = registro["measurements"]["temperature_f"]
        temp_c = (float(temp_f) - 32) * 5 / 9

        viento_ms = registro["measurements"]["wind_speed_ms"]
        viento_kmh = float(viento_ms) * 3.6

        fecha = datetime.fromisoformat(registro["observed_at"])
        fecha_iso = fecha.isoformat()

        origen_crudo = registro.get("source", "")
        if origen_crudo not in ORIGEN_PERMITIDOS:
            raise ValueError(f"origen no reconocido: {origen_crudo}")

        return {
            "ok": True,
            "id_origen": registro.get("provider_record_id"),
            "dato": {
                "ciudad": registro["station"]["city_name"],
                "pais": registro["station"]["country_code"],
                "latitud": float(registro["location"]["lat"]),
                "longitud": float(registro["location"]["lon"]),
                "temperatura_c": round(temp_c, 2),
                "humedad": float(registro["measurements"]["relative_humidity"]),
                "viento_kmh": round(viento_kmh, 2),
                "fecha_hora": fecha_iso,
                "origen": ORIGEN_PERMITIDOS[origen_crudo],
            },
        }
    except (KeyError, ValueError, TypeError) as e:
        return {
            "ok": False,
            "id_origen": registro.get("provider_record_id", "desconocido"),
            "error": str(e),
        }


def normalizar_registro_b(registro: dict) -> dict:
    """Normaliza un registro del proveedor B al contrato institucional."""
    try:
        temp_c = float(registro["temp_celsius"])
        viento_kmh = float(registro["wind_kmh"])
        humedad = float(registro["humidity_pct"])
        latitud = float(registro["latitude_deg"])
        longitud = float(registro["longitude_deg"])

        fecha_dt = datetime.strptime(registro["measurement_time"], "%d/%m/%Y %H:%M")
        fecha_dt = fecha_dt.replace(tzinfo=OFFSET_COLOMBIA)
        fecha_iso = fecha_dt.isoformat()

        origen_crudo = registro.get("origin_code", "")
        if origen_crudo not in ORIGEN_PERMITIDOS:
            raise ValueError(f"origen no reconocido: {origen_crudo}")

        return {
            "ok": True,
            "id_origen": registro.get("record_code"),
            "dato": {
                "ciudad": registro["municipality"],
                "pais": registro["country"],
                "latitud": latitud,
                "longitud": longitud,
                "temperatura_c": round(temp_c, 2),
                "humedad": humedad,
                "viento_kmh": round(viento_kmh, 2),
                "fecha_hora": fecha_iso,
                "origen": ORIGEN_PERMITIDOS[origen_crudo],
            },
        }
    except (KeyError, ValueError, TypeError) as e:
        return {
            "ok": False,
            "id_origen": registro.get("record_code", "desconocido"),
            "error": str(e),
        }


def normalizar_todos(registros_a: list[dict], registros_b: list[dict]) -> list[dict]:
    """Aplica la normalización a ambos proveedores y devuelve una lista unificada de resultados."""
    resultados = []
    for i, r in enumerate(registros_a):
        resultado = normalizar_registro_a(r)
        if not resultado.get("id_origen"):
            resultado["id_origen"] = f"proveedor_a#{i}"
        resultados.append(resultado)
    for i, r in enumerate(registros_b):
        resultado = normalizar_registro_b(r)
        if not resultado.get("id_origen"):
            resultado["id_origen"] = f"proveedor_b#{i}"
        resultados.append(resultado)
    return resultados


# =========================
# 3. VALIDACIÓN LOCAL
# =========================

ORIGEN_VALIDOS = {"proveedor_a", "proveedor_b"}


def validar_registro(dato: dict) -> tuple[bool, list[str]]:
    """Valida un registro ya normalizado contra las reglas de negocio del contrato."""
    motivos = []

    if not dato.get("ciudad", "").strip():
        motivos.append("ciudad vacía")

    if not dato.get("pais", "").strip():
        motivos.append("pais vacío")

    lat = dato.get("latitud")
    if lat is None or not (-90 <= lat <= 90):
        motivos.append(f"latitud fuera de rango: {lat}")

    lon = dato.get("longitud")
    if lon is None or not (-180 <= lon <= 180):
        motivos.append(f"longitud fuera de rango: {lon}")

    if not isinstance(dato.get("temperatura_c"), (int, float)):
        motivos.append("temperatura_c no es numérico")

    hum = dato.get("humedad")
    if hum is None or not (0 <= hum <= 100):
        motivos.append(f"humedad fuera de rango: {hum}")

    viento = dato.get("viento_kmh")
    if viento is None or viento < 0:
        motivos.append(f"viento_kmh negativo: {viento}")

    if not dato.get("fecha_hora", "").strip():
        motivos.append("fecha_hora vacía")

    if dato.get("origen") not in ORIGEN_VALIDOS:
        motivos.append(f"origen no permitido: {dato.get('origen')}")

    return (len(motivos) == 0, motivos)


def clasificar_resultados(resultados_normalizacion: list[dict]) -> dict:
    """Clasifica cada registro en válido, rechazado_localmente o error_normalizacion."""
    validos = []
    rechazados = []
    con_error = []

    for r in resultados_normalizacion:
        if not r["ok"]:
            con_error.append({
                "id_origen": r["id_origen"],
                "estado": "error_normalizacion",
                "motivo": r["error"],
            })
            continue

        es_valido, motivos = validar_registro(r["dato"])
        if es_valido:
            validos.append({
                "id_origen": r["id_origen"],
                "estado": "valido",
                "dato": r["dato"],
            })
        else:
            rechazados.append({
                "id_origen": r["id_origen"],
                "estado": "rechazado_localmente",
                "dato": r["dato"],
                "motivo": "; ".join(motivos),
            })

    return {
        "validos": validos,
        "rechazados_localmente": rechazados,
        "error_normalizacion": con_error,
    }


# =========================
# 4. EVIDENCIAS
# =========================

def guardar_normalizadas(clasificados: dict, ruta: str = "salida/normalizadas.json") -> None:
    """Escribe salida/normalizadas.json con los registros válidos y rechazados_localmente."""
    registros_a_guardar = []

    for r in clasificados["validos"]:
        registros_a_guardar.append({
            "id_origen": r["id_origen"],
            "estado": r["estado"],
            "dato": r["dato"],
        })

    for r in clasificados["rechazados_localmente"]:
        registros_a_guardar.append({
            "id_origen": r["id_origen"],
            "estado": r["estado"],
            "dato": r["dato"],
            "motivo": r["motivo"],
        })

    ruta_path = Path(ruta)
    ruta_path.parent.mkdir(parents=True, exist_ok=True)

    with open(ruta_path, "w", encoding="utf-8") as f:
        json.dump(registros_a_guardar, f, ensure_ascii=False, indent=2)

# =========================
# 5. INTEGRACIÓN HTTP
# =========================

def construir_headers() -> dict:
    """Construye los encabezados requeridos para consumir la API."""
    return {
        "Content-Type": "application/json",
        "X-Equipo": EQUIPO,
    }

def enviar_medicion(registro: dict):
    """Envía una medición válida a la API institucional."""

    url = f"{URL_BASE}/api/v1/mediciones"

    respuesta = requests.post(
        url,
        headers=construir_headers(),
        json=registro["dato"],
        timeout=TIMEOUT_SEGUNDOS,
    )
    return respuesta

def interpretar_respuesta(respuesta) -> dict:
    """Interpreta una respuesta HTTP recibida desde la API."""

    try:
        contenido = respuesta.json()
    except ValueError:
        contenido = {
            "mensaje": respuesta.text.strip() or "Respuesta sin contenido"
        }

    codigo = respuesta.status_code

    if codigo == 201:
        resultado = "aceptado"
        reintentar = False

    elif codigo in (400, 409, 422):
        resultado = "rechazado_api"
        reintentar = False

    elif 500 <= codigo < 600:
        resultado = "error_transitorio"
        reintentar = True

    else:
        resultado = "respuesta_inesperada"
        reintentar = False

    return {
        "codigo_http": codigo,
        "resultado": resultado,
        "reintentar": reintentar,
        "respuesta": contenido,
    }

def enviar_medicion_con_reintentos(registro: dict) -> dict:
    """Envía una medición y reintenta ante errores transitorios."""

    ultimo_resultado = None

    for intento in range(1, MAX_INTENTOS + 1):
        try:
            respuesta = enviar_medicion(registro)
            resultado = interpretar_respuesta(respuesta)

            resultado["id_origen"] = registro["id_origen"]
            resultado["intentos"] = intento

            # 201 o 4xx o código inesperado: termina aquí.
            if not resultado["reintentar"]:
                return resultado

            # 5xx: se conserva el resultado y se vuelve a intentar.
            ultimo_resultado = resultado

        except requests.exceptions.Timeout:
            ultimo_resultado = {
                "id_origen": registro["id_origen"],
                "codigo_http": None,
                "resultado": "error_transitorio",
                "reintentar": True,
                "intentos": intento,
                "respuesta": {
                    "mensaje": "Timeout al comunicarse con la API"
                },
            }

        except requests.exceptions.ConnectionError:
            ultimo_resultado = {
                "id_origen": registro["id_origen"],
                "codigo_http": None,
                "resultado": "error_transitorio",
                "reintentar": True,
                "intentos": intento,
                "respuesta": {
                    "mensaje": "Pérdida de conexión con la API"
                },
            }

        except requests.exceptions.RequestException as error:
            return {
                "id_origen": registro["id_origen"],
                "codigo_http": None,
                "resultado": "error_comunicacion",
                "reintentar": False,
                "intentos": intento,
                "respuesta": {
                    "mensaje": str(error)
                },
            }

    # Si llegó hasta aquí, agotó los 3 intentos.
    return {
        "id_origen": registro["id_origen"],
        "codigo_http": ultimo_resultado["codigo_http"],
        "resultado": "error_comunicacion",
        "reintentar": False,
        "intentos": MAX_INTENTOS,
        "respuesta": ultimo_resultado["respuesta"],
    }

def enviar_registros_validos(registros_validos: list) -> list:
    """Envía todos los registros válidos y conserva el resultado de cada uno."""

    resultados_envio = []
    total = len(registros_validos)

    for indice, registro in enumerate(registros_validos, start=1):
        resultado = enviar_medicion_con_reintentos(registro)
        resultados_envio.append(resultado)

        print(
            f"[{indice}/{total}] "
            f"{registro['id_origen']} -> "
            f"{resultado['resultado']} "
            f"(HTTP: {resultado['codigo_http']}, "
            f"intentos: {resultado['intentos']})"
        )

    return resultados_envio

def consultar_mediciones_equipo() -> dict:
    """Consulta las mediciones almacenadas para el equipo."""

    url = f"{URL_BASE}/api/v1/mediciones"

    try:
        respuesta = requests.get(
            url,
            params={"equipo": EQUIPO},
            timeout=TIMEOUT_SEGUNDOS,
        )

        if respuesta.status_code != 200:
            return {
                "ok": False,
                "codigo_http": respuesta.status_code,
                "respuesta": respuesta.text,
            }

        try:
            contenido = respuesta.json()
        except ValueError:
            return {
                "ok": False,
                "codigo_http": respuesta.status_code,
                "respuesta": "La respuesta del GET no es JSON válido",
            }

        return {
            "ok": True,
            "codigo_http": respuesta.status_code,
            "respuesta": contenido,
        }

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "codigo_http": None,
            "respuesta": "Timeout durante la consulta final",
        }

    except requests.exceptions.ConnectionError:
        return {
            "ok": False,
            "codigo_http": None,
            "respuesta": "Error de conexión durante la consulta final",
        }

    except requests.exceptions.RequestException as error:
        return {
            "ok": False,
            "codigo_http": None,
            "respuesta": str(error),
        }

def generar_reporte(
    procesados: int,
    clasificados: dict,
    resultados_envio: list,
    consulta_final: dict,
) -> dict:
    """Construye el reporte general y la trazabilidad de la integración."""

    aceptados_api = sum(
        1
        for resultado in resultados_envio
        if resultado["resultado"] == "aceptado"
    )

    rechazados_api = sum(
        1
        for resultado in resultados_envio
        if resultado["resultado"] == "rechazado_api"
    )

    errores_comunicacion = sum(
        1
        for resultado in resultados_envio
        if resultado["resultado"] in {
            "error_comunicacion",
            "respuesta_inesperada",
        }
    )

    reporte = {
        "resumen": {
            "procesados": procesados,
            "normalizados": (
                len(clasificados["validos"])
                + len(clasificados["rechazados_localmente"])
            ),
            "errores_normalizacion": len(
                clasificados["error_normalizacion"]
            ),
            "validos_localmente": len(
                clasificados["validos"]
            ),
            "rechazados_localmente": len(
                clasificados["rechazados_localmente"]
            ),
            "enviados": len(resultados_envio),
            "aceptados_api": aceptados_api,
            "rechazados_api": rechazados_api,
            "errores_comunicacion": errores_comunicacion,
        },

        "trazabilidad": {
            "error_normalizacion": clasificados[
                "error_normalizacion"
            ],
            "rechazados_localmente": clasificados[
                "rechazados_localmente"
            ],
            "envios_api": resultados_envio,
        },

        "consulta_final": consulta_final,
    }

    return reporte

def guardar_reporte(
    reporte: dict,
    ruta: str = "salida/reporte.json"
) -> None:
    """Guarda el reporte final de integración."""

    ruta_path = Path(ruta)
    ruta_path.parent.mkdir(parents=True, exist_ok=True)

    with open(ruta_path, "w", encoding="utf-8") as archivo:
        json.dump(
            reporte,
            archivo,
            ensure_ascii=False,
            indent=2
        )

# =========================
# MAIN
# =========================

def main():
    ruta_a = Path("datos/proveedor_a.json")
    ruta_b = Path("datos/proveedor_b.csv")

    # =========================
    # LECTURA
    # =========================

    registros_a = leer_proveedor_a(ruta_a)
    registros_b = leer_proveedor_b(ruta_b)

    procesados = len(registros_a) + len(registros_b)

    print(f"Registros leídos de proveedor A: {len(registros_a)}")
    print(f"Registros leídos de proveedor B: {len(registros_b)}")
    print(f"Total procesados: {procesados}")

    # =========================
    # NORMALIZACIÓN Y VALIDACIÓN
    # =========================

    resultados = normalizar_todos(
        registros_a,
        registros_b
    )

    clasificados = clasificar_resultados(resultados)

    guardar_normalizadas(clasificados)

    print("\n--- Clasificación ---")
    print(f"Válidos: {len(clasificados['validos'])}")
    print(
        "Rechazados localmente: "
        f"{len(clasificados['rechazados_localmente'])}"
    )
    print(
        "Error de normalización: "
        f"{len(clasificados['error_normalizacion'])}"
    )

    # =========================
    # INTEGRACIÓN CON LA API
    # =========================

    print("\n--- Envío a la API ---")

    resultados_envio = enviar_registros_validos(
        clasificados["validos"]
    )

    # =========================
    # CONSULTA FINAL
    # =========================

    print("\n--- Consulta final ---")

    consulta_final = consultar_mediciones_equipo()

    # =========================
    # REPORTE
    # =========================

    reporte = generar_reporte(
        procesados=procesados,
        clasificados=clasificados,
        resultados_envio=resultados_envio,
        consulta_final=consulta_final,
    )

    guardar_reporte(reporte)

    # =========================
    # RESUMEN EN CONSOLA
    # =========================

    resumen = reporte["resumen"]

    print("\n--- Resumen final ---")
    print(f"Procesados: {resumen['procesados']}")
    print(f"Normalizados: {resumen['normalizados']}")
    print(
        "Errores de normalización: "
        f"{resumen['errores_normalizacion']}"
    )
    print(
        "Válidos localmente: "
        f"{resumen['validos_localmente']}"
    )
    print(
        "Rechazados localmente: "
        f"{resumen['rechazados_localmente']}"
    )
    print(f"Enviados: {resumen['enviados']}")
    print(
        "Aceptados por API: "
        f"{resumen['aceptados_api']}"
    )
    print(
        "Rechazados por API: "
        f"{resumen['rechazados_api']}"
    )
    print(
        "Errores de comunicación: "
        f"{resumen['errores_comunicacion']}"
    )

    if consulta_final["ok"]:
        total_api = consulta_final[
            "respuesta"
        ].get("total")

        print(
            "Mediciones registradas para el equipo: "
            f"{total_api}"
        )

    else:
        print(
            "No fue posible completar la consulta final: "
            f"{consulta_final['respuesta']}"
        )

    print(
        "\nReporte generado en: "
        "salida/reporte.json"
    )

    return (
        registros_a,
        registros_b,
        clasificados,
        resultados_envio,
        consulta_final,
        reporte,
    )

if __name__ == "__main__":
    try:
        main()

    except FileNotFoundError as error:
        print(
            "\nERROR: No se encontró uno de los archivos requeridos."
        )
        print(error)

    except json.JSONDecodeError as error:
        print(
            "\nERROR: Se encontró un archivo JSON inválido."
        )
        print(error)

    except PermissionError as error:
        print(
            "\nERROR: No hay permisos suficientes para acceder "
            "a uno de los archivos."
        )
        print(error)

    except Exception as error:
        print(
            "\nERROR inesperado durante la ejecución."
        )
        print(error)