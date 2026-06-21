#!/usr/bin/env python3
"""
report_id 회귀 테스트 (U6).

- 빈 폴더 → 001, 폴더 추가 후 → 002 (증가).
- 코드별 독립(ES 와 PL 각자 001).
- RPT_*_NNN 패턴만 스캔(구버전 타임스탬프 폴더 무시).
- build_based_on 이 latest 포인터가 아닌 실제 fetched_at 반영.
- 동일 입력 → 동일 based_on(재현성).

pytest 있으면 pytest, 없으면 standalone.
"""

import tempfile
from pathlib import Path

import report_id as RID


def _with_report_base(tmp):
    RID.REPORT_BASE = Path(tmp)


def test_first_id_is_001():
    orig = RID.REPORT_BASE
    with tempfile.TemporaryDirectory() as tmp:
        _with_report_base(tmp)
        try:
            assert RID.next_report_id("country", "ES") == "RPT_CTR_ES_001"
            assert RID.next_report_id("region", "EU") == "RPT_RGN_EU_001"
        finally:
            RID.REPORT_BASE = orig


def test_increments_after_existing():
    orig = RID.REPORT_BASE
    with tempfile.TemporaryDirectory() as tmp:
        _with_report_base(tmp)
        (Path(tmp) / "country" / "ES" / "RPT_CTR_ES_001").mkdir(parents=True)
        (Path(tmp) / "country" / "ES" / "RPT_CTR_ES_002").mkdir(parents=True)
        try:
            assert RID.next_report_id("country", "ES") == "RPT_CTR_ES_003"
        finally:
            RID.REPORT_BASE = orig


def test_per_code_independent():
    orig = RID.REPORT_BASE
    with tempfile.TemporaryDirectory() as tmp:
        _with_report_base(tmp)
        (Path(tmp) / "country" / "ES" / "RPT_CTR_ES_005").mkdir(parents=True)
        try:
            # PL 은 ES 와 무관하게 001 부터
            assert RID.next_report_id("country", "PL") == "RPT_CTR_PL_001"
            assert RID.next_report_id("country", "ES") == "RPT_CTR_ES_006"
        finally:
            RID.REPORT_BASE = orig


def test_ignores_legacy_folders():
    """구버전 타임스탬프 폴더·data/ 는 패턴 불일치 → 무시."""
    orig = RID.REPORT_BASE
    with tempfile.TemporaryDirectory() as tmp:
        _with_report_base(tmp)
        base = Path(tmp) / "country" / "PL"
        (base / "data").mkdir(parents=True)               # 구버전 data 폴더
        (base / "PL_rpt_2026-06-18T1500").mkdir()          # 구버전 타임스탬프
        (base / "RPT_CTR_PL_001").mkdir()                  # 신규 패턴
        try:
            assert RID.next_report_id("country", "PL") == "RPT_CTR_PL_002"
        finally:
            RID.REPORT_BASE = orig


def test_based_on_reflects_fetched_at():
    """실 ES latest 의 fetched_at 이 based_on 에 박힌다(latest 포인터 아님)."""
    internal = {"version": "1.3"}
    based = RID.build_based_on(["ES"], internal, schema_version="1.1")
    # ES latest 가 존재하면 fetched_at(ISO) 반영
    es_v = based["country_versions"].get("ES")
    assert es_v and es_v != "ES_latest", based
    assert based["internal_version"] == "1.3"
    assert based["schema_version"] == "1.1"


def test_based_on_deterministic():
    """동일 입력 → 동일 based_on(재현성)."""
    internal = {"version": "1.3"}
    a = RID.build_based_on(["ES"], internal, schema_version="1.1")
    b = RID.build_based_on(["ES"], internal, schema_version="1.1")
    assert a == b


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
