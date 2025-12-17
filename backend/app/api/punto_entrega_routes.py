from flask import Blueprint
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.models.punto_entrega import PuntoEntrega
from app.utils.responses import success_response


bp = Blueprint("puntos_entrega", __name__)


def _to_public_dict(p: PuntoEntrega) -> dict:
    # Campos mínimos + placeholders para compat sin migraciones extra
    return {
        "id": p.id,
        "nombre": p.nombre,
        "direccion": p.direccion,  # aproximada
        "ciudad": None,
        "estado": None,
        "horario": None,
        "notas": None,
    }


@bp.get("/puntos-entrega")
@jwt_required()
def listar_puntos_entrega_publicos():
    """Lista pública (JWT) de puntos activos para selección en coordinación."""

    try:
        items = (
            PuntoEntrega.query.filter(PuntoEntrega.activo.is_(True))
            .order_by(PuntoEntrega.id.asc())
            .all()
        )
        return success_response(data={"items": [_to_public_dict(x) for x in items]}, message="OK")
    except (OperationalError, ProgrammingError):
        # Compat: si el recurso no existe en una BD desfasada, no rompemos el flujo.
        return success_response(data={"items": []}, message="OK")
