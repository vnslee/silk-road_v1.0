#!/usr/bin/env python3
"""
조회 API 회귀 테스트 (U8).

각 엔드포인트 200 + 응답 스키마, 없는 코드 404.
픽스처: ES(country research + RPT_CTR_ES_001 보고서), EU(region), PL(구버전 보고서).

실행: .venv/bin/python -m pytest test_api_query.py -v
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
API = "/api/v1"


# ── countries ─────────────────────────────────────────────────────────────
def test_list_countries():
    r = client.get(f"{API}/countries")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list) and items
    es = next((c for c in items if c["code"] == "ES"), None)
    assert es is not None and es["has_data"] is True
    # GB 는 EU 기준국·운영중 → is_entered True, is_baseline True
    gb = next((c for c in items if c["code"] == "GB"), None)
    assert gb is not None
    assert gb["is_entered"] is True and gb["is_baseline"] is True


def test_get_country_es():
    r = client.get(f"{API}/countries/ES")
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == "ES" and d["schema_version"] == "1.1"


def test_get_country_lowercase_normalized():
    """소문자 코드도 정규화되어 조회."""
    assert client.get(f"{API}/countries/es").status_code == 200


def test_get_country_404():
    assert client.get(f"{API}/countries/ZZ").status_code == 404


# ── regions ─────────────────────────────────────────────────────────────--
def test_list_regions():
    r = client.get(f"{API}/regions")
    assert r.status_code == 200
    items = r.json()
    eu = next((x for x in items if x["region"] == "EU"), None)
    assert eu is not None
    assert eu["baseline"] == "GB"
    assert "ES" in eu["members_with_data"]


def test_get_region_404():
    assert client.get(f"{API}/regions/ZZZ").status_code == 404


# ── reports ─────────────────────────────────────────────────────────────--
def test_list_reports_country_es():
    r = client.get(f"{API}/reports/country/ES")
    assert r.status_code == 200
    reports = r.json()
    assert any(rep["report_id"] == "RPT_CTR_ES_001" for rep in reports), reports


def test_get_report_detail():
    r = client.get(f"{API}/reports/country/ES/RPT_CTR_ES_001")
    assert r.status_code == 200
    d = r.json()
    assert d["report_id"] == "RPT_CTR_ES_001"
    assert "tabs" in d


def test_get_report_html():
    r = client.get(f"{API}/reports/country/ES/RPT_CTR_ES_001/html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "masthead" in r.text


def test_report_unknown_kind_404():
    assert client.get(f"{API}/reports/planet/ES").status_code == 404


def test_report_missing_404():
    assert client.get(f"{API}/reports/country/ES/RPT_CTR_ES_999").status_code == 404


def test_list_reports_legacy_pl():
    """구버전 PL 보고서(data/ 직접)도 목록에 잡힌다."""
    r = client.get(f"{API}/reports/country/PL")
    assert r.status_code == 200
    reports = r.json()
    assert any(rep["legacy"] for rep in reports), reports


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
