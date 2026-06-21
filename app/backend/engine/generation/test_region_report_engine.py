#!/usr/bin/env python3
"""
region_report_engine 회귀 테스트 (U4).

- 합성 권역(baseline + 후보 3국): 킬스위치 집계·매력도 순위·퀵윈 순위·상위3국 카드.
- EU 실데이터: graceful(후보 1개국, baseline 부재) — 구조는 생성되나 순위 의미 제한.
- 블록 계약(nature/source_flag) 누락 0건.

pytest 있으면 pytest, 없으면 standalone.
"""

import json
import tempfile
from pathlib import Path

import region_report_engine as R


# ── 합성 권역 데이터 ──────────────────────────────────────────────────────
def _score(name, value, direction="up", unit=None):
    it = {"item": name, "role": "score", "value": value, "category": "x",
          "tier": 2, "direction": direction}
    if unit:
        it["unit"] = unit
    return it


def _gate(name, result="PASS"):
    return {"item": name, "role": "gate", "gate_result": result,
            "gate_scope": "country", "category": "shared", "tier": 1, "value": "x"}


def _country(code, *, market, pen, captive, days, vendor, cb, gate="PASS"):
    return {
        "code": code, "country_ko": code, "region": "EU",
        "schema_version": "1.1", "overall_insight": f"{code} 테스트",
        "items": [
            _score("시장규모", market, "up"),
            _score("침투율", pen, "up"),
            _score("캡티브강도", captive, "down"),
            _score("회수기간", days, "down"),
            _score("솔루션벤더", vendor, "up", "match_1to5"),
            _score("CB인프라", cb, "up", "maturity_1to5"),
            _gate("외국인지분", gate),
            {"item": "브랜드 Top10", "role": "context", "context_type": "descriptive",
             "value": ["A", "B"], "category": "business", "tier": 3},
        ],
    }


_INTERNAL = {
    "version": "test",
    "country_assets": {"BL": {"solution": "X", "build_cost": 5000,
                              "build_months": 18, "reuse_factor": 0.7}},
    "regions": {"EU": {"name_ko": "유럽", "name_en": "Europe",
                       "members": ["BL", "C1", "C2", "C3"], "baseline": "BL"}},
    "similarity_brackets": [{"min": 80, "max": 100, "discount": 0.40},
                            {"min": 0, "max": 79, "discount": 0.0}],
    "maintenance_rate": 0.18,
    "weights": {"category_weights": {"market": 25, "finance": 30,
                                     "regulation": 20, "system": 25},
                "items": {"market": {"시장규모": 1.0},
                          "finance": {"침투율": 0.5, "캡티브강도": 0.5},
                          "regulation": {"회수기간": 1.0},
                          "system": {"솔루션벤더": 0.5, "CB인프라": 0.5}}},
    "quick_win_rules": {"weights": {"similarity": 0.4, "attractiveness": 0.35, "ease": 0.25},
                        "thresholds": {"quick_win_score": 40, "min_similarity": 30,
                                       "min_attractiveness": 20, "max_difficulty": 90}},
}


def _setup_synthetic(tmp):
    """합성 country 파일을 임시 storage 에 쓰고 R 의 경로를 patch."""
    cdir = Path(tmp) / "country"
    countries = {
        "BL": _country("BL", market=50, pen=50, captive=50, days=150, vendor=5, cb=5),
        "C1": _country("C1", market=100, pen=80, captive=10, days=50, vendor=5, cb=5),  # 최강
        "C2": _country("C2", market=50, pen=50, captive=50, days=150, vendor=3, cb=3),
        "C3": _country("C3", market=0, pen=10, captive=90, days=300, vendor=1, cb=1),   # 최약
    }
    for code, data in countries.items():
        d = cdir / code
        d.mkdir(parents=True)
        (d / f"{code}_latest.json").write_text(json.dumps(data), encoding="utf-8")
    R.COUNTRY_DIR = cdir
    return countries


def _all_blocks(report):
    for t in report["tabs"]:
        for b in t["blocks"]:
            yield t["tab"], b


