from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from api.errores import error_integridad
from crud import consultas
from crud import sensor as crud
from crud import sensor_magnitud as crud_magnitud
from database import get_db
from schemas.medicion_detalle import MedicionDetalleResponse
from schemas.sensor import CategoriaSensor, SensorCreate, SensorResponse, SensorUpdate
from schemas.sensor_magnitud import SensorMagnitudResponse
from schemas.tiempo import a_utc

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


# ---------------------------------------------------------------- consultas

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


@router.get("/por-codigo/{codigo}", response_model=SensorResponse)
def obtener_por_codigo(codigo: str, db: Session = Depends(get_db)):
    sensor = crud.obtener_sensor_por_codigo(db, codigo)
    if sensor is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"No existe un sensor con código '{codigo}'"
        )
    return sensor


@router.get("/{sensor_id}", response_model=SensorResponse)
def obtener(sensor_id: int, db: Session = Depends(get_db)):
    return _sensor_o_404(db, sensor_id)


@router.get("/{sensor_id}/magnitudes", response_model=list[SensorMagnitudResponse])
def listar_magnitudes_del_sensor(sensor_id: int, db: Session = Depends(get_db)):
    _sensor_o_404(db, sensor_id)
    return crud_magnitud.listar_magnitudes(db, skip=0, limit=500, sensor_id=sensor_id)


@router.get("/{sensor_id}/mediciones", response_model=list[MedicionDetalleResponse])
def listar_mediciones_del_sensor(
    sensor_id: int,
    magnitud: str | None = Query(None, description="Nombre de la magnitud, ej. temperature"),
    desde: datetime | None = Query(
        None, description="Desde (inclusive). Sin zona horaria = hora de Colombia"
    ),
    hasta: datetime | None = Query(
        None, description="Hasta (inclusive). Sin zona horaria = hora de Colombia"
    ),
    limit: int = Query(
        100, ge=1, le=1000, description="Devuelve las últimas N mediciones"
    ),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    _sensor_o_404(db, sensor_id)
    desde_utc = a_utc(desde) if desde else None
    hasta_utc = a_utc(hasta) if hasta else None
    if desde_utc and hasta_utc and desde_utc > hasta_utc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "'desde' no puede ser posterior a 'hasta'"
        )
    return consultas.listar_mediciones_de_sensor(
        db,
        sensor_id,
        magnitud=magnitud,
        desde=desde_utc,
        hasta=hasta_utc,
        limit=limit,
        skip=skip,
    )


@router.get("/{sensor_id}/ultima-medicion", response_model=list[MedicionDetalleResponse])
def ultima_medicion_del_sensor(
    sensor_id: int,
    magnitud: str | None = Query(None, description="Nombre de la magnitud"),
    db: Session = Depends(get_db),
):
    _sensor_o_404(db, sensor_id)
    ultimas = consultas.ultima_medicion_por_magnitud(db, sensor_id, magnitud)
    if not ultimas:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "El sensor no tiene mediciones registradas"
        )
    return ultimas


# ------------------------------------------------------------ escritura

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


