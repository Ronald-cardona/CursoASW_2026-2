from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MedicionBase(BaseModel):
    estudiante_id: int
    variable: str = Field(max_length=50)
    valor: float
    unidad: str = Field(max_length=20)
    fecha_hora: datetime


class MedicionCreate(MedicionBase):
    """Entrada para POST y PUT (todos los campos obligatorios)."""
    pass


class MedicionUpdate(BaseModel):
    """Entrada para PATCH (todos opcionales)."""
    estudiante_id: Optional[int] = None
    variable: Optional[str] = Field(default=None, max_length=50)
    valor: Optional[float] = None
    unidad: Optional[str] = Field(default=None, max_length=20)
    fecha_hora: Optional[datetime] = None


class MedicionResponse(MedicionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)