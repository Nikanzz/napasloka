"""Integration tests for PWA static files, routes, service worker, and web pages."""

import json
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_serve_app_and_index():
    """Verify that /app and /index.html return the PWA entry point."""
    resp_app = client.get("/app")
    assert resp_app.status_code == 200
    assert "text/html" in resp_app.headers["content-type"]
    assert "Sistem NapasLoka" in resp_app.text or "NapasLoka" in resp_app.text

    resp_index = client.get("/index.html")
    assert resp_index.status_code == 200
    assert resp_index.text == resp_app.text


def test_serve_manifest_json():
    """Verify that /manifest.json returns valid PWA manifest metadata."""
    resp = client.get("/manifest.json")
    assert resp.status_code == 200
    manifest = json.loads(resp.text)
    assert manifest["name"] == "Sistem NapasLoka"
    assert manifest["short_name"] == "NapasLoka"
    assert manifest["display"] == "standalone"
    assert len(manifest["icons"]) >= 1


def test_serve_service_worker():
    """Verify that /service-worker.js is served with precached assets."""
    resp = client.get("/service-worker.js")
    assert resp.status_code == 200
    assert "napasloka-v1.0.0" in resp.text
    assert "/pages/interpretation.html" in resp.text
    assert "/pages/evaluation.html" in resp.text
    assert "/pages/prediction.html" in resp.text


def test_serve_all_frontend_pages():
    """Verify that all core dashboard pages exist and return valid HTML."""
    pages = [
        ("/pages/prediction.html", "Konfigurasi Prediksi"),
        ("/pages/evaluation.html", "Grafik dan Evaluasi"),
        ("/pages/interpretation.html", "Lihat alasan di balik keluaran model."),
        ("/pages/information.html", "Informasi"),
    ]
    for url, keyword in pages:
        resp = client.get(url)
        assert resp.status_code == 200, f"Page {url} failed with status {resp.status_code}"
        assert keyword in resp.text, f"Keyword '{keyword}' not found in {url}"


def test_serve_static_scripts_and_styles():
    """Verify that stylesheets and JavaScript modules are reachable."""
    assets = [
        ("/css/main.css", "--color-primary"),
        ("/css/components.css", "shap-item-row"),
        ("/js/api.js", "NapasLokaApi"),
        ("/js/app.js", "serviceWorker"),
        ("/js/home.js", "quickConfigBtn"),
        ("/js/prediction.js", "prediction-form"),
        ("/js/evaluation.js", "plotly-evaluation-chart"),
        ("/js/interpretation.js", "loadInterpretation"),
    ]
    for url, keyword in assets:
        resp = client.get(url)
        assert resp.status_code == 200, f"Asset {url} returned status {resp.status_code}"
        assert keyword in resp.text, f"Keyword '{keyword}' not found in {url}"
