from datetime import datetime

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.schemas.auth_schemas import RegistroSchema, LoginSchema
from app.services import usuario_service, auth_service
from app.utils.responses import success_response
from app.utils.errors import ApiError
from app.utils.email_mock import send_email

bp = Blueprint("auth", __name__)


@bp.get("/ping")
def ping():
    return success_response(message="auth ok")


@bp.post("/register")
def register():
    data = RegistroSchema().load(request.json or {})
    usuario = usuario_service.crear_usuario(data)
    return success_response(
        data=usuario_service.usuario_to_dict(usuario),
        message="Usuario registrado correctamente",
        status_code=201
    )


@bp.post("/login")
def login():
    data = LoginSchema().load(request.json or {})
    result = auth_service.autenticar(
        data["correo_electronico"],
        data["contrasena"]
    )
    return success_response(data=result, message="Login exitoso")


@bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    usuario = usuario_service.obtener_usuario_por_id(user_id_int)
    if not usuario:
        raise ApiError("Usuario no encontrado", 404)

    return success_response(
        data=usuario_service.usuario_to_dict(usuario),
        message="Perfil del usuario"
    )


@bp.post("/enviar-verificacion")
@jwt_required()
def enviar_verificacion_email():
    user_id = get_jwt_identity()
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    usuario = usuario_service.obtener_usuario_por_id(user_id_int)
    if not usuario:
        raise ApiError("Usuario no encontrado", 404)

    ya_verificado = bool(getattr(usuario, "email_verificado", False)) or bool(getattr(usuario, "verificado", False))
    if ya_verificado:
        return success_response(message="El correo ya está verificado")

    token = auth_service.generar_token_verificacion_email(usuario)

    # Persistir token/sent_at si existen los campos (según prompt)
    try:
        usuario.email_verification_token = token
        usuario.email_verification_sent_at = datetime.utcnow()
        from app.extensions import db

        db.session.add(usuario)
        db.session.commit()
    except Exception:
        # best-effort: no romper el flujo si faltan migraciones
        try:
            from app.extensions import db

            db.session.rollback()
        except Exception:
            pass

    frontend_base = (current_app.config.get("FRONTEND_BASE_URL") or "http://localhost:4200").rstrip("/")
    link = f"{frontend_base}/verificar-email?token={token}"

    send_email(
        to=usuario.correo_electronico,
        subject="Verifica tu correo",
        body=f"Hola {usuario.nombre}.\n\nVerifica tu correo haciendo clic en este link:\n{link}\n\nSi no solicitaste esto, ignora este mensaje.",
    )

    return success_response(message="Link de verificación enviado")


@bp.get("/verificar-email")
def verificar_email():
    token = request.args.get("token")
    usuario = auth_service.verificar_token_verificacion_email(str(token or ""))

    # Si el usuario tiene token persistido, exigir que coincida (evita links viejos)
    stored = getattr(usuario, "email_verification_token", None)
    if stored and str(stored) != str(token or ""):
        raise ApiError("El link de verificación no es el más reciente. Solicita uno nuevo.", 400)

    from app.extensions import db

    # Marcar verificado en ambos campos (compat)
    try:
        usuario.email_verificado = True
    except Exception:
        pass
    try:
        usuario.verificado = True
    except Exception:
        pass
    try:
        usuario.email_verification_token = None
        usuario.email_verification_sent_at = None
    except Exception:
        pass

    db.session.add(usuario)
    db.session.commit()

    return success_response(message="Correo verificado correctamente")


@bp.get("/verificar")
def verificar_email_alias():
    # Alias solicitado: /api/auth/verificar?token=
    return verificar_email()
