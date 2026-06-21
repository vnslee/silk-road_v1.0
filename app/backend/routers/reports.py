#!/usr/bin/env python3
"""보고서 조회 라우터 (U8) — 목록·상세·HTML 제공(읽기 전용).

생성 트리거는 U9, PDF 는 U10.
kind 는 'country' | 'region'.
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services import jobs, pdf as pdf_svc, report_runner, storage

router = APIRouter(prefix="/reports", tags=["reports"])

_KINDS = {"country", "region"}


def _check_kind(kind):
    if kind not in _KINDS:
        raise HTTPException(status_code=404, detail=f"unknown kind '{kind}' (country|region)")


def _check_target_exists(kind, code):
    """트리거 전 대상 존재 검증 — 없으면 404(백그라운드 진입 전 차단)."""
    try:
        if kind == "country":
            storage.load_country(code)
        else:
            storage.get_region(code)
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


class ReportSummary(BaseModel):
    report_id: str
    created_at: Optional[str] = None
    has_html: bool
    legacy: bool
    json_name: str


class TriggerResponse(BaseModel):
    job_id: str
    status: str


@router.post("/{kind}/{code}", response_model=TriggerResponse, status_code=202)
def trigger_report(kind: str, code: str, background: BackgroundTasks):
    """보고서 생성 트리거(비동기). job_id 반환 → GET /jobs/{job_id} 로 폴링."""
    _check_kind(kind)
    code = code.upper()
    _check_target_exists(kind, code)
    job_id = jobs.create_job(kind, code)
    background.add_task(report_runner.run, job_id, kind, code)
    return {"job_id": job_id, "status": "pending"}


@router.get("/{kind}/{code}", response_model=list[ReportSummary])
def list_reports(kind: str, code: str):
    """대상(국가/권역)의 보고서 목록. 신구조 + 구버전 모두 포함."""
    _check_kind(kind)
    return storage.list_reports(kind, code.upper())


@router.get("/{kind}/{code}/{report_id}")
def get_report(kind: str, code: str, report_id: str):
    """보고서 JSON 상세."""
    _check_kind(kind)
    try:
        return storage.load_report(kind, code.upper(), report_id)
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{kind}/{code}/{report_id}/html", response_class=FileResponse)
def get_report_html(kind: str, code: str, report_id: str):
    """보고서 HTML(U5 산출물) 정적 제공."""
    _check_kind(kind)
    try:
        path = storage.report_html_path(kind, code.upper(), report_id)
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return FileResponse(path, media_type="text/html")


@router.get("/{kind}/{code}/{report_id}/pdf", response_class=FileResponse)
def get_report_pdf(kind: str, code: str, report_id: str):
    """보고서 PDF(weasyprint, D2). HTML→PDF 변환·캐시.

    HTML 없으면 404, weasyprint(시스템 라이브러리) 불가 시 503.
    """
    _check_kind(kind)
    try:
        path = pdf_svc.render_pdf(kind, code.upper(), report_id)
    except storage.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except pdf_svc.PdfUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    return FileResponse(path, media_type="application/pdf",
                        filename=f"{report_id}.pdf")
