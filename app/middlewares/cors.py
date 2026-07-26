from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()


def configure_cors(app: FastAPI) -> FastAPI:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Total-Count", "X-Request-ID"],
        max_age=600,
    )
    return app
