from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import func

from app.extensions import db
from app.models.resena import Resena
from app.models.renta import Renta
from app.utils.errors import ApiError


def resena_to_dict(r: Resena) -> dict:
	return {
		"id": r.id_resenas,
		"id_renta": r.id_renta,
		"id_autor": r.id_revisor,
		"id_receptor": r.id_usuario_resenado,
		"rating": int(r.calificacion) if r.calificacion is not None else None,
		"comentario": r.comentario,
		"created_at": r.fecha_resena.isoformat() if getattr(r, "fecha_resena", None) else None,
	}


def obtener_mi_calificacion(id_renta: int, id_usuario_actual: int) -> dict | None:
	try:
		r = Resena.query.filter_by(id_renta=id_renta, id_revisor=id_usuario_actual).first()
		return resena_to_dict(r) if r else None
	except (OperationalError, ProgrammingError):
		raise ApiError(
			"Calificaciones no disponibles: ejecuta migraciones (flask db upgrade).",
			status_code=500,
		)


def crear_calificacion(id_renta: int, id_usuario_actual: int, estrellas: int, comentario: str | None) -> dict:
	renta: Renta | None = Renta.query.get(id_renta)
	if not renta:
		raise ApiError("Renta no encontrada.", status_code=404)

	# Solo permitido si renta está finalizada (estado interno completada)
	if renta.estado_renta != "completada":
		raise ApiError("Solo puedes calificar cuando la renta esté finalizada.", status_code=400)

	if renta.id_arrendatario != id_usuario_actual and renta.id_propietario != id_usuario_actual:
		raise ApiError("No tienes permisos para calificar esta renta.", status_code=403)

	try:
		rating_int = int(estrellas)
	except (TypeError, ValueError):
		raise ApiError("El rating debe estar entre 1 y 5.", status_code=400)

	if rating_int < 1 or rating_int > 5:
		raise ApiError("El rating debe estar entre 1 y 5.", status_code=400)

	comentario_norm = (comentario or "").strip() or None
	if comentario_norm is not None and len(comentario_norm) > 300:
		raise ApiError("El comentario no puede exceder 300 caracteres.", status_code=400)

	# receptor es la contraparte
	id_receptor = renta.id_propietario if renta.id_arrendatario == id_usuario_actual else renta.id_arrendatario

	# Si ya calificó, 400
	try:
		existente = Resena.query.filter_by(id_renta=id_renta, id_revisor=id_usuario_actual).first()
		if existente:
			raise ApiError("Ya calificaste esta renta.", status_code=400)
	except (OperationalError, ProgrammingError):
		raise ApiError(
			"Calificaciones no disponibles: ejecuta migraciones (flask db upgrade).",
			status_code=500,
		)

	resena = Resena(
		id_renta=id_renta,
		id_revisor=id_usuario_actual,
		id_usuario_resenado=id_receptor,
		calificacion=rating_int,
		comentario=comentario_norm,
		tipo_resena=None,
		fecha_resena=func.now(),
	)
	db.session.add(resena)

	try:
		db.session.commit()
	except IntegrityError:
		db.session.rollback()
		raise ApiError("Ya calificaste esta renta.", status_code=400)
	except (OperationalError, ProgrammingError):
		db.session.rollback()
		raise ApiError(
			"Calificaciones no disponibles: ejecuta migraciones (flask db upgrade).",
			status_code=500,
		)

	return resena_to_dict(resena)


def obtener_rating_usuario(id_usuario: int) -> dict:
	# promedio + total de reseñas recibidas
	try:
		avg_val, count_val = (
			db.session.query(func.avg(Resena.calificacion), func.count(Resena.id_resenas))
			.filter(Resena.id_usuario_resenado == id_usuario)
			.first()
		)
	except (OperationalError, ProgrammingError):
		# Sin migraciones: no rompemos perfil/detalle; devolvemos 0
		avg_val, count_val = None, 0

	total = int(count_val or 0)
	promedio = float(avg_val) if avg_val is not None else 0.0

	# redondeo suave para UI
	return {
		"id_usuario": id_usuario,
		"promedio": round(promedio, 2),
		"total": total,
	}

