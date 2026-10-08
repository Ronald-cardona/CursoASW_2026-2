from sqlalchemy import select
from sqlalchemy.orm import Session

from crud.comun import guardar
from models.sensor import Sensor
from schemas.sensor import SensorCreate


def listar_sensores(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    categoria: str | None = None,
    activo: bool | None = None,
) -> list[Sensor]:
    stmt = select(Sensor).order_by(Sensor.id).offset(skip).limit(limit)
    if categoria is not None:
        stmt = stmt.where(Sensor.categoria == categoria)
    if activo is not None:
        stmt = stmt.where(Sensor.activo == activo)
    return list(db.scalars(stmt).all())


def obtener_sensor(db: Session, sensor_id: int) -> Sensor | None:
    return db.get(Sensor, sensor_id)


def obtener_sensor_por_codigo(db: Session, codigo: str) -> Sensor | None:
    return db.scalars(select(Sensor).where(Sensor.codigo == codigo)).first()


def crear_sensor(db: Session, datos: SensorCreate) -> Sensor:
    sensor = Sensor(**datos.model_dump())
    db.add(sensor)
    guardar(db)
    db.refresh(sensor)
    return sensor


def actualizar_sensor(db: Session, sensor: Sensor, cambios: dict) -> Sensor:
    for campo, valor in cambios.items():
        setattr(sensor, campo, valor)
    guardar(db)
    db.refresh(sensor)
    return sensor


def eliminar_sensor(db: Session, sensor: Sensor) -> None:
    db.delete(sensor)
    guardar(db)
