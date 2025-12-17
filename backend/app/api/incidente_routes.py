from flask import Blueprint
from app.utils.responses import success_response

bp = Blueprint("incidentes", __name__)


@bp.get("/ping")
def ping_incidentes():
    return success_response(message="incidentes ok")
