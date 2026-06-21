#!/usr/bin/env python3
"""
Report ID / 재현성 도장 (U6).

report_generate_req.md "보고서 생성 규칙" 의 채번·메타 로직을 한 곳에 모은다.
country(U3)·region(U4) 엔진이 공유한다.

채번 형식:  RPT_{CTR|RGN}_{코드}_{NNN}
  - CTR=유형1(국가, ISO alpha-2) / RGN=유형2(권역, 사내코드 EU·NA·SA·APAC)
  - NNN: 대상 코드별 독립 3자리(PL 의 001 과 GB 의 001 은 별개)
  - "새로 생성" 시 대상 폴더 스캔 → 최대 NNN+1. 없으면 001.
  - 시점 구분은 폴더명이 아니라 내부 메타(data_snapshot_id)로.

재현성:  based_on 에 입력 스냅샷의 **실제 버전**(latest 포인터가 아니라 fetched_at)을
  박아, 재조사로 순위가 바뀌어도 "어느 시점 데이터로 만든 보고서인지" 추적 가능.
"""

import json
import re
from pathlib import Path

STORAGE = Path(__file__).resolve().parent.parent.parent / "storage"
COUNTRY_DIR = STORAGE / "data" / "research" / "country"
REPORT_BASE = STORAGE / "report"

# RPT_CTR_ES_001 / RPT_RGN_EU_012 — 끝의 NNN 추출
_ID_RE = re.compile(r"^RPT_(?:CTR|RGN)_[A-Z0-9]+_(\d{3})$")

TYPE_PREFIX = {"country": "CTR", "region": "RGN"}


def next_report_id(report_kind, code):
    """다음 보고서 ID 채번. report_kind='country'|'region', code=대상코드.

    대상 폴더(report/<kind>/<code>/) 하위의 RPT_*_NNN 폴더만 스캔한다
    (구버전 타임스탬프 폴더·data/ 등은 패턴 불일치로 자동 무시).
    """
    prefix = TYPE_PREFIX[report_kind]
    target_dir = REPORT_BASE / report_kind / code
    max_nnn = 0
    if target_dir.exists():
        for child in target_dir.iterdir():
            if not child.is_dir():
                continue
            m = _ID_RE.match(child.name)
            if m:
                max_nnn = max(max_nnn, int(m.group(1)))
    return f"RPT_{prefix}_{code}_{max_nnn + 1:03d}"


def _snapshot_version(code):
    """국가 latest 의 실제 스냅샷 식별자(fetched_at). 없으면 'latest' 폴백."""
    path = COUNTRY_DIR / code / f"{code}_latest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # fetched_at(ISO) 을 그대로 스냅샷 ID 로 사용. 콜론 압축은 안 함(메타는 표시용).
        return data.get("fetched_at") or "latest"
    except (json.JSONDecodeError, OSError):
        return "latest"


def build_based_on(country_codes, internal, *, schema_version, baseline_code=None):
    """재현성 도장. country_codes 각각의 실제 fetched_at 을 박는다.

    country_codes: 보고서가 참조한 국가 코드 리스트.
    internal: 룰셋 dict(version 읽음).
    """
    versions = {}
    for c in country_codes:
        v = _snapshot_version(c)
        if v is not None:
            versions[c] = v
    based = {
        "country_versions": versions,
        "internal_version": internal.get("version"),
        "schema_version": schema_version,
    }
    if baseline_code:
        based["baseline_version"] = _snapshot_version(baseline_code)
    return based


def snapshot_id(code, internal):
    """data_snapshot_id — 시점 구분용 내부 메타(국가 fetched_at + 룰셋 버전)."""
    fa = _snapshot_version(code) or "unknown"
    return f"SNAP_{code}_{fa}_CFG{internal.get('version', '?')}"


if __name__ == "__main__":
    import sys
    kind = sys.argv[1] if len(sys.argv) > 1 else "country"
    code = sys.argv[2] if len(sys.argv) > 2 else "ES"
    print("next id:", next_report_id(kind, code))
    print("snapshot version:", _snapshot_version(code))
