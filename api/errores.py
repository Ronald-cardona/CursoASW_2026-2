from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError


def error_integridad(e: IntegrityError) -> HTTPException:
    """Traduce errores de PostgreSQL a un 409 con mensaje legible."""
    codigo = getattr(e.orig, "pgcode", None) or getattr(e.orig, "sqlstate", None)
    mensajes = {
        "23505": "Ya existe un registro con esos valores únicos",
        "23503": "Operación bloqueada por una relación: el registro referenciado "
        "no existe o tiene registros asociados",
        "23514": "Los datos no cumplen una restricción de la base de datos",
    }
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=mensajes.get(codigo, "Error de integridad en la base de datos"),
    )