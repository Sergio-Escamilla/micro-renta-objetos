import io

from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.schemas.renta_schemas import RentaCreateSchema
from app.schemas.resena_schemas import ResenaCreateSchema
from app.services import renta_service
from app.services import resena_service
from app.utils.responses import success_response
from app.utils.errors import ApiError
from app.utils.security import require_usuario_habilitado

bp = Blueprint("rentas", __name__)

renta_create_schema = RentaCreateSchema()
resena_create_schema = ResenaCreateSchema()


@bp.get("/ping")
def ping():
    return success_response(message="rentas ok")


@bp.post("")
@jwt_required()
def crear_renta():
    """
    Crea una renta para un artículo.
    Body JSON:
    {
      "id_articulo": 1,
      "fecha_inicio": "2025-12-10T10:00:00",
      "fecha_fin": "2025-12-12T10:00:00"
    }
    """
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    # Admin NO puede rentar (bloqueo temprano, sin efectos colaterales)
    claims = get_jwt() or {}
    roles = claims.get("roles") or []
    es_admin = any(str(r).upper() in ("ADMIN", "ADMINISTRADOR") for r in roles)
    if es_admin:
        raise ApiError(
            "Los administradores no pueden rentar artículos. Usa una cuenta de usuario.",
            403,
            payload={"code": "ADMIN_FORBIDDEN"},
        )

    # Exigir correo verificado + perfil completo
    require_usuario_habilitado(id_usuario)

    json_data = request.get_json() or {}
    data = renta_create_schema.load(json_data)
    renta_dict = renta_service.crear_renta(data, id_usuario)

    return success_response(
        message="Renta creada correctamente",
        data=renta_dict,
        status_code=201,
    )


@bp.get("/mis")
@jwt_required()
def listar_mis_rentas():
    """
    Lista las rentas del usuario autenticado.
    Query param opcional:
    - ?como=arrendatario (default)
    - ?como=propietario
    """
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)
    como = request.args.get("como", "arrendatario")

    rentas = renta_service.listar_rentas_usuario(id_usuario, como=como)

    return success_response(
        data={"items": rentas, "como": como},
        message="OK",
    )


@bp.get("/mias")
@jwt_required()
def listar_rentas_mias():
    """Bandeja (Inbox): rentas del usuario por rol + estado, paginadas."""

    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    rol = request.args.get("rol") or ""
    estado = request.args.get("estado") or ""
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", 10)

    data = renta_service.listar_rentas_mias(
        id_usuario_actual=id_usuario,
        rol=rol,
        estado=estado,
        page=page,
        per_page=per_page,
    )
    return success_response(data=data, message="OK")


