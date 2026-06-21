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
    assert set(d["category_weights"]) == {"market", "finance", "regulation", "system"}
    assert d["category_labels"]["market"] == "시장"


def test_put_weights_ok():
    new = {"market": 30, "finance": 30, "regulation": 20, "system": 20}
    r = client.put(f"{API}/ruleset/weights", json={"category_weights": new})
    assert r.status_code == 200
    # 실제 파일에 반영됐는지
    saved = json.loads(storage.INTERNAL_LATEST.read_text(encoding="utf-8"))
    assert saved["weights"]["category_weights"] == new


def test_put_weights_sum_not_100_rejected():
    bad = {"market": 50, "finance": 30, "regulation": 20, "system": 20}  # 합 120
    r = client.put(f"{API}/ruleset/weights", json={"category_weights": bad})
    assert r.status_code == 400
    assert "합" in r.json()["detail"]


def test_put_weights_bad_keys_rejected():
    bad = {"market": 50, "finance": 50}  # 키 누락
    r = client.put(f"{API}/ruleset/weights", json={"category_weights": bad})
    assert r.status_code == 400


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
