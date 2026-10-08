"""Consumidor MQTT de ejemplo para el taller.

Este archivo solo demuestra cómo conectarse, suscribirse y visualizar mensajes.
No implementa las validaciones Pydantic, la persistencia en PostgreSQL ni la
lógica completa exigida por el taller.
"""

import json
import logging
import os
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from mqtt.ingesta import guardar_mensaje

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

BROKER = os.getenv("MQTT_BROKER")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC", "iot/sensors/GAS-002/data")
USERNAME = os.getenv("MQTT_USERNAME")
PASSWORD = os.getenv("MQTT_PASSWORD")
KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))

# LOG_PAYLOADS=1 guarda cada mensaje crudo en un archivo, útil para documentar
LOG_PAYLOADS = os.getenv("LOG_PAYLOADS", "0") == "1"
PAYLOADS_FILE = "payloads_recibidos.jsonl"


def on_connect(client, userdata, flags, reason_code, properties=None):
    """Se ejecuta cuando el cliente se conecta al broker."""
    if reason_code.is_failure:
        print(f"Error de conexión MQTT: {reason_code}")
        return

    print(f"Conectado al broker {BROKER}:{PORT}")
    result, _ = client.subscribe(TOPIC)
    if result != mqtt.MQTT_ERR_SUCCESS:
        print(f"No fue posible suscribirse a {TOPIC}: código {result}")
        return

    print(f"Suscrito al tópico: {TOPIC}")
    print("Esperando mensajes... Presiona Ctrl+C para finalizar.")


def on_message(client, userdata, message):
    """Se ejecuta cada vez que llega un mensaje al tópico suscrito."""
    received_at = datetime.now(timezone.utc).isoformat()
    raw = message.payload.decode("utf-8", errors="replace")

    if LOG_PAYLOADS:
        with open(PAYLOADS_FILE, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {"topic": message.topic, "recibido_utc": received_at, "payload": raw},
                    ensure_ascii=False,
                )
                + "\n"
            )

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        print(f"[{received_at}] Payload inválido en {message.topic}: {error}")
        return

    print(f"\n[{received_at}] Mensaje recibido")
    print(f"Tópico: {message.topic}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    guardadas = guardar_mensaje(payload)
    print(f"Mediciones guardadas en la BD: {guardadas}")


def main():
    if not BROKER:
        raise RuntimeError(
            "Falta MQTT_BROKER. Configúralo en el archivo .env antes de ejecutar."
        )

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD or "")

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Conectando a {BROKER}:{PORT}...")
    client.connect(BROKER, PORT, KEEPALIVE)
    client.loop_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nConsumidor detenido por el usuario.")
