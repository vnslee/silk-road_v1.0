#!/usr/bin/env python3
"""
ruleset API 테스트 (U21, PS1).

조회·저장·합≠100 거부. 저장은 internal_latest 를 건드리므로 원본 백업·복원.

실행: .venv/bin/python -m pytest test_api_ruleset.py -v
"""

import json

from fastapi.testclient import TestClient

from main import app
from services import storage

client = TestClient(app)
API = "/api/v1"


def setup_function():
    # 원본 백업
    setup_function._orig = storage.INTERNAL_LATEST.read_text(encoding="utf-8")


def teardown_function():
    storage.INTERNAL_LATEST.write_text(setup_function._orig, encoding="utf-8")


def test_get_ruleset():
    r = client.get(f"{API}/ruleset")
    assert r.status_code == 200
    d = r.json()
    assert "biz_attractiveness" in d and "it_readiness" in d
    assert "w_biz" in d["report_blend"] and "w_it" in d["report_blend"]


def test_put_blend_ok():
    r = client.put(f"{API}/ruleset/blend", json={"w_biz": 0.7, "w_it": 0.3})
    assert r.status_code == 200
    saved = json.loads(storage.INTERNAL_LATEST.read_text(encoding="utf-8"))
    assert saved["values"]["report_blend"] == {"w_biz": 0.7, "w_it": 0.3}


def test_put_blend_sum_not_1_rejected():
    r = client.put(f"{API}/ruleset/blend", json={"w_biz": 0.7, "w_it": 0.5})  # 합 1.2
    assert r.status_code == 400
    assert "1.0" in r.json()["detail"]


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
