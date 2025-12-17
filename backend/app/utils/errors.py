from flask import jsonify
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError


class ApiError(Exception):
    """
    Excepción genérica para errores de negocio.
    """
    def __init__(self, message, status_code=400, errors=None, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.errors = errors or {}
        self.payload = payload or {}


def register_error_handlers(app):

    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        response = {
            "success": False,
            "message": err.message,
        }
        if err.errors:
            response["errors"] = err.errors
        if getattr(err, "payload", None):
            response["payload"] = err.payload

        return jsonify(response), err.status_code

    @app.errorhandler(ValidationError)
    def handle_marshmallow_validation(err: ValidationError):
        response = {
            "success": False,
            "message": "Datos inválidos",
            "errors": err.messages if hasattr(err, "messages") else str(err),
        }
        return jsonify(response), 400

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        response = {
            "success": False,
            "message": err.description or "Error HTTP",
        }
        return jsonify(response), err.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(err: Exception):
        # 🔥 Imprime la traza completa en la consola
        app.logger.exception(err)

        response = {
            "success": False,
            "message": "Error interno del servidor",
        }
        return jsonify(response), 500
