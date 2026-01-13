# backend/app/api/articulo_routes.py
import os
import uuid
from urllib.parse import urlparse

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.extensions import db
from app.models.articulo import Articulo
from app.models.articulo_imagen import ArticuloImagen
from app.models.categoria import Categoria
from app.schemas.articulo_schemas import (
    ArticuloListadoSchema,
    ArticuloCreateSchema,
    ArticuloDetalleSchema,
    ArticuloUpdateSchema,
)
from app.utils.errors import ApiError
from app.utils.security import require_usuario_habilitado
from app.services import renta_service

bp = Blueprint("articulo_routes", __name__)

articulo_listado_schema = ArticuloListadoSchema(many=True)
articulo_detalle_schema = ArticuloDetalleSchema()
articulo_create_schema = ArticuloCreateSchema()
articulo_update_schema = ArticuloUpdateSchema()


def _reject_admin_publicar() -> None:
    claims = get_jwt() or {}
    roles = claims.get("roles") or []
    es_admin = any(str(r).upper() in ("ADMIN", "ADMINISTRADOR") for r in roles)
    if es_admin:
        raise ApiError(
            "Los administradores no pueden publicar artículos. Usa una cuenta de usuario.",
            403,
            payload={"code": "ADMIN_FORBIDDEN"},
        )

 
@bp.get("")
@jwt_required(optional=True)
def listar_articulos():
    """
    Listado público de artículos disponibles para renta.
    Más adelante podemos filtrar por categoría, por ciudad, etc.
    """
    articulos = (
        Articulo.query
        .filter(Articulo.estado_publicacion != "eliminado")
        .order_by(Articulo.id_articulo.desc())
        .all()
    )

    data = articulo_listado_schema.dump(articulos)
    return jsonify({"success": True, "data": data}), 200


@bp.get("/mis")
@jwt_required()
def listar_mis_articulos():
    id_usuario = get_jwt_identity()
    try:
        id_usuario_int = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    articulos = (
        Articulo.query
        .filter(
            Articulo.id_propietario == id_usuario_int,
            Articulo.estado_publicacion != "eliminado",
        )
        .order_by(Articulo.id_articulo.desc())
        .all()
    )

    data = articulo_listado_schema.dump(articulos)
    return jsonify({"success": True, "data": data}), 200


@bp.post("")
@jwt_required()
def crear_articulo():
    id_usuario = get_jwt_identity()
    try:
        id_usuario_int = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    # Admin NO puede publicar (bloqueo temprano, sin efectos colaterales)
    _reject_admin_publicar()

    # Exigir correo verificado + perfil completo
    require_usuario_habilitado(id_usuario_int)

    data = articulo_create_schema.load(request.json or {})

    precio_dia = data.get("precio_renta_dia")
    precio_hora = data.get("precio_renta_hora")

    def _ok(v):
        try:
            return v is not None and float(v) > 0
        except Exception:
            return False

    dia_ok = _ok(precio_dia)
    hora_ok = _ok(precio_hora)

    # La BD real soporta 1 unidad por artículo. Si vienen ambas, guardamos solo una.
    unit_hint = str(data.get("unidad_precio") or "").strip().lower() or None
    if unit_hint not in ("por_hora", "por_dia", "por_semana"):
        unit_hint = None

    warnings: list[str] = []
    selected_unit: str | None = None
    if hora_ok and dia_ok:
        selected_unit = unit_hint if unit_hint in ("por_hora", "por_dia") else "por_dia"
        warnings.append(
            "Tu base actual soporta 1 modalidad por artículo. Se guardó solo la modalidad principal."
        )
    elif hora_ok:
        selected_unit = "por_hora"
    elif dia_ok:
        selected_unit = "por_dia"
    else:
        # El schema ya valida, pero dejamos fallback defensivo.
        raise ApiError("Debes indicar un precio por día y/o por hora.", 400)

    selected_price = precio_hora if selected_unit == "por_hora" else precio_dia
    if selected_price is None:
        # fallback defensivo
        selected_price = precio_dia if dia_ok else precio_hora

    categoria = Categoria.query.get(data["id_categoria"])
    if not categoria:
        raise ApiError("Categoría inválida", 400)

    articulo = Articulo(
        id_propietario=id_usuario_int,
        titulo=data["titulo"].strip(),
        descripcion=data["descripcion"].strip(),
        id_categoria=data["id_categoria"],
        precio_base=selected_price,
        unidad_precio=selected_unit,
        monto_deposito=data.get("deposito_garantia") or 0,
        ubicacion_texto=data.get("ubicacion_texto"),
        estado="disponible",
        estado_publicacion="publicado",
    )

    db.session.add(articulo)
    db.session.flush()

    urls = data.get("urls_imagenes") or []
    for idx, url in enumerate(urls):
        img = ArticuloImagen(
            id_articulo=articulo.id_articulo,
            url_imagen=url,
            es_principal=(idx == 0),
            orden=idx,
        )
        db.session.add(img)

    db.session.commit()

    resp = {"success": True, "data": articulo_detalle_schema.dump(articulo)}
    if warnings:
        resp["warnings"] = warnings
    return jsonify(resp), 201


