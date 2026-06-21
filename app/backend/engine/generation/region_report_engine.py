#!/usr/bin/env python3
"""
Region Report Engine (U4) — 유형2 권역 퀵윈 보고서 JSON 생성.

권역 멤버 country.json 들을 모아 U2 스코어링(매력도·난이도·유사도·퀵윈)으로
순위를 내고, render_req 데이터 블록 계약(nature·source_flag)을 충족하는
탭 2-0~2-3 + 상위 3개국 프로파일 카드를 만든다. 계산은 U2 에 위임.

peer set = 권역 멤버 중 데이터 존재 + 킬스위치 통과국(매력도/난이도 정규화 기준).
baseline = regions[RGN].baseline (유사도 비교 기준).

출력 경로 (A3): storage/report/region/<RGN>/<ID>/data/<RGN>_rpt_<ID>.json
  (U3 country 와 대칭: <ID>/data/ 하위)

엔진 컨벤션: calculation 형제 폴더 import. country_report_engine 의 block 빌더 재사용.
"""

import json
import sys
from pathlib import Path

STORAGE = Path(__file__).resolve().parent.parent.parent / "storage"
COUNTRY_DIR = STORAGE / "data" / "research" / "country"
INTERNAL_LATEST = STORAGE / "data" / "internal" / "internal_latest.json"
REPORT_BASE = STORAGE / "report" / "region"

_CALC = Path(__file__).resolve().parent.parent / "calculation"
if str(_CALC) not in sys.path:
    sys.path.insert(0, str(_CALC))
import scoring_engine as SC  # noqa: E402

# block 빌더·nature 상수는 country 엔진과 공유(중복 정의 방지)
from country_report_engine import block, NATURE, _src  # noqa: E402,F401
import report_id as RID  # noqa: E402


def _band10(score):
    """10점 구간 표기(과잉정밀 방지, render_req 원칙). 예: 82.2 → '80점대'."""
    if score is None:
        return None
    return f"{int(score // 10) * 10}점대"


# ── 후보국 로드 + 스코어링 ────────────────────────────────────────────────
def _load_members(region, internal):
    """권역 멤버 중 데이터가 존재하는 국가들의 (code, data) 리스트 + baseline items."""
    meta = internal.get("regions", {}).get(region, {})
    members = meta.get("members", [])
    baseline_code = meta.get("baseline")
    loaded = []
    for code in members:
        path = COUNTRY_DIR / code / f"{code}_latest.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                loaded.append((code, json.load(f)))
    baseline_items = None
    for code, d in loaded:
        if code == baseline_code:
            baseline_items = d["items"]
    return loaded, baseline_code, baseline_items


