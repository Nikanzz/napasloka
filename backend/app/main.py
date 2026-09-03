"""FastAPI application factory for the Phase 0 backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import config, evaluation, health, interpretation, prediction


def create_app() -> FastAPI:
    """Create and configure the NapasLoka API."""

    application = FastAPI(
        title="NapasLoka API",
        version="0.1.0",
        description="Research artifact API; scientific prediction is unavailable in Phase 0.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    for router in (
        health.router,
        config.router,
        prediction.router,
        evaluation.router,
        interpretation.router,
    ):
        application.include_router(router, prefix="/api/v1")
    return application


app = create_app()
