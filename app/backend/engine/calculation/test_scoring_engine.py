#!/usr/bin/env python3
"""
scoring_engine 회귀 테스트 (U2).

손으로 계산한 합성 픽스처로 각 산식의 기대값을 고정한다.
실데이터(ES 1개국)로는 baseline 비교·peer 정규화가 불가하므로, 단순한 값의
가짜 baseline(UK)·후보국(A·B)을 만들어 산식 자체를 검증한다.

pytest 있으면 pytest, 없으면 standalone 폴백(U1 과 동일 패턴).
"""

import math

import scoring_engine as S


# ── 합성 internal 룰셋 (계산 검증용 최소 구조) ────────────────────────────
INTERNAL = {
    "country_assets": {
        "UK": {"solution": "NetSol", "build_cost": 5000, "build_months": 18, "reuse_factor": 0.70},
    },
    "regions": {"EU": {"name_ko": "유럽", "name_en": "Europe",
                       "members": ["UK", "A", "B"], "baseline": "UK"}},
    "similarity_brackets": [
        {"min": 80, "max": 100, "discount": 0.40},
        {"min": 70, "max": 79, "discount": 0.30},
        {"min": 60, "max": 69, "discount": 0.20},
        {"min": 50, "max": 59, "discount": 0.10},
        {"min": 0, "max": 49, "discount": 0.00},
    ],
    "maintenance_rate": 0.18,
    "weights": {
        "category_weights": {"market": 25, "finance": 30, "regulation": 20, "system": 25},
        "items": {
            # 합성: 카테고리당 항목 1~2개, 내부 합=1.0
            "market": {"시장규모": 1.0},
            "finance": {"침투율": 0.5, "캡티브강도": 0.5},
            "regulation": {"회수기간": 1.0},
            "system": {"솔루션벤더": 0.5, "CB인프라": 0.5},
        },
    },
    "quick_win_rules": {
        "weights": {"similarity": 0.40, "attractiveness": 0.35, "ease": 0.25},
        "thresholds": {"quick_win_score": 55, "min_similarity": 60,
                       "min_attractiveness": 40, "max_difficulty": 65},
    },
}


def _score(name, value, *, direction="up", unit=None, role="score"):
    it = {"item": name, "role": role, "value": value, "category": "x", "tier": 2}
    if direction:
        it["direction"] = direction
    if unit:
        it["unit"] = unit
    return it


def _gate(name, result):
    return {"item": name, "role": "gate", "gate_result": result,
            "gate_scope": "country", "category": "shared", "tier": 1, "value": "x"}


def _isclose(a, b, tol=0.01):
    return a is not None and b is not None and math.isclose(a, b, abs_tol=tol)


# ── 게이트 ────────────────────────────────────────────────────────────────
def test_gates_pass_with_flag():
    items = [_gate("외국인지분", "PASS"), _gate("송금", "PASS"),
             _gate("금리상한", "FLAG")]
    r = S.evaluate_gates(items)
    assert r["passed"] is True          # FAIL 없음 → 통과
    assert r["flag_items"] == ["금리상한"]
    assert r["pass_count"] == 2


def test_gates_fail():
    items = [_gate("외국인지분", "PASS"), _gate("데이터현지화", "FAIL")]
    r = S.evaluate_gates(items)
    assert r["passed"] is False
    assert r["fail_items"] == ["데이터현지화"]


# ── 유사도 (vs baseline) ──────────────────────────────────────────────────
def test_similarity_identical_is_100():
    """동일 값이면 유사도 100."""
    base = [_score("솔루션벤더", 5, unit="match_1to5"), _score("CB인프라", 4, unit="maturity_1to5")]
    cand = [_score("솔루션벤더", 5, unit="match_1to5"), _score("CB인프라", 4, unit="maturity_1to5")]
    r = S.similarity_score(cand, base, INTERNAL)
    assert _isclose(r["score"], 100.0), r


def test_similarity_one_to_five_gap():
    """1~5 척도, gap=2 → 1 - 2/4 = 0.5 → 50점. 두 항목 동일하면 종합 50."""
    base = [_score("솔루션벤더", 5, unit="match_1to5"), _score("CB인프라", 5, unit="maturity_1to5")]
    cand = [_score("솔루션벤더", 3, unit="match_1to5"), _score("CB인프라", 3, unit="maturity_1to5")]
    r = S.similarity_score(cand, base, INTERNAL)
    # 각 항목 50점, 가중 0.5/0.5 → 50
    assert _isclose(r["score"], 50.0), r
    assert _isclose(r["coverage"], 1.0), r


def test_similarity_partial_coverage_reweights():
    """한 항목만 양쪽에 있으면 그 항목으로만 채점(가중 재정규화)."""
    base = [_score("솔루션벤더", 5, unit="match_1to5")]   # CB인프라 없음
    cand = [_score("솔루션벤더", 5, unit="match_1to5"), _score("CB인프라", 1, unit="maturity_1to5")]
    r = S.similarity_score(cand, base, INTERNAL)
    assert _isclose(r["score"], 100.0), r       # 솔루션벤더만 채점 → 100
    assert _isclose(r["coverage"], 0.5), r      # 채점된 가중치 합


# ── 매력도 / 난이도 (peer min-max) ────────────────────────────────────────
def _peer(market, pen, captive):
    return [_score("시장규모", market, direction="up"),
            _score("침투율", pen, direction="up"),
            _score("캡티브강도", captive, direction="down")]  # 高=惡 역점수


