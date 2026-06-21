#!/usr/bin/env python3
"""
Scoring core (U2).

순수 계산 함수 모음. country research items + internal ruleset 을 입력받아
[CALC] 값을 산출한다 — 보고서 JSON 생성·렌더링은 하지 않는다(관심사 분리).

산출 산식 (report_generate_req.md 기준):
  gates         — 킬스위치 PASS/FAIL/FLAG 집계 (탭2-0)
  similarity    — system 카테고리 항목을 baseline 과 비교 → 0~100 (탭1-1)
  attractiveness— market+finance 항목 min-max 정규화 → blend (탭2-1)
  difficulty    — regulation 항목 역점수 → 0~100 (난이도축, 차량회수 포함)
  tco           — 유사도%→구축비·유지비·10년 TCO (탭1-3, 일부는 추가 INT 필요)
  quick_win     — sim·attractiveness·ease blend → 점수 (탭2-2)

★ 축(axis) 판정은 country 데이터의 `axis` 필드가 아니라 **internal.weights.items 의
  카테고리 소속**으로 한다(C2: 엔진이 항목명 매핑으로 결정). 데이터의 axis 는 무시.

엔진 컨벤션: 자기 위치 기준 storage 해석.
"""

import json
from pathlib import Path

STORAGE = Path(__file__).resolve().parent.parent.parent / "storage"
COUNTRY_DIR = STORAGE / "data" / "research" / "country"
INTERNAL_LATEST = STORAGE / "data" / "internal" / "internal_latest.json"

ATTRACTIVENESS_CATS = ("market", "finance")  # 매력도 풀
DIFFICULTY_CAT = "regulation"                # 난이도 풀
SIMILARITY_CAT = "system"                    # 유사도 풀


# ── 데이터 접근 헬퍼 ──────────────────────────────────────────────────────
def _index_items(items):
    """item명 → item 객체. 같은 이름 중복 시 첫 항목."""
    idx = {}
    for it in items:
        idx.setdefault(it.get("item"), it)
    return idx


def _numeric(it):
    """item 의 value 가 수치면 float, 아니면 None."""
    if it is None:
        return None
    v = it.get("value")
    if isinstance(v, bool):  # bool 은 int 의 하위형 — 제외
        return None
    return float(v) if isinstance(v, (int, float)) else None


def _direction(it):
    return it.get("direction") if it else None


def category_of(item_name, internal):
    """item명이 속한 룰셋 카테고리(market/finance/regulation/system). 없으면 None."""
    for cat, weights in internal["weights"]["items"].items():
        if item_name in weights:
            return cat
    return None


# ── 1. 게이트 (킬스위치) ──────────────────────────────────────────────────
def evaluate_gates(items):
    """gate 항목 집계. passed = FAIL 이 하나도 없으면 True (FLAG 는 통과·보류)."""
    gates = [it for it in items if it.get("role") == "gate"]
    results = {"PASS": [], "FAIL": [], "FLAG": []}
    for g in gates:
        results.setdefault(g.get("gate_result"), []).append(g.get("item"))
    return {
        "passed": len(results["FAIL"]) == 0,
        "fail_items": results["FAIL"],
        "flag_items": results["FLAG"],
        "pass_count": len(results["PASS"]),
        "counts": {k: len(v) for k, v in results.items()},
    }


# ── 2. 유사도 (vs baseline) ───────────────────────────────────────────────
def _item_similarity(a_val, b_val, unit):
    """두 수치값의 근접도 0~100. 1~5 척도면 span=4, 아니면 상대 척도."""
    if "1to5" in (unit or ""):
        span = 4.0
    else:
        span = max(abs(a_val), abs(b_val), 1.0)
    gap = abs(a_val - b_val)
    return max(0.0, 1.0 - gap / span) * 100.0


