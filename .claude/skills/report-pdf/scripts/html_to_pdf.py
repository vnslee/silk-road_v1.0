#!/usr/bin/env python3
"""HTML 진단 보고서 → PDF 변환 (WeasyPrint 기반).

입력: rendering 엔진이 생성한 HTML 보고서 (report/<country|region>/<ID>/html/*.html)
출력: 같은 ID 폴더의 pdf/ 하위에 동일 파일명(.pdf)

사용법:
  python3 html_to_pdf.py <HTML_PATH> [OUT_PDF_PATH]
  - OUT_PDF_PATH 생략 시: 입력의 .../html/<name>.html → .../pdf/<name>.pdf 로 자동 산출
"""
import os
import sys


def derive_out(src):
    """.../html/<name>.html → .../pdf/<name>.pdf 규약으로 출력 경로 도출."""
    d, fn = os.path.split(os.path.abspath(src))
    base = os.path.splitext(fn)[0] + ".pdf"
    parent = os.path.dirname(d)
    leaf = os.path.basename(d)
    # html 폴더면 형제 pdf 폴더로, 아니면 같은 폴더에 출력
    outdir = os.path.join(parent, "pdf") if leaf == "html" else d
    return os.path.join(outdir, base)


def convert(src, out=None):
    from weasyprint import HTML  # 지연 임포트 — 미설치 시 안내
    if not os.path.exists(src):
        raise SystemExit(f"[오류] 입력 HTML 없음: {src}")
    out = out or derive_out(src)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    HTML(filename=src).write_pdf(out)
    print(f"[PDF] {os.path.relpath(src)} → {os.path.relpath(out)} ({os.path.getsize(out)} bytes)")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit("사용법: python3 html_to_pdf.py <HTML_PATH> [OUT_PDF_PATH]")
    convert(args[0], args[1] if len(args) > 1 else None)
