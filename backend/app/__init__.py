import pymysql
pymysql.install_as_MySQLdb()
import os
from sqlalchemy import text
from flask import Flask, send_from_directory
from flask_cors import CORS
from pathlib import Path

from .config import DevConfig
from .extensions import db, migrate, jwt, ma, bcrypt
from .utils.errors import register_error_handlers
from .api import (
    auth_routes,
    usuario_routes,
    articulo_routes,
    categoria_routes,
    renta_routes,
    pago_routes,
    incidente_routes,
    resena_routes,
    notificacion_routes,
    punto_entrega_routes,
    admin_routes,
)


def create_app(config_class=DevConfig) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Carpeta para uploads (imágenes de artículos)
    uploads_articulos_dir = (Path(app.root_path).parent / "uploads" / "articulos").resolve()
    uploads_articulos_dir.mkdir(parents=True, exist_ok=True)
    app.config["UPLOADS_ARTICULOS_DIR"] = str(uploads_articulos_dir)

    # CORS
    # - Dev (por defecto): http://localhost:4200
    # - Prod (Railway): define CORS_ORIGINS (comma-separated) o FRONTEND_BASE_URL
    raw_origins = os.getenv("CORS_ORIGINS")
    if raw_origins:
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        if len(origins) == 1:
            origins = origins[0]
    else:
        origins = app.config.get("FRONTEND_BASE_URL") or "http://localhost:4200"

    supports_credentials = origins != "*"
    CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=supports_credentials)

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    bcrypt.init_app(app)

    # Registrar blueprints
    app.register_blueprint(auth_routes.bp, url_prefix="/api/auth")
    app.register_blueprint(usuario_routes.bp, url_prefix="/api/usuarios")
    app.register_blueprint(articulo_routes.bp, url_prefix="/api/articulos")
    app.register_blueprint(categoria_routes.bp, url_prefix="/api/categorias")
    app.register_blueprint(renta_routes.bp, url_prefix="/api/rentas")
    app.register_blueprint(pago_routes.bp, url_prefix="/api/pagos")
    app.register_blueprint(incidente_routes.bp, url_prefix="/api/incidentes")
    app.register_blueprint(resena_routes.bp, url_prefix="/api/resenas")
    app.register_blueprint(notificacion_routes.bp, url_prefix="/api/notificaciones")
    app.register_blueprint(punto_entrega_routes.bp, url_prefix="/api")
    app.register_blueprint(admin_routes.bp, url_prefix="/api/admin")

    # Manejadores de errores
    register_error_handlers(app)

    @app.get("/api/health")
    def health_check():
        return {"status": "ok", "service": "micro-renta-backend"}

    @app.get("/api/db-health")
    def db_health_check():
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok", "db": "ok"}, 200
        except Exception as e:
            # No exponer credenciales; solo el tipo de error y mensaje.
            return {
                "status": "error",
                "db": "error",
                "error_type": e.__class__.__name__,
                "error": str(e),
            }, 500

    @app.get("/uploads/articulos/<path:filename>")
    def servir_upload_articulo(filename: str):
        return send_from_directory(app.config["UPLOADS_ARTICULOS_DIR"], filename)

    return app
