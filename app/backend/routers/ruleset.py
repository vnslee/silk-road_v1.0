#!/usr/bin/env python3
"""룰셋(internal) 조회·저장 라우터 (U21, PS1).

GET  /ruleset          internal 전체(또는 PS1 표시용 요약)
PUT  /ruleset/weights  4카테고리 가중치 저장(합=100 검증). C3 결정 구조.
"""

from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import storage

router = APIRouter(prefix="/ruleset", tags=["ruleset"])

CATEGORIES = {"market", "finance", "regulation", "system"}
LABELS_KO = {"market": "시장", "finance": "환경(금융)", "regulation": "규제", "system": "시스템"}


@router.get("")
def get_ruleset():
    """internal 룰셋 + PS1 표시용 메타(카테고리 라벨)."""
    try:
        d = storage.load_internal()
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "version": d.get("version"),
        "category_weights": d["weights"]["category_weights"],
        "category_labels": LABELS_KO,
        "quick_win_rules": d.get("quick_win_rules", {}),
        "similarity_brackets": d.get("similarity_brackets", []),
    }


class WeightsUpdate(BaseModel):
    category_weights: Dict[str, float]   # {market,finance,regulation,system} 합=100


@router.put("/weights")
def update_weights(body: WeightsUpdate):
    """4카테고리 가중치 저장. 키·합(=100) 검증 후 internal 갱신."""
    cw = body.category_weights
    if set(cw.keys()) != CATEGORIES:
        raise HTTPException(status_code=400,
                            detail=f"카테고리 키는 {sorted(CATEGORIES)} 여야 합니다")
    total = sum(cw.values())
    if abs(total - 100) > 1e-6:
        raise HTTPException(status_code=400, detail=f"가중치 합={total} (100 이어야 함)")

    try:
        d = storage.load_internal()
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    d["weights"]["category_weights"] = {k: cw[k] for k in CATEGORIES}
    storage.save_internal(d)
    return {"status": "saved", "category_weights": d["weights"]["category_weights"]}
