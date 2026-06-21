#!/usr/bin/env python3
"""Job 진행률 폴링 라우터 (U9)."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import jobs as job_svc

router = APIRouter(prefix="/jobs", tags=["jobs"])


class Step(BaseModel):
    key: str
    label: str
    state: str   # pending | running | done | error


class JobStatus(BaseModel):
    job_id: str
    kind: str
    code: str
    status: str          # pending | running | done | error
    progress: int        # 0~100
    steps: List[Step]
    report_id: Optional[str] = None
    error: Optional[str] = None


@router.get("/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    """진행률 폴링. 완료 시 report_id 로 GET /reports/... 조회."""
    job = job_svc.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job '{job_id}' 없음")
    return job
