from __future__ import annotations

import json
from datetime import datetime, timedelta

from app.models.notificacion import Notificacion
from app.models.renta import Renta


def _iso(dt: datetime) -> str:
	return dt.replace(microsecond=0).isoformat()


def test_admin_no_puede_publicar_articulos(client, make_user, auth_header):
	admin = make_user("admin_pub@test.com")

	resp = client.post(
		"/api/articulos",
		json={},
		headers=auth_header(admin.id_usuario, roles=["ADMIN"]),
	)
	assert resp.status_code == 403
	body = resp.get_json() or {}
	assert body.get("payload", {}).get("code") == "ADMIN_FORBIDDEN"


def test_admin_no_puede_rentar_articulos(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_art@test.com")
	admin = make_user("admin_rent@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=2)
	fin = inicio + timedelta(days=1)

	resp = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(admin.id_usuario, roles=["ADMIN"]),
	)
	assert resp.status_code == 403
	body = resp.get_json() or {}
	assert body.get("payload", {}).get("code") == "ADMIN_FORBIDDEN"


def test_admin_puede_resolver_incidente_idempotente(client, make_user, auth_header, make_articulo, db_session):
	dueno = make_user("dueno_inc@test.com")	
	arr = make_user("arr_inc@test.com")
	admin = make_user("admin_inc@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=3)
	fin = inicio + timedelta(days=1)

	# Crear renta (arrendatario)
	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	# Flujo hasta devolución
	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	conf = client.post(f"/api/rentas/{id_renta}/confirmar", headers=auth_header(dueno.id_usuario))
	assert conf.status_code == 200

	en_uso = client.post(f"/api/rentas/{id_renta}/en-uso", headers=auth_header(arr.id_usuario))
	assert en_uso.status_code == 200

	dev = client.post(f"/api/rentas/{id_renta}/devolver", headers=auth_header(arr.id_usuario))
	assert dev.status_code == 200

	# Reportar incidente (dueño)
	inc = client.post(
		f"/api/rentas/{id_renta}/incidente",
		json={"descripcion": "Artículo dañado"},
		headers=auth_header(dueno.id_usuario),
	)
	assert inc.status_code == 200

	# Resolver por admin (retención parcial)
	res1 = client.post(
		f"/api/rentas/{id_renta}/resolver-incidente",
		json={"decision": "retener_parcial", "monto_retenido": 10, "nota": "Daño leve"},
		headers=auth_header(admin.id_usuario, roles=["ADMIN"]),
	)
	assert res1.status_code == 200
	data1 = res1.get_json().get("data")
	assert data1["estado_renta"] == "finalizada"
	assert data1.get("deposito_liberado") in (False, None)  # compat: debe ser False

	# No debe duplicar notificaciones al repetir
	count_inc_arr_1 = Notificacion.query.filter_by(id_usuario=arr.id_usuario, tipo="INCIDENTE_RESUELTO").count()
	count_dep_arr_1 = (
		Notificacion.query.filter(
			Notificacion.id_usuario == arr.id_usuario,
			Notificacion.tipo.in_(["DEPOSITO_RETENIDO", "DEPOSITO_LIBERADO"]),
		).count()
	)

	res2 = client.post(
		f"/api/rentas/{id_renta}/resolver-incidente",
		json={"decision": "retener_parcial", "monto_retenido": 10, "nota": "Daño leve"},
		headers=auth_header(admin.id_usuario, roles=["ADMIN"]),
	)
	assert res2.status_code == 200

	count_inc_arr_2 = Notificacion.query.filter_by(id_usuario=arr.id_usuario, tipo="INCIDENTE_RESUELTO").count()
	count_dep_arr_2 = (
		Notificacion.query.filter(
			Notificacion.id_usuario == arr.id_usuario,
			Notificacion.tipo.in_(["DEPOSITO_RETENIDO", "DEPOSITO_LIBERADO"]),
		).count()
	)

	assert count_inc_arr_2 == count_inc_arr_1
	assert count_dep_arr_2 == count_dep_arr_1

	# Estado interno coherente
	renta_db = Renta.query.get(id_renta)
	assert renta_db is not None
	assert renta_db.estado_renta in ("completada", "cancelada", "con_incidente", "en_curso")
	assert renta_db.estado_renta == "completada"
	assert bool(renta_db.deposito_liberado) is False
	assert renta_db.fecha_liberacion_deposito is not None

	# Meta útil en notificación de incidente resuelto
	n = Notificacion.query.filter_by(id_usuario=arr.id_usuario, tipo="INCIDENTE_RESUELTO").first()
	assert n is not None
	meta = json.loads(n.meta_json or "{}")
	assert meta.get("id_renta") == id_renta
	assert meta.get("decision") == "retener_parcial"
	assert meta.get("resuelto_por") == "administrador"
