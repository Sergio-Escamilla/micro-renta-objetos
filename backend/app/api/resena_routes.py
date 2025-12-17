from flask import Blueprint
from app.utils.responses import success_response

bp = Blueprint("resenas", __name__)


@bp.get("/ping")
def ping_resenas():
    return success_response(message="resenas ok")
