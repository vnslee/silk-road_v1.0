# Engine

핵심 비즈니스 로직을 처리하는 엔진 모듈입니다. 권역(region) 진단 보고서 생성 파이프라인과, 국가(P1)·권역(P2) 상세화면 렌더링을 단계별로 구성합니다.

> **산출 라인 구분**: 진단 보고서(PR1/PR2)는 `report/`에, 상세화면(P1/P2)은 `detail/`에 HTML을 출력하는 별개 라인입니다.

## 파이프라인 단계

```
calculation → generation → rendering
 (스코어링)    (데이터 생성)   (HTML 렌더링)
```

| 폴더 | 파일 | 역할 |
|------|------|------|
| `calculation/` | `scoring_engine.py` | 단일국 스코어링 엔진. 활성 항목 기반으로 매력도·난이도·유사도 등을 계산 |
| `generation/` | `region_report_generation_engine.py` | 권역 퀵윈 스코어링. `scoring_engine`을 재사용해 권역 내 국가를 일괄 평가하고 리포트 JSON 생성 |
| `rendering/` | `region_report_rendering_engine.py` | 리포트 JSON을 받아 권역 진단 보고서(PR2) standalone HTML로 렌더링. 계산은 하지 않고 표현만 담당 |
| `rendering/` | `country_detail_rendering_engine.py` | 국가 리서치 JSON(`data/research/country/`)을 받아 국가 상세화면(P1) standalone HTML로 렌더링 |
| `rendering/` | `region_detail_rendering_engine.py` | 권역 리서치 JSON(`data/research/region/`)을 받아 권역 상세화면(P2) standalone HTML로 렌더링 |
| `rendering/templates/` | `region_report_template.html` | 보고서 렌더링 엔진이 읽는 HTML 템플릿. `{{PAGE_TITLE}}`·`{{TAB_NAV}}`·`{{TAB_PANELS}}` 등 플레이스홀더를 치환해 최종 보고서 생성 |
| `rendering/templates/` | `country_detail_template.html` | 국가 상세화면(P1) 템플릿. `{{COUNTRY_EN}}`·`{{GENERAL_CARDS}}`·`{{CHARTS}}`·`{{INSIGHT_PANEL}}`·`{{DETAIL_SECTIONS}}` 등 치환 |
| `rendering/templates/` | `region_detail_template.html` | 권역 상세화면(P2) 템플릿. `{{REGION_EN}}`·`{{KPI_CARDS}}`·`{{ENTERED_LIST}}`·`{{QUICKWIN_TABLE}}`·`{{PERF_CHART}}` 등 치환 |

## 모듈 의존 관계

- `generation`은 형제 폴더의 `calculation`(스코어링)과 `rendering`(렌더링)을 import 합니다.
- 크로스 폴더 import를 위해 `generation` 엔진이 실행 시 형제 폴더 경로를 `sys.path`에 추가합니다.
- `rendering` 엔진은 `rendering/templates/`의 HTML 템플릿을 읽어 플레이스홀더를 치환하는 방식으로 HTML을 생성합니다 (템플릿 경로: `<엔진폴더>/templates/`).
- 상세화면(detail) 엔진은 같은 `rendering/` 폴더의 `region_report_rendering_engine`을 `sys.path`에 추가해 `import ... as rre`로 포맷·차트 헬퍼(`esc`·`fmt_value`·`line_chart`·`bar`·`score_color`·`card` 등)를 재사용합니다.

## 실행

```bash
# 권역 리포트 데이터 생성 (+ 내부적으로 렌더링까지 위임)
python3 generation/region_report_generation_engine.py <REGION>

# 렌더링만 단독 실행 (리포트 JSON이 이미 있는 경우)
python3 rendering/region_report_rendering_engine.py <REGION>

# 국가 상세화면(P1) 렌더 — 리서치 데이터 → detail/country/<CODE>/html
python3 rendering/country_detail_rendering_engine.py <CODE>

# 권역 상세화면(P2) 렌더 — 리서치 데이터 → detail/region/<REGION>/html
python3 rendering/region_detail_rendering_engine.py <REGION>
```

> 보고서 출력물: `report/region/<REGION>/data/<REGION>_rpt_<TS>.json` (generation) 및 `report/region/<REGION>/html/<REGION>_rpt_<TS>.html` (rendering)
> 상세화면 출력물: `detail/country/<CODE>/html/<CODE>_detail_<TS>.html` (P1) 및 `detail/region/<REGION>/html/<REGION>_detail_<TS>.html` (P2)
