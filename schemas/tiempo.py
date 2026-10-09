from datetime import datetime, timezone
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import PlainSerializer

#zona horaria de colombia UTC-5
ZONA_COLOMBIA = ZoneInfo("America/Bogota")

def a_hora_colombia(dt: datetime) -> str:
    """Convierte un datetime a hora de Colombia con formato fijo.

    Ejemplo: 2026-10-07 11:25:30 (UTC-05:00)
    """
    if dt.tzinfo is None:  # por seguridad: lo que se guarda es siempre UTC
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(ZONA_COLOMBIA)
    desfase = local.strftime("%z")  # -0500
    return f"{local:%Y-%m-%d %H:%M:%S} (UTC{desfase[:3]}:{desfase[3:]})"


def a_utc(dt: datetime) -> datetime:
    """Para filtros: una fecha sin zona se interpreta como hora de Colombia."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZONA_COLOMBIA)
    return dt.astimezone(timezone.utc)


# Tipo para campos de respuesta: en el JSON de salida se ve en hora de Colombia
HoraColombia = Annotated[
    datetime, PlainSerializer(a_hora_colombia, return_type=str, when_used="json")
]