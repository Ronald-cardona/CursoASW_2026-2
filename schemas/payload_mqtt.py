import math
import re
from datetime import timezone
from decimal import Decimal, InvalidOperation

from pydantic import AwareDatetime, BaseModel, Field, field_validator


class MagnitudPayload(BaseModel):
    """Una magnitud dentro de `measurements`: {"value": 24.6, "unit": "C"}."""

    value: Decimal = Field(max_digits=12, decimal_places=4)
    unit: str = Field(min_length=1, max_length=20)

    @field_validator("value", mode="before")
    @classmethod
    def solo_numeros(cls, v):
        # bool es subclase de int en Python: se rechaza de forma explícita
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("value debe ser un número (int o float)")
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("value debe ser un número finito")
        try:
            # Se redondea a 4 decimales, igual que NUMERIC(12,4) en la BD
            return Decimal(str(v)).quantize(Decimal("0.0001"))
        except InvalidOperation:
            raise ValueError("value fuera del rango numérico soportado")

    @field_validator("unit", mode="before")
    @classmethod
    def unidad_texto(cls, v):
        if not isinstance(v, str):
            raise ValueError("unit debe ser texto")
        return v.strip()


class PayloadMQTT(BaseModel):
    """Estructura completa del mensaje publicado por un sensor."""

    sensor_id: str = Field(min_length=1, max_length=20)  # equivale a sensores.codigo
    timestamp: AwareDatetime
    measurements: dict[str, MagnitudPayload] = Field(min_length=1)

    @field_validator("sensor_id", mode="before")
    @classmethod
    def sensor_id_texto(cls, v):
        if not isinstance(v, str):
            raise ValueError("sensor_id debe ser texto")
        return v.strip()

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_iso(cls, v):
        # Pydantic aceptaría también números (epoch) y fechas sin hora;
        # aquí se exige texto ISO 8601 con fecha y hora.
        if not isinstance(v, str) or not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", v):
            raise ValueError(
                "timestamp debe ser texto ISO 8601 con zona horaria, "
                "ej. 2026-10-07T16:25:30Z"
            )
        return v

    @field_validator("timestamp", mode="after")
    @classmethod
    def timestamp_a_utc(cls, v):
        return v.astimezone(timezone.utc)

    @field_validator("measurements")
    @classmethod
    def claves_validas(cls, v):
        for nombre in v:
            if not nombre.strip() or len(nombre) > 50:
                raise ValueError(f"nombre de magnitud inválido: {nombre!r}")
        return v