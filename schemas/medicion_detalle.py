from pydantic import AliasPath, Field

from schemas.medicion import MedicionResponse


class MedicionDetalleResponse(MedicionResponse):
    """Medición con el nombre y la unidad de su magnitud."""

    magnitud: str = Field(validation_alias=AliasPath("sensor_magnitud", "magnitud"))
    unidad: str = Field(validation_alias=AliasPath("sensor_magnitud", "unidad"))