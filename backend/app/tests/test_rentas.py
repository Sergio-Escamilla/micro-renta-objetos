
from datetime import datetime, timedelta
import json

from app.models.renta import Renta
from app.models.notificacion import Notificacion
from app.models.punto_entrega import PuntoEntrega


def _iso(dt: datetime) -> str:
	return dt.replace(microsecond=0).isoformat()


def test_permiso_ver_renta_ajeno(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno@test.com")
	arr = make_user("arr@test.com")
	ajeno = make_user("ajeno@test.com")

	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=1)
	fin = inicio + timedelta(days=2)

	resp = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert resp.status_code == 201
	id_renta = resp.get_json()["data"]["id"]

	resp2 = client.get(f"/api/rentas/{id_renta}", headers=auth_header(ajeno.id_usuario))
	assert resp2.status_code == 403


def test_no_permite_traslape_creacion(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno2@test.com")
	arr1 = make_user("arr1@test.com")
	arr2 = make_user("arr2@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=3)
	fin = inicio + timedelta(days=2)

	r1 = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr1.id_usuario),
	)
	assert r1.status_code == 201

	# Traslape parcial
	r2 = client.post(
		"/api/rentas",
		json={
			"id_articulo": art.id_articulo,
			"fecha_inicio": _iso(inicio + timedelta(days=1)),
			"fecha_fin": _iso(fin + timedelta(days=1)),
		},
		headers=auth_header(arr2.id_usuario),
	)
	assert r2.status_code in (400, 409)


