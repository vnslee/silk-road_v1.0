#!/usr/bin/env python3
"""
Bedrock Guardrails 정책 + 연결 (U13).

guardrail/PLAN.md 의 4개 영역 정책을 코드로 정의하고, Bedrock Guardrails 에 연결한다.
실제 Guardrail 리소스 생성(CreateGuardrail)은 4차 CFN(IaC)에서 관리 — 이 모듈은
정책 정의 + 생성/검증 헬퍼 + 거부응답 매핑까지(PLAN 구현방향 1·2·3).

4개 영역 (PLAN §4영역 매핑):
  답변 범위 제한   → Denied topics
  프롬프트 인젝션  → Prompt attack filter (Standard tier)
  출처/사실성      → Contextual grounding (grounding + relevance 임계값)
  PII             → Sensitive info filter (내장 PII + 한국 주민번호 regex)

Standard tier + 서울 cross-Region (PLAN §한국어 보강).
"""

import re

# ── PII: 한국 특화 regex (내장 PII 외 보강, PLAN §3) ─────────────────────
KR_RRN_REGEX = r"\b\d{6}-?[1-4]\d{6}\b"        # 주민등록번호
KR_PHONE_REGEX = r"\b01[016-9]-?\d{3,4}-?\d{4}\b"  # 휴대폰

CUSTOM_PII_REGEXES = [
    {"name": "KR_RRN", "pattern": KR_RRN_REGEX, "action": "ANONYMIZE",
     "description": "한국 주민등록번호"},
    {"name": "KR_PHONE", "pattern": KR_PHONE_REGEX, "action": "ANONYMIZE",
     "description": "한국 휴대폰 번호"},
]

# ── 답변 범위 제한: denied topics (PLAN §미해결 — 초기 목록) ──────────────
DENIED_TOPICS = [
    {"name": "InvestmentAdvice", "type": "DENY",
     "definition": "특정 금융상품·주식·암호화폐 매수/매도 권유 또는 투자 수익 보장",
     "examples": ["이 주식 사야 할까요?", "어디에 투자하면 돈을 벌까요?"]},
    {"name": "LegalTaxAdvice", "type": "DENY",
     "definition": "구체적 법률 자문·세무 신고 대행·소송 전략 등 전문 자격 필요 자문",
     "examples": ["이 계약서로 소송하면 이길까요?", "세금 신고를 대신 해주세요"]},
    {"name": "OffTopic", "type": "DENY",
     "definition": "오토파이낸스 글로벌 진출 진단과 무관한 일반 주제",
     "examples": ["오늘 날씨 어때?", "시 한 편 써줘"]},
]

# ── 콘텐츠 필터 (프롬프트 인젝션 포함, Standard tier) ─────────────────────
CONTENT_FILTERS = [
    {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"},
    {"type": "MISCONDUCT", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"},
]

# ── Contextual grounding 임계값 (PLAN §미해결 — 초기값, 파일럿 튜닝) ──────
GROUNDING_THRESHOLD = 0.7   # 답변이 주입 컨텍스트에 근거하는 정도
RELEVANCE_THRESHOLD = 0.5   # 답변이 질문과 관련된 정도

# ── 차단 메시지 (web_design_spec §6.5 톤과 일치, PLAN 구현방향 1) ─────────
BLOCKED_INPUT_MSG = "해당 질문에는 답변하기 어렵습니다. 오토파이낸스 진출 진단 관련 질문을 해주세요."
BLOCKED_OUTPUT_MSG = "해당 정보가 부족하여 답변하기 어렵습니다."


def build_guardrail_config(name="silk-road-guardrail"):
    """CreateGuardrail 요청 본문(boto3 bedrock client.create_guardrail용).

    실제 생성은 create_guardrail() 또는 4차 CFN(AWS::Bedrock::Guardrail).
    """
    return {
        "name": name,
        "description": "silk-road 챗봇 가드레일 (Standard tier, 4영역)",
        "topicPolicyConfig": {"topicsConfig": DENIED_TOPICS},
        "contentPolicyConfig": {"filtersConfig": CONTENT_FILTERS},
        "contextualGroundingPolicyConfig": {"filtersConfig": [
            {"type": "GROUNDING", "threshold": GROUNDING_THRESHOLD},
            {"type": "RELEVANCE", "threshold": RELEVANCE_THRESHOLD},
        ]},
        "sensitiveInformationPolicyConfig": {
            "piiEntitiesConfig": [
                {"type": "EMAIL", "action": "ANONYMIZE"},
                {"type": "PHONE", "action": "ANONYMIZE"},
                {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
            ],
            "regexesConfig": CUSTOM_PII_REGEXES,
        },
        "blockedInputMessaging": BLOCKED_INPUT_MSG,
        "blockedOutputsMessaging": BLOCKED_OUTPUT_MSG,
    }


def create_guardrail(*, region="ap-northeast-2", client=None, name="silk-road-guardrail"):
    """AWS 에 Guardrail 리소스 생성. (guardrail_id, version) 반환.

    데모/4차 CFN 전에 수동 생성용. client 주입 시 모킹.
    """
    if client is None:
        import boto3
        client = boto3.client("bedrock", region_name=region)
    resp = client.create_guardrail(**build_guardrail_config(name))
    return resp["guardrailId"], resp.get("version", "DRAFT")


# ── 거부 응답 처리 (PLAN 구현방향 2) ──────────────────────────────────────
def is_intervened(converse_response):
    """Converse 응답에서 가드레일 개입(차단) 여부."""
    return (converse_response or {}).get("stopReason") == "guardrail_intervened"


def refusal_message(scope="input"):
    """차단 시 사용자에게 보일 메시지(§6.5 톤)."""
    return BLOCKED_INPUT_MSG if scope == "input" else BLOCKED_OUTPUT_MSG


def apply_guardrail(text, *, guardrail_id, guardrail_version="DRAFT", source="INPUT",
                    region="ap-northeast-2", client=None):
    """ApplyGuardrail API 로 텍스트 단독 평가(단위 검증용, PLAN 검증방법 1).

    반환: {"action": "GUARDRAIL_INTERVENED"|"NONE", "blocked": bool, ...원시}.
    """
    if client is None:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=region)
    resp = client.apply_guardrail(
        guardrailIdentifier=guardrail_id,
        guardrailVersion=guardrail_version,
        source=source,
        content=[{"text": {"text": text}}],
    )
    action = resp.get("action", "NONE")
    return {"action": action, "blocked": action == "GUARDRAIL_INTERVENED",
            "raw": resp}


# ── tier 기반 이중 방어 (PLAN 구현방향 3, 코드로 강제) ────────────────────
def tier_label(tier):
    """출처 tier → 신뢰도 라벨. tier≤3 은 '실사 보류/추정' 표시(프롬프트 FLAG 규칙)."""
    if tier is None:
        return None
    if tier <= 1:
        return "공식"
    if tier == 2:
        return "준공식"
    return "실사 보류/추정"   # tier 3~4


def annotate_low_tier(items):
    """답변에 인용된 item 중 tier≥3 에 '추정' 라벨 부착(코드 강제, 프롬프트 아님)."""
    flagged = []
    for it in items:
        t = it.get("tier")
        if isinstance(t, int) and t >= 3:
            flagged.append({"item": it.get("item"), "tier": t,
                            "label": tier_label(t)})
    return flagged
