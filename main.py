from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import models  # registra los modelos y sus relaciones
from api.sensores import router as sensores_router
from api.sensor_magnitudes import router as magnitudes_router
from api.mediciones import router as mediciones_router
from database import SessionLocal

app = FastAPI(title="API de mediciones")
app.include_router(sensores_router)
app.include_router(magnitudes_router)
app.include_router(mediciones_router)

@app.get("/")
def read_root():
    return {"message": "API de Sensores conectada a PostgreSQL"}

@app.get("/health/db")
def health_db():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"database": "ok"}
    except SQLAlchemyError as exc:
        return {"database": "unavailable", "detail": str(exc)}
