#!/usr/bin/env python3
"""
main.py API 골격 테스트 (U7).

FastAPI TestClient(httpx 기반)로 /health 200 확인.

실행: .venv/bin/python -m pytest test_main.py -v
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "silk-road"


def test_cors_header_present():
    """CORS 미들웨어가 동작하는지(개발용 전체 허용)."""
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "*"