def test_chat_rechaza_links(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno3@test.com")
	arr = make_user("arr3@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=5)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	bad = client.post(
		f"/api/rentas/{id_renta}/chat",
		json={"mensaje": "mira esto https://ejemplo.com"},
		headers=auth_header(arr.id_usuario),
	)
	assert bad.status_code == 400


def test_expiracion_lazy_en_mias(client, make_user, auth_header, make_articulo, db_session):
	dueno = make_user("dueno_exp@test.com")
	arr = make_user("arr_exp@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=1)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	# Forzar que quede vencida
	renta = Renta.query.get(id_renta)
	renta.fecha_creacion = datetime.utcnow() - timedelta(minutes=20)
	db_session.commit()

	resp = client.get(
		"/api/rentas/mias?rol=arrendatario&estado=activas&page=1&per_page=10",
		headers=auth_header(arr.id_usuario),
	)
	assert resp.status_code == 200
	items = resp.get_json()["data"]["items"]
	item = next((x for x in items if x.get("id_renta") == id_renta), None)
	assert item is not None
	assert item.get("estado") == "expirada"

	# En BD queda cancelada + marcador
	renta2 = Renta.query.get(id_renta)
	assert renta2.estado_renta == "cancelada"
	assert "EXPIRACION_PAGO" in (renta2.notas_devolucion or "")


def test_pagar_renta_expirada_devuelve_409(client, make_user, auth_header, make_articulo, db_session):
	dueno = make_user("dueno_exp2@test.com")
	arr = make_user("arr_exp2@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=1)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	renta = Renta.query.get(id_renta)
	renta.fecha_creacion = datetime.utcnow() - timedelta(minutes=20)
	db_session.commit()

	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 409


def test_confirmar_entrega_otp_codigo_incorrecto(client, make_user, auth_header, make_articulo, db_session):
	dueno = make_user("dueno4@test.com")
	arr = make_user("arr4@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=7)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	renta = Renta.query.get(id_renta)
	renta.codigo_entrega = "123456"
	db_session.commit()

	resp = client.post(
		f"/api/rentas/{id_renta}/confirmar-entrega-otp",
		json={"codigo": "000000"},
		headers=auth_header(dueno.id_usuario),
	)
	assert resp.status_code == 400


def test_no_permite_cancelar_en_uso(client, make_user, auth_header, make_articulo, db_session):
	dueno = make_user("dueno5@test.com")
	arr = make_user("arr5@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=9)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	# confirmada por dueño (flujo clásico)
	conf = client.post(f"/api/rentas/{id_renta}/confirmar", headers=auth_header(dueno.id_usuario))
	assert conf.status_code == 200

	en_uso = client.post(f"/api/rentas/{id_renta}/en-uso", headers=auth_header(arr.id_usuario))
	assert en_uso.status_code == 200

	cancel = client.post(
		f"/api/rentas/{id_renta}/cancelar",
		json={"motivo": "ya no"},
		headers=auth_header(arr.id_usuario),
	)
	assert cancel.status_code == 400


def test_chat_unread_y_marcar_leido(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_unread@test.com")
	arr = make_user("arr_unread@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=2)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	send1 = client.post(
		f"/api/rentas/{id_renta}/chat",
		json={"mensaje": "hola"},
		headers=auth_header(dueno.id_usuario),
	)
	assert send1.status_code == 201

	unread_arr = client.get(
		f"/api/rentas/{id_renta}/chat/unread-count",
		headers=auth_header(arr.id_usuario),
	)
	assert unread_arr.status_code == 200
	assert unread_arr.get_json()["data"]["unread"] == 1

	mark = client.post(
		f"/api/rentas/{id_renta}/chat/marcar-leido",
		headers=auth_header(arr.id_usuario),
	)
	assert mark.status_code == 200

	unread_arr2 = client.get(
		f"/api/rentas/{id_renta}/chat/unread-count",
		headers=auth_header(arr.id_usuario),
	)
	assert unread_arr2.status_code == 200
	assert unread_arr2.get_json()["data"]["unread"] == 0

	send2 = client.post(
		f"/api/rentas/{id_renta}/chat",
		json={"mensaje": "ok"},
		headers=auth_header(arr.id_usuario),
	)
	assert send2.status_code == 201

	unread_dueno = client.get(
		f"/api/rentas/{id_renta}/chat/unread-count",
		headers=auth_header(dueno.id_usuario),
	)
	assert unread_dueno.status_code == 200
	assert unread_dueno.get_json()["data"]["unread"] == 1

	total = client.get(
		"/api/rentas/chat/unread-total",
		headers=auth_header(dueno.id_usuario),
	)
	assert total.status_code == 200


def test_chat_rechaza_email(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_email@test.com")
	arr = make_user("arr_email@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=2)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	bad = client.post(
		f"/api/rentas/{id_renta}/chat",
		json={"mensaje": "escríbeme a test@example.com"},
		headers=auth_header(arr.id_usuario),
	)
	assert bad.status_code == 400


def test_chat_rate_limit_429(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_rl@test.com")
	arr = make_user("arr_rl@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=2)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	send1 = client.post(
		f"/api/rentas/{id_renta}/chat",
		json={"mensaje": "hola"},
		headers=auth_header(dueno.id_usuario),
	)
	assert send1.status_code == 201

	send2 = client.post(
		f"/api/rentas/{id_renta}/chat",
		json={"mensaje": "otro"},
		headers=auth_header(dueno.id_usuario),
	)
	assert send2.status_code == 429


def test_get_puntos_entrega_publicos_solo_activos(client, make_user, auth_header, db_session):
	u = make_user("pe_list@test.com")
	# Crear puntos
	p1 = PuntoEntrega(nombre="Plaza Segura", direccion="Centro", activo=True)
	p2 = PuntoEntrega(nombre="Inactivo", direccion="X", activo=False)
	db_session.add(p1)
	db_session.add(p2)
	db_session.commit()

	resp = client.get("/api/puntos-entrega", headers=auth_header(u.id_usuario))
	assert resp.status_code == 200
	items = resp.get_json()["data"]["items"]
	assert any(x["nombre"] == "Plaza Segura" for x in items)
	assert all(x["nombre"] != "Inactivo" for x in items)


def test_coordinacion_guarda_punto_y_se_refleja_en_resumen(client, make_user, auth_header, make_articulo, db_session):
	dueno = make_user("dueno_pe@test.com")
	arr = make_user("arr_pe@test.com")
	art = make_articulo(dueno.id_usuario)

	p = PuntoEntrega(nombre="Punto Seguro X", direccion="Plaza X", activo=True)
	db_session.add(p)
	db_session.commit()

	inicio = datetime.utcnow() + timedelta(days=3)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	coord = client.post(
		f"/api/rentas/{id_renta}/coordinar",
		json={
			"entrega_modo": "punto_entrega",
			"id_punto_entrega": p.id,
			"ventanas_entrega_propuestas": ["Lun 10-12", "Mar 16-18"],
			"ventanas_devolucion_propuestas": ["Jue 10-12", "Vie 16-18"],
		},
		headers=auth_header(dueno.id_usuario),
	)
	assert coord.status_code == 200

	getr = client.get(f"/api/rentas/{id_renta}", headers=auth_header(arr.id_usuario))
	assert getr.status_code == 200
	data = getr.get_json()["data"]
	assert data.get("entrega_modo") == "punto_entrega"
	assert data.get("punto_entrega") is not None
	assert data.get("punto_entrega", {}).get("nombre") == "Punto Seguro X"


def test_listar_rentas_mias_filtra_por_rol_y_estado(client, make_user, auth_header, make_articulo, db_session):
	dueno = make_user("dueno_inbox@test.com")
	arr = make_user("arr_inbox@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio1 = datetime.utcnow() + timedelta(days=10)
	fin1 = inicio1 + timedelta(days=1)
	r1 = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio1), "fecha_fin": _iso(fin1)},
		headers=auth_header(arr.id_usuario),
	)
	assert r1.status_code == 201
	id1 = r1.get_json()["data"]["id"]

	inicio2 = datetime.utcnow() + timedelta(days=20)
	fin2 = inicio2 + timedelta(days=1)
	r2 = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio2), "fecha_fin": _iso(fin2)},
		headers=auth_header(arr.id_usuario),
	)
	assert r2.status_code == 201
	id2 = r2.get_json()["data"]["id"]

	# Forzamos una renta al historial para que el filtro sea determinista
	renta2 = Renta.query.get(id2)
	renta2.estado_renta = "cancelada"
	db_session.commit()

	activas = client.get(
		"/api/rentas/mias?rol=arrendatario&estado=activas&page=1&per_page=10",
		headers=auth_header(arr.id_usuario),
	)
	assert activas.status_code == 200
	items_activas = activas.get_json()["data"]["items"]
	ids_activas = [x["id_renta"] for x in items_activas]
	assert id1 in ids_activas
	assert id2 not in ids_activas
	# modalidad se calcula (compat) y no depende de columna en BD
	if items_activas:
		assert items_activas[0].get("modalidad") in ("dias", "horas", None)

	hist = client.get(
		"/api/rentas/mias?rol=arrendatario&estado=historial&page=1&per_page=10",
		headers=auth_header(arr.id_usuario),
	)
	assert hist.status_code == 200
	ids_hist = [x["id_renta"] for x in hist.get_json()["data"]["items"]]
	assert id2 in ids_hist


def test_descargar_recibo_pdf(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_recibo@test.com")
	arr = make_user("arr_recibo@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=2)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	resp = client.get(f"/api/rentas/{id_renta}/recibo", headers=auth_header(arr.id_usuario))
	assert resp.status_code == 200
	assert resp.mimetype == "application/pdf"
	assert resp.data.startswith(b"%PDF")


def test_mias_historial_incluye_timeline_fecha_keys(client, make_user, auth_header, make_articulo, db_session):
	dueno = make_user("dueno_hist_timeline@test.com")
	arr = make_user("arr_hist_timeline@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=4)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	# Forzar historial
	renta = Renta.query.get(id_renta)
	renta.estado_renta = "cancelada"
	db_session.commit()

	hist = client.get(
		"/api/rentas/mias?rol=arrendatario&estado=historial&page=1&per_page=10",
		headers=auth_header(arr.id_usuario),
	)
	assert hist.status_code == 200
	items = hist.get_json()["data"]["items"]
	assert any(x["id_renta"] == id_renta for x in items)

	item = next(x for x in items if x["id_renta"] == id_renta)

	# Campos top-level esperados (None permitido)
	expected = [
		"fecha_pago",
		"fecha_coordinacion_confirmada",
		"fecha_entrega",
		"fecha_en_uso",
		"fecha_devolucion",
		"fecha_finalizacion",
		"fecha_incidente",
		"fecha_cancelacion",
		"fecha_expiracion",
		"fecha_liberacion_deposito",
		"deposito_liberado",
		"reembolso_simulado",
		"timeline",
	]
	for k in expected:
		assert k in item

	assert isinstance(item["timeline"], dict)
	for k in [
		"fecha_pago",
		"fecha_coordinacion_confirmada",
		"fecha_entrega",
		"fecha_en_uso",
		"fecha_devolucion",
		"fecha_finalizacion",
		"fecha_incidente",
		"fecha_cancelacion",
		"fecha_expiracion",
		"fecha_liberacion_deposito",
	]:
		assert k in item["timeline"]


def test_notificaciones_crear_y_deposito_dedupe(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_notif@test.com")
	arr = make_user("arr_notif@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=6)
	fin = inicio + timedelta(days=1)

	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	# Notificación al dueño por creación
	creadas = Notificacion.query.filter_by(id_usuario=dueno.id_usuario, tipo="RENTA_CREADA").all()
	assert len(creadas) >= 1

	# Flujo hasta finalizar y liberar depósito
	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	conf = client.post(f"/api/rentas/{id_renta}/confirmar", headers=auth_header(dueno.id_usuario))
	assert conf.status_code == 200

	en_uso = client.post(f"/api/rentas/{id_renta}/en-uso", headers=auth_header(arr.id_usuario))
	assert en_uso.status_code == 200

	dev = client.post(f"/api/rentas/{id_renta}/devolver", headers=auth_header(arr.id_usuario))
	assert dev.status_code == 200

	fin1 = client.post(f"/api/rentas/{id_renta}/finalizar", headers=auth_header(dueno.id_usuario))
	assert fin1.status_code == 200

	# Debe existir una sola notificación de depósito liberado (dedupe) para arrendatario
	deps = Notificacion.query.filter_by(id_usuario=arr.id_usuario, tipo="DEPOSITO_LIBERADO").all()
	assert len(deps) == 1
	meta = json.loads(deps[0].meta_json or "{}")
	assert meta.get("id_renta") == id_renta
	assert float(meta.get("monto_deposito") or 0) == 50.0

	# Repetir finalizar no debe duplicar notificación
	fin2 = client.post(f"/api/rentas/{id_renta}/finalizar", headers=auth_header(dueno.id_usuario))
	assert fin2.status_code == 200
	deps2 = Notificacion.query.filter_by(id_usuario=arr.id_usuario, tipo="DEPOSITO_LIBERADO").all()
	assert len(deps2) == 1


def test_admin_no_puede_rentar(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_admin_forbidden_rentar@test.com")
	admin = make_user("admin_no_renta@test.com")
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


def test_admin_resuelve_incidente_idempotente_notifica(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_inc_admin@test.com")
	arr = make_user("arr_inc_admin@test.com")
	admin = make_user("admin_inc_admin@test.com")
	art = make_articulo(dueno.id_usuario)

	inicio = datetime.utcnow() + timedelta(days=3)
	fin = inicio + timedelta(days=1)

	# Crear renta
	r = client.post(
		"/api/rentas",
		json={"id_articulo": art.id_articulo, "fecha_inicio": _iso(inicio), "fecha_fin": _iso(fin)},
		headers=auth_header(arr.id_usuario),
	)
	assert r.status_code == 201
	id_renta = r.get_json()["data"]["id"]

	# Avanzar flujo mínimo hasta devolución
	pago = client.post(f"/api/rentas/{id_renta}/pagar", headers=auth_header(arr.id_usuario))
	assert pago.status_code == 200

	conf = client.post(f"/api/rentas/{id_renta}/confirmar", headers=auth_header(dueno.id_usuario))
	assert conf.status_code == 200

	en_uso = client.post(f"/api/rentas/{id_renta}/en-uso", headers=auth_header(arr.id_usuario))
	assert en_uso.status_code == 200

	dev = client.post(f"/api/rentas/{id_renta}/devolver", headers=auth_header(arr.id_usuario))
	assert dev.status_code == 200

	# Reportar incidente
	inc = client.post(
		f"/api/rentas/{id_renta}/incidente",
		json={"descripcion": "Artículo devuelto con daños"},
		headers=auth_header(dueno.id_usuario),
	)
	assert inc.status_code == 200

	# Resolver como admin (retención total)
	res = client.post(
		f"/api/rentas/{id_renta}/resolver-incidente",
		json={"decision": "retener_total", "nota": "Daños comprobados"},
		headers=auth_header(admin.id_usuario, roles=["ADMIN"]),
	)
	assert res.status_code == 200
	data = res.get_json()["data"]
	assert data.get("estado_renta") == "finalizada"
	assert data.get("deposito_liberado") is False

	# Notificaciones: 1x incidente resuelto + 1x depósito retenido
	inc_res = Notificacion.query.filter_by(id_usuario=arr.id_usuario, tipo="INCIDENTE_RESUELTO").all()
	assert len(inc_res) == 1
	meta1 = json.loads(inc_res[0].meta_json or "{}")
	assert meta1.get("id_renta") == id_renta
	assert meta1.get("decision") == "retener_total"
	assert meta1.get("resuelto_por") == "administrador"

	deps_ret = Notificacion.query.filter_by(id_usuario=arr.id_usuario, tipo="DEPOSITO_RETENIDO").all()
	assert len(deps_ret) == 1
	meta2 = json.loads(deps_ret[0].meta_json or "{}")
	assert meta2.get("id_renta") == id_renta
	assert meta2.get("resuelto_por") == "administrador"

	# Idempotencia: repetir no duplica notificaciones
	res2 = client.post(
		f"/api/rentas/{id_renta}/resolver-incidente",
		json={"decision": "retener_total", "nota": "Daños comprobados"},
		headers=auth_header(admin.id_usuario, roles=["ADMIN"]),
	)
	assert res2.status_code == 200
	inc_res2 = Notificacion.query.filter_by(id_usuario=arr.id_usuario, tipo="INCIDENTE_RESUELTO").all()
	deps_ret2 = Notificacion.query.filter_by(id_usuario=arr.id_usuario, tipo="DEPOSITO_RETENIDO").all()
	assert len(inc_res2) == 1
	assert len(deps_ret2) == 1
