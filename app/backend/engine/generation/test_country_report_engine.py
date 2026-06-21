#!/usr/bin/env python3
"""
country_report_engine 회귀 테스트 (U3).

- 실데이터 ES: 보고서 생성 → 모든 데이터 블록에 nature·source_flag 누락 0건.
- baseline 부재(ES, UK 없음): 탭1-1/1-3 이 에러가 아니라 '조사 필요' 구조.
- 합성 baseline 픽스처: 탭1-1/1-3 정상 생성(유사도·TCO 값 존재).

pytest 있으면 pytest, 없으면 standalone 폴백.
"""

import country_report_engine as G


# ── 블록 계약 검사 헬퍼 ───────────────────────────────────────────────────
def _all_blocks(report):
    for tab in report["tabs"]:
        for b in tab["blocks"]:
            yield tab["tab"], b


def _assert_contract(report):
    """모든 블록이 nature·source_flag 를 가지는지(누락 0건)."""
    for tab_id, b in _all_blocks(report):
        assert "nature" in b and b["nature"] in G.NATURE, f"{tab_id}: bad nature {b}"
        assert b.get("source_flag") in {"EXT", "INT", "CALC", "AI", "NEWS"}, \
            f"{tab_id}: bad source_flag {b}"
        assert "key" in b and "label" in b, f"{tab_id}: missing key/label {b}"


# ── 실데이터 ES (baseline UK 없음) ────────────────────────────────────────
def test_es_generates_with_contract():
    data = G.load_country("ES")
    internal = G.load_internal()
    report = G.generate_country_report(data, internal, report_id="test")
    _assert_contract(report)
    # 탭 5종 존재
    tabs = [t["tab"] for t in report["tabs"]]
    assert tabs == ["1-0", "1-1", "1-2", "1-3", "1-4"], tabs


def test_es_baseline_missing_is_placeholder():
    """UK 데이터 없음 → 유사도/TCO 가 조사필요(값 None) 플레이스홀더."""
    data = G.load_country("ES")
    internal = G.load_internal()
    report = G.generate_country_report(data, internal, report_id="test")
    tab_1_1 = next(t for t in report["tabs"] if t["tab"] == "1-1")
    assert tab_1_1.get("score") is None
    # 결정트리는 '조사 필요' 분기
    tab_1_2 = next(t for t in report["tabs"] if t["tab"] == "1-2")
    assert tab_1_2["branch"] == "조사 필요"


# ── 합성 baseline 으로 탭1-1/1-3 정상 생성 ────────────────────────────────
def _score(name, value, **kw):
    it = {"item": name, "role": "score", "value": value,
          "category": "x", "tier": 2, "direction": kw.get("direction", "up")}
    if "unit" in kw:
        it["unit"] = kw["unit"]
    return it


def _make_country(code, region, vendor, cb):
    return {
        "code": code, "country_ko": code, "region": region,
        "schema_version": "1.1", "overall_insight": "테스트",
        "items": [
            _score("솔루션 벤더", vendor, unit="match_1to5"),
            _score("신용정보(CB) 인프라", cb, unit="maturity_1to5"),
        ],
    }


# 합성 internal: system 카테고리에 두 항목, EU baseline=BL
_SYNTH_INTERNAL = {
    "version": "test",
    "country_assets": {"BL": {"solution": "X", "build_cost": 5000,
                              "build_months": 18, "reuse_factor": 0.7}},
    "regions": {"EU": {"name_ko": "유럽", "name_en": "Europe",
                       "members": ["BL", "CA"], "baseline": "BL"}},
    "similarity_brackets": [
        {"min": 80, "max": 100, "discount": 0.40},
        {"min": 0, "max": 79, "discount": 0.0},
    ],
    "maintenance_rate": 0.18,
    "weights": {"category_weights": {"market": 25, "finance": 30,
                                     "regulation": 20, "system": 25},
                "items": {"market": {}, "finance": {}, "regulation": {},
                          "system": {"솔루션 벤더": 0.5, "신용정보(CB) 인프라": 0.5}}},
    "quick_win_rules": {"weights": {"similarity": 0.4, "attractiveness": 0.35, "ease": 0.25},
                        "thresholds": {"quick_win_score": 55, "min_similarity": 60,
                                       "min_attractiveness": 40, "max_difficulty": 65}},
}


def test_synthetic_baseline_similarity(monkeypatch_load=None):
    """후보국 == baseline 동일값 → 유사도 100, 결정트리 B확산, TCO discount 적용."""
    baseline = _make_country("BL", "EU", vendor=5, cb=4)
    candidate = _make_country("CA", "EU", vendor=5, cb=4)

    # baseline 로더를 합성으로 대체
    orig = G._baseline_items
    G._baseline_items = lambda region, internal: (baseline["items"], "BL")
    try:
        report = G.generate_country_report(candidate, _SYNTH_INTERNAL, report_id="syn")
    finally:
        G._baseline_items = orig

    _assert_contract(report)
    tab_1_1 = next(t for t in report["tabs"] if t["tab"] == "1-1")
    assert abs(tab_1_1["score"] - 100.0) < 0.01, tab_1_1
    tab_1_2 = next(t for t in report["tabs"] if t["tab"] == "1-2")
    assert tab_1_2["branch"] == "B시스템 확산", tab_1_2
    # 유사도 100 → discount 0.40 → build_cost 5000*0.6 = 3000
    tab_1_3 = next(t for t in report["tabs"] if t["tab"] == "1-3")
    bc = next(b["value"] for b in tab_1_3["blocks"] if b["key"] == "build_cost")
    assert abs(bc - 3000.0) < 0.01, tab_1_3


def test_block_builder_rejects_bad_nature():
    try:
        G.block("k", "l", 1, "bogus_nature", "CALC")
        assert False, "bad nature 가 통과됨"
    except AssertionError as e:
        assert "nature" in str(e)


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
