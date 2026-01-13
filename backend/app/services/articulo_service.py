from typing import Dict, Any, List, Optional

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Articulo, ArticuloImagen, Categoria, Usuario
from app.utils.errors import ApiError


def _articulo_to_dict(articulo: Articulo, incluir_propietario: bool = True) -> Dict[str, Any]:
    imagenes = [
        {
            "id": img.id,
            "url_imagen": img.url_imagen,
            "es_principal": img.es_principal,
            "orden": img.orden,
        }
        for img in articulo.imagenes
    ]

    propietario_data = None
    if incluir_propietario and articulo.propietario:
        propietario_data = {
            "id": articulo.propietario.id,
            "nombre": articulo.propietario.nombre,
            "apellidos": articulo.propietario.apellidos,
        }

    return {
        "id": articulo.id,
        "titulo": articulo.titulo,
        "descripcion": articulo.descripcion,
        "id_categoria": articulo.id_categoria,
        "categoria": articulo.categoria.nombre if articulo.categoria else None,
        "precio_base": float(articulo.precio_base),
        "unidad_precio": articulo.unidad_precio,
        "monto_deposito": float(articulo.monto_deposito),
        "ubicacion_texto": articulo.ubicacion_texto,
        "estado": articulo.estado,
        "estado_publicacion": articulo.estado_publicacion,
        "es_destacado": articulo.es_destacado,
        "vistas": articulo.vistas,
        "fecha_creacion": articulo.fecha_creacion.isoformat() if articulo.fecha_creacion else None,
        "fecha_actualizacion": articulo.fecha_actualizacion.isoformat() if articulo.fecha_actualizacion else None,
        "imagenes": imagenes,
        "propietario": propietario_data,
    }


def crear_articulo(data: Dict[str, Any], id_propietario: int) -> Dict[str, Any]:
    # validar que el propietario existe
    propietario = Usuario.query.get(id_propietario)
    if not propietario:
        raise ApiError("Propietario no encontrado", 404)

    # validar que la categoría existe
    categoria = Categoria.query.get(data["id_categoria"])
    if not categoria or not categoria.activa:
        raise ApiError("Categoría inválida", 400)

    articulo = Articulo(
        id_propietario=id_propietario,
        titulo=data["titulo"].strip(),
        descripcion=data["descripcion"].strip(),
        id_categoria=data["id_categoria"],
        precio_base=data["precio_base"],
        unidad_precio=data.get("unidad_precio", "por_dia"),
        monto_deposito=data.get("monto_deposito", 0.0),
        ubicacion_texto=data.get("ubicacion_texto"),
        estado=data.get("estado"),
        estado_publicacion="borrador",  # luego se puede publicar
        es_destacado=data.get("es_destacado", False),
    )

    db.session.add(articulo)
    db.session.flush()  # para tener articulo.id

    urls = data.get("urls_imagenes") or []
    for idx, url in enumerate(urls):
        img = ArticuloImagen(
            id_articulo=articulo.id,
            url_imagen=url,
            es_principal=(idx == 0),
            orden=idx,
        )
        db.session.add(img)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("Error al crear el artículo", 500)

    return _articulo_to_dict(articulo)


def obtener_articulo(articulo_id: int) -> Optional[Dict[str, Any]]:
    articulo = Articulo.query.get(articulo_id)
    if not articulo or articulo.estado_publicacion == "eliminado":
        return None
    return _articulo_to_dict(articulo)


def actualizar_articulo(
    articulo_id: int, id_propietario: int, data: Dict[str, Any]
) -> Dict[str, Any]:
    articulo = Articulo.query.get(articulo_id)
    if not articulo or articulo.estado_publicacion == "eliminado":
        raise ApiError("Artículo no encontrado", 404)

    if articulo.id_propietario != id_propietario:
        raise ApiError("No tienes permiso para modificar este artículo", 403)

    if "titulo" in data:
        articulo.titulo = data["titulo"].strip()
    if "descripcion" in data:
        articulo.descripcion = data["descripcion"].strip()
    if "id_categoria" in data:
        categoria = Categoria.query.get(data["id_categoria"])
        if not categoria or not categoria.activa:
            raise ApiError("Categoría inválida", 400)
        articulo.id_categoria = data["id_categoria"]
    if "precio_base" in data:
        articulo.precio_base = data["precio_base"]
    if "unidad_precio" in data:
        articulo.unidad_precio = data["unidad_precio"]
    if "monto_deposito" in data:
        articulo.monto_deposito = data["monto_deposito"]
    if "ubicacion_texto" in data:
        articulo.ubicacion_texto = data["ubicacion_texto"]
    if "estado" in data:
        articulo.estado = data["estado"]
    if "estado_publicacion" in data:
        articulo.estado_publicacion = data["estado_publicacion"]
    if "es_destacado" in data:
        articulo.es_destacado = data["es_destacado"]

    if "urls_imagenes" in data and data["urls_imagenes"] is not None:
        # reemplazar imágenes
        articulo.imagenes.clear()
        db.session.flush()
        for idx, url in enumerate(data["urls_imagenes"]):
            img = ArticuloImagen(
                id_articulo=articulo.id,
                url_imagen=url,
                es_principal=(idx == 0),
                orden=idx,
            )
            db.session.add(img)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("Error al actualizar el artículo", 500)

    return _articulo_to_dict(articulo)


def eliminar_articulo(articulo_id: int, id_propietario: int) -> None:
    articulo = Articulo.query.get(articulo_id)
    if not articulo or articulo.estado_publicacion == "eliminado":
        raise ApiError("Artículo no encontrado", 404)
    if articulo.id_propietario != id_propietario:
        raise ApiError("No tienes permiso para eliminar este artículo", 403)

    articulo.estado_publicacion = "eliminado"

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("Error al eliminar el artículo", 500)


def listar_articulos_publicos(filtros: Dict[str, Any]) -> Dict[str, Any]:
    query = Articulo.query.filter(Articulo.estado_publicacion == "publicado")

    if filtros.get("id_categoria"):
        query = query.filter(Articulo.id_categoria == filtros["id_categoria"])
    if filtros.get("texto"):
        texto = f"%{filtros['texto']}%"
        query = query.filter(
            or_(Articulo.titulo.ilike(texto), Articulo.descripcion.ilike(texto))
        )
    if filtros.get("precio_min") is not None:
        query = query.filter(Articulo.precio_base >= filtros["precio_min"])
    if filtros.get("precio_max") is not None:
        query = query.filter(Articulo.precio_base <= filtros["precio_max"])
    if filtros.get("solo_destacados"):
        query = query.filter(Articulo.es_destacado.is_(True))

    page = max(int(filtros.get("page", 1)), 1)
    per_page = min(max(int(filtros.get("per_page", 10)), 1), 50)

    total = query.count()
    items: List[Articulo] = (
        query.order_by(Articulo.fecha_creacion.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "items": [_articulo_to_dict(a) for a in items],
    }


def listar_mis_articulos(id_propietario: int) -> List[Dict[str, Any]]:
    query = Articulo.query.filter(
        Articulo.id_propietario == id_propietario,
        Articulo.estado_publicacion != "eliminado",
    ).order_by(Articulo.fecha_creacion.desc())

    return [_articulo_to_dict(a, incluir_propietario=False) for a in query.all()]
