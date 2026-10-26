"""Integration tests for FastAPI interpretation endpoints."""

import asyncio
import httpx
import pytest

from backend.app.main import app


def test_post_interpretation_endpoint_success():
    """Verify POST /api/v1/interpretation returns 200 OK with SHAP explanation."""
    async def run_interpret() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/v1/interpretation",
                json={
                    "location": "taman-kamal",
                    "pollutant": "co",
                    "scenario": "scenario_1",
                    "algorithm": "xgboost",
                },
            )

    response = asyncio.run(run_interpret())
    assert response.status_code == 200
    data = response.json()

    assert data["experiment_id"] == "taman-kamal__co__scenario_1__xgboost"
    assert data["location"] == "taman-kamal"
    assert data["pollutant"] == "co"
    assert "base_value" in data
    assert "top_contributor" in data
    assert "local_contributions" in data
    assert len(data["local_contributions"]) == 3
    assert "chart_series" in data
    assert "scientific_disclaimer" in data
    assert "BUKAN merupakan bukti hubungan kausalitas" in data["scientific_disclaimer"]


def test_post_interpretation_scenario_2_endpoint():
    """Verify POST /api/v1/interpretation returns all 15 features for Scenario 2."""
    async def run_interpret() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/v1/interpretation",
                json={
                    "location": "cibinong",
                    "pollutant": "co2",
                    "scenario": "scenario_2",
                    "algorithm": "lightgbm",
                    "top_k": 5,
                },
            )

    response = asyncio.run(run_interpret())
    assert response.status_code == 200
    data = response.json()

    assert data["scenario"] == "scenario_2"
    assert data["pollutant"] == "co2"
    assert len(data["local_contributions"]) == 15
    assert len(data["chart_series"]["features"]) == 5


def test_post_interpretation_invalid_location_returns_400():
    """Verify invalid location returns 400 Bad Request."""
    async def run_interpret() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/v1/interpretation",
                json={
                    "location": "invalid-location",
                    "pollutant": "co",
                    "scenario": "scenario_1",
                    "algorithm": "xgboost",
                },
            )

    response = asyncio.run(run_interpret())
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_INTERPRETATION_REQUEST"
