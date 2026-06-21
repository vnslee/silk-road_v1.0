#!/usr/bin/env python3
"""권역 조회 라우터 (U8)."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import storage

router = APIRouter(prefix="/regions", tags=["regions"])


class RegionSummary(BaseModel):
    region: str
    name_ko: Optional[str] = None
    name_en: Optional[str] = None
    baseline: Optional[str] = None
    members: List[str]
    members_with_data: List[str]


@router.get("", response_model=list[RegionSummary])
def list_regions():
    """권역 목록 — internal.regions 카탈로그 + 멤버 보유 현황."""
    return storage.list_regions()


@router.get("/{region}", response_model=RegionSummary)
def get_region(region: str):
    """권역 상세."""
    try:
        return storage.get_region(region.upper())
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
