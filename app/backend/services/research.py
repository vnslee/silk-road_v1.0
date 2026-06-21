#!/usr/bin/env python3
"""
country 리서치 Agent (U12).

국가 코드 → country_research_prompt.md 프롬프트로 Bedrock(Claude) 호출 → v1.1 스키마
준수 country JSON 생성 → 스냅샷 + latest 포인터 저장.

명세 준수 (md):
  - ROADMAP 2차: "research 프롬프트·스키마를 실제 Bedrock 호출로 연결"
  - 순수 Bedrock 호출(외부 검색 API 없음, B3). NEWS 는 화이트리스트 출처로 채우되
    불확실하면 "조사 필요"(country_research_prompt 환각 금지).
  - 저장 경로/명명: country_research_prompt §저장경로 + schema §0.
  - 생성 후 U1 검증기(validate_country)로 스키마 검증.

흐름: load_prompt → bedrock.ask → extract_json → inject meta → validate → save
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent          # app/backend
STORAGE = BASE / "storage"
COUNTRY_DIR = STORAGE / "data" / "research" / "country"
PROMPT_PATH = (BASE.parent.parent / "architecture" / "research"
               / "country_research_prompt.md")

from services import bedrock as BR  # noqa: E402

# U1 검증기 import (validation 폴더)
_VAL = BASE / "validation"
if str(_VAL) not in sys.path:
    sys.path.insert(0, str(_VAL))
import validate_data as V  # noqa: E402

SCHEMA_VERSION = "1.1"

# 권역 매핑 — 국가코드 → region (internal.regions 와 일치해야 함)
# 프롬프트의 {REGION} 치환용. 모르는 코드는 호출부에서 명시.
DEFAULT_SEGMENT = "개인 신차 / B2B 리스"


class ResearchError(Exception):
    """리서치 실패(호출·파싱·검증)."""


def _extract_prompt_template(md_text):
    """country_research_prompt.md 의 ``` 펜스 안 프롬프트 본문 추출.

    문서는 '## 1. 리서치 프롬프트' 아래 ``` ... ``` 로 프롬프트를 감싼다.
    첫 코드펜스 블록을 프롬프트로 사용.
    """
    lines = md_text.splitlines()
    inside, buf = False, []
    for ln in lines:
        if ln.strip().startswith("```"):
            if inside:
                break          # 첫 블록 끝
            inside = True
            continue
        if inside:
            buf.append(ln)
    if not buf:
        raise ResearchError("프롬프트 코드펜스 블록을 찾지 못함")
    return "\n".join(buf)


def load_prompt(country, region, segment=DEFAULT_SEGMENT, prompt_path=PROMPT_PATH):
    """프롬프트 템플릿 로드 + 치환."""
    md = Path(prompt_path).read_text(encoding="utf-8")
    tmpl = _extract_prompt_template(md)
    return (tmpl.replace("{COUNTRY}", country)
                .replace("{REGION}", region)
                .replace("{SEGMENT}", segment))


def _timestamp_compact(iso_ts):
    """ISO fetched_at → 파일명용 압축(YYYY-MM-DDTHHMM). 콜론 제거."""
    # "2026-06-21T12:00:00+09:00" → "2026-06-21T1200"
    date, _, rest = iso_ts.partition("T")
    hhmm = rest[:5].replace(":", "")
    return f"{date}T{hhmm}"


def generate_country(country_name, code, region, *, fetched_at,
                     segment=DEFAULT_SEGMENT, client=None, model=BR.DEFAULT_MODEL,
                     guardrail_id=None, guardrail_version=None):
    """국가 리서치 → 검증된 country dict 반환(저장은 save_country).

    fetched_at: ISO 타임스탬프(시스템 주입 — 외부 randomness 회피 위해 호출부가 전달).
    client: 테스트용 Bedrock 스텁 주입.
    """
    prompt = load_prompt(country_name, region, segment)
    # country JSON(48+ 항목)은 길다 — 넉넉한 출력 한도. read_timeout 은 client 에서 600s.
    raw = BR.ask(prompt, model=model, client=client,
                 guardrail_id=guardrail_id, guardrail_version=guardrail_version,
                 max_tokens=32000)
    try:
        data = BR.extract_json(raw)
    except ValueError as e:
        raise ResearchError(f"JSON 파싱 실패: {e}")

    # 시스템 주입 메타(프롬프트가 비워둬도 됨)
    data["code"] = code
    data["region"] = region
    data.setdefault("country", country_name)
    data["schema_version"] = SCHEMA_VERSION
    data["fetched_at"] = fetched_at
    data.setdefault("fetched_by", "ai")
    data.setdefault("is_baseline", False)

    errs = V.validate_country(data, label=code)
    if errs:
        raise ResearchError(f"스키마 검증 실패({len(errs)}건): {errs[:3]}")
    return data


def save_country(data, code, *, country_dir=None):
    """스냅샷 + latest 포인터 저장. (snapshot_path, latest_path) 반환."""
    cdir = Path(country_dir) if country_dir else (COUNTRY_DIR)
    out_dir = cdir / code
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = _timestamp_compact(data["fetched_at"])
    import json
    snapshot = out_dir / f"{code}_{ts}.json"
    latest = out_dir / f"{code}_latest.json"
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    snapshot.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    return snapshot, latest


def research_country(country_name, code, region, *, fetched_at, segment=DEFAULT_SEGMENT,
                     client=None, country_dir=None, model=BR.DEFAULT_MODEL,
                     guardrail_id=None, guardrail_version=None):
    """end-to-end: 생성→검증→저장. (data, snapshot_path, latest_path) 반환."""
    data = generate_country(country_name, code, region, fetched_at=fetched_at,
                            segment=segment, client=client, model=model,
                            guardrail_id=guardrail_id, guardrail_version=guardrail_version)
    snap, latest = save_country(data, code, country_dir=country_dir)
    return data, snap, latest


if __name__ == "__main__":
    # CLI: research.py <COUNTRY_NAME> <CODE> <REGION> [fetched_at]
    if len(sys.argv) < 4:
        print("usage: research.py <COUNTRY_NAME> <CODE> <REGION> [fetched_at_iso]")
        sys.exit(1)
    name, code, region = sys.argv[1], sys.argv[2].upper(), sys.argv[3]
    # fetched_at 은 외부 주입(스크립트에서 now() 사용 — 엔진 모듈은 순수 유지)
    if len(sys.argv) > 4:
        ts = sys.argv[4]
    else:
        from datetime import datetime, timezone, timedelta
        kst = timezone(timedelta(hours=9))
        ts = datetime.now(kst).replace(microsecond=0).isoformat()
    print(f"리서치 시작: {name} ({code}, {region}) @ {ts}")
    data, snap, latest = research_country(name, code, region, fetched_at=ts)
    print(f"✓ 생성 완료: {len(data.get('items', []))} items")
    print(f"  스냅샷: {snap}")
    print(f"  latest: {latest}")
