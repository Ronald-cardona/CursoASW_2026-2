"""Consumidor MQTT de ejemplo para el taller.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from mqtt.ingesta import guardar_mensaje
from schemas.tiempo import ZONA_COLOMBIA, a_hora_colombia

load_dotenv()

# Las horas del log salen siempre en hora de Colombia, sin importar la zona del PC
logging.Formatter.converter = staticmethod(
    lambda ts: datetime.fromtimestamp(ts, ZONA_COLOMBIA).timetuple()
)

# Los avisos y rechazos quedan también en ingesta.log (evidencia de la recolección)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ingesta.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("client")

BROKER = os.getenv("MQTT_BROKER")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC", "iot/sensors/AQ-005/data")
USERNAME = os.getenv("MQTT_USERNAME")
PASSWORD = os.getenv("MQTT_PASSWORD")
KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))

# LOG_PAYLOADS=1 guarda cada mensaje crudo (válido o no) en un archivo
LOG_PAYLOADS = os.getenv("LOG_PAYLOADS", "0") == "1"
PAYLOADS_FILE = "payloads_recibidos.jsonl"

# Contadores de la recolección
INICIO = time.monotonic()
INICIO_UTC = datetime.now(timezone.utc)
STATS = {"recibidos": 0, "guardados": 0, "rechazados": 0, "mediciones": 0}


def imprimir_resumen():
    fin_utc = datetime.now(timezone.utc)
    minutos = (time.monotonic() - INICIO) / 60
    print("\n=== Resumen de la recolección ===")
    print(f"Inicio:                {a_hora_colombia(INICIO_UTC)}")
    print(f"Fin:                   {a_hora_colombia(fin_utc)}")
    print(f"Duración:              {minutos:.1f} minutos")
    print(f"Mensajes recibidos:    {STATS['recibidos']}")
    print(f"Mensajes almacenados:  {STATS['guardados']} ({STATS['mediciones']} mediciones)")
    print(f"Mensajes rechazados:   {STATS['rechazados']} (detalle en ingesta.log)")


def on_connect(client, userdata, flags, reason_code, properties=None):
    """Se ejecuta al conectar y en cada reconexión automática."""
    if reason_code.is_failure:
        log.error("Error de conexión MQTT: %s", reason_code)
        return

    log.info("Conectado al broker %s:%s", BROKER, PORT)
    result, _ = client.subscribe(TOPIC)
    if result != mqtt.MQTT_ERR_SUCCESS:
        log.error("No fue posible suscribirse a %s: código %s", TOPIC, result)
        return

    log.info("Suscrito al tópico: %s. Presiona Ctrl+C para finalizar.", TOPIC)


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    log.warning("Desconectado del broker (%s). Se reintentará automáticamente.", reason_code)


def on_message(client, userdata, message):
    """Se ejecuta cada vez que llega un mensaje (válido o inválido)."""
    STATS["recibidos"] += 1
    received_at = datetime.now(timezone.utc)
    raw = message.payload.decode("utf-8", errors="replace")

    if LOG_PAYLOADS:
        with open(PAYLOADS_FILE, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "topic": message.topic,
                        "recibido_utc": received_at.isoformat(),
                        "payload": raw,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    guardadas = 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        log.warning("Mensaje rechazado, no es JSON válido (%s): %s", error, raw[:200])
    else:
        guardadas = guardar_mensaje(payload)  # valida y guarda; 0 si se rechaza

    if guardadas > 0:
        STATS["guardados"] += 1
        STATS["mediciones"] += guardadas
    else:
        STATS["rechazados"] += 1

    hora = received_at.astimezone(ZONA_COLOMBIA)
    print(
        f"[{hora:%Y-%m-%d %H:%M:%S}] {message.topic} -> "
        f"{guardadas} mediciones en este mensaje | "
        f"TOTAL: recibidos={STATS['recibidos']} almacenados={STATS['guardados']} "
        f"rechazados={STATS['rechazados']}"
    )


def main():
    if not BROKER:
        raise RuntimeError(
            "Falta MQTT_BROKER. Configúralo en el archivo .env antes de ejecutar."
        )

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD or "")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    log.info("Conectando a %s:%s...", BROKER, PORT)
    client.connect(BROKER, PORT, KEEPALIVE)
    client.loop_forever()  # reconecta solo si se cae la conexión


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nConsumidor detenido por el usuario.")
    finally:
        imprimir_resumen()