"""Integration tests for FastAPI evaluation endpoints."""

import asyncio
import httpx
import pytest

from backend.app.main import app


def test_post_evaluation_endpoint_success() -> None:
    """Verify POST /api/v1/evaluation returns complete report with 200 OK."""
    async def run_eval() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/v1/evaluation",
                json={
                    "location": "taman-kamal",
                    "pollutant": "co",
                    "scenario": "scenario_1",
                    "algorithm": "xgboost",
                },
            )

    response = asyncio.run(run_eval())
    assert response.status_code == 200
    data = response.json()

    assert data["experiment_id"] == "taman-kamal__co__scenario_1__xgboost"
    assert data["location"] == "taman-kamal"
    assert data["pollutant"] == "co"
    assert "metrics" in data
    assert data["metrics"]["mae"] > 0
    assert data["metrics"]["r2"] > 0
    assert "comparison" in data
    assert data["comparison"]["counterpart_algorithm"] == "lightgbm"
    assert "chart_data" in data
    assert len(data["chart_data"]["timestamps"]) > 0


def test_post_evaluation_sliced_date_range() -> None:
    """Verify POST /api/v1/evaluation with datetime range slices properly."""
    async def run_eval() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/v1/evaluation",
                json={
                    "location": "cibinong",
                    "pollutant": "co2",
                    "scenario": "scenario_2",
                    "algorithm": "lightgbm",
                    "start_datetime": "2026-07-01T00:00:00+07:00",
                    "end_datetime": "2026-07-15T00:00:00+07:00",
                },
            )

    response = asyncio.run(run_eval())
    assert response.status_code == 200
    data = response.json()

    assert data["algorithm"] == "lightgbm"
    assert data["pollutant_unit"] == "ppm"
    assert data["time_range"]["evaluated_samples"] < data["time_range"]["total_test_samples"]


def test_post_evaluation_invalid_date_range_returns_400() -> None:
    """Verify out-of-range date filter returns 400 Bad Request."""
    async def run_eval() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/v1/evaluation",
                json={
                    "location": "taman-kamal",
                    "pollutant": "co",
                    "scenario": "scenario_1",
                    "algorithm": "xgboost",
                    "start_datetime": "2020-01-01T00:00:00+07:00",
                    "end_datetime": "2020-01-05T00:00:00+07:00",
                },
            )

    response = asyncio.run(run_eval())
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_EVALUATION_REQUEST"


def test_get_evaluation_range_endpoint() -> None:
    """Verify GET /api/v1/evaluation/range returns temporal bounds."""
    async def get_range() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/api/v1/evaluation/range?location=taman-kamal&pollutant=co")

    response = asyncio.run(get_range())
    assert response.status_code == 200
    data = response.json()

    assert "start" in data
    assert "end" in data
    assert data["total_samples"] == 3506
