from flask import Blueprint, jsonify

from app.models.categoria import Categoria


bp = Blueprint("categoria_routes", __name__)


@bp.get("")
def listar_categorias():
    categorias = Categoria.query.order_by(Categoria.nombre.asc()).all()
    data = [{"id": c.id, "nombre": c.nombre} for c in categorias]
    return jsonify({"success": True, "data": data}), 200
