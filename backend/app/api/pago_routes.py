from flask import Blueprint
from app.utils.responses import success_response

bp = Blueprint("pagos", __name__)


@bp.get("/ping")
def ping_pagos():
    return success_response(message="pagos ok")