def _score_candidates(loaded, baseline_items, internal):
    """각 후보국 스코어링. peer set = 게이트 통과국. (rows, gate_rows) 반환."""
    # 1단계: 게이트 평가 → 통과국만 peer set
    gate_rows = []
    passed = []
    for code, d in loaded:
        g = SC.evaluate_gates(d["items"])
        gate_rows.append({"code": code, "country_ko": d.get("country_ko", code),
                          "passed": g["passed"], "fail_items": g["fail_items"],
                          "flag_items": g["flag_items"], "counts": g["counts"]})
        if g["passed"]:
            passed.append((code, d))

    peer_items = [d["items"] for _, d in passed]

    # 2단계: 통과국 매력도/난이도/유사도/퀵윈
    rows = []
    for code, d in passed:
        items = d["items"]
        att = SC.attractiveness_score(items, peer_items, internal)["score"]
        dif = SC.difficulty_score(items, peer_items, internal)["score"]
        if baseline_items is not None:
            sim = SC.similarity_score(items, baseline_items, internal)["score"]
        else:
            sim = None
        qw = None
        if sim is not None and att is not None and dif is not None:
            qw = SC.quick_win_score(sim, att, dif, internal)
        rows.append({
            "code": code, "country_ko": d.get("country_ko", code),
            "attractiveness": att, "difficulty": dif, "similarity": sim,
            "quick_win_score": qw["score"] if qw else None,
            "quick_win_band": _band10(qw["score"]) if qw else None,
            "qualified": qw["qualified"] if qw else None,
        })

    # 퀵윈 점수 내림차순 순위(None 은 뒤로)
    rows.sort(key=lambda r: (r["quick_win_score"] is not None,
                             r["quick_win_score"] or 0), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows, gate_rows


# ── 탭 빌더 ───────────────────────────────────────────────────────────────
def build_tab_2_0(gate_rows):
    """킬스위치 매트릭스(국가×게이트 통과/탈락)."""
    return {"tab": "2-0", "name": "킬스위치", "blocks": [
        block("kill_switch", "킬스위치 통과/탈락", gate_rows, "status_matrix", "EXT")
    ]}


def build_tab_2_1(rows):
    """매력도 순위(ranking)."""
    ranking = [{"code": r["code"], "country_ko": r["country_ko"],
                "attractiveness": r["attractiveness"]} for r in rows]
    return {"tab": "2-1", "name": "매력도", "blocks": [
        block("attractiveness_ranking", "비즈니스 매력도 순위", ranking, "ranking", "CALC")
    ]}


def build_tab_2_2(rows):
    """IT유사도 히트맵·퀵윈 순위·산점도 좌표 + 상위 3개국 카드."""
    heatmap = [{"code": r["code"], "similarity": r["similarity"],
                "difficulty": r["difficulty"]} for r in rows]
    quickwin = [{"code": r["code"], "country_ko": r["country_ko"], "rank": r["rank"],
                 "quick_win_score": r["quick_win_score"],
                 "quick_win_band": r["quick_win_band"], "qualified": r["qualified"]}
                for r in rows]
    scatter = [{"code": r["code"], "x_attractiveness": r["attractiveness"],
                "y_similarity": r["similarity"]} for r in rows]
    top3 = _profile_cards(rows[:3])
    return {"tab": "2-2", "name": "IT유사도/순위", "blocks": [
        block("it_similarity_heatmap", "IT유사도 히트맵", heatmap, "score_multiaxis", "CALC"),
        block("quick_win_ranking", "퀵윈 순위", quickwin, "ranking", "CALC"),
        block("scatter", "매력도×IT유사도 좌표", scatter, "score_multiaxis", "CALC"),
        block("top3_profiles", "상위 3개국 프로파일", top3, "qualitative", "CALC"),
    ]}


def build_tab_2_summary(loaded, rows):
    """1~3위 KPI + AI 인사이트(권역) + NEWS 카드."""
    top = rows[:3]
    kpi = block("quick_win_top3", "퀵윈 상위 3개국",
                [{"rank": r["rank"], "code": r["code"], "country_ko": r["country_ko"],
                  "band": r["quick_win_band"]} for r in top], "ranking", "CALC")
    # NEWS: 멤버국들의 news item 취합
    news_items = []
    for code, d in loaded:
        for it in d["items"]:
            if it.get("context_type") == "news" and isinstance(it.get("value"), list):
                news_items.append({"code": code, "issues": it["value"]})
    blocks = [kpi,
              block("region_insight", "권역 AI 인사이트", _region_insight(rows),
                    "qualitative", "AI"),
              block("news_scan", "권역 외부 이슈", news_items, "qualitative", "NEWS")]
    return {"tab": "2-요약", "name": "요약", "blocks": blocks}


def build_tab_2_3(loaded):
    """시장 배경: 멤버국 context 항목(브랜드·OEM·구매유형) 취합."""
    blocks = []
    for code, d in loaded:
        for it in d["items"]:
            if it.get("role") == "context" and it.get("context_type") != "news":
                val = it.get("value")
                nature = "ranking" if isinstance(val, list) else "qualitative"
                blocks.append(block(f"{code}_{_slug(it['item'])}",
                                    f"[{code}] {it['item']}", val, nature,
                                    "EXT", _src(it)))
    return {"tab": "2-3", "name": "시장 배경", "blocks": blocks}


# ── 헬퍼 ──────────────────────────────────────────────────────────────────
def _slug(name):
    return "".join(c if c.isalnum() else "_" for c in name).strip("_").lower()


def _profile_cards(rows):
    return [{"rank": r["rank"], "code": r["code"], "country_ko": r["country_ko"],
             "quick_win_band": r["quick_win_band"],
             "attractiveness": r["attractiveness"], "similarity": r["similarity"],
             "qualified": r["qualified"]} for r in rows]


def _region_insight(rows):
    if not rows:
        return "후보국 데이터 없음 — 조사 필요."
    qualified = [r for r in rows if r.get("qualified")]
    if not qualified:
        top = rows[0]
        return (f"퀵윈 임계 충족국 없음. 최상위 후보: {top['country_ko']}({top['code']}) "
                f"— baseline 데이터/추가 후보 조사 필요.")
    names = ", ".join(f"{r['country_ko']}({r['code']})" for r in qualified[:3])
    return f"{len(qualified)}개 후보가 퀵윈 임계 충족. 우선 진입 후보: {names}."


# ── 조립 ──────────────────────────────────────────────────────────────────
def generate_region_report(region, internal, *, report_id):
    """권역 멤버 country 데이터 → 유형2 보고서 JSON(탭 2-0~2-3 + 요약)."""
    loaded, baseline_code, baseline_items = _load_members(region, internal)
    rows, gate_rows = _score_candidates(loaded, baseline_items, internal)

    meta = internal.get("regions", {}).get(region, {})
    return {
        "report_id": report_id,
        "report_type": "type2_region",
        "title": f"{meta.get('name_ko', region)}({meta.get('name_en', region)}) "
                 f"권역 Quick-Win 분석 보고서",
        "target": {"region": region,
                   "evaluated_countries": [c for c, _ in loaded],
                   "baseline": baseline_code},
        "data_snapshot_id": f"SNAP_{region}_CFG{internal.get('version', '?')}",
        "based_on": RID.build_based_on(
            [c for c, _ in loaded], internal,
            schema_version=loaded[0][1].get("schema_version") if loaded else None,
            baseline_code=baseline_code),
        "candidate_count": len(loaded),
        "tabs": [
            build_tab_2_summary(loaded, rows),
            build_tab_2_0(gate_rows),
            build_tab_2_1(rows),
            build_tab_2_2(rows),
            build_tab_2_3(loaded),
        ],
    }


def save_report(report, region, report_id):
    out_dir = REPORT_BASE / region / report_id / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def load_internal():
    with open(INTERNAL_LATEST, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    region = sys.argv[1] if len(sys.argv) > 1 else None
    if not region:
        print("usage: region_report_engine.py <REGION> [REPORT_ID]")
        sys.exit(1)
    internal = load_internal()
    rid = sys.argv[2] if len(sys.argv) > 2 else RID.next_report_id("region", region)
    report = generate_region_report(region, internal, report_id=rid)
    path = save_report(report, region, rid)
    print(f"생성: {path} (후보 {report['candidate_count']}개국)")
    for t in report["tabs"]:
        print(f"  {t['tab']} {t['name']}: {len(t['blocks'])} blocks")
