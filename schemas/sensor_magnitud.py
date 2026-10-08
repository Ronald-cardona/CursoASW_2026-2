from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SensorMagnitudBase(BaseModel):
    sensor_id: int
    magnitud: str = Field(min_length=1, max_length=50)
    unidad: str = Field(min_length=1, max_length=20)
    valor_minimo: Decimal = Field(max_digits=12, decimal_places=4)
    valor_maximo: Decimal = Field(max_digits=12, decimal_places=4)

    @model_validator(mode="after")
    def validar_rango(self):
        if self.valor_minimo >= self.valor_maximo:
            raise ValueError("valor_minimo debe ser menor que valor_maximo")
        return self


class SensorMagnitudCreate(SensorMagnitudBase):
    pass


class SensorMagnitudUpdate(BaseModel):
    """Para PATCH: todos opcionales. El rango final se valida en la API."""

    sensor_id: int | None = None
    magnitud: str | None = Field(default=None, min_length=1, max_length=50)
    unidad: str | None = Field(default=None, min_length=1, max_length=20)
    valor_minimo: Decimal | None = Field(default=None, max_digits=12, decimal_places=4)
    valor_maximo: Decimal | None = Field(default=None, max_digits=12, decimal_places=4)


class SensorMagnitudResponse(SensorMagnitudBase):
    model_config = ConfigDict(from_attributes=True)

    id: int