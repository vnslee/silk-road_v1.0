#!/usr/bin/env python3
"""
Country Report Engine (U3) — 유형1 단일국가 보고서 JSON 생성.

U2 스코어링(scoring_engine) 결과 + country items + internal 을 조립해
render_req 의 데이터 블록 계약(nature·source_flag 포함)을 충족하는
탭 1-0~1-4 보고서 JSON 을 만든다. 계산은 U2 에 위임, 여기선 조립·구조화만.

출력 경로 (A3): storage/report/country/<CODE>/<ID>/data/<CODE>_rpt_<ID>.json
  HTML(html/)은 U5 렌더링 엔진이 채운다(JSON 과 섞지 않음).

baseline(권역 기준국) 데이터가 없으면 유사도·TCO 탭은 에러가 아니라
"조사 필요" 플레이스홀더로 산출한다(render_req: 빈 차트 금지).

엔진 컨벤션: calculation 형제 폴더를 sys.path 에 추가해 scoring_engine import.
"""

import json
import sys
from pathlib import Path

STORAGE = Path(__file__).resolve().parent.parent.parent / "storage"
COUNTRY_DIR = STORAGE / "data" / "research" / "country"
INTERNAL_LATEST = STORAGE / "data" / "internal" / "internal_latest.json"
REPORT_BASE = STORAGE / "report" / "country"

# calculation 형제 폴더 import (generation→engine→calculation)
_CALC = Path(__file__).resolve().parent.parent / "calculation"
if str(_CALC) not in sys.path:
    sys.path.insert(0, str(_CALC))
import scoring_engine as SC  # noqa: E402
import report_id as RID  # noqa: E402 (engine/generation — 동일 폴더)

# render_req 데이터 성격(nature) 7종
NATURE = {"timeseries", "composition", "ranking", "score_multiaxis",
          "single_value", "qualitative", "status_matrix"}
# 결정트리 분기 임계 (report_generate_req 탭1-2)
DECISION_HIGH = 70   # ≥ → B시스템 확산
DECISION_LOW = 50    # < → 외부솔루션


# ── 데이터 블록 빌더 ──────────────────────────────────────────────────────
def block(key, label, value, nature, source_flag, source=None):
    """render_req §0 데이터 블록 계약. 모든 표시 수치는 이 형태로 감싼다."""
    assert nature in NATURE, f"unknown nature: {nature}"
    return {"key": key, "label": label, "value": value,
            "nature": nature, "source_flag": source_flag,
            "source": source or {}}


def _src(item):
    """country item 의 출처 메타 → 블록 source."""
    return {"org": item.get("source", ""), "tier": item.get("tier")}


def _flag_for(item):
    """item role/context_type → source_flag (EXT/NEWS/AI 중)."""
    if item.get("context_type") == "news":
        return "NEWS"
    if item.get("insight_ai_generated"):
        return "EXT"  # 값 자체는 외부조사. insight 는 별도 AI 블록으로.
    return "EXT"


def _placeholder(key, label, reason):
    """'조사 필요' 플레이스홀더 블록(빈 차트 금지 원칙)."""
    return block(key, label, None, "qualitative", "EXT",
                 {"note": reason})


# ── 탭 1-1 유사도 ─────────────────────────────────────────────────────────
def build_tab_1_1(items, baseline_items, internal):
    """종합 유사도[CALC] + 축별 점수. baseline 없으면 조사필요."""
    if baseline_items is None:
        return {"tab": "1-1", "name": "유사도",
                "blocks": [_placeholder("similarity", "종합 유사도",
                                        "baseline 데이터 없음 — 조사 필요")]}
    sim = SC.similarity_score(items, baseline_items, internal)
    blocks = [
        block("similarity_overall", "종합 유사도", sim["score"],
              "single_value", "CALC", {"formula": "system 항목 가중 유사도"}),
        block("similarity_by_item", "항목별 유사도", sim["scored_items"],
              "score_multiaxis", "CALC", {"coverage": sim["coverage"]}),
    ]
    return {"tab": "1-1", "name": "유사도", "score": sim["score"], "blocks": blocks}


