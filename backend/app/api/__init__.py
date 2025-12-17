from .auth_routes import bp as auth_bp
from .usuario_routes import bp as usuarios_bp
from .articulo_routes import bp as articulos_bp
from .categoria_routes import bp as categorias_bp
from .renta_routes import bp as rentas_bp
from .pago_routes import bp as pagos_bp
from .incidente_routes import bp as incidentes_bp
from .resena_routes import bp as resenas_bp
from .notificacion_routes import bp as notificaciones_bp
from .admin_routes import bp as admin_bp
from .punto_entrega_routes import bp as puntos_entrega_bp

__all__ = [
    "auth_bp",
    "usuarios_bp",
    "articulos_bp",
    "categorias_bp",
    "rentas_bp",
    "pagos_bp",
    "incidentes_bp",
    "resenas_bp",
    "notificaciones_bp",
    "admin_bp",
    "puntos_entrega_bp",
]
