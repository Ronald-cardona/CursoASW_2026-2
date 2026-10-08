from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.errores import error_integridad
from crud import sensor as crud_sensor
from crud import sensor_magnitud as crud
from database import get_db
from schemas.sensor_magnitud import (
    SensorMagnitudCreate,
    SensorMagnitudResponse,
    SensorMagnitudUpdate,
)

router = APIRouter(prefix="/sensor-magnitudes", tags=["Sensor magnitudes"])


def _magnitud_o_404(db: Session, magnitud_id: int):
    magnitud = crud.obtener_magnitud(db, magnitud_id)
    if magnitud is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Magnitud no encontrada")
    return magnitud


def _sensor_existe(db: Session, sensor_id: int):
    if crud_sensor.obtener_sensor(db, sensor_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El sensor indicado no existe")


def _validar_unica(db: Session, sensor_id: int, magnitud: str, propia_id: int | None = None):
    existente = crud.obtener_magnitud_de_sensor(db, sensor_id, magnitud)
    if existente is not None and existente.id != propia_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El sensor {sensor_id} ya tiene la magnitud '{magnitud}'",
        )


def _validar_rango(minimo: Decimal, maximo: Decimal):
    if minimo >= maximo:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "valor_minimo debe ser menor que valor_maximo",
        )


@router.get("/", response_model=list[SensorMagnitudResponse])
def listar(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sensor_id: int | None = None,
    db: Session = Depends(get_db),
):
    return crud.listar_magnitudes(db, skip=skip, limit=limit, sensor_id=sensor_id)


@router.get("/{magnitud_id}", response_model=SensorMagnitudResponse)
def obtener(magnitud_id: int, db: Session = Depends(get_db)):
    return _magnitud_o_404(db, magnitud_id)


@router.post("/", response_model=SensorMagnitudResponse, status_code=status.HTTP_201_CREATED)
def crear(datos: SensorMagnitudCreate, db: Session = Depends(get_db)):
    _sensor_existe(db, datos.sensor_id)
    _validar_unica(db, datos.sensor_id, datos.magnitud)
    try:
        return crud.crear_magnitud(db, datos)
    except IntegrityError as e:
        raise error_integridad(e)


@router.put("/{magnitud_id}", response_model=SensorMagnitudResponse)
def reemplazar(
    magnitud_id: int, datos: SensorMagnitudCreate, db: Session = Depends(get_db)
):
    magnitud = _magnitud_o_404(db, magnitud_id)
    _sensor_existe(db, datos.sensor_id)
    _validar_unica(db, datos.sensor_id, datos.magnitud, magnitud_id)
    try:
        return crud.actualizar_magnitud(db, magnitud, datos.model_dump())
    except IntegrityError as e:
        raise error_integridad(e)


@router.patch("/{magnitud_id}", response_model=SensorMagnitudResponse)
def actualizar(
    magnitud_id: int, datos: SensorMagnitudUpdate, db: Session = Depends(get_db)
):
    magnitud = _magnitud_o_404(db, magnitud_id)
    cambios = datos.model_dump(exclude_unset=True, exclude_none=True)

    # Validar el estado final combinando lo existente con lo que llega
    sensor_id = cambios.get("sensor_id", magnitud.sensor_id)
    nombre = cambios.get("magnitud", magnitud.magnitud)
    minimo = cambios.get("valor_minimo", magnitud.valor_minimo)
    maximo = cambios.get("valor_maximo", magnitud.valor_maximo)

    if "sensor_id" in cambios:
        _sensor_existe(db, sensor_id)
    if "sensor_id" in cambios or "magnitud" in cambios:
        _validar_unica(db, sensor_id, nombre, magnitud_id)
    _validar_rango(minimo, maximo)

    try:
        return crud.actualizar_magnitud(db, magnitud, cambios)
    except IntegrityError as e:
        raise error_integridad(e)


@router.delete("/{magnitud_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(magnitud_id: int, db: Session = Depends(get_db)):
    magnitud = _magnitud_o_404(db, magnitud_id)
    try:
        crud.eliminar_magnitud(db, magnitud)
    except IntegrityError as e:  # ON DELETE RESTRICT: tiene mediciones
        raise error_integridad(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)