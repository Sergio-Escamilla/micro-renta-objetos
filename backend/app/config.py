import os
from datetime import timedelta

from dotenv import load_dotenv

# Cargar variables desde .env
base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.join(base_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)


class BaseConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:password@localhost:3306/micro_renta"
    )
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
