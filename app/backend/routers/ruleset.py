#!/usr/bin/env python3
"""룰셋(internal) 조회·저장 라우터 (PS1) — 원격 internal 구조판.

원격 internal 의 values(biz_attractiveness·it_readiness·report_blend)와
quick_win_rules 를 PS1 에 노출. 저장은 report_blend(w_biz/w_it) 가중치.
"""

from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import storage

router = APIRouter(prefix="/ruleset", tags=["ruleset"])


@router.get("")
def get_ruleset():
    """internal 룰셋 + PS1 표시용 가중치."""
    try:
        d = storage.load_internal()
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    values = d.get("values", {})
    return {
        "version": d.get("version"),
        "biz_attractiveness": values.get("biz_attractiveness", {}),
        "it_readiness": values.get("it_readiness", {}),
        "report_blend": values.get("report_blend", {"w_biz": 0.6, "w_it": 0.4}),
        "quick_win_rules": d.get("quick_win_rules", {}),
        "decision_thresholds": d.get("decision_thresholds", {}),
    }


class BlendUpdate(BaseModel):
    w_biz: float
    w_it: float


@router.put("/blend")
def update_blend(body: BlendUpdate):
    """report_blend(비즈니스·IT 가중치) 저장. 합=1.0 검증."""
    total = body.w_biz + body.w_it
    if abs(total - 1.0) > 1e-6:
        raise HTTPException(status_code=400, detail=f"w_biz + w_it = {total} (1.0 이어야 함)")
    try:
        d = storage.load_internal()
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    d.setdefault("values", {})["report_blend"] = {"w_biz": body.w_biz, "w_it": body.w_it}
    storage.save_internal(d)
    return {"status": "saved", "report_blend": d["values"]["report_blend"]}
