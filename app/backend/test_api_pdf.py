#!/usr/bin/env python3
"""
보고서 PDF 제공 테스트 (U10).

weasyprint 는 시스템 라이브러리 의존이라 환경에 따라 동작/불가가 갈린다:
  - 사용 가능: 200 + application/pdf + %PDF 매직바이트.
  - 불가: 503 (graceful, HTML/JSON 은 영향 없음).
둘 중 어느 쪽이든 "에러 없이 정의된 응답"이면 통과로 본다.
HTML 없는 보고서는 404.

실행(PDF 실제 생성하려면 macOS):
  DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/python -m pytest test_api_pdf.py -v
"""

import shutil

from fastapi.testclient import TestClient

from main import app
from services import storage

client = TestClient(app)
API = "/api/v1"

# U8 픽스처: RPT_CTR_ES_001 (HTML 포함 생성돼 있음)
FIXTURE = ("country", "ES", "RPT_CTR_ES_001")


def test_pdf_returns_pdf_or_503():
    kind, code, rid = FIXTURE
    r = client.get(f"{API}/reports/{kind}/{code}/{rid}/pdf")
    assert r.status_code in (200, 503), r.text
    if r.status_code == 200:
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-", "PDF 매직바이트 아님"
        assert len(r.content) > 1000, "PDF 가 너무 작음"
        # 캐시 파일 정리
        pdf_dir = storage.REPORT_BASE / kind / code / rid / "pdf"
        shutil.rmtree(pdf_dir, ignore_errors=True)
    else:
        # 503 이면 안내 메시지 포함
        assert "weasyprint" in r.json()["detail"].lower()


def test_pdf_missing_html_404():
    """HTML 없는 report_id → 404."""
    r = client.get(f"{API}/reports/country/ES/RPT_CTR_ES_999/pdf")
    assert r.status_code == 404


def test_pdf_unknown_kind_404():
    assert client.get(f"{API}/reports/planet/ES/X/pdf").status_code == 404


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
