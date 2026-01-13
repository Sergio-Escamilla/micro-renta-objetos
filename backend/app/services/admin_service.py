from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.extensions import db
from app.models.articulo import Articulo
from app.models.incidente_renta import IncidenteRenta
from app.models.notificacion import Notificacion
from app.models.punto_entrega import PuntoEntrega
from app.models.renta import Renta
from app.models.resena import Resena
from app.models.usuario import Usuario
from app.utils.errors import ApiError


def obtener_resumen_admin() -> dict:
	usuarios = db.session.query(func.count(Usuario.id_usuario)).scalar() or 0
	articulos = db.session.query(func.count(Articulo.id_articulo)).scalar() or 0

	rentas_activas = (
		db.session.query(func.count(Renta.id))
		.filter(Renta.estado_renta.in_(["pendiente_pago", "pagada", "confirmada", "en_curso", "con_incidente"]))
		.scalar()
		or 0
	)
	rentas_finalizadas = (
		db.session.query(func.count(Renta.id))
		.filter(Renta.estado_renta.in_(["completada", "cancelada"]))
		.scalar()
		or 0
	)

	incidentes_abiertos = (
		db.session.query(func.count(IncidenteRenta.id))
		.filter(IncidenteRenta.decision.is_(None))
		.scalar()
		or 0
	)

	try:
		notificaciones_no_leidas_total = (
			db.session.query(func.count(Notificacion.id))
			.filter(Notificacion.leida.is_(False))
			.scalar()
			or 0
		)
	except Exception:
		# Si la tabla no existe en algún entorno, no rompemos el panel.
		notificaciones_no_leidas_total = None

	return {
		"usuarios": int(usuarios),
		"articulos": int(articulos),
		"rentas_activas": int(rentas_activas),
		"rentas_finalizadas": int(rentas_finalizadas),
		"incidentes_abiertos": int(incidentes_abiertos),
		"notificaciones_no_leidas_total": (
			int(notificaciones_no_leidas_total) if notificaciones_no_leidas_total is not None else None
		),
	}


def _incidente_to_dict(i: IncidenteRenta) -> dict:
	renta: Renta | None = Renta.query.get(i.id_renta)

	articulo = getattr(renta, "articulo", None) if renta else None
	arr = getattr(renta, "arrendatario", None) if renta else None
	prop = getattr(renta, "propietario", None) if renta else None

	estado = "abierto" if i.decision is None else "resuelto"
	return {
		"id": i.id,
		"id_renta": i.id_renta,
		"estado": estado,
		"descripcion": i.descripcion,
		"decision": i.decision,
		"monto_retenido": float(i.monto_retenido) if i.monto_retenido is not None else None,
		"nota": i.nota,
		"created_at": i.created_at.isoformat() if i.created_at else None,
		"resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
		"renta": {
			"id": renta.id,
			"estado_renta": renta.estado_renta,
			"fecha_inicio": renta.fecha_inicio.isoformat() if renta.fecha_inicio else None,
			"fecha_fin": renta.fecha_fin.isoformat() if renta.fecha_fin else None,
			"precio_total_renta": float(renta.precio_total_renta) if renta.precio_total_renta is not None else None,
			"monto_deposito": float(renta.monto_deposito) if renta.monto_deposito is not None else None,
			"deposito_liberado": bool(renta.deposito_liberado),
			"fecha_liberacion_deposito": renta.fecha_liberacion_deposito.isoformat() if renta.fecha_liberacion_deposito else None,
		}
		if renta
		else None,
		"articulo": {
			"id_articulo": articulo.id_articulo,
			"titulo": articulo.titulo,
		}
		if articulo
		else None,
		"arrendatario": {
			"id_usuario": arr.id_usuario,
			"nombre": arr.nombre,
			"apellidos": arr.apellidos,
		}
		if arr
		else None,
		"propietario": {
			"id_usuario": prop.id_usuario,
			"nombre": prop.nombre,
			"apellidos": prop.apellidos,
		}
		if prop
		else None,
	}


