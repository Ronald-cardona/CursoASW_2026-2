import logging

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import models  # noqa: F401  (registra los modelos)
from crud import medicion as crud_medicion
from crud import sensor as crud_sensor
from crud import sensor_magnitud as crud_magnitud
from database import SessionLocal
from schemas.medicion import MedicionCreate
from schemas.payload_mqtt import PayloadMQTT

log = logging.getLogger("ingesta")

# archivo que recibe la ingesta de datos y decide si llevarlo a base de datos

# Si el nombre en el payload no coincide con sensor_magnitudes.magnitud,
# agrega el equivalente aquí. Ej: {"temp": "temperature"}
ALIAS_MAGNITUDES: dict[str, str] = {}


def resumen_errores_pydantic(e: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()
    )


def validar_reglas_negocio(
    db, payload: PayloadMQTT
) -> tuple[list[MedicionCreate], list[str]]:
    """Valida el payload contra la base de datos.

    Devuelve (mediciones_a_guardar, errores). Se revisa TODO el payload y se
    acumulan los errores; si hay alguno, no se debe guardar nada.
    """
    errores: list[str] = []
    codigo = payload.sensor_id

    # 1. Existencia del sensor
    sensor = crud_sensor.obtener_sensor_por_codigo(db, codigo)
    if sensor is None:
        return [], [f"el sensor con código '{codigo}' no existe"]

    # 2. Estado del sensor
    if not sensor.activo:
        return [], [f"el sensor '{codigo}' está inactivo"]

    sensor_id = sensor.id
    mediciones: list[MedicionCreate] = []
    magnitudes_vistas: set[str] = set()

    for nombre, medida in payload.measurements.items():
        nombre_bd = ALIAS_MAGNITUDES.get(nombre, nombre)

        if nombre_bd in magnitudes_vistas:
            errores.append(f"la magnitud '{nombre_bd}' aparece repetida en el payload")
            continue
        magnitudes_vistas.add(nombre_bd)

        # 3. Relación sensor - magnitud
        magnitud = crud_magnitud.obtener_magnitud_de_sensor(db, sensor_id, nombre_bd)
        if magnitud is None:
            errores.append(
                f"la magnitud '{nombre_bd}' no está registrada para el sensor '{codigo}'"
            )
            continue

        # 5. Consistencia de claves foráneas
        if magnitud.sensor_id != sensor_id:
            errores.append(
                f"la magnitud '{nombre_bd}' (id {magnitud.id}) no pertenece al sensor '{codigo}'"
            )
            continue

        # 4. Correspondencia de la unidad
        if medida.unit != magnitud.unidad:
            errores.append(
                f"unidad de '{nombre_bd}': llegó '{medida.unit}' y la registrada es "
                f"'{magnitud.unidad}'"
            )
            continue

        if not (magnitud.valor_minimo <= medida.value <= magnitud.valor_maximo):
            log.warning(
                "[%s] %s: valor %s fuera del rango [%s, %s] (se guarda igual)",
                codigo, nombre_bd, medida.value,
                magnitud.valor_minimo, magnitud.valor_maximo,
            )

        # Un registro independiente por magnitud; todos con el mismo
        # timestamp_utc, el del payload.
        mediciones.append(
            MedicionCreate(
                sensor_magnitud_id=magnitud.id,
                valor=medida.value,
                timestamp_utc=payload.timestamp,
            )
        )

    return mediciones, errores


def procesar_payload(db, datos) -> int:
    """Valida y guarda un payload. Devuelve cuántas mediciones guardó (0 si se rechaza)."""
    # Fase 1: estructura, campos obligatorios, tipos y timestamp (Pydantic)
    try:
        payload = PayloadMQTT.model_validate(datos)
    except ValidationError as e:
        log.warning("Payload rechazado por estructura: %s", resumen_errores_pydantic(e))
        return 0

    # Fase 2: reglas de negocio contra la BD (ORM)
    mediciones, errores = validar_reglas_negocio(db, payload)
    if errores:
        log.warning(
            "Payload de '%s' rechazado, no se guarda nada: %s",
            payload.sensor_id, " | ".join(errores),
        )
        return 0

    # Fase 3: guardado atómico (todas las magnitudes o ninguna)
    try:
        crud_medicion.crear_mediciones_lote(db, mediciones)
    except IntegrityError as e:
        log.error("Payload de '%s' rechazado por la BD: %s", payload.sensor_id, e.orig)
        return 0

    return len(mediciones)


def guardar_mensaje(datos) -> int:
    """Punto de entrada para el cliente MQTT: abre sesión y guarda el mensaje."""
    try:
        with SessionLocal() as db:
            return procesar_payload(db, datos)
    except SQLAlchemyError:
        log.exception("Error de base de datos")
    except Exception:
        log.exception("Error inesperado al procesar el mensaje")
    return 0