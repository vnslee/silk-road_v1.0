#!/usr/bin/env python3
"""
validate_data 회귀 테스트.

- 정상 픽스처(실제 ES + internal_latest)는 PASS.
- 고의로 오염시킨 픽스처 3종은 각각 FAIL 을 검출해야 한다:
    (a) category_weights 합 ≠ 100
    (b) tier = 5 (범위 밖)
    (c) NEWS publisher 가 화이트리스트 밖
"""

import copy
import json
from pathlib import Path

import validate_data as V


# ── 정상 픽스처 PASS ──────────────────────────────────────────────────────
def test_real_data_passes():
    """존재하는 country 전부 + internal 이 PASS 여야 한다."""
    ok, report = V.run()
    assert ok, f"실데이터 검증 실패:\n{report}"


def _load_es():
    p = V.COUNTRY_DIR / "ES" / "ES_latest.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _load_internal():
    return json.loads(V.INTERNAL_LATEST.read_text(encoding="utf-8"))


# ── 오염 (b) tier = 5 ─────────────────────────────────────────────────────
def test_tier_out_of_range_fails():
    data = _load_es()
    # 첫 item 의 tier 를 5 로 오염
    data["items"][0]["tier"] = 5
    errs = V.validate_country(data, label="ES_tampered")
    assert any("tier" in e for e in errs), errs


# ── 오염 (c) NEWS 화이트리스트 밖 ─────────────────────────────────────────
def test_news_publisher_off_whitelist_fails():
    data = _load_es()
    news_item = next(
        it for it in data["items"]
        if it.get("role") == "context" and it.get("context_type") == "news"
    )
    # 실제 출처가 있는(=placeholder 아닌) 객체를 골라 출처만 가짜로 교체
    target = next(
        obj for obj in news_item["value"]
        if (obj.get("so_what") or "").strip() != "조사 필요"
        and (obj.get("publisher") or "").strip() != ""
    )
    target["publisher"] = "Daily Tabloid 123"
    errs = V.validate_country(data, label="ES_tampered_news")
    assert any("화이트리스트" in e for e in errs), errs


# ── 오염 (a) category_weights 합 ≠ 100 ────────────────────────────────────
def test_category_weights_not_100_fails():
    data = _load_internal()
    cw = data["weights"]["category_weights"]
    # 한 카테고리 값을 +10 해서 합을 110 으로
    first_key = next(iter(cw))
    cw[first_key] += 10
    errs = V.validate_internal(data, label="internal_tampered")
    assert any("category_weights 합" in e for e in errs), errs


# ── 추가: gate FAIL + tier≥3 금지 규칙 ────────────────────────────────────
def test_gate_fail_with_low_tier_fails():
    data = _load_es()
    gate = next(it for it in data["items"] if it.get("role") == "gate")
    gate["tier"] = 3
    gate["gate_result"] = "FAIL"
    errs = V.validate_country(data, label="ES_tampered_gate")
    assert any("FLAG" in e for e in errs), errs


if __name__ == "__main__":
    # pytest 가 있으면 pytest 로, 없으면 standalone 으로 실행(환경 무관 회귀).
    import sys
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
        failed = 0
        for t in tests:
            try:
                t()
                print(f"PASS  {t.__name__}")
            except AssertionError as e:
                failed += 1
                print(f"FAIL  {t.__name__}: {e}")
        print(f"\n{len(tests) - failed}/{len(tests)} passed")
        sys.exit(1 if failed else 0)
