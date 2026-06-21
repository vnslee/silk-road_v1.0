# Engine

핵심 비즈니스 로직을 처리하는 엔진 모듈입니다. 국가(country)·권역(region) 진단 보고서 생성 파이프라인과, 국가(P1)·권역(P2) 상세화면 렌더링을 구성합니다.

> **산출 라인 구분**: 진단 보고서(PR1/PR2)는 `report/`에, 상세화면(P1/P2)은 `detail/`에 HTML을 출력하는 별개 라인입니다.

## 파이프라인 단계

```
[보고서 라인]  generation → rendering
              (리포트 JSON)  (HTML 보고서)

[상세화면 라인] rendering (리서치 JSON → HTML 상세화면, generation 없이 직접 렌더)
```

| 폴더 | 파일 | 역할 |
|------|------|------|
| `generation/` | `country_report_engine.py` | 국가 리서치 JSON을 받아 단일국 진단 리포트(TCO·스코어링) JSON 생성. `report/country/<CODE>/data/`에 `RPT_CTR_<CODE>_<NNN>.json` 출력 |
| `generation/` | `region_report_engine.py` | 권역 리서치 JSON을 받아 권역 진단 리포트(퀵윈 스코어링·랭킹) JSON 생성. `report/region/<REGION>/data/`에 `RPT_RGN_<REGION>_<NNN>.json` 출력 |
| `rendering/` | `country_report_renderer.py` | 리포트 JSON을 받아 국가 진단 보고서(PR1) standalone HTML로 렌더링. 계산은 하지 않고 표현만 담당 |
| `rendering/` | `region_report_renderer.py` | 리포트 JSON을 받아 권역 진단 보고서(PR2) standalone HTML로 렌더링. 계산은 하지 않고 표현만 담당 |
| `rendering/` | `country_detail_renderer.py` | 국가 리서치 JSON(`data/research/country/`)을 받아 국가 상세화면(P1) standalone HTML로 렌더링 |
| `rendering/` | `region_detail_renderer.py` | 권역 리서치 JSON(`data/research/region/`)을 받아 권역 상세화면(P2) standalone HTML로 렌더링 |
| `rendering/` | `render_helpers.py` | 공유 표현/차트/포맷 헬퍼 모듈. 상세화면 렌더러가 `import ... as rre`로 재사용(중복 작성 금지) |
| `rendering/templates/` | `country_detail_template.html` | 국가 상세화면(P1) 템플릿. `{{COUNTRY_EN}}`·`{{GENERAL_CARDS}}`·`{{CHARTS}}`·`{{INSIGHT_PANEL}}`·`{{DETAIL_SECTIONS}}` 등 치환 |
| `rendering/templates/` | `region_detail_template.html` | 권역 상세화면(P2) 템플릿. `{{REGION_EN}}`·`{{KPI_CARDS}}`·`{{ENTERED_LIST}}`·`{{QUICKWIN_TABLE}}`·`{{PERF_CHART}}` 등 치환 |

## 모듈 의존 관계

- `generation`(보고서 리포트 JSON 생성)과 `rendering`(HTML 렌더링)은 인자(JSON 경로)로 연결되는 별도 실행 단계입니다 — `generation`이 `rendering`을 직접 호출하지 않습니다(렌더링은 별도로 실행).
- `rendering` 엔진은 `rendering/templates/`의 HTML 템플릿을 읽어 플레이스홀더를 치환하는 방식으로 HTML을 생성합니다 (템플릿 경로: `<엔진폴더>/templates/`).
- 상세화면(detail) 렌더러는 같은 `rendering/` 폴더의 `render_helpers`를 `sys.path`에 추가해 `import ... as rre`로 포맷·차트 헬퍼(`esc`·`fmt_value`·`line_chart`·`bar`·`score_color`·`card` 등)를 재사용합니다.

## 실행

```bash
# 국가 진단 리포트 JSON 생성 — 인자는 국가 리서치 JSON 경로
python3 generation/country_report_engine.py <country_research_json>

# 권역 진단 리포트 JSON 생성 — 인자는 권역 리서치 JSON 경로
python3 generation/region_report_engine.py <region_research_json>

# 보고서 렌더링은 별도 실행 (리포트 JSON이 이미 있는 경우) — 인자는 리포트 JSON 경로
python3 rendering/country_report_renderer.py <report_json_path>   # 국가 보고서(PR1)
python3 rendering/region_report_renderer.py <report_json_path>   # 권역 보고서(PR2)

# 국가 상세화면(P1) 렌더 — 리서치 데이터 → detail/country/<CODE>/html
python3 rendering/country_detail_renderer.py <CODE>

# 권역 상세화면(P2) 렌더 — 리서치 데이터 → detail/region/<REGION>/html
python3 rendering/region_detail_renderer.py <REGION>
```

> 보고서 출력물: `report/<country|region>/<ID>/data/RPT_{CTR|RGN}_<ID>_<NNN>.json` (generation) 및 `report/<country|region>/<ID>/html/RPT_{CTR|RGN}_<ID>_<NNN>.html` (rendering)
> 상세화면 출력물: `detail/country/<CODE>/html/<CODE>_detail_<TS>.html` (P1) 및 `detail/region/<REGION>/html/<REGION>_detail_<TS>.html` (P2)
