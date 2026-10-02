"""Integration tests for FastAPI config and options endpoints."""

import asyncio
import httpx
import pytest

from backend.app.main import app


def test_root_endpoint() -> None:
    """Verify root endpoint returns API identification."""
    async def get_root() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/")

    response = asyncio.run(get_root())
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Sistem NapasLoka"
    assert data["status"] == "online"


def test_config_options_endpoint() -> None:
    """Verify /api/v1/config/options returns all required dimensions."""
    async def get_options() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/api/v1/config/options")

    response = asyncio.run(get_options())
    assert response.status_code == 200
    data = response.json()

    assert "locations" in data
    assert len(data["locations"]) == 15
    assert "pollutants" in data
    assert len(data["pollutants"]) == 2
    assert "scenarios" in data
    assert len(data["scenarios"]) == 2
    assert "algorithms" in data
    assert len(data["algorithms"]) == 2
    assert "evaluation_range" in data
    assert "start" in data["evaluation_range"]
    assert "end" in data["evaluation_range"]


def test_models_summary_endpoint() -> None:
    """Verify /api/v1/config/models returns 120 completed models."""
    async def get_models() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/api/v1/config/models")

    response = asyncio.run(get_models())
    assert response.status_code == 200
    data = response.json()

    assert data["total_experiments"] == 120
    assert data["completed_experiments"] == 120
    assert data["ready_ratio"] == 100.0
    assert len(data["models"]) == 120