# ── 탭 1-2 결정트리 ───────────────────────────────────────────────────────
def build_tab_1_2(similarity_score):
    """유사도 → 분기 판정. 추천 솔루션 목록은 데이터 부재 → 플레이스홀더."""
    if similarity_score is None:
        branch, detail = "조사 필요", "유사도 미산출(baseline 없음)"
    elif similarity_score >= DECISION_HIGH:
        branch, detail = "B시스템 확산", f"유사도 {similarity_score} ≥ {DECISION_HIGH}"
    elif similarity_score < DECISION_LOW:
        branch, detail = "외부솔루션", f"유사도 {similarity_score} < {DECISION_LOW} (추천 솔루션 조사 필요)"
    else:
        branch, detail = "본사 자체구축", f"{DECISION_LOW} ≤ 유사도 {similarity_score} < {DECISION_HIGH}"
    return {"tab": "1-2", "name": "결정트리", "branch": branch,
            "blocks": [block("decision", "시스템 결정", {"branch": branch, "detail": detail},
                             "qualitative", "CALC")]}


# ── 탭 1-3 TCO ────────────────────────────────────────────────────────────
def build_tab_1_3(similarity_score, internal, baseline_code):
    """유사도 → TCO 빌드업. 계약 입력 부재분은 missing_inputs."""
    if similarity_score is None:
        return {"tab": "1-3", "name": "TCO",
                "blocks": [_placeholder("tco", "10년 TCO", "유사도 미산출 — 조사 필요")]}
    tco = SC.tco_estimate(similarity_score, internal, baseline_code)
    if "error" in tco:
        return {"tab": "1-3", "name": "TCO",
                "blocks": [_placeholder("tco", "10년 TCO", tco["error"])]}
    blocks = [
        block("build_cost", "구축비(일회성)", tco["build_cost"], "single_value", "CALC"),
        block("annual_maintenance", "연 유지비", tco["annual_maintenance"], "single_value", "CALC"),
        block("system_10y_tco", "시스템 10년 TCO", tco["system_10y_tco"], "single_value", "CALC"),
        block("build_months", "구축 기간(개월)", tco["build_months"], "single_value", "CALC"),
    ]
    notes = []
    if tco["missing_inputs"]:
        notes.append(f"계약건수·구독료 입력 미수록: {tco['missing_inputs']}")
    return {"tab": "1-3", "name": "TCO", "blocks": blocks, "notes": notes}


# ── 탭 1-4 시장·경쟁 배경 ─────────────────────────────────────────────────
def build_tab_1_4(items):
    """context/score 항목을 nature 별로 블록화(순위·시계열·정성)."""
    blocks = []
    for it in items:
        role = it.get("role")
        name = it.get("item")
        if role == "context" and it.get("context_type") == "news":
            continue  # NEWS 는 요약 탭으로
        if role == "context":
            val = it.get("value")
            nature = "ranking" if isinstance(val, list) else "qualitative"
            blocks.append(block(_slug(name), name, val, nature, _flag_for(it), _src(it)))
        elif role == "score" and it.get("timeseries"):
            blocks.append(block(_slug(name), name, it["timeseries"],
                                "timeseries", "EXT", _src(it)))
    return {"tab": "1-4", "name": "시장·경쟁 배경", "blocks": blocks}


