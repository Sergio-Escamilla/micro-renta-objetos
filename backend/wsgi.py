import os

from app import create_app
from app.config import DevConfig, ProdConfig


def _running_on_railway() -> bool:
    return any(
        os.getenv(k)
        for k in (
            "RAILWAY_PROJECT_ID",
            "RAILWAY_SERVICE_ID",
            "RAILWAY_ENVIRONMENT_ID",
            "RAILWAY_ENVIRONMENT",
        )
    )


config = ProdConfig if _running_on_railway() else DevConfig
app = create_app(config)

if __name__ == "__main__":
    app.run()
