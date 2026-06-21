#!/usr/bin/env python3
"""
보고서 생성 러너 (U9 → 원격 엔진 통합판).

원격 엔진(CountryReportEngine / RegionReportEngine)을 호출해 보고서 JSON 생성 +
원격 렌더러(CountryReportRenderer / RegionReportRenderer)로 HTML 생성.
PS2 5단계 진행률은 표시용으로 매핑(원격 엔진은 단일 호출이라 단계 경계는 관찰적).

경로:
  country 입력: storage/data/research/country/<CODE>/<CODE>_latest.json
  region  입력: storage/data/research/region/<RGN>/<RGN>_latest.json
  internal:     storage/data/internal/internal_latest.json
  출력:         storage/report/...  (원격 엔진이 채번·저장)
"""

import sys
from pathlib import Path

from services import jobs

_BACKEND = Path(__file__).resolve().parent.parent
STORAGE = _BACKEND / "storage"
_GEN = _BACKEND / "engine" / "generation"
_REND = _BACKEND / "engine" / "rendering"
for p in (str(_GEN), str(_REND)):
    if p not in sys.path:
        sys.path.insert(0, p)

INTERNAL = str(STORAGE / "data" / "internal" / "internal_latest.json")
REPORT_BASE = str(STORAGE / "report")


def run_country(job_id, code):
    """country 보고서 생성(원격 엔진) + HTML 렌더. 진행률 갱신."""
    from country_report_engine import CountryReportEngine
    country_path = str(STORAGE / "data" / "research" / "country" / code / f"{code}_latest.json")

    jobs.start_step(job_id, "market")
    engine = CountryReportEngine(country_path, INTERNAL, REPORT_BASE)
    if not engine.load_country_data() or not engine.load_internal_data():
        raise RuntimeError(f"country '{code}' 데이터 로드 실패")
    jobs.finish_step(job_id, "market")

    jobs.start_step(job_id, "system")
    report = engine.generate_type1_report()
    jobs.finish_step(job_id, "system")
    jobs.start_step(job_id, "regulation"); jobs.finish_step(job_id, "regulation")
    jobs.start_step(job_id, "product"); jobs.finish_step(job_id, "product")

    jobs.start_step(job_id, "result")
    json_path = engine.save_type1_report(report)
    _render_country(json_path)
    jobs.finish_step(job_id, "result")
    jobs.complete(job_id, report.get("report_id"))


def run_region(job_id, region):
    """region 보고서 생성(원격 엔진) + HTML 렌더."""
    from region_report_engine import RegionReportEngine
    region_path = str(STORAGE / "data" / "research" / "region" / region / f"{region}_latest.json")

    jobs.start_step(job_id, "market")
    engine = RegionReportEngine(region_path, INTERNAL, REPORT_BASE)
    if not engine.load_region_data() or not engine.load_internal_data():
        raise RuntimeError(f"region '{region}' 데이터 로드 실패")
    jobs.finish_step(job_id, "market")
    jobs.start_step(job_id, "regulation"); jobs.finish_step(job_id, "regulation")
    jobs.start_step(job_id, "product"); jobs.finish_step(job_id, "product")

    jobs.start_step(job_id, "system")
    report = engine.generate_type2_report()
    jobs.finish_step(job_id, "system")

    jobs.start_step(job_id, "result")
    json_path = engine.save_type2_report(report)
    _render_region(json_path)
    jobs.finish_step(job_id, "result")
    jobs.complete(job_id, report.get("report_id"))


def _render_country(json_path):
    try:
        from country_report_renderer import CountryReportRenderer
        r = CountryReportRenderer(str(json_path))
        if r.load_report():
            r.save_html()
    except Exception:  # noqa: BLE001 — HTML 실패는 보고서 생성 자체를 막지 않음
        pass


def _render_region(json_path):
    try:
        from region_report_renderer import RegionReportRenderer
        r = RegionReportRenderer(str(json_path))
        if r.load_report():
            r.save_html()
    except Exception:  # noqa: BLE001
        pass


def run(job_id, kind, code):
    """kind 분기 + 예외 → job fail."""
    try:
        if kind == "country":
            run_country(job_id, code)
        elif kind == "region":
            run_region(job_id, code)
        else:
            jobs.fail(job_id, f"unknown kind '{kind}'")
    except Exception as e:  # noqa: BLE001
        jobs.fail(job_id, f"{type(e).__name__}: {e}")
