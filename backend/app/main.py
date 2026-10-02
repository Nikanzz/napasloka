"""FastAPI application factory for the Sistem NapasLoka backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import config, evaluation, health, interpretation, prediction
from backend.app.core.config import settings


def create_app() -> FastAPI:
    """Create and configure the Sistem NapasLoka API."""

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Backend API untuk Sistem NapasLoka: Prediksi dan Evaluasi Kualitas Udara (CO dan CO2) "
            "1 Jam ke Depan pada 15 Lokasi Jabodetabek menggunakan XGBoost dan LightGBM."
        ),
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API Routers
    for router in (
        health.router,
        config.router,
        prediction.router,
        evaluation.router,
        interpretation.router,
    ):
        application.include_router(router, prefix=settings.api_v1_prefix)

    @application.get("/", tags=["root"])
    def root() -> dict[str, str]:
        """Root endpoint returning API service identification."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "online",
            "docs_url": "/docs",
        }

    return application


app = create_app()