def listar_incidentes_admin(estado: str | None, page: int | str, per_page: int | str) -> dict:
	try:
		page_int = max(int(page), 1)
	except Exception:
		page_int = 1
	try:
		per_page_int = min(max(int(per_page), 1), 50)
	except Exception:
		per_page_int = 10

	query = IncidenteRenta.query

	if estado:
		est = str(estado).strip().lower()
		if est == "abierto":
			query = query.filter(IncidenteRenta.decision.is_(None))
		elif est == "resuelto":
			query = query.filter(IncidenteRenta.decision.is_not(None))
		else:
			raise ApiError("Parámetro 'estado' inválido. Usa: abierto|resuelto", 400)

	total = query.count()
	items = (
		query.order_by(IncidenteRenta.created_at.desc())
		.offset((page_int - 1) * per_page_int)
		.limit(per_page_int)
		.all()
	)

	return {
		"page": page_int,
		"per_page": per_page_int,
		"total": int(total),
		"items": [_incidente_to_dict(i) for i in items],
	}


def listar_usuarios_admin(search: str | None, page: int | str, per_page: int | str) -> dict:
	try:
		page_int = max(int(page), 1)
	except Exception:
		page_int = 1
	try:
		per_page_int = min(max(int(per_page), 1), 50)
	except Exception:
		per_page_int = 10

	rentas_count_sq = (
		select(func.count(Renta.id))
		.where(or_(Renta.id_arrendatario == Usuario.id_usuario, Renta.id_propietario == Usuario.id_usuario))
		.correlate(Usuario)
		.scalar_subquery()
	)
	rating_prom_sq = (
		select(func.avg(Resena.calificacion))
		.where(Resena.id_usuario_resenado == Usuario.id_usuario)
		.correlate(Usuario)
		.scalar_subquery()
	)
	rating_total_sq = (
		select(func.count(Resena.id_resenas))
		.where(Resena.id_usuario_resenado == Usuario.id_usuario)
		.correlate(Usuario)
		.scalar_subquery()
	)

	query = db.session.query(
		Usuario,
		rentas_count_sq.label("rentas_count"),
		rating_prom_sq.label("rating_promedio"),
		rating_total_sq.label("rating_total"),
	)

	if search:
		s = f"%{str(search).strip()}%"
		query = query.filter(
			or_(
				Usuario.nombre.ilike(s),
				Usuario.apellidos.ilike(s),
				Usuario.correo_electronico.ilike(s),
			)
		)

	total = query.count()
	rows = (
		query.order_by(Usuario.id_usuario.desc())
		.offset((page_int - 1) * per_page_int)
		.limit(per_page_int)
		.all()
	)

	items: list[dict] = []
	for u, rentas_count, rating_promedio, rating_total in rows:
		roles = [ur.rol.nombre for ur in (u.roles or []) if getattr(ur, "rol", None) is not None]
		items.append(
			{
				"id_usuario": u.id_usuario,
				"nombre": u.nombre,
				"apellidos": u.apellidos,
				"correo_electronico": u.correo_electronico,
				"estado_cuenta": u.estado_cuenta,
				"roles": roles,
				"rentas_count": int(rentas_count or 0),
				"rating_promedio": round(float(rating_promedio or 0.0), 2),
				"rating_total": int(rating_total or 0),
			}
		)

	return {
		"page": page_int,
		"per_page": per_page_int,
		"total": int(total),
		"items": items,
	}


def listar_articulos_admin(search: str | None, page: int | str, per_page: int | str) -> dict:
	try:
		page_int = max(int(page), 1)
	except Exception:
		page_int = 1
	try:
		per_page_int = min(max(int(per_page), 1), 50)
	except Exception:
		per_page_int = 10

	query = Articulo.query
	if search:
		s = f"%{str(search).strip()}%"
		query = query.filter(or_(Articulo.titulo.ilike(s), Articulo.descripcion.ilike(s)))

	total = query.count()
	items = (
		query.order_by(Articulo.id_articulo.desc())
		.offset((page_int - 1) * per_page_int)
		.limit(per_page_int)
		.all()
	)

	out: list[dict] = []
	for a in items:
		prop = getattr(a, "propietario", None)
		out.append(
			{
				"id_articulo": a.id_articulo,
				"titulo": a.titulo,
				"estado_publicacion": a.estado_publicacion,
				"id_propietario": a.id_propietario,
				"propietario": {
					"id_usuario": prop.id_usuario,
					"nombre": prop.nombre,
					"apellidos": prop.apellidos,
					"correo_electronico": prop.correo_electronico,
				}
				if prop
				else None,
			}
		)

	return {
		"page": page_int,
		"per_page": per_page_int,
		"total": int(total),
		"items": out,
	}


