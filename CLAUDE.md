# silk-road_v1.0

글로벌 오토파이낸스 진출 진단 서비스. 국가·권역 데이터를 스코어링하고 인터랙티브 지도 UI + 챗봇으로 진단 보고서를 제공한다.

서비스는 **국가(country)** 와 **권역(region)** 두 축으로 구성되며, 리서치 명세·엔진·산출물이 각 축별로 존재한다(보고서·상세화면 엔진 모두 country·region 양쪽 구현됨).

## 아키텍처

- `app/backend/engine/` — Python 엔진 파이프라인 (generation → rendering)
  - `generation/country_report_engine.py` — 국가 리서치 JSON → 국가 진단 리포트 JSON 생성 (단일국 TCO/스코어링)
  - `generation/region_report_engine.py` — 권역 리서치 JSON → 권역 진단 리포트 JSON 생성 (권역 퀵윈 스코어링·랭킹)
  - `rendering/country_report_renderer.py` — 국가 리포트 JSON → HTML **보고서**(PR1) 렌더링
  - `rendering/region_report_renderer.py` — 권역 리포트 JSON → HTML **보고서**(PR2) 렌더링
  - `rendering/country_detail_renderer.py` — 국가 리서치 JSON → HTML **상세화면**(P1) 렌더링
  - `rendering/region_detail_renderer.py` — 권역 리서치 JSON → HTML **상세화면**(P2) 렌더링
  - `rendering/render_helpers.py` — 공유 표현/차트/포맷 헬퍼 모듈(`esc`·`fmt_value`·`line_chart`·`bar`·`score_color`·`card`·`TOK` 등). 상세화면 렌더러가 `import ... as rre`로 재사용(중복 작성 금지).
  - ⚠️ **보고서(report) 렌더링은 country(PR1)·region(PR2) 양쪽 구현됨**, **상세화면(detail) 렌더링도 country(P1)·region(P2) 양쪽 구현됨**. 상세화면(P1/P2, `detail/` 출력)과 진단 보고서(PR1/PR2, `report/` 출력)는 별개 산출 라인이다.
- `app/backend/storage/` — 데이터 (입력/출력 분리)
- `app/frontend/` — 클라이언트 (지도 UI + 챗봇)
- `architecture/` — 설계 명세
  - `design/` — 화면·디자인 명세
  - `research/` — AI 리서치 프롬프트·스키마. country 리서치(`country_research_prompt.md`, `country_research_schema.md`)와 보고서 생성·렌더링 명세(`report_generate_req.md`, `report_render_req.md`)가 정의됨. **region 리서치 프롬프트·스키마가 추가될 예정** — country와 동일한 파일 네이밍(`region_research_*.md`)을 따른다.

## 경로 규칙 (중요)

- 엔진별 경로 해석 방식:
  - **보고서 generation 엔진**(`generation/*_report_engine.py`)은 입력 JSON 경로를 인자로 받고, 출력 베이스(`storage/report`)를 인자로 받는다. 기본 인자는 CWD 기준 상대경로(`storage/...`)이므로 보통 `app/backend/`에서 실행하거나 절대경로를 넘긴다.
  - **상세화면 detail 렌더러**(`rendering/*_detail_renderer.py`)는 자기 파일 위치 기준으로 `app/backend/storage`를 찾는다(파일 상단 `BASE`·`STORAGE` 변수 self-locate) — 어디서 실행해도 동작한다.
- **입력**: `storage/data/research/country/<CODE>/<CODE>_latest.json` · `storage/data/research/region/<REGION>/<REGION>_latest.json` (AI 조사), `storage/data/internal/internal_latest.json` (사내 룰셋).
- **출력**: 진단 보고서(PR1/PR2) JSON은 `storage/report/<country|region>/<ID>/data/`, HTML은 `.../html/` 에 둔다. 상세화면(P1/P2) HTML은 `storage/detail/<country|region>/<ID>/html/` 에 둔다. JSON과 HTML을 같은 폴더에 섞지 않는다.
- **파일 네이밍**: 보고서 리포트는 `RPT_CTR_<CODE>_<NNN>.json`(국가)·`RPT_RGN_<REGION>_<NNN>.json`(권역), HTML도 같은 ID(`RPT_CTR_ES_001.html` 등). 상세화면 HTML은 `<ID>_detail_<TS>.html`.
- **보고서** rendering 엔진은 `report/.../data/`의 JSON 경로를 인자로 받아 같은 도메인 `report/.../html/`에 HTML을 쓴다. **상세화면** rendering 엔진은 `data/research/...`(리서치 원본)를 읽어 `detail/.../html/`에 HTML을 쓴다.

## 실행