def _assert_contract(report):
    for tab_id, b in _all_blocks(report):
        assert b.get("nature") in R.NATURE, f"{tab_id}: bad nature {b}"
        assert b.get("source_flag") in {"EXT", "INT", "CALC", "AI", "NEWS"}, f"{tab_id}: {b}"


# ── 합성 테스트 ───────────────────────────────────────────────────────────
def test_synthetic_region_ranking():
    orig = R.COUNTRY_DIR
    with tempfile.TemporaryDirectory() as tmp:
        _setup_synthetic(tmp)
        try:
            report = R.generate_region_report("EU", _INTERNAL, report_id="syn")
        finally:
            R.COUNTRY_DIR = orig

    _assert_contract(report)
    assert report["candidate_count"] == 4
    # 탭 5종
    tabs = [t["tab"] for t in report["tabs"]]
    assert tabs == ["2-요약", "2-0", "2-1", "2-2", "2-3"], tabs

    # 퀵윈 순위: C1(최강)이 1위, C3(최약)이 꼴찌
    qw_tab = next(t for t in report["tabs"] if t["tab"] == "2-2")
    ranking = next(b["value"] for b in qw_tab["blocks"] if b["key"] == "quick_win_ranking")
    assert ranking[0]["code"] == "C1", ranking
    assert ranking[-1]["code"] == "C3", ranking
    # 10점 구간 표기 존재
    assert ranking[0]["quick_win_band"] is not None


def test_synthetic_kill_switch():
    """게이트 FAIL 국은 peer set 에서 제외되고 매트릭스에 탈락 표기."""
    orig = R.COUNTRY_DIR
    with tempfile.TemporaryDirectory() as tmp:
        countries = _setup_synthetic(tmp)
        # C2 를 게이트 탈락으로 덮어쓰기
        bad = _country("C2", market=50, pen=50, captive=50, days=150,
                       vendor=3, cb=3, gate="FAIL")
        (Path(tmp) / "country" / "C2" / "C2_latest.json").write_text(
            json.dumps(bad), encoding="utf-8")
        try:
            report = R.generate_region_report("EU", _INTERNAL, report_id="syn")
        finally:
            R.COUNTRY_DIR = orig

    ks_tab = next(t for t in report["tabs"] if t["tab"] == "2-0")
    matrix = ks_tab["blocks"][0]["value"]
    c2 = next(r for r in matrix if r["code"] == "C2")
    assert c2["passed"] is False, c2
    # 순위에는 통과국만(C2 제외 → 3개)
    qw_tab = next(t for t in report["tabs"] if t["tab"] == "2-2")
    ranking = next(b["value"] for b in qw_tab["blocks"] if b["key"] == "quick_win_ranking")
    assert "C2" not in [r["code"] for r in ranking], ranking


def test_top3_profile_cards():
    orig = R.COUNTRY_DIR
    with tempfile.TemporaryDirectory() as tmp:
        _setup_synthetic(tmp)
        try:
            report = R.generate_region_report("EU", _INTERNAL, report_id="syn")
        finally:
            R.COUNTRY_DIR = orig
    qw_tab = next(t for t in report["tabs"] if t["tab"] == "2-2")
    top3 = next(b["value"] for b in qw_tab["blocks"] if b["key"] == "top3_profiles")
    assert len(top3) == 3
    assert [c["rank"] for c in top3] == [1, 2, 3]


# ── EU 실데이터 graceful ──────────────────────────────────────────────────
def test_real_eu_graceful():
    """EU 실데이터: ES 1개국만 존재, baseline UK 부재 → 구조 생성·유사도 None."""
    internal = R.load_internal()
    report = R.generate_region_report("EU", internal, report_id="test")
    _assert_contract(report)
    assert report["candidate_count"] >= 1
    # baseline 부재 → 유사도 None → 퀵윈 None 이지만 에러 없이 생성
    qw_tab = next(t for t in report["tabs"] if t["tab"] == "2-2")
    ranking = next(b["value"] for b in qw_tab["blocks"] if b["key"] == "quick_win_ranking")
    assert isinstance(ranking, list)


if __name__ == "__main__":
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