# ── 탭 1-0 요약 (마지막 생성) ─────────────────────────────────────────────
def build_tab_1_0(data, similarity_score, decision_branch, tco_block, items):
    """핵심 KPI + overall_insight(AI) + NEWS 카드."""
    kpis = [
        block("kpi_similarity", "종합 유사도", similarity_score, "single_value", "CALC"),
        block("kpi_decision", "시스템 결정", decision_branch, "qualitative", "CALC"),
    ]
    if tco_block is not None:
        kpis.append(block("kpi_tco", "시스템 10년 TCO", tco_block, "single_value", "CALC"))

    ai = block("overall_insight", "AI 종합 인사이트",
               data.get("overall_insight", ""), "qualitative", "AI")

    news = []
    for it in items:
        if it.get("context_type") == "news" and isinstance(it.get("value"), list):
            news.append(block("news_scan", it.get("item"), it["value"],
                              "qualitative", "NEWS", _src(it)))
    return {"tab": "1-0", "name": "요약", "blocks": kpis + [ai] + news}


# ── 헬퍼 ──────────────────────────────────────────────────────────────────
def _slug(name):
    return "".join(c if c.isalnum() else "_" for c in name).strip("_").lower()


def _baseline_items(region, internal):
    """region 의 baseline 국 items. 없으면 (None, code)."""
    meta = internal.get("regions", {}).get(region)
    if not meta:
        return None, None
    code = meta.get("baseline")
    path = COUNTRY_DIR / code / f"{code}_latest.json"
    if not path.exists():
        return None, code
    with open(path, encoding="utf-8") as f:
        return json.load(f)["items"], code


# ── 조립 ──────────────────────────────────────────────────────────────────
def generate_country_report(data, internal, *, report_id):
    """country research data → 유형1 보고서 JSON(탭 1-0~1-4)."""
    items = data["items"]
    region = data["region"]
    code = data["code"]
    baseline_items, baseline_code = _baseline_items(region, internal)

    tab_1_1 = build_tab_1_1(items, baseline_items, internal)
    sim_score = tab_1_1.get("score")
    tab_1_2 = build_tab_1_2(sim_score)
    tab_1_3 = build_tab_1_3(sim_score, internal, baseline_code)
    tab_1_4 = build_tab_1_4(items)

    # 1-3 의 시스템 TCO 값을 요약 KPI 로 끌어옴
    tco_val = next((b["value"] for b in tab_1_3["blocks"]
                    if b["key"] == "system_10y_tco"), None)
    tab_1_0 = build_tab_1_0(data, sim_score, tab_1_2["branch"], tco_val, items)

    return {
        "report_id": report_id,
        "report_type": "type1_country",
        "title": f"{data.get('country_ko', code)} 오토파이낸스 진출 비용·TCO 보고서",
        "target": {"country": code, "base_country": baseline_code},
        "region": region,
        "data_snapshot_id": RID.snapshot_id(code, internal),
        "based_on": RID.build_based_on(
            [code], internal,
            schema_version=data.get("schema_version"),
            baseline_code=baseline_code),
        "tabs": [tab_1_0, tab_1_1, tab_1_2, tab_1_3, tab_1_4],
    }


def save_report(report, code, report_id):
    """data/ 에 JSON 저장(html/ 은 U5). 폴더 없으면 생성."""
    out_dir = REPORT_BASE / code / report_id / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def load_internal():
    with open(INTERNAL_LATEST, encoding="utf-8") as f:
        return json.load(f)


def load_country(code):
    with open(COUNTRY_DIR / code / f"{code}_latest.json", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else None
    if not code:
        print("usage: country_report_engine.py <COUNTRY_CODE> [REPORT_ID]")
        sys.exit(1)
    data = load_country(code)
    internal = load_internal()
    # 인자로 ID 를 주면 그대로, 아니면 자동 채번(RPT_CTR_<CODE>_NNN)
    rid = sys.argv[2] if len(sys.argv) > 2 else RID.next_report_id("country", code)
    report = generate_country_report(data, internal, report_id=rid)
    path = save_report(report, code, rid)
    print(f"생성: {path}")
    print(f"  report_id={rid}  snapshot={report['data_snapshot_id']}")
    for t in report["tabs"]:
        print(f"  {t['tab']} {t['name']}: {len(t['blocks'])} blocks")
