#!/usr/bin/env python3
"""
Silk Road 백엔드 API (U7 — 골격).

글로벌 오토파이낸스 진출 진단 서비스의 HTTP API.
country/region 진단 파이프라인(engine/)을 프론트가 호출할 수 있게 노출한다.

U7 범위: FastAPI 앱 + CORS + /health 만. 실제 엔드포인트(조회·생성·제공)는
  U8~U10 에서 라우터로 추가한다.

인증 없음(E1, 데모). 데이터 저장소는 파일시스템 storage/ (A1).

실행:
  cd app/backend
  .venv/bin/uvicorn main:app --reload
  # weasyprint(PDF, U10) 사용 시 macOS 에서는 시스템 라이브러리 경로 필요:
  #   DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib .venv/bin/uvicorn main:app
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

API_VERSION = "v1"

app = FastAPI(
    title="Silk Road API",
    description="글로벌 오토파이낸스 진출 진단 서비스 백엔드",
    version="1.0.0",
)

# CORS — 개발용 전체 허용. 배포(U23) 시 프론트 오리진으로 좁힌다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """헬스체크 — 로드밸런서·배포 검증용."""
    return {"status": "ok", "service": "silk-road", "api_version": API_VERSION}


# 조회 라우터 (U8). 생성 트리거(U9)·PDF(U10)는 이후 추가.
from routers import countries, regions, reports, jobs, chat, ruleset  # noqa: E402

_API = f"/api/{API_VERSION}"
app.include_router(countries.router, prefix=_API)
app.include_router(regions.router, prefix=_API)
app.include_router(reports.router, prefix=_API)
app.include_router(jobs.router, prefix=_API)
app.include_router(chat.router, prefix=_API)
app.include_router(ruleset.router, prefix=_API)
