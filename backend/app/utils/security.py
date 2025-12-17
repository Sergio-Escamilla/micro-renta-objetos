from app.models.usuario import Usuario
from app.utils.errors import ApiError


def _missing_profile_fields(usuario: Usuario) -> list[str]:
	missing: list[str] = []

	email_verificado = bool(getattr(usuario, "email_verificado", False)) or bool(getattr(usuario, "verificado", False))
	if not email_verificado:
		missing.append("correo_verificado")

	telefono = str(getattr(usuario, "telefono", "") or "").strip()
	if not telefono:
		missing.append("telefono")

	ciudad = str(getattr(usuario, "ciudad", "") or "").strip()
	estado = str(getattr(usuario, "estado", "") or "").strip()
	if not (ciudad and estado):
		missing.append("ubicacion")

	return missing


def require_usuario_habilitado(id_usuario: int) -> Usuario:
	usuario: Usuario | None = Usuario.query.get(id_usuario)
	if not usuario:
		raise ApiError("Usuario no encontrado", 404)

	missing = _missing_profile_fields(usuario)
	if missing:
		raise ApiError(
			"Completa tu perfil y verifica tu correo para continuar.",
			403,
			payload={"code": "PROFILE_INCOMPLETE", "missing": missing},
		)

	return usuario
