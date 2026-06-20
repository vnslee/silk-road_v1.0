# Research

AI 리서치로 국가(country) 데이터를 생성하기 위한 명세 문서를 포함하는 디렉토리입니다.

## 문서

| 문서 | 내용 |
|------|------|
| `country_research_prompt.md` | 국가 리서치 진행 시 AI에 입력할 프롬프트 |
| `country_research_schema.md` | 리서치 결과 데이터(country JSON)의 스키마 정의 |

## 산출물 연계

- 이 명세에 따라 생성된 국가 데이터는 `app/backend/storage/data/research/country/<CODE>/<CODE>_latest.json` 에 저장됩니다.
- 해당 데이터의 실제 구조 및 `schema_version`은 위 스키마 문서를 기준으로 합니다.
