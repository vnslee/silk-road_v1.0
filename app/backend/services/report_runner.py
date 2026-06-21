#!/usr/bin/env python3
"""
보고서 생성 러너 (U9) — 파이프라인을 PS2 5단계로 실행하며 진행률 갱신.

엔진(U3 country / U4 region)의 개별 탭 빌더를 단계 순서로 호출해, 각 단계 완료마다
job 상태를 갱신한다(B2 비동기). 마지막 '결과 생성' 단계에서 채번(U6)·저장·렌더(U5).

단계 → 탭 매핑:
  country: 시장=1-4 / 규제=1-2(+게이트) / 상품=1-3 / 시스템=1-1 / 결과=1-0+저장+렌더
  region:  시장=2-1 / 규제=2-0 / 상품=2-3 / 시스템=2-2 / 결과=2-요약+저장+렌더
"""

import sys
from pathlib import Path

from services import jobs

_GEN = Path(__file__).resolve().parent.parent / "engine" / "generation"
_REND = Path(__file__).resolve().parent.parent / "engine" / "rendering"
for p in (str(_GEN), str(_REND)):
    if p not in sys.path:
        sys.path.insert(0, p)

import country_report_engine as CE  # noqa: E402
import region_report_engine as RE   # noqa: E402
import report_id as RID             # noqa: E402
import report_rendering_engine as RR  # noqa: E402


def run_country(job_id, code):
    """country 보고서를 5단계로 생성. 예외는 호출부(BackgroundTask)에서 fail 처리."""
    data = CE.load_country(code)
    internal = CE.load_internal()
    items = data["items"]
    region = data["region"]
    baseline_items, baseline_code = CE._baseline_items(region, internal)

    # 시장
    jobs.start_step(job_id, "market")
    tab_1_4 = CE.build_tab_1_4(items)
    jobs.finish_step(job_id, "market")

    # 시스템(유사도) — 규제/상품이 유사도 점수에 의존하므로 먼저 계산
    jobs.start_step(job_id, "system")
    tab_1_1 = CE.build_tab_1_1(items, baseline_items, internal)
    sim = tab_1_1.get("score")
    jobs.finish_step(job_id, "system")

    # 규제(결정트리)
    jobs.start_step(job_id, "regulation")
    tab_1_2 = CE.build_tab_1_2(sim)
    jobs.finish_step(job_id, "regulation")

    # 상품(TCO)
    jobs.start_step(job_id, "product")
    tab_1_3 = CE.build_tab_1_3(sim, internal, baseline_code)
    jobs.finish_step(job_id, "product")

    # 결과 생성: 요약 + 조립 + 채번 + 저장 + 렌더
    jobs.start_step(job_id, "result")
    tco_val = next((b["value"] for b in tab_1_3["blocks"]
                    if b["key"] == "system_10y_tco"), None)
    tab_1_0 = CE.build_tab_1_0(data, sim, tab_1_2["branch"], tco_val, items)
    report_id = RID.next_report_id("country", code)
    report = {
        "report_id": report_id, "report_type": "type1_country",
        "title": f"{data.get('country_ko', code)} 오토파이낸스 진출 비용·TCO 보고서",
        "target": {"country": code, "base_country": baseline_code},
        "region": region,
        "data_snapshot_id": RID.snapshot_id(code, internal),
        "based_on": RID.build_based_on([code], internal,
                                       schema_version=data.get("schema_version"),
                                       baseline_code=baseline_code),
        "tabs": [tab_1_0, tab_1_1, tab_1_2, tab_1_3, tab_1_4],
    }
    json_path = CE.save_report(report, code, report_id)
    RR.render_from_path(json_path)
    jobs.finish_step(job_id, "result")
    jobs.complete(job_id, report_id)
    return report_id


def run_region(job_id, region):
    """region 보고서를 5단계로 생성."""
    internal = RE.load_internal()
    loaded, baseline_code, baseline_items = RE._load_members(region, internal)
    rows, gate_rows = RE._score_candidates(loaded, baseline_items, internal)

    jobs.start_step(job_id, "market")
    tab_2_1 = RE.build_tab_2_1(rows)
    jobs.finish_step(job_id, "market")

    jobs.start_step(job_id, "regulation")
    tab_2_0 = RE.build_tab_2_0(gate_rows)
    jobs.finish_step(job_id, "regulation")

    jobs.start_step(job_id, "product")
    tab_2_3 = RE.build_tab_2_3(loaded)
    jobs.finish_step(job_id, "product")

    jobs.start_step(job_id, "system")
    tab_2_2 = RE.build_tab_2_2(rows)
    jobs.finish_step(job_id, "system")

    jobs.start_step(job_id, "result")
    tab_sum = RE.build_tab_2_summary(loaded, rows)
    report_id = RID.next_report_id("region", region)
    meta = internal.get("regions", {}).get(region, {})
    report = {
        "report_id": report_id, "report_type": "type2_region",
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
        "tabs": [tab_sum, tab_2_0, tab_2_1, tab_2_2, tab_2_3],
    }
    json_path = RE.save_report(report, region, report_id)
    RR.render_from_path(json_path)
    jobs.finish_step(job_id, "result")
    jobs.complete(job_id, report_id)
    return report_id


def run(job_id, kind, code):
    """kind 분기 + 예외 → job fail."""
    try:
        if kind == "country":
            run_country(job_id, code)
        elif kind == "region":
            run_region(job_id, code)
        else:
            jobs.fail(job_id, f"unknown kind '{kind}'")
    except Exception as e:  # noqa: BLE001 — 백그라운드에서 어떤 예외든 job 에 기록
        jobs.fail(job_id, f"{type(e).__name__}: {e}")
