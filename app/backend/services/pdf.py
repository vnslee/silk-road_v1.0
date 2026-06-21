#!/usr/bin/env python3
"""
PDF 변환 서비스 (U10) — 보고서 HTML(U5) → PDF (weasyprint, D2).

weasyprint 는 시스템 라이브러리(pango/cairo) 의존이라 환경에 따라 import 가 실패할
수 있다. 따라서:
  - weasyprint 는 **지연 import**(이 모듈 import 만으로 서버가 죽지 않게).
  - import/렌더 실패 시 PdfUnavailable 예외 → 라우터가 503 으로 변환(HTML/JSON 은 정상).

macOS 실행 시 `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` 필요(README 참조).
Docker(U22)는 apt libpango 설치로 환경변수 불필요.

산출물: report/<kind>/<code>/<ID>/pdf/<ID>.pdf (data/html/pdf 3분리). 캐시 후 재사용.
"""

from pathlib import Path

from services import storage


class PdfUnavailable(Exception):
    """weasyprint(시스템 라이브러리) 사용 불가 — 라우터가 503 으로 변환."""


def _pdf_path_for(html_path):
    """html/<ID>.html → pdf/<ID>.pdf (형제 pdf 폴더)."""
    pdf_dir = html_path.parent.parent / "pdf"
    return pdf_dir / (html_path.stem + ".pdf")


def render_pdf(kind, code, report_id, *, force=False):
    """보고서 HTML 을 PDF 로 변환. 캐시 있으면 재사용.

    반환: PDF 파일 Path.
    예외: storage.NotFound(HTML 없음) / PdfUnavailable(weasyprint 불가).
    """
    html_path = storage.report_html_path(kind, code, report_id)  # 없으면 NotFound
    pdf_path = _pdf_path_for(html_path)

    if pdf_path.exists() and not force:
        # HTML 이 PDF 보다 최신이면 재생성
        if pdf_path.stat().st_mtime >= html_path.stat().st_mtime:
            return pdf_path

    try:
        from weasyprint import HTML  # 지연 import
    except (ImportError, OSError) as e:
        raise PdfUnavailable(f"weasyprint 사용 불가(시스템 라이브러리 확인): {e}")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    except Exception as e:  # noqa: BLE001 — 네이티브 렌더 실패도 503 로
        raise PdfUnavailable(f"PDF 렌더 실패: {e}")
    return pdf_path
