from datetime import datetime
from decimal import Decimal
from schemas.tiempo import HoraColombia

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class MedicionBase(BaseModel):
    sensor_magnitud_id: int
    valor: Decimal = Field(max_digits=12, decimal_places=4)
    # AwareDatetime exige zona horaria (ej. 2026-10-07T15:30:00Z)
    timestamp_utc: AwareDatetime


class MedicionCreate(MedicionBase):
    pass


class MedicionUpdate(BaseModel):
    """Para PATCH: todos opcionales."""

    sensor_magnitud_id: int | None = None
    valor: Decimal | None = Field(default=None, max_digits=12, decimal_places=4)
    timestamp_utc: AwareDatetime | None = None


class MedicionResponse(BaseModel):
    """Respuesta de la API: las fechas salen en hora de Colombia.

    En la BD se conservan en UTC (timestamp_utc, fecha_recepcion).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_magnitud_id: int
    valor: Decimal
    timestamp_local: HoraColombia = Field(validation_alias="timestamp_utc")
    fecha_recepcion_local: HoraColombia = Field(validation_alias="fecha_recepcion")