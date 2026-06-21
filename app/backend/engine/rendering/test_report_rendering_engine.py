#!/usr/bin/env python3
"""
report_rendering_engine 회귀 테스트 (U5).

- ES(country)·EU(region) 보고서 JSON → HTML 생성.
- 모든 데이터 블록에 source_flag 뱃지가 렌더된다(배지 없는 수치 = 오류).
- nature 7종 렌더러가 모두 존재한다.
- 외부 JS 의존 0 (weasyprint 호환).

pytest 있으면 pytest, 없으면 standalone.
"""

import re

import report_rendering_engine as RR


def _sample_report():
    """7종 nature 를 모두 포함하는 합성 보고서."""
    return {
        "report_id": "TST_001", "report_type": "type1_country",
        "title": "테스트 보고서", "target": {"country": "ES", "base_country": "UK"},
        "based_on": {"internal_version": "1.3"},
        "tabs": [{
            "tab": "1-X", "name": "전체 nature",
            "blocks": [
                {"key": "sv", "label": "단일값", "value": 42,
                 "nature": "single_value", "source_flag": "CALC", "source": {}},
                {"key": "ts", "label": "시계열", "nature": "timeseries",
                 "source_flag": "EXT", "source": {"org": "ACEA", "tier": 2},
                 "value": {"history": [{"year": 2021, "value": 10}, {"year": 2022, "value": 20}],
                           "forecast": [{"year": 2023, "value": 30}], "cagr_hist": 41.4}},
                {"key": "rk", "label": "순위", "nature": "ranking", "source_flag": "CALC",
                 "source": {}, "value": [{"country_ko": "스페인", "attractiveness": 80},
                                         {"country_ko": "독일", "attractiveness": 40}]},
                {"key": "comp", "label": "구성비", "nature": "composition", "source_flag": "EXT",
                 "source": {}, "value": [{"name": "할부", "value": 60}, {"name": "리스", "value": 40}]},
                {"key": "sma", "label": "다축", "nature": "score_multiaxis", "source_flag": "CALC",
                 "source": {}, "value": {"시스템": 80, "규제": 60}},
                {"key": "ql", "label": "정성", "nature": "qualitative", "source_flag": "AI",
                 "source": {}, "value": "서술 텍스트"},
                {"key": "sm", "label": "킬스위치", "nature": "status_matrix", "source_flag": "EXT",
                 "source": {}, "value": [{"code": "ES", "passed": True, "fail_items": [], "flag_items": []},
                                         {"code": "XX", "passed": False, "fail_items": ["송금"], "flag_items": []}]},
            ]}],
    }


def test_all_natures_have_renderer():
    for nature in ("single_value", "timeseries", "ranking", "composition",
                   "score_multiaxis", "qualitative", "status_matrix"):
        assert nature in RR.NATURE_RENDERERS, f"{nature} 렌더러 없음"


def test_every_block_has_badge():
    """블록 수 == 뱃지 수 (배지 없는 수치 0건)."""
    report = _sample_report()
    out = RR.render_report(report)
    n_blocks = sum(len(t["blocks"]) for t in report["tabs"])
    n_badges = len(re.findall(r'class="flag flag-', out))
    assert n_badges >= n_blocks, f"badges {n_badges} < blocks {n_blocks}"


def test_no_external_js():
    """weasyprint 호환: <script> 태그·CDN JS 0건."""
    out = RR.render_report(_sample_report())
    assert "<script" not in out.lower(), "외부/인라인 JS 발견"
    assert "cdn.tailwindcss" not in out, "Tailwind CDN 발견"


def test_placeholder_for_null_value():
    """value=None 이면 '조사 필요' 플레이스홀더(빈 차트 금지)."""
    report = _sample_report()
    report["tabs"][0]["blocks"] = [
        {"key": "x", "label": "없음", "value": None, "nature": "single_value",
         "source_flag": "EXT", "source": {"note": "baseline 없음"}}]
    out = RR.render_report(report)
    assert "baseline 없음" in out and "placeholder" in out


def test_real_es_renders():
    """실 ES 보고서(있으면) 렌더 — draft 산출물 사용."""
    import json
    p = RR.REPORT / "country" / "ES" / "draft" / "data" / "ES_rpt_draft.json"
    if not p.exists():
        return  # U3 미생성 시 skip
    report = json.loads(p.read_text(encoding="utf-8"))
    out = RR.render_report(report)
    assert "<html" in out
    assert 'class="masthead"' in out


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
