#!/usr/bin/env python3
"""국가 조회 라우터 (U8)."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import storage

router = APIRouter(prefix="/countries", tags=["countries"])


class CountrySummary(BaseModel):
    code: str
    country_ko: Optional[str] = None
    country_en: Optional[str] = None
    region: Optional[str] = None
    has_data: bool
    is_entered: bool      # 진출국(자산 보유) 여부 — M1 지도 채운점/빈점
    is_baseline: bool


@router.get("", response_model=list[CountrySummary])
def list_countries():
    """국가 목록 — research 보유국 + 권역 후보(예정국) 통합."""
    return storage.list_countries()


@router.get("/{code}")
def get_country(code: str):
    """국가 상세 — research JSON 원본."""
    try:
        return storage.load_country(code.upper())
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
