#!/usr/bin/env python3
"""
보고서 생성 트리거 + 진행률 폴링 테스트 (U9).

TestClient 의 BackgroundTasks 는 응답 반환 직후 동기 실행되므로, POST 후 폴링하면
이미 done 상태다(완료 산출물 검증 가능). 5단계 구조·report_id·404 를 확인한다.

실행: .venv/bin/python -m pytest test_api_jobs.py -v
"""

import shutil

from fastapi.testclient import TestClient

from main import app
from services import jobs, storage

client = TestClient(app)
API = "/api/v1"


def setup_function():
    jobs.reset()


def test_trigger_country_returns_job():
    r = client.post(f"{API}/reports/country/ES")
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["job_id"].startswith("job_country_ES_")
    assert body["status"] == "pending"


def test_job_completes_with_5_steps():
    """생성 job 이 5단계 PS2 구조로 완료되고 report_id(원격 엔진 채번)를 반환한다."""
    r = client.post(f"{API}/reports/country/ES")
    job_id = r.json()["job_id"]
    j = client.get(f"{API}/jobs/{job_id}").json()
    keys = [s["key"] for s in j["steps"]]
    assert keys == ["market", "regulation", "product", "system", "result"]
    # BackgroundTask 동기 실행 완료 → done (원격 엔진 호출)
    assert j["status"] == "done", j
    assert j["progress"] == 100
    assert j["report_id"] and j["report_id"].startswith("RPT_CTR_ES_")


def test_completed_report_is_fetchable():
    """완료 job 의 report_id 로 보고서 JSON 조회 가능(end-to-end)."""
    r = client.post(f"{API}/reports/country/ES")
    job_id = r.json()["job_id"]
    rid = client.get(f"{API}/jobs/{job_id}").json()["report_id"]
    detail = client.get(f"{API}/reports/country/ES/{rid}")
    assert detail.status_code == 200
    assert detail.json()["report_id"] == rid


def test_trigger_region():
    r = client.post(f"{API}/reports/region/EU")
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    j = client.get(f"{API}/jobs/{job_id}").json()
    assert j["status"] == "done", j
    assert j["report_id"].startswith("RPT_RGN_EU_")


def test_trigger_unknown_country_404():
    assert client.post(f"{API}/reports/country/ZZ").status_code == 404


def test_trigger_unknown_kind_404():
    assert client.post(f"{API}/reports/planet/ES").status_code == 404


def test_poll_unknown_job_404():
    assert client.get(f"{API}/jobs/job_nope_0001").status_code == 404


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
