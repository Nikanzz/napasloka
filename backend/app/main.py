"""FastAPI application factory for the Sistem NapasLoka backend."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

    # Mount static assets for frontend PWA
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
    if frontend_dir.is_dir():
        application.mount("/pages", StaticFiles(directory=str(frontend_dir / "pages")), name="pages")
        application.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")
        application.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
        application.mount("/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")

        @application.get("/app", include_in_schema=False)
        @application.get("/index.html", include_in_schema=False)
        def serve_app() -> FileResponse:
            """Serve PWA Home page."""
            return FileResponse(frontend_dir / "index.html")

        @application.get("/manifest.json", include_in_schema=False)
        def serve_manifest() -> FileResponse:
            """Serve PWA manifest."""
            return FileResponse(frontend_dir / "manifest.json")

        @application.get("/service-worker.js", include_in_schema=False)
        def serve_sw() -> FileResponse:
            """Serve PWA service worker."""
            return FileResponse(frontend_dir / "service-worker.js")

    @application.get("/", tags=["root"])
    def root() -> dict[str, str]:
        """Root endpoint returning API service identification."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "online",
            "docs_url": "/docs",
            "app_url": "/app",
        }

    return application


app = create_app()