@bp.post("/<int:articulo_id>/imagenes")
@jwt_required()
def subir_imagenes_articulo(articulo_id: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario_int = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    articulo = Articulo.query.get_or_404(articulo_id)
    if articulo.id_propietario != id_usuario_int:
        raise ApiError("No autorizado", 403)

    archivos = request.files.getlist("imagenes")
    if not archivos:
        raise ApiError("Debes enviar al menos un archivo en el campo 'imagenes'.", 400)

    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    upload_dir = current_app.config.get("UPLOADS_ARTICULOS_DIR")
    if not upload_dir:
        raise ApiError("Configuración de uploads no disponible", 500)

    os.makedirs(upload_dir, exist_ok=True)

    # Orden y principal
    existentes = ArticuloImagen.query.filter_by(id_articulo=articulo.id_articulo).all()
    next_orden = 0
    if existentes:
        ordenes = [img.orden for img in existentes if img.orden is not None]
        next_orden = (max(ordenes) + 1) if ordenes else len(existentes)

    ya_hay_principal = any(img.es_principal for img in existentes)

    nuevas = []
    for idx, f in enumerate(archivos):
        original = f.filename or ""
        _, ext = os.path.splitext(original)
        ext = (ext or "").lower()
        if ext not in allowed:
            raise ApiError(
                "Formato inválido. Solo se permiten: jpg, jpeg, png, webp.",
                400,
            )

        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, filename)
        f.save(file_path)

        base = (request.host_url or "http://127.0.0.1:5000/").rstrip("/")
        url = f"{base}/uploads/articulos/{filename}"

        img = ArticuloImagen(
            id_articulo=articulo.id_articulo,
            url_imagen=url,
            es_principal=(False if ya_hay_principal else idx == 0),
            orden=next_orden + idx,
        )
        db.session.add(img)
        nuevas.append(img)

    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "articulo_id": articulo.id_articulo,
                    "imagenes": [img.url_imagen for img in nuevas],
                    # Backward-compatible: campo extra con detalle para UI de edición
                    "imagenes_detalle": [
                        {
                            "id": img.id,
                            "url_imagen": img.url_imagen,
                            "es_principal": bool(img.es_principal),
                            "orden": img.orden,
                        }
                        for img in nuevas
                    ],
                },
            }
        ),
        201,
    )


