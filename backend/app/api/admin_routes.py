from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt

from app.services import admin_service
from app.utils.errors import ApiError
from app.utils.responses import success_response

bp = Blueprint("admin", __name__)


def _require_admin() -> None:
    claims = get_jwt() or {}
    roles = claims.get("roles") or []
    es_admin = any(str(r).upper() in ("ADMIN", "ADMINISTRADOR") for r in roles)
    if not es_admin:
        raise ApiError("No autorizado (admin)", 403)


@bp.get("/ping")
def ping_admin():
    return success_response(message="admin ok")


@bp.get("/resumen")
@jwt_required()
def resumen_admin():
    _require_admin()
    data = admin_service.obtener_resumen_admin()
    return success_response(data=data, message="OK")


@bp.get("/incidentes")
@jwt_required()
def listar_incidentes_admin():
    _require_admin()

    estado = request.args.get("estado")
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", 10)

    data = admin_service.listar_incidentes_admin(estado=estado, page=page, per_page=per_page)
    return success_response(data=data, message="OK")


@bp.get("/usuarios")
@jwt_required()
def listar_usuarios_admin():
    _require_admin()

    search = request.args.get("search")
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", 10)

    data = admin_service.listar_usuarios_admin(search=search, page=page, per_page=per_page)
    return success_response(data=data, message="OK")


@bp.get("/articulos")
@jwt_required()
def listar_articulos_admin():
    _require_admin()

    search = request.args.get("search")
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", 10)

    data = admin_service.listar_articulos_admin(search=search, page=page, per_page=per_page)
    return success_response(data=data, message="OK")


@bp.post("/articulos/<int:id_articulo>/estado-publicacion")
@jwt_required()
def actualizar_estado_publicacion_admin(id_articulo: int):
    """Pausar/reactivar publicación (si el modelo tiene estado_publicacion)."""

    _require_admin()

    payload = request.get_json() or {}
    estado_publicacion = payload.get("estado_publicacion")
    data = admin_service.actualizar_estado_publicacion_articulo(id_articulo, estado_publicacion)
    return success_response(data=data, message="OK")


@bp.get("/puntos-entrega")
@jwt_required()
def listar_puntos_entrega_admin():
    _require_admin()

    search = request.args.get("search")
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", 10)

    data = admin_service.listar_puntos_entrega_admin(search=search, page=page, per_page=per_page)
    return success_response(data=data, message="OK")


@bp.post("/puntos-entrega")
@jwt_required()
def crear_punto_entrega_admin():
    _require_admin()
    payload = request.get_json() or {}
    data = admin_service.crear_punto_entrega_admin(payload)
    return success_response(data=data, message="Creado", status_code=201)


@bp.put("/puntos-entrega/<int:id_punto>")
@jwt_required()
def actualizar_punto_entrega_admin(id_punto: int):
    _require_admin()
    payload = request.get_json() or {}
    data = admin_service.actualizar_punto_entrega_admin(id_punto, payload)
    return success_response(data=data, message="OK")


@bp.delete("/puntos-entrega/<int:id_punto>")
@jwt_required()
def desactivar_punto_entrega_admin(id_punto: int):
    _require_admin()
    data = admin_service.desactivar_punto_entrega_admin(id_punto)
    return success_response(data=data, message="OK")
