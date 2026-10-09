from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.errores import error_integridad
from crud import consultas
from crud import medicion as crud
from crud import sensor_magnitud as crud_magnitud
from database import get_db
from schemas.medicion import MedicionCreate, MedicionResponse, MedicionUpdate
from schemas.medicion_detalle import MedicionDetalleResponse
from schemas.tiempo import a_utc

router = APIRouter(prefix="/mediciones", tags=["Mediciones"])


def _medicion_o_404(db: Session, medicion_id: int):
    medicion = crud.obtener_medicion(db, medicion_id)
    if medicion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medición no encontrada")
    return medicion


def _magnitud_existe(db: Session, magnitud_id: int):
    if crud_magnitud.obtener_magnitud(db, magnitud_id) is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "La magnitud del sensor indicada no existe"
        )


def _rango_utc(desde: datetime | None, hasta: datetime | None):
    """Sin zona horaria = hora de Colombia. Devuelve (desde, hasta) en UTC."""
    desde_utc = a_utc(desde) if desde else None
    hasta_utc = a_utc(hasta) if hasta else None
    if desde_utc and hasta_utc and desde_utc > hasta_utc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "'desde' no puede ser posterior a 'hasta'"
        )
    return desde_utc, hasta_utc


# ---------------------------------------------------------------- consultas

@router.get("/", response_model=list[MedicionDetalleResponse])
def listar(
    sensor_id: int | None = Query(None, description="id numérico del sensor"),
    sensor_magnitud_id: int | None = Query(None, description="id de la magnitud del sensor"),
    magnitud: str | None = Query(None, description="Nombre de la magnitud, ej. temperature"),
    desde: datetime | None = Query(
        None, description="Desde (inclusive). Sin zona horaria = hora de Colombia"
    ),
    hasta: datetime | None = Query(
        None, description="Hasta (inclusive). Sin zona horaria = hora de Colombia"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Devuelve las últimas N mediciones"),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    desde_utc, hasta_utc = _rango_utc(desde, hasta)
    return consultas.buscar_mediciones(
        db,
        sensor_id=sensor_id,
        sensor_magnitud_id=sensor_magnitud_id,
        magnitud=magnitud,
        desde=desde_utc,
        hasta=hasta_utc,
        limit=limit,
        skip=skip,
    )


@router.get("/{medicion_id}", response_model=MedicionDetalleResponse)
def obtener(medicion_id: int, db: Session = Depends(get_db)):
    medicion = consultas.obtener_medicion_detalle(db, medicion_id)
    if medicion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medición no encontrada")
    return medicion


# ------------------------------------------------------------ escritura

@router.post("/", response_model=MedicionResponse, status_code=status.HTTP_201_CREATED)
def crear(datos: MedicionCreate, db: Session = Depends(get_db)):
    _magnitud_existe(db, datos.sensor_magnitud_id)
    try:
        return crud.crear_medicion(db, datos)
    except IntegrityError as e:
        raise error_integridad(e)


@router.put("/{medicion_id}", response_model=MedicionResponse)
def reemplazar(medicion_id: int, datos: MedicionCreate, db: Session = Depends(get_db)):
    medicion = _medicion_o_404(db, medicion_id)
    _magnitud_existe(db, datos.sensor_magnitud_id)
    try:
        return crud.actualizar_medicion(db, medicion, datos.model_dump())
    except IntegrityError as e:
        raise error_integridad(e)


@router.patch("/{medicion_id}", response_model=MedicionResponse)
def actualizar(medicion_id: int, datos: MedicionUpdate, db: Session = Depends(get_db)):
    medicion = _medicion_o_404(db, medicion_id)
    cambios = datos.model_dump(exclude_unset=True, exclude_none=True)
    if "sensor_magnitud_id" in cambios:
        _magnitud_existe(db, cambios["sensor_magnitud_id"])
    try:
        return crud.actualizar_medicion(db, medicion, cambios)
    except IntegrityError as e:
        raise error_integridad(e)


@router.delete("/{medicion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(medicion_id: int, db: Session = Depends(get_db)):
    medicion = _medicion_o_404(db, medicion_id)
    crud.eliminar_medicion(db, medicion)
    return Response(status_code=status.HTTP_204_NO_CONTENT)