@bp.delete("/<int:articulo_id>/imagenes/<int:imagen_id>")
@jwt_required()
def eliminar_imagen_articulo(articulo_id: int, imagen_id: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario_int = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    articulo = Articulo.query.get_or_404(articulo_id)
    if articulo.id_propietario != id_usuario_int:
        raise ApiError("No autorizado", 403)

    imagen = ArticuloImagen.query.get_or_404(imagen_id)
    if imagen.id_articulo != articulo.id_articulo:
        raise ApiError("Imagen inválida", 400)

    was_principal = bool(imagen.es_principal)
    url = imagen.url_imagen

    # Eliminar registro
    db.session.delete(imagen)
    db.session.flush()

    # Si era principal, asignar uno nuevo best-effort
    if was_principal:
        restantes = ArticuloImagen.query.filter_by(id_articulo=articulo.id_articulo).all()
        restantes = sorted(
            restantes,
            key=lambda img: (
                (img.orden if img.orden is not None else 10**9),
                img.id,
            ),
        )
        if restantes:
            for img in restantes:
                img.es_principal = False
            restantes[0].es_principal = True

    db.session.commit()

    # Eliminar archivo si aplica (best-effort)
    try:
        upload_dir = current_app.config.get("UPLOADS_ARTICULOS_DIR")
        if upload_dir and url:
            path = urlparse(url).path or ""
            prefix = "/uploads/articulos/"
            if prefix in path:
                filename = path.split(prefix, 1)[1]
                filename = os.path.basename(filename)
                file_path = os.path.join(upload_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
    except Exception:
        pass

    return jsonify({"success": True, "data": {"deleted": True}}), 200


@bp.patch("/<int:articulo_id>/imagenes/orden")
@jwt_required()
def reordenar_imagenes_articulo(articulo_id: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario_int = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    articulo = Articulo.query.get_or_404(articulo_id)
    if articulo.id_propietario != id_usuario_int:
        raise ApiError("No autorizado", 403)

    body = request.json or {}
    orden = body.get("orden")
    if not isinstance(orden, list) or not orden:
        raise ApiError("Body inválido. Usa: {orden: [id_imagen,...]}", 400)

    try:
        orden_ids = [int(x) for x in orden]
    except Exception:
        raise ApiError("Body inválido. Los ids deben ser enteros.", 400)

    imagenes = ArticuloImagen.query.filter_by(id_articulo=articulo.id_articulo).all()
    ids_existentes = {img.id for img in imagenes}
    if set(orden_ids) != ids_existentes:
        raise ApiError("La lista de orden no coincide con las imágenes del artículo.", 400)

    pos = {img_id: idx for idx, img_id in enumerate(orden_ids)}
    for img in imagenes:
        img.orden = pos[img.id]

    db.session.commit()
    return jsonify({"success": True, "data": {"ok": True}}), 200


@bp.patch("/<int:articulo_id>/imagenes/<int:imagen_id>/principal")
@jwt_required()
def marcar_imagen_principal(articulo_id: int, imagen_id: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario_int = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    articulo = Articulo.query.get_or_404(articulo_id)
    if articulo.id_propietario != id_usuario_int:
        raise ApiError("No autorizado", 403)

    imagen = ArticuloImagen.query.get_or_404(imagen_id)
    if imagen.id_articulo != articulo.id_articulo:
        raise ApiError("Imagen inválida", 400)

    imagenes = ArticuloImagen.query.filter_by(id_articulo=articulo.id_articulo).all()
    for img in imagenes:
        img.es_principal = (img.id == imagen.id)

    db.session.commit()
    return jsonify({"success": True, "data": {"ok": True}}), 200


@bp.get("/<int:articulo_id>")
@jwt_required(optional=True)
def obtener_articulo(articulo_id: int):
    """
    Detalle de un artículo.
    Este endpoint lo vamos a usar para la pantalla de detalles.
    """
    articulo = Articulo.query.get_or_404(articulo_id)
    data = articulo_detalle_schema.dump(articulo)
    return jsonify({"success": True, "data": data}), 200


@bp.patch("/<int:articulo_id>")
@jwt_required()
def editar_articulo(articulo_id: int):
    id_usuario = get_jwt_identity()
    try:
        id_usuario_int = int(id_usuario)
    except (TypeError, ValueError):
        raise ApiError("Token inválido", 401)

    # Admin NO puede editar/publicar artículos (bloqueo temprano)
    _reject_admin_publicar()

    articulo = Articulo.query.get_or_404(articulo_id)
    if articulo.id_propietario != id_usuario_int:
        raise ApiError("No autorizado", 403)

    payload = articulo_update_schema.load(request.json or {})

    if "titulo" in payload:
        t = str(payload.get("titulo") or "").strip()
        if not t:
            raise ApiError("El título es obligatorio", 400)
        articulo.titulo = t

    if "descripcion" in payload:
        d = str(payload.get("descripcion") or "").strip()
        if not d:
            raise ApiError("La descripción es obligatoria", 400)
        articulo.descripcion = d

    warnings: list[str] = []

    # Tarifas (compat): aceptar hora/día/ambas, pero persistir solo 1 (precio_base+unidad_precio).
    if ("precio_renta_dia" in payload) or ("precio_renta_hora" in payload):
        dia = payload.get("precio_renta_dia")
        hora = payload.get("precio_renta_hora")

        def _ok(v):
            try:
                return v is not None and float(v) > 0
            except Exception:
                return False

        dia_ok = _ok(dia)
        hora_ok = _ok(hora)
        if not dia_ok and not hora_ok:
            raise ApiError("Debes indicar un precio por día y/o por hora.", 400)

        unit_hint = str(payload.get("unidad_precio") or "").strip().lower() or None
        if unit_hint not in ("por_hora", "por_dia", "por_semana"):
            unit_hint = None

        selected_unit: str | None = None
        if dia_ok and hora_ok:
            selected_unit = unit_hint if unit_hint in ("por_hora", "por_dia") else (articulo.unidad_precio if articulo.unidad_precio in ("por_hora", "por_dia") else "por_dia")
            warnings.append(
                "Tu base actual soporta 1 modalidad por artículo. Se guardó solo la modalidad principal."
            )
        elif hora_ok:
            selected_unit = "por_hora"
        else:
            selected_unit = "por_dia"

        selected_price = hora if selected_unit == "por_hora" else dia
        if selected_price is None:
            selected_price = dia if dia_ok else hora

        articulo.unidad_precio = selected_unit
        articulo.precio_base = selected_price

    if "deposito_garantia" in payload:
        articulo.monto_deposito = payload.get("deposito_garantia")

    if "estado_publicacion" in payload:
        articulo.estado_publicacion = payload.get("estado_publicacion")

    db.session.add(articulo)
    db.session.commit()

    resp = {"success": True, "data": articulo_detalle_schema.dump(articulo)}
    if warnings:
        resp["warnings"] = warnings
    return jsonify(resp), 200


@bp.get("/<int:articulo_id>/ocupacion")
def ocupacion_articulo(articulo_id: int):
    """Devuelve rangos ocupados (fechas/horas) para mostrar disponibilidad visible."""

    articulo = Articulo.query.get_or_404(articulo_id)

    desde = request.args.get("desde")
    hasta = request.args.get("hasta")
    if not desde or not hasta:
        raise ApiError("Parámetros requeridos: desde, hasta (YYYY-MM-DD).", 400)

    try:
        d0 = datetime.fromisoformat(str(desde).strip())
        d1 = datetime.fromisoformat(str(hasta).strip())
    except Exception:
        raise ApiError("Formato inválido. Usa YYYY-MM-DD.", 400)

    desde_dt = datetime(d0.year, d0.month, d0.day)
    hasta_dt = datetime(d1.year, d1.month, d1.day) + timedelta(days=1)
    if hasta_dt <= desde_dt:
        raise ApiError("Rango inválido.", 400)

    ocupado = renta_service.listar_ocupacion_articulo(articulo.id_articulo, desde_dt, hasta_dt)
    return jsonify({"success": True, "data": {"ocupado": ocupado}}), 200
