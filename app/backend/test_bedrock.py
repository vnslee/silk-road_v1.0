#!/usr/bin/env python3
"""
bedrock 호출 모듈 테스트 (U11).

실제 AWS 호출 없이 가짜 client(FakeBedrock)로 Converse 응답 파싱·tool_use 추출·
도구 루프·JSON 추출을 검증한다.

실행: .venv/bin/python -m pytest test_bedrock.py -v
"""

import json

from services import bedrock as B


class FakeBedrock:
    """boto3 bedrock-runtime 스텁. converse() 호출마다 미리 큐잉한 응답 반환."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def _text_response(text, stop="end_turn"):
    return {"output": {"message": {"content": [{"text": text}]}}, "stopReason": stop}


def _tool_response(tool_use_id, name, inp):
    return {"output": {"message": {"content": [
        {"toolUse": {"toolUseId": tool_use_id, "name": name, "input": inp}}]}},
        "stopReason": "tool_use"}


# ── 기본 호출/파싱 ─────────────────────────────────────────────────────────
def test_converse_extracts_text():
    fake = FakeBedrock([_text_response("안녕하세요")])
    resp = B.converse([{"role": "user", "content": [{"text": "hi"}]}], client=fake)
    assert B.extract_text(resp) == "안녕하세요"


def test_converse_passes_system_and_tools():
    fake = FakeBedrock([_text_response("ok")])
    B.converse([{"role": "user", "content": [{"text": "hi"}]}],
               system="너는 진단 컨설턴트다",
               tools=[{"name": "web_search", "description": "검색",
                       "input_schema": {"type": "object"}}],
               client=fake)
    call = fake.calls[0]
    assert call["system"] == [{"text": "너는 진단 컨설턴트다"}]
    assert call["toolConfig"]["tools"][0]["toolSpec"]["name"] == "web_search"


def test_guardrail_config_injected():
    fake = FakeBedrock([_text_response("ok")])
    B.converse([{"role": "user", "content": [{"text": "hi"}]}],
               guardrail_id="gr-123", guardrail_version="2", client=fake)
    assert fake.calls[0]["guardrailConfig"] == {
        "guardrailIdentifier": "gr-123", "guardrailVersion": "2"}


def test_extract_tool_uses():
    resp = _tool_response("tu-1", "web_search", {"query": "폴란드 오토금융"})
    tus = B.extract_tool_uses(resp)
    assert len(tus) == 1
    assert tus[0]["name"] == "web_search" and tus[0]["input"]["query"] == "폴란드 오토금융"


# ── 도구 루프 ──────────────────────────────────────────────────────────────
def test_tool_loop_executes_handler_and_finishes():
    """1라운드 tool_use → handler 실행 → 2라운드 최종 텍스트."""
    fake = FakeBedrock([
        _tool_response("tu-1", "lookup", {"q": "x"}),
        _text_response("결과는 42입니다"),
    ])
    calls = {}

    def lookup(inp):
        calls["got"] = inp
        return "42"

    final, msgs = B.run_tool_loop(
        [{"role": "user", "content": [{"text": "lookup x"}]}],
        tools=[{"name": "lookup", "input_schema": {"type": "object"}}],
        handlers={"lookup": lookup}, client=fake)
    assert final == "결과는 42입니다"
    assert calls["got"] == {"q": "x"}
    # 대화: user → assistant(tool_use) → user(toolResult) → assistant(text)
    assert msgs[-2]["content"][0]["toolResult"]["toolUseId"] == "tu-1"


def test_tool_loop_missing_handler_marks_error():
    fake = FakeBedrock([
        _tool_response("tu-1", "unknown", {}),
        _text_response("done"),
    ])
    final, msgs = B.run_tool_loop(
        [{"role": "user", "content": [{"text": "go"}]}],
        tools=[], handlers={}, client=fake)
    tr = msgs[-2]["content"][0]["toolResult"]
    assert tr["status"] == "error" and "no handler" in tr["content"][0]["text"]


def test_tool_loop_handler_exception_marks_error():
    fake = FakeBedrock([
        _tool_response("tu-1", "boom", {}),
        _text_response("recovered"),
    ])

    def boom(inp):
        raise RuntimeError("터짐")

    final, msgs = B.run_tool_loop(
        [{"role": "user", "content": [{"text": "go"}]}],
        tools=[{"name": "boom", "input_schema": {"type": "object"}}],
        handlers={"boom": boom}, client=fake)
    assert final == "recovered"
    assert msgs[-2]["content"][0]["toolResult"]["status"] == "error"


# ── JSON 추출 ──────────────────────────────────────────────────────────────
def test_extract_json_plain():
    assert B.extract_json('{"code":"PL","tier":2}') == {"code": "PL", "tier": 2}


def test_extract_json_code_fence():
    text = '```json\n{"code":"DE"}\n```'
    assert B.extract_json(text) == {"code": "DE"}


def test_extract_json_with_surrounding_text():
    text = '다음은 결과입니다:\n{"x": 1}\n이상입니다.'
    assert B.extract_json(text) == {"x": 1}


def test_extract_json_invalid_raises():
    try:
        B.extract_json("not json at all")
        assert False, "should raise"
    except ValueError:
        pass


# ── ask 편의 함수 ──────────────────────────────────────────────────────────
def test_ask():
    fake = FakeBedrock([_text_response("답변입니다")])
    assert B.ask("질문", client=fake) == "답변입니다"


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
