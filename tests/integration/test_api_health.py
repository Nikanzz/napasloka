"""FastAPI health endpoint contract."""

import asyncio

import httpx

from backend.app.main import app


def test_health_endpoint_returns_ok() -> None:
    async def get_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/api/v1/health")

    response = asyncio.run(get_health())
    assert response.status_code == 200
    assert response.json()["status"] == "OK"
