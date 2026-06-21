#!/usr/bin/env python3
"""
Bedrock 호출 모듈 (U11).

AWS Bedrock(Claude)을 boto3 bedrock-runtime **Converse API** 로 호출한다(가드레일
PLAN: boto3 로 충분, 추가 패키지 불필요). 리전 ap-northeast-2.

제공:
  converse(messages, system, tools, ...)  → Converse API 호출, 원시 응답 반환
  extract_text(response)                   → assistant 텍스트 추출
  extract_tool_uses(response)              → tool_use 블록 추출
  run_tool_loop(messages, tools, handlers) → tool_use→실행→결과 반환 루프(골격)
  extract_json(text)                       → 코드펜스 제거 후 JSON 파싱(리서치용)

가드레일(U13): converse() 에 guardrail_id/guardrail_version 인자를 두어 연결 지점 확보.
웹검색(B3): Bedrock 미지원 → 외부 검색 API 결과를 messages 컨텍스트로 주입하는 방식을
  U12 에서 구현. 이 모듈은 tools 인자로 client-side 도구 정의를 받는 골격만 제공.
"""

import json
import re

DEFAULT_REGION = "ap-northeast-2"
# Bedrock Claude 는 on-demand 직접 호출 불가 → inference profile 필요.
# ap-northeast-2 에서 global cross-region 프로파일이 ACTIVE (list_inference_profiles 확인).
DEFAULT_MODEL = "global.anthropic.claude-opus-4-8"
DEFAULT_MAX_TOKENS = 4096


def make_client(region=DEFAULT_REGION, client=None):
    """bedrock-runtime 클라이언트. 테스트는 client 를 주입해 모킹.

    Claude 의 긴 리서치 응답은 기본 read timeout(60s)을 넘기므로 넉넉히 설정.
    """
    if client is not None:
        return client
    import boto3  # 지연 import — 모듈 로드만으로 AWS 세션 만들지 않음
    from botocore.config import Config
    cfg = Config(read_timeout=600, connect_timeout=15, retries={"max_attempts": 2})
    return boto3.client("bedrock-runtime", region_name=region, config=cfg)


def converse(messages, *, system=None, tools=None, model=DEFAULT_MODEL,
             max_tokens=DEFAULT_MAX_TOKENS, region=DEFAULT_REGION,
             guardrail_id=None, guardrail_version=None, client=None):
    """Converse API 호출. 원시 응답(dict) 반환.

    messages: [{"role":"user"|"assistant", "content":[{"text":...} | {"toolUse":...} | {"toolResult":...}]}]
    system:   문자열 또는 None
    tools:    [{"name","description","input_schema"(JSON Schema)}] 또는 None
    guardrail_*: 주어지면 guardrailConfig 로 연결(U13).
    """
    bedrock = make_client(region, client)
    kwargs = {
        "modelId": model,
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens},
    }
    if system:
        kwargs["system"] = [{"text": system}]
    if tools:
        kwargs["toolConfig"] = {"tools": [_to_tool_spec(t) for t in tools]}
    if guardrail_id:
        kwargs["guardrailConfig"] = {
            "guardrailIdentifier": guardrail_id,
            "guardrailVersion": guardrail_version or "DRAFT",
        }
    return bedrock.converse(**kwargs)


def _to_tool_spec(tool):
    """우리 도구 정의 → Bedrock Converse toolSpec 형식."""
    return {
        "toolSpec": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "inputSchema": {"json": tool.get("input_schema", {"type": "object"})},
        }
    }


# ── 응답 파싱 ─────────────────────────────────────────────────────────────
def _content_blocks(response):
    return (response or {}).get("output", {}).get("message", {}).get("content", [])


def extract_text(response):
    """assistant 응답의 모든 text 블록을 이어붙여 반환."""
    return "".join(b["text"] for b in _content_blocks(response) if "text" in b)


def extract_tool_uses(response):
    """tool_use 블록 목록. 각 {toolUseId, name, input}."""
    out = []
    for b in _content_blocks(response):
        if "toolUse" in b:
            tu = b["toolUse"]
            out.append({"toolUseId": tu["toolUseId"], "name": tu["name"],
                        "input": tu.get("input", {})})
    return out


def stop_reason(response):
    return (response or {}).get("stopReason")


# ── 도구 호출 루프 (골격) ─────────────────────────────────────────────────
def run_tool_loop(messages, tools, handlers, *, system=None, model=DEFAULT_MODEL,
                  max_tokens=DEFAULT_MAX_TOKENS, region=DEFAULT_REGION,
                  guardrail_id=None, guardrail_version=None, client=None,
                  max_turns=8):
    """tool_use → handler 실행 → toolResult 반환 루프.

    handlers: {tool_name: callable(input_dict) -> result_str}
    종료: stopReason != 'tool_use' 이거나 max_turns 도달.
    반환: (final_text, messages)  — messages 는 전체 대화 누적.
    """
    msgs = list(messages)
    for _ in range(max_turns):
        resp = converse(msgs, system=system, tools=tools, model=model,
                        max_tokens=max_tokens, region=region,
                        guardrail_id=guardrail_id, guardrail_version=guardrail_version,
                        client=client)
        # assistant 응답을 대화에 추가
        assistant_content = _content_blocks(resp)
        msgs.append({"role": "assistant", "content": assistant_content})

        if stop_reason(resp) != "tool_use":
            return extract_text(resp), msgs

        # tool_use 실행 → toolResult 블록 모아 user 메시지로
        results = []
        for tu in extract_tool_uses(resp):
            handler = handlers.get(tu["name"])
            if handler is None:
                result_text = f"error: no handler for tool '{tu['name']}'"
                is_error = True
            else:
                try:
                    result_text = handler(tu["input"])
                    is_error = False
                except Exception as e:  # noqa: BLE001 — 도구 오류를 모델에 전달
                    result_text = f"error: {e}"
                    is_error = True
            block = {"toolResult": {
                "toolUseId": tu["toolUseId"],
                "content": [{"text": str(result_text)}],
            }}
            if is_error:
                block["toolResult"]["status"] = "error"
            results.append(block)
        msgs.append({"role": "user", "content": results})

    # max_turns 초과 — 마지막 텍스트라도 반환
    return extract_text(resp), msgs


# ── JSON 추출 (리서치 응답 파싱용, U12) ───────────────────────────────────
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def extract_json(text):
    """모델 응답에서 JSON 파싱. 코드펜스(```json ... ```)가 있으면 제거.

    프롬프트가 '순수 JSON만'을 안 지킬 때 대비(country_research_prompt §운영팁).
    파싱 실패 시 ValueError.
    """
    cleaned = _FENCE.sub("", text).strip()
    # 첫 { ~ 마지막 } 사이만 시도(앞뒤 설명 텍스트 제거)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


# ── 단순 텍스트 질의 (챗봇 기본, U14) ─────────────────────────────────────
def ask(prompt, *, system=None, model=DEFAULT_MODEL, region=DEFAULT_REGION,
        guardrail_id=None, guardrail_version=None, client=None,
        max_tokens=DEFAULT_MAX_TOKENS):
    """단일 사용자 프롬프트 → 텍스트 응답(편의 함수)."""
    resp = converse([{"role": "user", "content": [{"text": prompt}]}],
                    system=system, model=model, region=region,
                    guardrail_id=guardrail_id, guardrail_version=guardrail_version,
                    client=client, max_tokens=max_tokens)
    return extract_text(resp)
