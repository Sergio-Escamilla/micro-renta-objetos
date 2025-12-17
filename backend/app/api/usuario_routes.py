from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services import resena_service
from app.services import usuario_service
from app.extensions import db
from app.models.articulo import Articulo
from app.models.renta import Renta
from app.utils.responses import success_response
from app.utils.errors import ApiError

bp = Blueprint("usuarios", __name__)


@bp.get("/ping")
def ping_usuarios():
    return success_response(message="usuarios ok")


@bp.get("/<int:id_usuario>/rating")
def rating_usuario(id_usuario: int):
    data = resena_service.obtener_rating_usuario(id_usuario)
    return success_response(data=data, message="OK")


@bp.get("/me")
@jwt_required()
def me_usuario():
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    usuario = usuario_service.obtener_usuario_por_id(user_id_int)
    if not usuario:
        raise ApiError("Usuario no encontrado", 404)

    return success_response(data=usuario_service.usuario_to_dict(usuario), message="OK")


@bp.patch("/me")
@jwt_required()
def actualizar_me_usuario():
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    usuario = usuario_service.obtener_usuario_por_id(user_id_int)
    if not usuario:
        raise ApiError("Usuario no encontrado", 404)

    payload = request.get_json() or {}
    allowed = {
        "nombre",
        "apellidos",
        "telefono",
        "ciudad",
        "estado",
        "pais",
        "direccion_completa",
        "foto_perfil",
    }

    for key, value in payload.items():
        if key not in allowed:
            continue
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                value = None
        setattr(usuario, key, value)

    db.session.add(usuario)
    db.session.commit()

    return success_response(data=usuario_service.usuario_to_dict(usuario), message="Perfil actualizado")


@bp.get("/me/resumen")
@jwt_required()
def resumen_me_usuario():
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    usuario = usuario_service.obtener_usuario_por_id(user_id_int)
    if not usuario:
        raise ApiError("Usuario no encontrado", 404)

    articulos = (
        Articulo.query.filter(
            Articulo.id_propietario == user_id_int,
            Articulo.estado_publicacion != "eliminado",
        ).count()
    )
    rentas_arr = Renta.query.filter(Renta.id_arrendatario == user_id_int).count()
    rentas_prop = Renta.query.filter(Renta.id_propietario == user_id_int).count()
    rating = resena_service.obtener_rating_usuario(user_id_int)

    return success_response(
        data={
            "articulos_publicados": int(articulos),
            "rentas_como_arrendatario": int(rentas_arr),
            "rentas_como_propietario": int(rentas_prop),
            "rating": rating,
        },
        message="OK",
    )
