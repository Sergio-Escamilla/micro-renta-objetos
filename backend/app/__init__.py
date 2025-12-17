import pymysql
pymysql.install_as_MySQLdb()
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

    # Habilitar CORS para el frontend Angular (localhost:4200)
    # Si quieres permitir cualquier origen en desarrollo, cambia origins por "*"
    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:4200"}},
        supports_credentials=True,
    )

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

    @app.get("/uploads/articulos/<path:filename>")
    def servir_upload_articulo(filename: str):
        return send_from_directory(app.config["UPLOADS_ARTICULOS_DIR"], filename)

    return app
