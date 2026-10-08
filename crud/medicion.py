from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from crud.comun import guardar
from models.medicion import Medicion
from schemas.medicion import MedicionCreate


def listar_mediciones(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    sensor_magnitud_id: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> list[Medicion]:
    stmt = (
        select(Medicion)
        .order_by(Medicion.timestamp_utc.desc(), Medicion.id.desc())
        .offset(skip)
        .limit(limit)
    )
    if sensor_magnitud_id is not None:
        stmt = stmt.where(Medicion.sensor_magnitud_id == sensor_magnitud_id)
    if desde is not None:
        stmt = stmt.where(Medicion.timestamp_utc >= desde)
    if hasta is not None:
        stmt = stmt.where(Medicion.timestamp_utc <= hasta)
    return list(db.scalars(stmt).all())


def obtener_medicion(db: Session, medicion_id: int) -> Medicion | None:
    return db.get(Medicion, medicion_id)


def crear_medicion(db: Session, datos: MedicionCreate) -> Medicion:
    medicion = Medicion(**datos.model_dump())
    db.add(medicion)
    guardar(db)
    db.refresh(medicion)
    return medicion


def actualizar_medicion(db: Session, medicion: Medicion, cambios: dict) -> Medicion:
    for campo, valor in cambios.items():
        setattr(medicion, campo, valor)
    guardar(db)
    db.refresh(medicion)
    return medicion


def eliminar_medicion(db: Session, medicion: Medicion) -> None:
    db.delete(medicion)
    guardar(db)


def crear_mediciones_lote(db: Session, datos: list[MedicionCreate]) -> list[Medicion]:
    """Inserta varias mediciones en UNA sola transacción (todo o nada)."""
    mediciones = [Medicion(**d.model_dump()) for d in datos]
    db.add_all(mediciones)
    guardar(db)  # un único commit; si falla, hace rollback de todas
    return mediciones