```bash
# 국가 진단 리포트 JSON 생성 (인자: 국가 리서치 JSON 경로) — report/country/<CODE>/data 출력
python3 app/backend/engine/generation/country_report_engine.py app/backend/storage/data/research/country/ES/ES_latest.json

# 권역 진단 리포트 JSON 생성 (인자: 권역 리서치 JSON 경로) — report/region/<REGION>/data 출력
python3 app/backend/engine/generation/region_report_engine.py app/backend/storage/data/research/region/EU/EU_latest.json

# 보고서 렌더링 — 인자는 리포트 JSON 경로 (단독 실행 가능)
# 참고: country 생성 엔진(country_report_engine.py)은 리포트 JSON 저장 후 country_report_renderer를 자동 호출해 HTML까지 만든다.
#       region 생성 엔진은 자동 호출하지 않으므로 권역 보고서 HTML은 아래처럼 별도 실행한다(country↔region 비대칭).
# 국가 보고서(PR1): report/country/<CODE>/data → report/country/<CODE>/html
python3 app/backend/engine/rendering/country_report_renderer.py app/backend/storage/report/country/ES/data/RPT_CTR_ES_001.json
# 권역 보고서(PR2): report/region/<REGION>/data → report/region/<REGION>/html
python3 app/backend/engine/rendering/region_report_renderer.py app/backend/storage/report/region/EU/data/RPT_RGN_EU_001.json

# 국가 상세화면(P1) 렌더 — 리서치 데이터(data/research/country/<CODE>) → detail/country/<CODE>/html
python3 app/backend/engine/rendering/country_detail_renderer.py ES

# 권역 상세화면(P2) 렌더 — 리서치 데이터(data/research/region/<REGION>) → detail/region/<REGION>/html
python3 app/backend/engine/rendering/region_detail_renderer.py EU
```

## 컨벤션 / 게이트

- Python 파일 편집 후 `python3 -m py_compile <file>`로 구문 확인.
- 크로스 폴더 import가 필요하면 실행 시 대상 폴더 경로를 `sys.path`에 추가하는 패턴을 따른다(예: detail 렌더러가 같은 `rendering/` 폴더의 `render_helpers`를 `sys.path`에 추가). 새 크로스 폴더 import 시 같은 방식 사용.
- 새 엔진/문서를 추가할 때는 **기존 region 구현의 구조·네이밍·경로 규칙을 그대로 따른다**(country↔region 대칭 유지).
- 상세화면(detail) 렌더러는 `rendering/templates/`의 HTML 템플릿을 읽어 `{{PLACEHOLDER}}`를 치환한다 — `country_detail_template.html`(P1)·`region_detail_template.html`(P2). 계산은 하지 않고 표현만 담당(관심사 분리).
- 상세화면(detail) 렌더러는 같은 `rendering/` 폴더의 `render_helpers`를 `sys.path`에 추가해 `import ... as rre`로 포맷·차트 헬퍼(`esc`·`fmt_value`·`line_chart`·`bar`·`score_color`·`card` 등)를 재사용한다(중복 작성 금지).
- 색상·디자인 토큰은 `architecture/design/stitch/DESIGN.md`(Kinetic Enterprise 팔레트)를 따른다.
- **프론트(UI) 구현 시 우선순위**: ① `DESIGN.md`·stitch mockup·`web_design_spec.md`가 **디자인 source of truth**(임의 변경 금지). ② `frontend-design` 스킬 = 구현 충실도·품질 게이트(반응형·키보드 포커스·`prefers-reduced-motion`·CSS specificity). ③ `ui-ux-pro-max` 스킬 = 접근성·차트 등 **검증·보강 보조**(디자인 교체·신규 팔레트 제안 금지). 상충 시 ①이 항상 우선.

## 데이터 계약

- 리서치 데이터 스키마·생성 프롬프트는 `architecture/research/` 참조 (country 정의됨, region 예정).
- `internal_latest.json`(현재 v1.3)은 스코어링 룰셋(`values`{biz_attractiveness·it_readiness·report_blend}, `similarity_item_weights`, `tier_weights`, `scoring_rules`, `quick_win_rules`, `similarity_brackets`, `maintenance_rate` 등)과 사내 자산(`country_assets`)을 담는다. 전체 키 정의·산식 매핑의 단일 출처는 `app/backend/storage/data/internal/README.md`다. (구버전 v1.2의 `weights` 키는 `values`/`similarity_item_weights`/`tier_weights`로 분리됨.)

## Git

- 커밋·푸시는 사용자가 직접 한다. 요청 없이 커밋하지 않는다.
- `__pycache__/`, `*.pyc`는 `.gitignore`로 제외됨.

## 워크플로우

- 범위가 불확실하거나 여러 파일을 건드리는 작업은 plan mode로 먼저 설계한다.
- 큰 기능은 AI-DLC 방법론을 쓸 수 있다. 채팅에서 "Using AI-DLC, ..." 로 시작하면 활성화 — 상세 룰은 @.claude/rules/aidlc.md 참조.
- 단계별 구현 계획(4개 덩어리: 백엔드 API+진단 파이프라인 → 챗봇/리서치 → 프론트 → 배포)은 @architecture/ROADMAP.md 참조. AI-DLC는 이 로드맵의 한 덩어리씩 진행한다.
- 보고서 HTML → PDF 변환이 필요하면 report-pdf 스킬 사용.

## 답변 형식
- 사용자에게 질문하거나 답변하는 경우 항상 한국어만 사용한다.
- 진행상황 표시되는 것도 한국어로 표시한다.