from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CategoriaSensor(str, Enum):
    AIRE = "AIRE"
    GAS = "GAS"
    AGUA = "AGUA"
    AMBIENTE = "AMBIENTE"


class SensorBase(BaseModel):
    # use_enum_values: categoria llega como str simple a la BD
    model_config = ConfigDict(use_enum_values=True)

    codigo: str = Field(min_length=1, max_length=20)
    nombre: str = Field(min_length=1, max_length=100)
    categoria: CategoriaSensor
    ubicacion: str = Field(min_length=1, max_length=100)
    activo: bool = True


class SensorCreate(SensorBase):
    pass


class SensorUpdate(BaseModel):
    """Para PATCH: todos los campos son opcionales."""

    model_config = ConfigDict(use_enum_values=True)

    codigo: str | None = Field(default=None, min_length=1, max_length=20)
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    categoria: CategoriaSensor | None = None
    ubicacion: str | None = Field(default=None, min_length=1, max_length=100)
    activo: bool | None = None


class SensorResponse(SensorBase):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    fecha_registro: datetime