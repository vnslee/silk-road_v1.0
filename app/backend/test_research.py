#!/usr/bin/env python3
"""
country 리서치 Agent 테스트 (U12).

모킹 Bedrock(가짜 응답)으로 생성→검증→저장 흐름을 검증한다. 실제 ES latest 를
유효 응답 템플릿으로 사용해(스키마 통과 보장) Bedrock 이 그 JSON 을 반환했다고 가정.

실행: .venv/bin/python -m pytest test_research.py -v
"""

import json
import tempfile
from pathlib import Path

from services import research as R


def _valid_country_json():
    """실 ES latest 를 응답 본문으로 사용(v1.1 스키마 통과 보장)."""
    es = R.COUNTRY_DIR / "ES" / "ES_latest.json"
    return es.read_text(encoding="utf-8")


class FakeBedrockText:
    """ask()가 호출하는 converse 스텁 — 고정 텍스트(JSON)를 응답."""

    def __init__(self, text):
        self._text = text
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"content": [{"text": self._text}]}},
                "stopReason": "end_turn"}


# ── 프롬프트 로드/치환 ─────────────────────────────────────────────────────
def test_load_prompt_substitutes():
    p = R.load_prompt("Germany", "EU", "개인 신차")
    assert "Germany" in p and "EU" in p
    assert "{COUNTRY}" not in p and "{REGION}" not in p


def test_prompt_template_extracted():
    """프롬프트 본문(역할/조사항목)이 추출되는지."""
    p = R.load_prompt("X", "EU")
    assert "오토파이낸스" in p or "조사" in p


# ── 생성 흐름 ──────────────────────────────────────────────────────────────
def test_generate_injects_meta_and_validates():
    fake = FakeBedrockText(_valid_country_json())
    data = R.generate_country("Spain", "ES", "EU",
                              fetched_at="2026-06-21T12:00:00+09:00", client=fake)
    # 시스템 주입 메타
    assert data["code"] == "ES"
    assert data["schema_version"] == "1.1"
    assert data["fetched_at"] == "2026-06-21T12:00:00+09:00"
    assert data["fetched_by"] == "ai"


def test_generate_code_fence_response():
    """모델이 ```json 펜스로 감싸도 파싱 성공."""
    fenced = "```json\n" + _valid_country_json() + "\n```"
    fake = FakeBedrockText(fenced)
    data = R.generate_country("Spain", "ES", "EU",
                              fetched_at="2026-06-21T12:00:00+09:00", client=fake)
    assert data["code"] == "ES"


def test_generate_invalid_json_raises():
    fake = FakeBedrockText("죄송하지만 JSON을 만들 수 없습니다")
    try:
        R.generate_country("X", "XX", "EU",
                           fetched_at="2026-06-21T12:00:00+09:00", client=fake)
        assert False, "should raise"
    except R.ResearchError as e:
        assert "JSON" in str(e)


def test_generate_schema_violation_raises():
    """tier=5 로 오염된 응답 → 검증 실패."""
    bad = json.loads(_valid_country_json())
    bad["items"][0]["tier"] = 5
    fake = FakeBedrockText(json.dumps(bad, ensure_ascii=False))
    try:
        R.generate_country("Spain", "ES", "EU",
                           fetched_at="2026-06-21T12:00:00+09:00", client=fake)
        assert False, "should raise"
    except R.ResearchError as e:
        assert "검증 실패" in str(e)


# ── 저장 ───────────────────────────────────────────────────────────────────
def test_save_creates_snapshot_and_latest():
    fake = FakeBedrockText(_valid_country_json())
    with tempfile.TemporaryDirectory() as tmp:
        data, snap, latest = R.research_country(
            "Spain", "ES", "EU", fetched_at="2026-06-21T12:00:00+09:00",
            client=fake, country_dir=tmp)
        # 스냅샷 파일명 = ES_2026-06-21T1200.json (콜론 제거)
        assert snap.name == "ES_2026-06-21T1200.json"
        assert latest.name == "ES_latest.json"
        # 둘 다 동일 내용
        assert snap.read_text() == latest.read_text()
        # latest 가 유효 JSON
        assert json.loads(latest.read_text())["code"] == "ES"


def test_save_new_country_creates_dir():
    """신규국(폴더 없음) → 폴더 생성."""
    fake = FakeBedrockText(_valid_country_json())
    with tempfile.TemporaryDirectory() as tmp:
        _, snap, _ = R.research_country(
            "Spain", "ZZ", "EU", fetched_at="2026-06-21T09:00:00+09:00",
            client=fake, country_dir=tmp)
        # code 는 주입되어 ZZ 로 저장되지만 내용은 ES(템플릿) — 폴더 생성 확인
        assert (Path(tmp) / "ZZ").is_dir()


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
