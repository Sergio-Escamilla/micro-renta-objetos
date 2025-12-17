
import io


def test_editar_articulo_owner_puede_actualizar(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_edit@test.com")
	art = make_articulo(dueno.id_usuario)

	resp = client.patch(
		f"/api/articulos/{art.id_articulo}",
		json={
			"titulo": "Nuevo título",
			"descripcion": "Nueva descripción",
			"unidad_precio": "por_dia",
			"precio_renta_dia": 120,
			"precio_renta_hora": 25,
			"deposito_garantia": 99,
			"estado_publicacion": "pausado",
		},
		headers=auth_header(dueno.id_usuario),
	)
	assert resp.status_code == 200
	data = resp.get_json()["data"]
	assert data["id"] == art.id_articulo
	assert data["titulo"] == "Nuevo título"
	assert data["descripcion"] == "Nueva descripción"
	assert float(data["precio_renta_dia"]) == 120.0
	assert data.get("precio_renta_hora") in (None, 0, "", 0.0)
	assert float(data["deposito_garantia"]) == 99.0
	# estado_publicacion puede venir del auto schema
	assert data.get("estado_publicacion") in ("pausado", None)


def test_editar_articulo_rechaza_no_dueno(client, make_user, auth_header, make_articulo):
	dueno = make_user("dueno_edit2@test.com")
	ajeno = make_user("ajeno_edit@test.com")
	art = make_articulo(dueno.id_usuario)

	resp = client.patch(
		f"/api/articulos/{art.id_articulo}",
		json={"titulo": "Hack"},
		headers=auth_header(ajeno.id_usuario),
	)
	assert resp.status_code == 403
	assert resp.get_json()["message"] == "No autorizado"


def test_imagenes_dueno_puede_subir(client, app, tmp_path, make_user, auth_header, make_articulo):
	app.config["UPLOADS_ARTICULOS_DIR"] = str(tmp_path)
	dueno = make_user("dueno_img@test.com")
	art = make_articulo(dueno.id_usuario)

	resp = client.post(
		f"/api/articulos/{art.id_articulo}/imagenes",
		data={"imagenes": (io.BytesIO(b"fake-jpg"), "foto1.jpg")},
		headers=auth_header(dueno.id_usuario),
		content_type="multipart/form-data",
	)
	assert resp.status_code == 201

	det = client.get(f"/api/articulos/{art.id_articulo}")
	assert det.status_code == 200
	imgs = det.get_json()["data"]["imagenes"]
	assert len(imgs) == 1
	assert imgs[0]["url_imagen"]


def test_imagenes_no_dueno_no_puede_subir(client, app, tmp_path, make_user, auth_header, make_articulo):
	app.config["UPLOADS_ARTICULOS_DIR"] = str(tmp_path)
	dueno = make_user("dueno_img2@test.com")
	ajeno = make_user("ajeno_img@test.com")
	art = make_articulo(dueno.id_usuario)

	resp = client.post(
		f"/api/articulos/{art.id_articulo}/imagenes",
		data={"imagenes": (io.BytesIO(b"fake-jpg"), "foto1.jpg")},
		headers=auth_header(ajeno.id_usuario),
		content_type="multipart/form-data",
	)
	assert resp.status_code == 403


def test_admin_no_puede_publicar(client, make_user, auth_header):
	admin = make_user("admin_no_publica@test.com")
	resp = client.post(
		"/api/articulos",
		json={},
		headers=auth_header(admin.id_usuario, roles=["ADMIN"]),
	)
	assert resp.status_code == 403
	body = resp.get_json() or {}
	assert body.get("payload", {}).get("code") == "ADMIN_FORBIDDEN"


def test_imagenes_eliminar_ok_y_403(client, app, tmp_path, make_user, auth_header, make_articulo):
	app.config["UPLOADS_ARTICULOS_DIR"] = str(tmp_path)
	dueno = make_user("dueno_img3@test.com")
	ajeno = make_user("ajeno_img3@test.com")
	art = make_articulo(dueno.id_usuario)

	up = client.post(
		f"/api/articulos/{art.id_articulo}/imagenes",
		data={"imagenes": (io.BytesIO(b"fake-jpg"), "foto1.jpg")},
		headers=auth_header(dueno.id_usuario),
		content_type="multipart/form-data",
	)
	assert up.status_code == 201
	det = client.get(f"/api/articulos/{art.id_articulo}")
	img_id = det.get_json()["data"]["imagenes"][0]["id"]

	forbidden = client.delete(
		f"/api/articulos/{art.id_articulo}/imagenes/{img_id}",
		headers=auth_header(ajeno.id_usuario),
	)
	assert forbidden.status_code == 403

	ok = client.delete(
		f"/api/articulos/{art.id_articulo}/imagenes/{img_id}",
		headers=auth_header(dueno.id_usuario),
	)
	assert ok.status_code == 200

	det2 = client.get(f"/api/articulos/{art.id_articulo}")
	assert det2.status_code == 200
	assert det2.get_json()["data"]["imagenes"] == []


def test_imagenes_reordenar_y_portada(client, app, tmp_path, make_user, auth_header, make_articulo):
	app.config["UPLOADS_ARTICULOS_DIR"] = str(tmp_path)
	dueno = make_user("dueno_img4@test.com")
	art = make_articulo(dueno.id_usuario)

	up1 = client.post(
		f"/api/articulos/{art.id_articulo}/imagenes",
		data={"imagenes": (io.BytesIO(b"fake-jpg"), "foto1.jpg")},
		headers=auth_header(dueno.id_usuario),
		content_type="multipart/form-data",
	)
	assert up1.status_code == 201
	up2 = client.post(
		f"/api/articulos/{art.id_articulo}/imagenes",
		data={"imagenes": (io.BytesIO(b"fake-jpg"), "foto2.jpg")},
		headers=auth_header(dueno.id_usuario),
		content_type="multipart/form-data",
	)
	assert up2.status_code == 201

	det = client.get(f"/api/articulos/{art.id_articulo}")
	imgs = det.get_json()["data"]["imagenes"]
	assert len(imgs) == 2
	ids = [imgs[0]["id"], imgs[1]["id"]]

	# Reordenar (invertir)
	reo = client.patch(
		f"/api/articulos/{art.id_articulo}/imagenes/orden",
		json={"orden": [ids[1], ids[0]]},
		headers=auth_header(dueno.id_usuario),
	)
	assert reo.status_code == 200

	det2 = client.get(f"/api/articulos/{art.id_articulo}")
	imgs2 = det2.get_json()["data"]["imagenes"]
	assert [i["id"] for i in imgs2] == [ids[1], ids[0]]
	assert imgs2[0]["orden"] == 0
	assert imgs2[1]["orden"] == 1

	# Portada
	principal = client.patch(
		f"/api/articulos/{art.id_articulo}/imagenes/{ids[0]}/principal",
		json={},
		headers=auth_header(dueno.id_usuario),
	)
	assert principal.status_code == 200

	det3 = client.get(f"/api/articulos/{art.id_articulo}")
	imgs3 = det3.get_json()["data"]["imagenes"]
	assert any(i["id"] == ids[0] and i["es_principal"] for i in imgs3)
	assert all((i["id"] == ids[0]) == bool(i["es_principal"]) for i in imgs3)
