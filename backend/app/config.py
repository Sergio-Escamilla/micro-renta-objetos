import os
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "y", "on")


def _running_on_railway() -> bool:
    # Railway expone varias variables; usamos varias por compatibilidad.
    return any(
        os.getenv(k)
        for k in (
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
            "RAILWAY_ENVIRONMENT_ID",
            "RAILWAY_ENVIRONMENT",
        )
    )


def _build_database_url_from_parts() -> str | None:
    # Railway MySQL plugin suele exponer estas variables.
    host = os.getenv("MYSQLHOST")
    port = os.getenv("MYSQLPORT")
    user = os.getenv("MYSQLUSER")
    password = os.getenv("MYSQLPASSWORD")
    database = os.getenv("MYSQLDATABASE")

    if not all([host, port, user, password, database]):
        return None

    pw = quote_plus(password)
    return f"mysql+pymysql://{user}:{pw}@{host}:{port}/{database}"


def _resolve_database_url() -> str:
    # 1) Preferir DATABASE_URL si viene del entorno (Railway)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # 2) Si no, intentar construir desde variables MYSQL*
    db_url = _build_database_url_from_parts()
    if db_url:
        return db_url

    # 3) Fallback local
    return "mysql+pymysql://root:password@localhost:3306/micro_renta"


# Cargar variables desde .env SOLO en local/dev (evitar usar .env en Railway)
base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.join(base_dir, ".env")
if os.path.exists(env_path) and not _running_on_railway() and _is_truthy(os.getenv("LOAD_DOTENV", "1")):
    load_dotenv(env_path)


class BaseConfig:
    SQLALCHEMY_DATABASE_URI = _resolve_database_url()

    # ✅ FIX Railway/MySQL: evita conexiones muertas del pool y timeouts al leer resultados
    _connect_args = {
        "connect_timeout": 10,
        "read_timeout": 30,
        "write_timeout": 30,
    }

    # SSL opcional (solo si se configura explícitamente en Railway)
    # Para PyMySQL: connect_args={"ssl": {"ca": "..."}} o connect_args={"ssl": {}} para SSL por defecto.
    if _is_truthy(os.getenv("MYSQL_SSL")) or _is_truthy(os.getenv("DB_SSL")):
        ca = os.getenv("MYSQL_SSL_CA") or os.getenv("DB_SSL_CA")
        _connect_args["ssl"] = ({"ca": ca} if ca else {})

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_timeout": 30,
        "connect_args": _connect_args,
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-this")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=4)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Verificación de correo (link)
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:4200")
    EMAIL_VERIFY_TOKEN_MAX_AGE_SECONDS = int(os.getenv("EMAIL_VERIFY_TOKEN_MAX_AGE_SECONDS", "86400"))

    # Otros ajustes generales
    PROPAGATE_EXCEPTIONS = True
    JSON_SORT_KEYS = False

    # Renta: expiración de pago (lazy)
    PAGO_EXPIRA_MINUTOS = int(os.getenv("PAGO_EXPIRA_MINUTOS", "15"))

    # Chat: rate limit simple por usuario/renta (segundos)
    CHAT_RATE_LIMIT_SECONDS = int(os.getenv("CHAT_RATE_LIMIT_SECONDS", "3"))


class DevConfig(BaseConfig):
    DEBUG = True


class ProdConfig(BaseConfig):
    DEBUG = False


class TestConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:"
    )