def _punto_entrega_to_dict(p: PuntoEntrega) -> dict:
	return {
		"id": p.id,
		"nombre": p.nombre,
		"direccion": p.direccion,
		"activo": bool(p.activo),
		"created_at": p.created_at.isoformat() if p.created_at else None,
		"updated_at": p.updated_at.isoformat() if p.updated_at else None,
	}


def listar_puntos_entrega_admin(search: str | None, page: int | str, per_page: int | str) -> dict:
	try:
		page_int = max(int(page), 1)
	except Exception:
		page_int = 1
	try:
		per_page_int = min(max(int(per_page), 1), 50)
	except Exception:
		per_page_int = 10

	try:
		query = PuntoEntrega.query
		if search:
			s = f"%{str(search).strip()}%"
			query = query.filter(or_(PuntoEntrega.nombre.ilike(s), PuntoEntrega.direccion.ilike(s)))

		total = query.count()
		items = (
			query.order_by(PuntoEntrega.activo.desc(), PuntoEntrega.id.desc())
			.offset((page_int - 1) * per_page_int)
			.limit(per_page_int)
			.all()
		)
		return {
			"page": page_int,
			"per_page": per_page_int,
			"total": int(total),
			"items": [_punto_entrega_to_dict(x) for x in items],
		}
	except (OperationalError, ProgrammingError):
		raise ApiError("Recurso no disponible (faltan migraciones).", 501)


def crear_punto_entrega_admin(payload: dict) -> dict:
	nombre = str((payload or {}).get("nombre") or "").strip()
	if not nombre:
		raise ApiError("El nombre es obligatorio.", 400)
	direccion = (payload or {}).get("direccion")
	direccion = str(direccion).strip() if direccion is not None else None
	activo = (payload or {}).get("activo")
	activo_bool = True if activo is None else bool(activo)

	try:
		p = PuntoEntrega(nombre=nombre, direccion=direccion, activo=activo_bool)
		db.session.add(p)
		db.session.commit()
		return _punto_entrega_to_dict(p)
	except (OperationalError, ProgrammingError):
		raise ApiError("Recurso no disponible (faltan migraciones).", 501)


def actualizar_punto_entrega_admin(id_punto: int, payload: dict) -> dict:
	try:
		p: PuntoEntrega | None = PuntoEntrega.query.get(id_punto)
		if not p:
			raise ApiError("Punto de entrega no encontrado.", 404)

		if "nombre" in (payload or {}):
			nombre = str((payload or {}).get("nombre") or "").strip()
			if not nombre:
				raise ApiError("El nombre es obligatorio.", 400)
			p.nombre = nombre

		if "direccion" in (payload or {}):
			direccion = (payload or {}).get("direccion")
			p.direccion = str(direccion).strip() if direccion is not None else None

		if "activo" in (payload or {}):
			p.activo = bool((payload or {}).get("activo"))

		db.session.commit()
		return _punto_entrega_to_dict(p)
	except (OperationalError, ProgrammingError):
		raise ApiError("Recurso no disponible (faltan migraciones).", 501)


def desactivar_punto_entrega_admin(id_punto: int) -> dict:
	try:
		p: PuntoEntrega | None = PuntoEntrega.query.get(id_punto)
		if not p:
			raise ApiError("Punto de entrega no encontrado.", 404)
		p.activo = False
		db.session.commit()
		return _punto_entrega_to_dict(p)
	except (OperationalError, ProgrammingError):
		raise ApiError("Recurso no disponible (faltan migraciones).", 501)


def actualizar_estado_publicacion_articulo(id_articulo: int, estado_publicacion: str | None) -> dict:
	articulo: Articulo | None = Articulo.query.get(id_articulo)
	if not articulo:
		raise ApiError("Artículo no encontrado", 404)

	est = (estado_publicacion or "").strip()
	if est not in ("publicado", "pausado"):
		raise ApiError("estado_publicacion inválido. Usa: publicado|pausado", 400)

	articulo.estado_publicacion = est
	db.session.commit()

	return {
		"id_articulo": articulo.id_articulo,
		"estado_publicacion": articulo.estado_publicacion,
	}
