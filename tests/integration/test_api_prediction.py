"""Integration tests for FastAPI prediction endpoints."""

import asyncio
import httpx
import pytest

from backend.app.main import app


def test_post_prediction_endpoint_success():
    """Verify POST /api/v1/predict returns 200 OK with complete prediction report."""
    async def run_predict() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/v1/predict",
                json={
                    "location": "taman-kamal",
                    "pollutant": "co",
                    "scenario": "scenario_1",
                    "algorithm": "xgboost",
                },
            )

    response = asyncio.run(run_predict())
    assert response.status_code == 200
    data = response.json()

    assert data["experiment_id"] == "taman-kamal__co__scenario_1__xgboost"
    assert data["location"] == "taman-kamal"
    assert data["pollutant"] == "co"
    assert data["predicted_value"] > 0
    assert "target_time" in data
    assert "latest_observation_value" in data
    assert "feature_inputs" in data
    assert len(data["feature_inputs"]) == 3
    assert data["counterpart_algorithm"] == "lightgbm"
    assert data["counterpart_predicted_value"] is not None


def test_post_prediction_scenario_2_endpoint():
    """Verify POST /api/v1/predict returns 15 feature inputs for Scenario 2."""
    async def run_predict() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/v1/predict",
                json={
                    "location": "cibinong",
                    "pollutant": "co2",
                    "scenario": "scenario_2",
                    "algorithm": "lightgbm",
                },
            )

    response = asyncio.run(run_predict())
    assert response.status_code == 200
    data = response.json()

    assert data["scenario"] == "scenario_2"
    assert data["pollutant"] == "co2"
    assert len(data["feature_inputs"]) == 15


def test_post_prediction_invalid_location_returns_400():
    """Verify invalid location input returns 400 Bad Request."""
    async def run_predict() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/v1/predict",
                json={
                    "location": "unknown-city",
                    "pollutant": "co",
                    "scenario": "scenario_1",
                    "algorithm": "xgboost",
                },
            )

    response = asyncio.run(run_predict())
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_PREDICTION_REQUEST"