@bp.get("/<int:id_renta>")
@jwt_required()
def obtener_renta(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    renta_dict = renta_service.obtener_renta(id_renta, id_usuario)
    return success_response(
        data=renta_dict,
        message="OK",
    )


@bp.get("/<int:id_renta>/recibo")
@jwt_required()
def descargar_recibo(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    pdf_bytes = renta_service.generar_recibo_pdf(id_renta, id_usuario)
    filename = f"recibo-renta-{id_renta}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


@bp.post("/<int:id_renta>/pagar")
@jwt_required()
def pagar_renta(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    renta_dict = renta_service.pagar_renta(id_renta, id_usuario)
    return success_response(
        data=renta_dict,
        message="Pago simulado exitoso",
        status_code=200,
    )


@bp.post("/<int:id_renta>/confirmar")
@jwt_required()
def confirmar_entrega(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    renta_dict = renta_service.confirmar_entrega(id_renta, id_usuario)
    return success_response(
        data=renta_dict,
        message="Entrega confirmada",
        status_code=200,
    )


@bp.post("/<int:id_renta>/en-uso")
@jwt_required()
def marcar_en_uso(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    renta_dict = renta_service.marcar_en_uso(id_renta, id_usuario)
    return success_response(
        data=renta_dict,
        message="Renta marcada en uso",
        status_code=200,
    )


@bp.post("/<int:id_renta>/devolver")
@jwt_required()
def devolver(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    renta_dict = renta_service.devolver(id_renta, id_usuario)
    return success_response(
        data=renta_dict,
        message="Devolución registrada",
        status_code=200,
    )


@bp.post("/<int:id_renta>/finalizar")
@jwt_required()
def finalizar(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    renta_dict = renta_service.finalizar(id_renta, id_usuario)
    return success_response(
        data=renta_dict,
        message="Renta finalizada (depósito liberado)",
        status_code=200,
    )


@bp.post("/<int:id_renta>/incidente")
@jwt_required()
def incidente(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    payload = request.get_json() or {}
    descripcion = payload.get("descripcion")

    renta_dict = renta_service.reportar_incidente(id_renta, id_usuario, descripcion)
    return success_response(
        data=renta_dict,
        message="Incidente reportado",
        status_code=200,
    )


@bp.post("/<int:id_renta>/cancelar")
@jwt_required()
def cancelar(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    payload = request.get_json() or {}
    motivo = payload.get("motivo")

    claims = get_jwt() or {}
    roles = claims.get("roles") or []

    renta_dict = renta_service.cancelar_renta(id_renta, id_usuario, roles=roles, motivo=motivo)
    return success_response(
        data=renta_dict,
        message="Renta cancelada",
        status_code=200,
    )


@bp.post("/<int:id_renta>/coordinar")
@jwt_required()
def coordinar(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    payload = request.get_json() or {}
    renta_dict = renta_service.coordinar_renta(id_renta, id_usuario, payload)
    return success_response(
        data=renta_dict,
        message="Coordinación actualizada",
        status_code=200,
    )


@bp.post("/<int:id_renta>/aceptar-coordinacion")
@jwt_required()
def aceptar_coordinacion(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    payload = request.get_json() or {}
    renta_dict = renta_service.aceptar_coordinacion(id_renta, id_usuario, payload)
    return success_response(
        data=renta_dict,
        message="Coordinación aceptada",
        status_code=200,
    )


@bp.post("/<int:id_renta>/confirmar-entrega-otp")
@jwt_required()
def confirmar_entrega_otp(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    payload = request.get_json() or {}
    renta_dict = renta_service.confirmar_entrega_otp(id_renta, id_usuario, payload)
    return success_response(
        data=renta_dict,
        message="Entrega confirmada (OTP)",
        status_code=200,
    )


@bp.post("/<int:id_renta>/confirmar-devolucion-otp")
@jwt_required()
def confirmar_devolucion_otp(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    payload = request.get_json() or {}
    renta_dict = renta_service.confirmar_devolucion_otp(id_renta, id_usuario, payload)
    return success_response(
        data=renta_dict,
        message="Devolución confirmada (OTP)",
        status_code=200,
    )


@bp.get("/<int:id_renta>/chat")
@jwt_required()
def get_chat(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    items = renta_service.obtener_chat(id_renta, id_usuario)
    return success_response(
        data={"items": items},
        message="OK",
        status_code=200,
    )


@bp.post("/<int:id_renta>/chat")
@jwt_required()
def post_chat(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    payload = request.get_json() or {}
    msg = renta_service.enviar_chat(id_renta, id_usuario, payload)
    return success_response(
        data=msg,
        message="Mensaje enviado",
        status_code=201,
    )


@bp.get("/<int:id_renta>/chat/unread-count")
@jwt_required()
def chat_unread_count(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    unread = renta_service.chat_unread_count(id_renta, id_usuario)
    return success_response(data={"unread": unread}, message="OK")


@bp.post("/<int:id_renta>/chat/marcar-leido")
@jwt_required()
def chat_marcar_leido(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    renta_service.chat_marcar_leido(id_renta, id_usuario)
    return success_response(message="OK")


@bp.get("/chat/unread-total")
@jwt_required()
def chat_unread_total():
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    total = renta_service.chat_unread_total(id_usuario)
    return success_response(data={"total": total}, message="OK")


@bp.post("/<int:id_renta>/resolver-incidente")
@jwt_required()
def resolver_incidente(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    payload = request.get_json() or {}
    decision = payload.get("decision")
    monto_retenido = payload.get("monto_retenido")
    nota = payload.get("nota")

    claims = get_jwt() or {}
    roles = claims.get("roles") or []
    es_admin = any(str(r).upper() in ("ADMIN", "ADMINISTRADOR") for r in roles)

    renta_dict = renta_service.resolver_incidente(
        id_renta,
        id_usuario,
        decision,
        monto_retenido,
        nota,
        es_admin=es_admin,
    )
    return success_response(
        data=renta_dict,
        message="Incidente resuelto",
        status_code=200,
    )


@bp.get("/<int:id_renta>/calificacion")
@jwt_required()
def obtener_calificacion(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    calif = resena_service.obtener_mi_calificacion(id_renta, id_usuario)
    return success_response(
        data={"calificacion": calif},
        message="OK",
        status_code=200,
    )


@bp.post("/<int:id_renta>/calificar")
@jwt_required()
def calificar(id_renta: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    payload = request.get_json() or {}
    data = resena_create_schema.load(payload)

    resena = resena_service.crear_calificacion(
        id_renta=id_renta,
        id_usuario_actual=id_usuario,
        estrellas=data["estrellas"],
        comentario=data.get("comentario"),
    )
    return success_response(
        data=resena,
        message="Calificación registrada",
        status_code=201,
    )