def similarity_score(country_items, baseline_items, internal):
    """system 카테고리 항목을 baseline 과 비교 → 가중 유사도 0~100.

    수치값이 양쪽에 있는 항목만 채점. weights 는 채점된 항목들로 재정규화.
    """
    a_idx = _index_items(country_items)
    b_idx = _index_items(baseline_items)
    weights = internal["weights"]["items"][SIMILARITY_CAT]

    acc, total_w, scored = 0.0, 0.0, {}
    for name, w in weights.items():
        a, b = _numeric(a_idx.get(name)), _numeric(b_idx.get(name))
        if a is None or b is None:
            continue
        unit = (a_idx.get(name) or {}).get("unit")
        s = _item_similarity(a, b, unit)
        scored[name] = round(s, 2)
        acc += s * w
        total_w += w

    score = acc / total_w if total_w else None
    return {
        "score": round(score, 2) if score is not None else None,
        "scored_items": scored,
        "coverage": round(total_w, 4),  # 채점된 가중치 합(1.0 이면 전 항목 채점)
    }


# ── 3·4. 매력도 / 난이도 (peer set min-max) ───────────────────────────────
def _normalize(value, vmin, vmax):
    """min-max 0~100. 분모 0(전 국가 동일)이면 중립 50."""
    if vmax == vmin:
        return 50.0
    return (value - vmin) / (vmax - vmin) * 100.0


def _pool_score(country_items, peer_items_list, internal, category, mode):
    """카테고리 풀 점수. mode='attractiveness'|'difficulty'.

    peer_items_list: 정규화 기준이 되는 후보국 items 리스트(country 자신 포함).
    """
    weights = internal["weights"]["items"][category]
    a_idx = _index_items(country_items)
    peer_idxs = [_index_items(p) for p in peer_items_list]

    acc, total_w, contrib = 0.0, 0.0, {}
    for name, w in weights.items():
        a = _numeric(a_idx.get(name))
        if a is None:
            continue
        vals = [v for v in (_numeric(p.get(name)) for p in peer_idxs) if v is not None]
        if not vals:
            continue
        norm = _normalize(a, min(vals), max(vals))
        direction = _direction(a_idx.get(name))
        if mode == "attractiveness":
            score = norm if direction == "up" else 100.0 - norm
        else:  # difficulty: 클수록 난이도↑
            score = norm if direction == "down" else 100.0 - norm
        contrib[name] = round(score, 2)
        acc += score * w
        total_w += w

    pool = acc / total_w if total_w else None
    return {"score": round(pool, 2) if pool is not None else None,
            "contrib": contrib, "coverage": round(total_w, 4)}


def attractiveness_score(country_items, peer_items_list, internal):
    """매력도 = (market 풀 × cw_market + finance 풀 × cw_finance) / 합. 0~100."""
    cw = internal["weights"]["category_weights"]
    pools = {c: _pool_score(country_items, peer_items_list, internal, c, "attractiveness")
             for c in ATTRACTIVENESS_CATS}
    num, den = 0.0, 0.0
    for c in ATTRACTIVENESS_CATS:
        s = pools[c]["score"]
        if s is not None:
            num += s * cw[c]
            den += cw[c]
    return {"score": round(num / den, 2) if den else None, "pools": pools}


def difficulty_score(country_items, peer_items_list, internal):
    """난이도 = regulation 풀 점수(역점수 반영). 0~100, 높을수록 어려움."""
    pool = _pool_score(country_items, peer_items_list, internal, DIFFICULTY_CAT, "difficulty")
    return {"score": pool["score"], "pool": pool}


# ── 5. TCO (탭1-3) ────────────────────────────────────────────────────────
def _discount_for(similarity, brackets):
    """유사도 점수가 속한 구간의 discount(재사용률). 못 찾으면 0."""
    for b in brackets:
        if b["min"] <= similarity <= b["max"]:
            return b["discount"]
    return 0.0


