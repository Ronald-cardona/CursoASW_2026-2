from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.medicion import Medicion
    from models.sensor import Sensor


class SensorMagnitud(Base):
    __tablename__ = "sensor_magnitudes"
    __table_args__ = (
        UniqueConstraint("sensor_id", "magnitud", name="uq_sensor_magnitud"),
        CheckConstraint("valor_minimo < valor_maximo", name="ck_magnitud_rango"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int] = mapped_column(
        ForeignKey("sensores.id", onupdate="CASCADE", ondelete="RESTRICT")
    )
    magnitud: Mapped[str] = mapped_column(String(50))
    unidad: Mapped[str] = mapped_column(String(20))
    valor_minimo: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    valor_maximo: Mapped[Decimal] = mapped_column(Numeric(12, 4))

    sensor: Mapped[Sensor] = relationship(back_populates="magnitudes")
    mediciones: Mapped[list[Medicion]] = relationship(
        back_populates="sensor_magnitud", passive_deletes="all"
    )