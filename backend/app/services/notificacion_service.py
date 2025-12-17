import json
import os
from sqlalchemy.exc import OperationalError, ProgrammingError
from flask import current_app

from app.extensions.db import db
from app.models.notificacion import Notificacion
from app.utils.errors import ApiError


def _meta_like_event_key(event_key: str) -> str:
	# meta_json es TEXT; usamos LIKE simple para compat (SQLite/MySQL).
	# OJO: no es un query JSON real; es best-effort.
	return f'%"event_key": "{event_key}"%'


def crear_notificacion(
	id_usuario: int,
	tipo: str,
	mensaje: str,
	meta: dict | None = None,
	*,
	event_key: str | None = None,
) -> None:
	debug = os.getenv("NOTIFICACIONES_DEBUG", "0") == "1"

	t = (tipo or "").strip()
	m = (mensaje or "").strip()
	if not t or not m:
		if debug:
			current_app.logger.info("[notificaciones] skip create: tipo/mensaje vacío")
		return
	if len(m) > 300:
		m = m[:300]

	meta_json = None
	if meta:
		# Enriquecer deep link para UI
		try:
			id_renta = meta.get("id_renta")
			if id_renta is not None:
				meta.setdefault("renta_id", id_renta)
				if meta.get("chat"):
					meta.setdefault("link", f"/rentas/resumen/{id_renta}?chat=1#chat")
				else:
					meta.setdefault("link", f"/rentas/resumen/{id_renta}")
		except Exception:
			pass

		# Normalizar tipo_evento y event_key para dedupe en UI/backend.
		try:
			meta.setdefault("tipo_evento", t)
			if event_key:
				meta.setdefault("event_key", event_key)
		except Exception:
			pass

		try:
			meta_json = json.dumps(meta, ensure_ascii=False)
		except Exception:
			meta_json = None

	try:
		if event_key:
			# Evitar duplicados por doble click/reintentos (best-effort).
			exists = (
				Notificacion.query.filter_by(id_usuario=id_usuario, tipo=t)
				.filter(Notificacion.meta_json.isnot(None))
				.filter(Notificacion.meta_json.like(_meta_like_event_key(event_key)))
				.first()
			)
			if exists is not None:
				if debug:
					current_app.logger.info("[notificaciones] dedupe skip usuario=%s tipo=%s event_key=%s", id_usuario, t, event_key)
				return

		n = Notificacion(id_usuario=id_usuario, tipo=t, mensaje=m, leida=False, meta_json=meta_json)
		db.session.add(n)
		db.session.commit()
		if debug:
			current_app.logger.info(
				"[notificaciones] created id=%s usuario=%s tipo=%s",
				getattr(n, "id", None),
				id_usuario,
				t,
			)
	except (OperationalError, ProgrammingError):
		# Si falta tabla (sin migraciones), no romper flujo.
		db.session.rollback()
		if debug:
			current_app.logger.warning("[notificaciones] create failed (faltan migraciones/tablas)")
		return


def listar_notificaciones(id_usuario: int, limit: int = 50) -> dict:
	debug = os.getenv("NOTIFICACIONES_DEBUG", "0") == "1"
	try:
		q = (
			Notificacion.query.filter_by(id_usuario=id_usuario)
			.order_by(Notificacion.created_at.desc(), Notificacion.id.desc())
			.limit(max(1, min(int(limit), 100)))
		)
		items = q.all()
		unread = Notificacion.query.filter_by(id_usuario=id_usuario, leida=False).count()
	except (OperationalError, ProgrammingError):
		if debug:
			current_app.logger.warning("[notificaciones] list failed (faltan migraciones/tablas)")
		return {"items": [], "unread_count": 0}

	if debug:
		current_app.logger.info(
			"[notificaciones] list usuario=%s items=%s unread=%s",
			id_usuario,
			len(items),
			unread,
		)

	return {
		"items": [
			{
				"id": n.id,
				"tipo": n.tipo,
				"mensaje": n.mensaje,
				"leida": bool(n.leida),
				"created_at": n.created_at.isoformat() if n.created_at else None,
				"meta_json": n.meta_json,
			}
			for n in items
		],
		"unread_count": int(unread),
	}


def marcar_leida(id_notificacion: int, id_usuario: int) -> None:
	debug = os.getenv("NOTIFICACIONES_DEBUG", "0") == "1"
	try:
		n = Notificacion.query.get(id_notificacion)
	except (OperationalError, ProgrammingError):
		raise ApiError("Notificaciones no disponibles.", status_code=501)

	if not n or n.id_usuario != id_usuario:
		raise ApiError("Notificación no encontrada.", status_code=404)

	if not n.leida:
		n.leida = True
		db.session.commit()
		if debug:
			current_app.logger.info("[notificaciones] marked read id=%s usuario=%s", id_notificacion, id_usuario)
