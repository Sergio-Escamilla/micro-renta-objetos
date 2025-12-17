from flask import Blueprint
import os
from flask import current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.utils.responses import success_response
from app.utils.errors import ApiError
from app.services import notificacion_service

bp = Blueprint("notificaciones", __name__)


@bp.get("/ping")
def ping_notificaciones():
    return success_response(message="notificaciones ok")


@bp.get("")
@jwt_required()
def listar_notificaciones():
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    data = notificacion_service.listar_notificaciones(id_usuario)

    if os.getenv("NOTIFICACIONES_DEBUG", "0") == "1":
        current_app.logger.info(
            "[notificaciones] GET /api/notificaciones usuario=%s -> items=%s unread=%s",
            id_usuario,
            len(data.get("items") or []),
            data.get("unread_count"),
        )
    return success_response(data=data, message="OK")


@bp.post("/<int:id_notificacion>/leer")
@jwt_required()
def marcar_leida(id_notificacion: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    notificacion_service.marcar_leida(id_notificacion, id_usuario)
    return success_response(message="OK")