def tco_estimate(similarity, internal, baseline_code,
                 *, contract_inputs=None):
    """10년 TCO 빌드업.

    결정론적으로 계산 가능한 부분:
      build_cost     = baseline 구축비 × (1 − discount[유사도])
      annual_maint   = build_cost × maintenance_rate
      build_months   = baseline 구축기간 × (1 − discount)
      system_10y_tco = build_cost + annual_maint × 10

    contract_inputs(선택, dict)가 주어지면 계약건수·구독료까지 산출:
      sales_units, finance_penetration, installment_lease_ratio, our_share,
      existing_cumulative_units, subscription_unit_price, operation_total_10y
    없으면 해당 값들은 None + missing_inputs 표기(현재 internal.json 미수록).
    """
    asset = internal["country_assets"].get(baseline_code)
    if asset is None:
        return {"error": f"baseline '{baseline_code}' 자산 없음"}

    discount = _discount_for(similarity, internal["similarity_brackets"])
    reuse = 1.0 - discount
    build_cost = asset["build_cost"] * reuse
    annual_maint = build_cost * internal["maintenance_rate"]
    build_months = asset["build_months"] * reuse
    system_10y = build_cost + annual_maint * 10

    out = {
        "discount": discount,
        "reuse_factor_applied": round(reuse, 4),
        "build_cost": round(build_cost, 2),
        "annual_maintenance": round(annual_maint, 2),
        "build_months": round(build_months, 2),
        "system_10y_tco": round(system_10y, 2),
        "contract": None,
        "missing_inputs": [],
    }

    ci = contract_inputs
    required = ["sales_units", "finance_penetration", "installment_lease_ratio",
                "our_share", "existing_cumulative_units", "subscription_unit_price",
                "operation_total_10y"]
    if not ci:
        out["missing_inputs"] = required
        return out

    missing = [k for k in required if k not in ci]
    if missing:
        out["missing_inputs"] = missing
        return out

    # 산식2: 예상 계약건수
    expected_units = (ci["sales_units"] * ci["finance_penetration"]
                      * ci["installment_lease_ratio"] * ci["our_share"])
    # 산식3: 구독료 — 전체 누적 소급
    new_cumulative = ci["existing_cumulative_units"] + expected_units
    annual_subscription = new_cumulative * ci["subscription_unit_price"]
    # 산식4: 총 10년 TCO = 시스템 + 구독 10년 + 운영비 통금액
    total_10y = system_10y + annual_subscription * 10 + ci["operation_total_10y"]

    out["contract"] = {
        "expected_units": round(expected_units, 2),
        "new_cumulative_units": round(new_cumulative, 2),
        "annual_subscription": round(annual_subscription, 2),
        "total_10y_tco": round(total_10y, 2),
    }
    return out


# ── 6. 퀵윈 blend (탭2-2) ─────────────────────────────────────────────────
def quick_win_score(similarity, attractiveness, difficulty, internal):
    """퀵윈 = sim·w_sim + attractiveness·w_att + ease·w_ease. ease = 100 − difficulty."""
    w = internal["quick_win_rules"]["weights"]
    ease = 100.0 - difficulty
    score = (similarity * w["similarity"]
             + attractiveness * w["attractiveness"]
             + ease * w["ease"])
    th = internal["quick_win_rules"]["thresholds"]
    qualified = (
        score >= th["quick_win_score"]
        and similarity >= th["min_similarity"]
        and attractiveness >= th["min_attractiveness"]
        and difficulty <= th["max_difficulty"]
    )
    return {"score": round(score, 2), "ease": round(ease, 2), "qualified": qualified}


# ── 로더 ──────────────────────────────────────────────────────────────────
def load_internal():
    with open(INTERNAL_LATEST, encoding="utf-8") as f:
        return json.load(f)


def load_country(code):
    with open(COUNTRY_DIR / code / f"{code}_latest.json", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else None
    if not code:
        print("usage: scoring_engine.py <COUNTRY_CODE>")
        sys.exit(1)
    internal = load_internal()
    data = load_country(code)
    items = data["items"]
    region = data["region"]
    baseline_code = internal["regions"][region]["baseline"]
    print(f"=== {code} (region {region}, baseline {baseline_code}) ===")
    print("gates:", evaluate_gates(items))
    try:
        bl = load_country(baseline_code)["items"]
        print("similarity:", similarity_score(items, bl, internal))
    except FileNotFoundError:
        print(f"similarity: baseline '{baseline_code}' 데이터 없음 — 계산 불가")
