from sqlalchemy import select
from sqlalchemy.orm import Session

from crud.comun import guardar
from models.sensor_magnitud import SensorMagnitud
from schemas.sensor_magnitud import SensorMagnitudCreate


def listar_magnitudes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    sensor_id: int | None = None,
) -> list[SensorMagnitud]:
    stmt = select(SensorMagnitud).order_by(SensorMagnitud.id).offset(skip).limit(limit)
    if sensor_id is not None:
        stmt = stmt.where(SensorMagnitud.sensor_id == sensor_id)
    return list(db.scalars(stmt).all())


def obtener_magnitud(db: Session, magnitud_id: int) -> SensorMagnitud | None:
    return db.get(SensorMagnitud, magnitud_id)


def obtener_magnitud_de_sensor(
    db: Session, sensor_id: int, magnitud: str
) -> SensorMagnitud | None:
    stmt = select(SensorMagnitud).where(
        SensorMagnitud.sensor_id == sensor_id, SensorMagnitud.magnitud == magnitud
    )
    return db.scalars(stmt).first()


def crear_magnitud(db: Session, datos: SensorMagnitudCreate) -> SensorMagnitud:
    magnitud = SensorMagnitud(**datos.model_dump())
    db.add(magnitud)
    guardar(db)
    db.refresh(magnitud)
    return magnitud


def actualizar_magnitud(
    db: Session, magnitud: SensorMagnitud, cambios: dict
) -> SensorMagnitud:
    for campo, valor in cambios.items():
        setattr(magnitud, campo, valor)
    guardar(db)
    db.refresh(magnitud)
    return magnitud


def eliminar_magnitud(db: Session, magnitud: SensorMagnitud) -> None:
    db.delete(magnitud)
    guardar(db)