def test_attractiveness_max_in_peer():
    """peer 중 최고 시장·침투 + 최저 캡티브 → 매력도 100 근처."""
    A = _peer(market=100, pen=80, captive=10)
    B = _peer(market=50, pen=40, captive=50)
    C = _peer(market=0, pen=0, captive=90)
    peers = [A, B, C]
    r = S.attractiveness_score(A, peers, INTERNAL)
    # market: A=100 → norm 100 (up) → 100
    # finance: 침투율 A=80 → norm 100(up)→100; 캡티브 A=10 → norm 0, down → 100-0=100
    #   finance 풀 = 0.5*100 + 0.5*100 = 100
    # 매력도 = (100*25 + 100*30)/(25+30) = 100
    assert _isclose(r["score"], 100.0), r


def test_attractiveness_min_in_peer():
    """peer 중 최저 → 매력도 0 근처."""
    A = _peer(market=100, pen=80, captive=10)
    B = _peer(market=50, pen=40, captive=50)
    C = _peer(market=0, pen=0, captive=90)
    peers = [A, B, C]
    r = S.attractiveness_score(C, peers, INTERNAL)
    # market C=0 → 0; 침투 C=0 → 0; 캡티브 C=90 → norm 100, down → 0
    # 매력도 = 0
    assert _isclose(r["score"], 0.0), r


def test_difficulty_direction_down():
    """회수기간 direction=down: 값 클수록 난이도↑. peer max → 100."""
    def reg(days):
        return [_score("회수기간", days, direction="down")]
    A, B, C = reg(300), reg(150), reg(0)
    peers = [A, B, C]
    # difficulty mode + direction down → norm 그대로. A=300=max → norm100 → 100
    assert _isclose(S.difficulty_score(A, peers, INTERNAL)["score"], 100.0)
    assert _isclose(S.difficulty_score(C, peers, INTERNAL)["score"], 0.0)


def test_normalize_single_peer_is_neutral():
    """후보국 1개(min=max)면 정규화 분모 0 → 중립 50."""
    A = _peer(market=100, pen=80, captive=10)
    r = S.attractiveness_score(A, [A], INTERNAL)
    # 모든 항목 norm 50 → up은 50, down(캡티브)은 100-50=50 → 풀 50 → 매력도 50
    assert _isclose(r["score"], 50.0), r


# ── TCO ───────────────────────────────────────────────────────────────────
def test_tco_high_similarity_discount():
    """유사도 85 → 구간[80,100] discount 0.40. reuse 0.60."""
    r = S.tco_estimate(85, INTERNAL, "UK")
    # build_cost = 5000 * 0.60 = 3000
    assert _isclose(r["build_cost"], 3000.0), r
    # annual_maint = 3000 * 0.18 = 540
    assert _isclose(r["annual_maintenance"], 540.0), r
    # build_months = 18 * 0.60 = 10.8
    assert _isclose(r["build_months"], 10.8), r
    # system_10y = 3000 + 540*10 = 8400
    assert _isclose(r["system_10y_tco"], 8400.0), r
    assert r["contract"] is None and len(r["missing_inputs"]) == 7


def test_tco_low_similarity_no_discount():
    """유사도 30 → discount 0 → reuse 1.0 → build_cost 그대로 5000."""
    r = S.tco_estimate(30, INTERNAL, "UK")
    assert _isclose(r["build_cost"], 5000.0), r
    assert _isclose(r["system_10y_tco"], 5000 + 900 * 10), r  # maint=900


def test_tco_with_contract_inputs():
    """계약 입력 주면 예상건수·구독료·총 TCO 산출."""
    ci = {
        "sales_units": 1000, "finance_penetration": 0.5,
        "installment_lease_ratio": 0.8, "our_share": 0.1,
        "existing_cumulative_units": 60, "subscription_unit_price": 1.0,
        "operation_total_10y": 2000,
    }
    r = S.tco_estimate(85, INTERNAL, "UK", contract_inputs=ci)
    # expected = 1000*0.5*0.8*0.1 = 40
    assert _isclose(r["contract"]["expected_units"], 40.0), r
    # new_cumulative = 60 + 40 = 100 ; annual_sub = 100*1.0 = 100
    assert _isclose(r["contract"]["annual_subscription"], 100.0), r
    # total = system_10y(8400) + 100*10 + 2000 = 11400
    assert _isclose(r["contract"]["total_10y_tco"], 11400.0), r


def test_tco_unknown_baseline():
    r = S.tco_estimate(85, INTERNAL, "ZZ")
    assert "error" in r


# ── 퀵윈 blend ────────────────────────────────────────────────────────────
def test_quick_win_blend_and_qualify():
    """sim80·att70·diff40 → ease60. score = 80*.4+70*.35+60*.25 = 32+24.5+15 = 71.5."""
    r = S.quick_win_score(80, 70, 40, INTERNAL)
    assert _isclose(r["score"], 71.5), r
    assert _isclose(r["ease"], 60.0), r
    assert r["qualified"] is True   # 71.5≥55, 80≥60, 70≥40, 40≤65


def test_quick_win_disqualified_by_threshold():
    """유사도 50(<min_similarity 60) → 점수 높아도 미달."""
    r = S.quick_win_score(50, 90, 30, INTERNAL)
    assert r["qualified"] is False


def test_category_of_mapping():
    assert S.category_of("회수기간", INTERNAL) == "regulation"
    assert S.category_of("솔루션벤더", INTERNAL) == "system"
    assert S.category_of("없는항목", INTERNAL) is None


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
