from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.sensor_magnitud import SensorMagnitud


class Sensor(Base):
    __tablename__ = "sensores"
    __table_args__ = (
        CheckConstraint(
            "categoria IN ('AIRE', 'GAS', 'AGUA', 'AMBIENTE')",
            name="ck_sensores_categoria",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    categoria: Mapped[str] = mapped_column(String(30))
    ubicacion: Mapped[str] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("TRUE"))
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # passive_deletes="all": el ORM no intenta poner NULL en la FK al borrar;
    # deja que PostgreSQL aplique ON DELETE RESTRICT.
    magnitudes: Mapped[list[SensorMagnitud]] = relationship(
        back_populates="sensor", passive_deletes="all"
    )