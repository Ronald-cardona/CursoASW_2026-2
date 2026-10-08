from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def guardar(db: Session) -> None:
    """commit con rollback automático si la BD rechaza la operación.

    La IntegrityError se vuelve a lanzar para que la capa api la traduzca a 409.
    """
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise