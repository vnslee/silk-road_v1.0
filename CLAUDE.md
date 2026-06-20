# silk-road_v1.0

글로벌 오토파이낸스 진출 진단 서비스. 국가·권역 데이터를 스코어링하고 인터랙티브 지도 UI + 챗봇으로 진단 보고서를 제공한다.

서비스는 **국가(country)** 와 **권역(region)** 두 축으로 구성되며, 리서치 명세·엔진·산출물이 각 축별로 존재한다(권역은 구현됨, 국가 전용은 확장 예정).

## 아키텍처

- `app/backend/engine/` — Python 엔진 파이프라인 (calculation → generation → rendering)
  - `calculation/scoring_engine.py` — 단일국 스코어링 (매력도·난이도·유사도)
  - `generation/region_report_generation_engine.py` — 권역 퀵윈 스코어링 → 리포트 JSON 생성
  - `rendering/region_report_rendering_engine.py` — 권역 리포트 JSON → HTML 보고서 렌더링
  - ⚠️ generation/rendering은 현재 **권역(region) 전용**. **국가(country) 전용 generation/rendering 엔진이 추가될 예정** — 추가 시 region 엔진과 동일한 구조·경로 규칙을 따른다.
- `app/backend/storage/` — 데이터 (입력/출력 분리)
- `app/frontend/` — 클라이언트 (지도 UI + 챗봇)
- `architecture/` — 설계 명세
  - `design/` — 화면·디자인 명세
  - `research/` — AI 리서치 프롬프트·스키마. 현재 **country만 정의됨**(`country_research_prompt.md`, `country_research_schema.md`). **region 리서치 프롬프트·스키마가 추가될 예정** — country와 동일한 파일 네이밍(`region_research_*.md`)을 따른다.

## 경로 규칙 (중요)

- 엔진은 자기 위치 기준으로 `app/backend/storage`를 찾아 경로를 해석한다 (각 엔진 상단의 `STORAGE` 변수).
- **입력**: `storage/data/research/country/<CODE>/<CODE>_latest.json` (AI 조사), `storage/data/internal/internal_latest.json` (사내 룰셋). 권역 데이터가 추가되면 `storage/data/research/region/...` 형태를 따른다.
- **출력**: 리포트 JSON은 `storage/report/<country|region>/<ID>/data/`, HTML은 `.../html/` 에 둔다. JSON과 HTML을 같은 폴더에 섞지 않는다.
- rendering 엔진은 `data/`에서 JSON을 읽어 `html/`에 HTML을 쓴다.

## 실행

```bash
# 단일국 스코어링 (국가코드 + 선택 추가항목)
python3 app/backend/engine/calculation/scoring_engine.py PL

# 권역 리포트 데이터 생성 (+ 내부적으로 렌더링까지 위임)
python3 app/backend/engine/generation/region_report_generation_engine.py EU

# 권역 렌더링만 단독 실행 (리포트 JSON이 이미 있을 때)
python3 app/backend/engine/rendering/region_report_rendering_engine.py EU
```

## 컨벤션 / 게이트

- Python 파일 편집 후 `python3 -m py_compile <file>`로 구문 확인.
- 엔진 간 import는 `generation`이 형제 폴더(`calculation`, `rendering`)를 `sys.path`에 추가하는 패턴을 따른다. 새 크로스 폴더 import 시 같은 방식 사용.
- 새 엔진/문서를 추가할 때는 **기존 region 구현의 구조·네이밍·경로 규칙을 그대로 따른다**(country↔region 대칭 유지).
- rendering 엔진은 `rendering/templates/region_report_template.html`을 읽어 `{{PLACEHOLDER}}`를 치환한다. 계산은 하지 않고 표현만 담당(관심사 분리).
- 색상·디자인 토큰은 `architecture/design/stitch/DESIGN.md`(Kinetic Enterprise 팔레트)를 따른다.

## 데이터 계약

- 리서치 데이터 스키마·생성 프롬프트는 `architecture/research/` 참조 (country 정의됨, region 예정).
- `internal_latest.json`은 스코어링 룰셋(weights, scoring_rules, quick_win_rules, similarity_brackets, maintenance_rate)과 사내 자산(country_assets)을 담는다.

## Git

- 커밋·푸시는 사용자가 직접 한다. 요청 없이 커밋하지 않는다.
- `__pycache__/`, `*.pyc`는 `.gitignore`로 제외됨.

## 워크플로우

- 범위가 불확실하거나 여러 파일을 건드리는 작업은 plan mode로 먼저 설계한다.
- 큰 기능은 AI-DLC 방법론을 쓸 수 있다. 채팅에서 "Using AI-DLC, ..." 로 시작하면 활성화 — 상세 룰은 @.claude/rules/aidlc.md 참조.
- 단계별 구현 계획(4개 덩어리: 백엔드 API+진단 파이프라인 → 챗봇/리서치 → 프론트 → 배포)은 @architecture/ROADMAP.md 참조. AI-DLC는 이 로드맵의 한 덩어리씩 진행한다.
- 보고서 HTML → PDF 변환이 필요하면 report-pdf 스킬 사용.
