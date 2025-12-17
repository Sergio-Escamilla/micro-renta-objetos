from datetime import timedelta
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.extensions import bcrypt
from app.models.usuario import Usuario
from app.utils.errors import ApiError


def autenticar(correo_electronico: str, contrasena: str):
    correo = correo_electronico.lower().strip()
    usuario = Usuario.query.filter_by(correo_electronico=correo).first()

    if not usuario:
        raise ApiError("Credenciales inválidas", 401)

    try:
        password_ok = bcrypt.check_password_hash(usuario.hash_contrasena or "", contrasena)
    except (ValueError, TypeError):
        # Si el hash en BD está corrupto o en texto plano, no debe reventar en 500.
        raise ApiError("Credenciales inválidas", 401)

    if not password_ok:
        raise ApiError("Credenciales inválidas", 401)

    if usuario.estado_cuenta != "activo":
        raise ApiError("Cuenta inactiva", 403)

    roles = [ur.rol.nombre for ur in usuario.roles]

    email_verificado = bool(getattr(usuario, "email_verificado", False)) or bool(getattr(usuario, "verificado", False))

    access_token = create_access_token(
        identity=str(usuario.id_usuario),
        additional_claims={
            "roles": roles,
            # compat: front y lógica existente usan `verificado`
            "verificado": bool(getattr(usuario, "verificado", False)) or email_verificado,
            "email_verificado": email_verificado,
        },
        expires_delta=timedelta(hours=3)
    )

    refresh_token = create_refresh_token(identity=str(usuario.id_usuario))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "usuario": {
            "id": usuario.id_usuario,
            "nombre": usuario.nombre,
            "apellidos": usuario.apellidos,
            "roles": roles,
            "correo_electronico": usuario.correo_electronico,
            "verificado": bool(getattr(usuario, "verificado", False)) or email_verificado,
            "email_verificado": email_verificado,
        }
    }


def _email_token_serializer() -> URLSafeTimedSerializer:
    secret = current_app.config.get("JWT_SECRET_KEY") or current_app.secret_key
    if not secret:
        raise ApiError("Configuración inválida: secret no disponible", 500)
    return URLSafeTimedSerializer(secret_key=str(secret))


def generar_token_verificacion_email(usuario: Usuario) -> str:
    if not usuario:
        raise ApiError("Usuario inválido", 400)
    data = {
        "id_usuario": int(usuario.id_usuario),
        "correo_electronico": str(usuario.correo_electronico or "").lower().strip(),
    }
    s = _email_token_serializer()
    return s.dumps(data, salt="email-verify")


def verificar_token_verificacion_email(token: str) -> Usuario:
    t = (token or "").strip()
    if not t:
        raise ApiError("Token requerido", 400)

    max_age = int(current_app.config.get("EMAIL_VERIFY_TOKEN_MAX_AGE_SECONDS") or 86400)
    s = _email_token_serializer()
    try:
        data = s.loads(t, salt="email-verify", max_age=max_age)
    except SignatureExpired:
        raise ApiError("El link de verificación expiró. Solicita uno nuevo.", 400)
    except BadSignature:
        raise ApiError("Token inválido", 400)

    try:
        user_id = int(data.get("id_usuario"))
    except Exception:
        raise ApiError("Token inválido", 400)

    correo = str(data.get("correo_electronico") or "").lower().strip()
    usuario = Usuario.query.get(user_id)
    if not usuario:
        raise ApiError("Usuario no encontrado", 404)
    if str(usuario.correo_electronico or "").lower().strip() != correo:
        raise ApiError("Token inválido", 400)

    return usuario
