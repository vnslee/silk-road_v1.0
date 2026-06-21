#!/usr/bin/env python3
"""챗봇 라우터 (U14) — §6.5 질의응답 + 리서치 트리거.

가드레일 ID 는 환경변수 GUARDRAIL_ID(있으면)로 연결(U13). 없으면 None(데모: 가드레일
리소스 미생성 상태 — 4차 CFN 후 주입).
"""

import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from services import chat as chat_svc
from services import jobs

router = APIRouter(prefix="/chat", tags=["chat"])

GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION", "DRAFT")


class ChatRequest(BaseModel):
    message: str
    country: Optional[str] = None
    region: Optional[str] = None


@router.post("")
def post_chat(req: ChatRequest):
    """질의응답. 보유정보로 답변하거나 리서치를 제안(§6.5)."""
    return chat_svc.chat(
        req.message, country=req.country, region=req.region,
        guardrail_id=GUARDRAIL_ID, guardrail_version=GUARDRAIL_VERSION)


class ResearchRequest(BaseModel):
    country: str           # 영문 국가명 (프롬프트 {COUNTRY})
    code: str              # ISO alpha-2
    region: str            # EU | NORTH_AMERICA | SOUTH_AMERICA | APAC


@router.post("/research", status_code=202)
def post_research(req: ResearchRequest, background: BackgroundTasks):
    """리서치 Agent 트리거(비동기, U9 job 재사용). 진행률은 GET /jobs/{id}."""
    code = req.code.upper()
    job_id = jobs.create_job("research", code)
    background.add_task(_run_research, job_id, req.country, code, req.region)
    return {"job_id": job_id, "status": "pending"}


def _run_research(job_id, country_name, code, region):
    """백그라운드 리서치 실행 → job 상태 갱신. (단계는 단일 — 리서치 자체가 한 덩어리)"""
    # 지연 import: research 는 prompt 파일·검증기에 의존, 라우터 로드 가볍게.
    from services import research
    jobs.start_step(job_id, "result")  # 리서치는 단일 단계로 표현
    try:
        # fetched_at 은 여기서 주입(라우터 = 부수효과 경계)
        from datetime import datetime, timezone, timedelta
        kst = timezone(timedelta(hours=9))
        ts = datetime.now(kst).replace(microsecond=0).isoformat()
        data, _snap, _latest = research.research_country(
            country_name, code, region, fetched_at=ts)
        jobs.finish_step(job_id, "result")
        jobs.complete(job_id, f"{code}_latest")
    except Exception as e:  # noqa: BLE001
        jobs.fail(job_id, f"{type(e).__name__}: {e}")
