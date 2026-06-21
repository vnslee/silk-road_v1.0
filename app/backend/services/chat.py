#!/usr/bin/env python3
"""
챗봇 응답 로직 (U14) — web_design_spec §6.5 질의응답 분기.

흐름:
  국가/권역 질문 → 보유 정보 있나?
    있음 → 기존 정보로 답변 (Bedrock + 보유 JSON 을 grounding 으로 주입)
    없음 → "외부 리서치 진행?" 제안 (예: 리서치 트리거 U12/U9, 아니오: 정보부족 안내)

가드레일(U13) 연결: converse 에 guardrail_id 전달, 개입 시 §6.5 톤 거부 메시지.
tier 이중방어: 답변에 인용된 tier≥3 항목은 "추정" 라벨 동반.

storage(U8)·bedrock(U11)·guardrails(U13) 재사용. 순수 함수(외부 randomness 없음).
"""

import json

from services import bedrock as BR
from services import guardrails as GR
from services import storage

SYSTEM_PROMPT = (
    "너는 글로벌 오토파이낸스 진출 진단 서비스의 상담 챗봇이다. "
    "제공된 국가/권역 데이터(JSON)에 근거해서만 답한다. "
    "데이터에 없는 사실은 지어내지 말고 '해당 정보는 보유하고 있지 않습니다'라고 답한다. "
    "투자 권유·법률/세무 자문은 하지 않는다. 답변은 한국어로 간결하게."
)

# §6.5 메시지
MSG_NO_COUNTRY_INFO = "해당 국가의 정보가 존재하지 않습니다. 외부 리서치를 통해 정보를 생성하시겠습니까?"
MSG_NO_REGION_INFO = "해당 권역의 정보가 부족하여 외부 리서치가 필요합니다. 진행하시겠습니까?"
MSG_RESEARCH_DECLINED = "정보가 부족하여 답변하기 어렵습니다."
MSG_RESEARCH_DONE = "해당 국가의 정보 생성이 완료되었습니다. 궁금한 점을 물어보세요."


def _country_context(code):
    """보유 country JSON 을 grounding 컨텍스트 문자열로. 없으면 None."""
    try:
        data = storage.load_country(code)
    except storage.NotFound:
        return None, None
    return data, json.dumps(data, ensure_ascii=False)


def answer_country(message, code, *, guardrail_id=None, guardrail_version=None,
                   client=None, model=BR.DEFAULT_MODEL):
    """국가 질의 응답 (§6.5.1).

    반환 dict:
      {"status": "answered", "answer": ..., "low_tier_flags": [...]}  보유정보로 답변
      {"status": "needs_research", "message": ..., "code": ...}        정보 없음 → 리서치 제안
      {"status": "blocked", "message": ...}                            가드레일 차단
    """
    code = code.upper()
    data, ctx = _country_context(code)
    if data is None:
        return {"status": "needs_research", "message": MSG_NO_COUNTRY_INFO, "code": code}

    prompt = f"[국가 데이터]\n{ctx}\n\n[질문]\n{message}"
    resp = BR.converse(
        [{"role": "user", "content": [{"text": prompt}]}],
        system=SYSTEM_PROMPT, model=model, client=client,
        guardrail_id=guardrail_id, guardrail_version=guardrail_version)

    if GR.is_intervened(resp):
        return {"status": "blocked", "message": GR.refusal_message("output")}

    answer = BR.extract_text(resp)
    flags = GR.annotate_low_tier(data.get("items", []))
    return {"status": "answered", "answer": answer, "low_tier_flags": flags}


def answer_region(message, region, *, guardrail_id=None, guardrail_version=None,
                  client=None, model=BR.DEFAULT_MODEL):
    """권역 질의 응답 (§6.5.2). 멤버국 데이터 유무로 분기."""
    region = region.upper()
    try:
        meta = storage.get_region(region)
    except storage.NotFound:
        return {"status": "needs_research", "message": MSG_NO_REGION_INFO, "region": region}

    have = meta.get("members_with_data", [])
    if not have:
        return {"status": "needs_research", "message": MSG_NO_REGION_INFO,
                "region": region, "missing": meta.get("members", [])}

    # 보유국 데이터를 묶어 컨텍스트로
    blocks = []
    all_items = []
    for code in have:
        d = storage.load_country(code)
        blocks.append(f"== {code} ==\n{json.dumps(d, ensure_ascii=False)}")
        all_items.extend(d.get("items", []))
    ctx = "\n\n".join(blocks)

    prompt = f"[권역 {region} 보유국 데이터]\n{ctx}\n\n[질문]\n{message}"
    resp = BR.converse(
        [{"role": "user", "content": [{"text": prompt}]}],
        system=SYSTEM_PROMPT, model=model, client=client,
        guardrail_id=guardrail_id, guardrail_version=guardrail_version)

    if GR.is_intervened(resp):
        return {"status": "blocked", "message": GR.refusal_message("output")}

    answer = BR.extract_text(resp)
    flags = GR.annotate_low_tier(all_items)
    return {"status": "answered", "answer": answer,
            "low_tier_flags": flags, "answered_with": have}


def chat(message, *, country=None, region=None, guardrail_id=None,
         guardrail_version=None, client=None, model=BR.DEFAULT_MODEL):
    """단일 진입점. country 또는 region 지정에 따라 분기."""
    if country:
        return answer_country(message, country, guardrail_id=guardrail_id,
                              guardrail_version=guardrail_version, client=client, model=model)
    if region:
        return answer_region(message, region, guardrail_id=guardrail_id,
                             guardrail_version=guardrail_version, client=client, model=model)
    # 대상 미지정 — 일반 안내
    return {"status": "needs_target",
            "message": "어느 국가 또는 권역에 대한 질문인지 알려주세요."}
