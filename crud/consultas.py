from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager, joinedload

from models.medicion import Medicion
from models.sensor_magnitud import SensorMagnitud


def buscar_mediciones(
    db: Session,
    *,
    sensor_id: int | None = None,
    sensor_magnitud_id: int | None = None,
    magnitud: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limit: int = 100,
    skip: int = 0,
) -> list[Medicion]:
    """Búsqueda general de mediciones, de la más reciente a la más antigua.

    Todos los filtros son opcionales y se pueden combinar.
    Con `limit` se obtienen las últimas N.
    """
    stmt = (
        select(Medicion)
        .join(Medicion.sensor_magnitud)
        .options(contains_eager(Medicion.sensor_magnitud))
        .order_by(Medicion.timestamp_utc.desc(), Medicion.id.desc())
        .offset(skip)
        .limit(limit)
    )
    if sensor_id is not None:
        stmt = stmt.where(SensorMagnitud.sensor_id == sensor_id)
    if sensor_magnitud_id is not None:
        stmt = stmt.where(Medicion.sensor_magnitud_id == sensor_magnitud_id)
    if magnitud is not None:
        stmt = stmt.where(SensorMagnitud.magnitud == magnitud)
    if desde is not None:
        stmt = stmt.where(Medicion.timestamp_utc >= desde)
    if hasta is not None:
        stmt = stmt.where(Medicion.timestamp_utc <= hasta)
    return list(db.scalars(stmt).all())


def listar_mediciones_de_sensor(
    db: Session,
    sensor_id: int,
    magnitud: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limit: int = 100,
    skip: int = 0,
) -> list[Medicion]:
    """Historial de un sensor (usado por /sensores/{id}/mediciones)."""
    return buscar_mediciones(
        db,
        sensor_id=sensor_id,
        magnitud=magnitud,
        desde=desde,
        hasta=hasta,
        limit=limit,
        skip=skip,
    )


def obtener_medicion_detalle(db: Session, medicion_id: int) -> Medicion | None:
    return db.get(
        Medicion, medicion_id, options=[joinedload(Medicion.sensor_magnitud)]
    )


def ultima_medicion_de_magnitud(
    db: Session, sensor_magnitud_id: int
) -> Medicion | None:
    """La medición más reciente de una magnitud concreta."""
    return db.scalars(
        select(Medicion)
        .options(joinedload(Medicion.sensor_magnitud))
        .where(Medicion.sensor_magnitud_id == sensor_magnitud_id)
        .order_by(Medicion.timestamp_utc.desc(), Medicion.id.desc())
        .limit(1)
    ).first()


def ultima_medicion_por_magnitud(
    db: Session, sensor_id: int, magnitud: str | None = None
) -> list[Medicion]:
    """La medición más reciente de cada magnitud del sensor."""
    stmt = (
        select(SensorMagnitud)
        .where(SensorMagnitud.sensor_id == sensor_id)
        .order_by(SensorMagnitud.id)
    )
    if magnitud is not None:
        stmt = stmt.where(SensorMagnitud.magnitud == magnitud)

    resultado: list[Medicion] = []
    for mag in db.scalars(stmt).all():
        ultima = ultima_medicion_de_magnitud(db, mag.id)
        if ultima is not None:
            resultado.append(ultima)
    return resultado