from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from crud import medicion as crud
from database import get_db
from models.estudiante import Estudiante
from schemas.medicion import MedicionCreate, MedicionResponse, MedicionUpdate

router = APIRouter(prefix="/mediciones", tags=["Mediciones"])


def validar_estudiante(db: Session, estudiante_id: int):
    if not db.get(Estudiante, estudiante_id):
        raise HTTPException(status_code=404, detail="El estudiante no existe")


def obtener_o_404(db: Session, medicion_id: int):
    medicion = crud.get(db, medicion_id)
    if medicion is None:
        raise HTTPException(status_code=404, detail="La medición no existe")
    return medicion


@router.get("", response_model=list[MedicionResponse])
def listar_mediciones(db: Session = Depends(get_db)):
    return crud.get_all(db)


@router.get("/{medicion_id}", response_model=MedicionResponse)
def obtener_medicion(medicion_id: int, db: Session = Depends(get_db)):
    return obtener_o_404(db, medicion_id)


@router.post("", response_model=MedicionResponse, status_code=status.HTTP_201_CREATED)
def agregar_medicion(data: MedicionCreate, db: Session = Depends(get_db)):
    validar_estudiante(db, data.estudiante_id)
    return crud.create(db, data)


@router.put("/{medicion_id}", response_model=MedicionResponse)
def reemplazar_medicion(medicion_id: int, data: MedicionCreate, db: Session = Depends(get_db)):
    medicion = obtener_o_404(db, medicion_id)
    validar_estudiante(db, data.estudiante_id)
    return crud.update(db, medicion, MedicionUpdate(**data.model_dump()))


@router.patch("/{medicion_id}", response_model=MedicionResponse)
def actualizar_medicion(medicion_id: int, data: MedicionUpdate, db: Session = Depends(get_db)):
    medicion = obtener_o_404(db, medicion_id)
    if data.estudiante_id is not None:
        validar_estudiante(db, data.estudiante_id)
    return crud.update(db, medicion, data)


@router.delete("/{medicion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_medicion(medicion_id: int, db: Session = Depends(get_db)):
    medicion = obtener_o_404(db, medicion_id)
    crud.delete(db, medicion)