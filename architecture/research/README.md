# Research

AI 리서치로 국가(country) 데이터를 생성하기 위한 명세와, 그 데이터를 진단 보고서로 만드는 생성·렌더링 엔진 명세 문서를 포함하는 디렉토리입니다.

## 문서

| 문서 | 내용 |
|------|------|
| `country_research_prompt.md` | 국가 리서치 진행 시 AI에 입력할 프롬프트 |
| `country_research_schema.md` | 리서치 결과 데이터(country JSON)의 스키마 정의 |
| `report_generate_req.md` | 보고서 생성 엔진 명세 — 리서치 JSON → 진단 리포트 JSON(데이터 원천 플래그·데이터 성격·산식). 차트/배지는 책임 밖 |
| `report_render_req.md` | 보고서 렌더링 엔진 명세 — 리포트 JSON → HTML(데이터 성격→차트 매핑·배지·레이아웃·탭 구성) |

> region 리서치 프롬프트·스키마(`region_research_*.md`)는 ROADMAP 2차에서 country 대칭으로 추가될 예정입니다.

## 산출물 연계

- 이 명세에 따라 생성된 국가 데이터는 `app/backend/storage/data/research/country/<CODE>/<CODE>_latest.json` 에 저장됩니다.
- 해당 데이터의 실제 구조 및 `schema_version`은 위 스키마 문서를 기준으로 합니다.
