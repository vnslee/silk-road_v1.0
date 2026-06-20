---
name: report-pdf
description: 진단 보고서 HTML을 PDF로 변환한다. rendering 엔진이 만든 권역/국가 진단 보고서(PR1/PR2) HTML을 PDF 다운로드용 파일로 만든다. 사용자가 "PDF", "보고서 PDF", "PDF 다운로드", "HTML을 PDF로"를 언급할 때 사용.
---

# 진단 보고서 PDF 생성

rendering 엔진이 생성한 HTML 보고서(`report/<country|region>/<ID>/html/*.html`)를 PDF로 변환한다.
PR1/PR2 화면 스펙의 "보고서 PDF 다운로드" 버튼이 제공할 산출물이다.

## 도구: WeasyPrint

HTML/CSS 렌더링 품질이 우수해 Tailwind 기반 보고서 레이아웃을 잘 보존한다.

- Python 패키지: `weasyprint` (설치됨, v66)
- 시스템 의존성: `pango`, `cairo` (dnf로 설치 완료). 새 환경에서 `OSError: libpango...` 가 나면:
  `sudo dnf install -y pango cairo`

## 사용법

변환 스크립트: `.claude/skills/report-pdf/scripts/html_to_pdf.py`

```bash
# 출력 경로 자동 도출 (.../html/<name>.html → .../pdf/<name>.pdf)
python3 .claude/skills/report-pdf/scripts/html_to_pdf.py \
  app/backend/storage/report/region/EU/html/EU_rpt_<TS>.html

# 출력 경로 명시
python3 .claude/skills/report-pdf/scripts/html_to_pdf.py <HTML_PATH> <OUT_PDF_PATH>
```

## 출력 규약

- 입력이 `.../<ID>/html/<name>.html` 이면 출력은 `.../<ID>/pdf/<name>.pdf` (형제 `pdf/` 폴더).
- 이로써 보고서 산출물은 `data/`(JSON) · `html/`(HTML) · `pdf/`(PDF) 세 형식으로 분리된다.
- 출력 폴더는 자동 생성된다.

## 주의

- 변환 전 입력 HTML이 존재하는지 확인(없으면 먼저 rendering 엔진 실행).
- 외부 폰트/CDN(Tailwind, Google Fonts)을 쓰는 HTML은 네트워크가 없으면 일부 스타일이 누락될 수 있다 — 품질이 중요하면 오프라인 폰트 임베드를 검토.
- 신규 PDF를 백지에서 작성(폼 채우기 등)하는 작업은 이 스킬이 아니라 reportlab/pypdf 기반 접근이 맞다(이 스킬은 HTML→PDF 변환 전용).
