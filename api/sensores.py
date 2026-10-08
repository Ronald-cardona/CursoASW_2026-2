from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.errores import error_integridad
from crud import sensor as crud
from database import get_db
from schemas.sensor import CategoriaSensor, SensorCreate, SensorResponse, SensorUpdate

router = APIRouter(prefix="/sensores", tags=["Sensores"])


def _sensor_o_404(db: Session, sensor_id: int):
    sensor = crud.obtener_sensor(db, sensor_id)
    if sensor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sensor no encontrado")
    return sensor


def _validar_codigo_libre(db: Session, codigo: str, sensor_id: int | None = None):
    existente = crud.obtener_sensor_por_codigo(db, codigo)
    if existente is not None and existente.id != sensor_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Ya existe un sensor con código '{codigo}'"
        )


@router.get("/", response_model=list[SensorResponse])
def listar(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    categoria: CategoriaSensor | None = None,
    activo: bool | None = None,
    db: Session = Depends(get_db),
):
    return crud.listar_sensores(
        db,
        skip=skip,
        limit=limit,
        categoria=categoria.value if categoria else None,
        activo=activo,
    )


@router.get("/{sensor_id}", response_model=SensorResponse)
def obtener(sensor_id: int, db: Session = Depends(get_db)):
    return _sensor_o_404(db, sensor_id)


@router.post("/", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
def crear(datos: SensorCreate, db: Session = Depends(get_db)):
    _validar_codigo_libre(db, datos.codigo)
    try:
        return crud.crear_sensor(db, datos)
    except IntegrityError as e:
        raise error_integridad(e)


@router.put("/{sensor_id}", response_model=SensorResponse)
def reemplazar(sensor_id: int, datos: SensorCreate, db: Session = Depends(get_db)):
    sensor = _sensor_o_404(db, sensor_id)
    _validar_codigo_libre(db, datos.codigo, sensor_id)
    try:
        return crud.actualizar_sensor(db, sensor, datos.model_dump())
    except IntegrityError as e:
        raise error_integridad(e)


@router.patch("/{sensor_id}", response_model=SensorResponse)
def actualizar(sensor_id: int, datos: SensorUpdate, db: Session = Depends(get_db)):
    sensor = _sensor_o_404(db, sensor_id)
    cambios = datos.model_dump(exclude_unset=True, exclude_none=True)
    if "codigo" in cambios:
        _validar_codigo_libre(db, cambios["codigo"], sensor_id)
    try:
        return crud.actualizar_sensor(db, sensor, cambios)
    except IntegrityError as e:
        raise error_integridad(e)


@router.delete("/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(sensor_id: int, db: Session = Depends(get_db)):
    sensor = _sensor_o_404(db, sensor_id)
    try:
        crud.eliminar_sensor(db, sensor)
    except IntegrityError as e:  # ON DELETE RESTRICT: tiene magnitudes
        raise error_integridad(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)