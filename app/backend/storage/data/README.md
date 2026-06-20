# Data

엔진 입력으로 사용되는 원본 데이터를 **출처(provenance) 기준**으로 구분해 저장하는 디렉토리입니다.

## 구조

- `research/` - AI로 조사한 외부 데이터
  - `country/<CODE>/<CODE>_latest.json` - 국가별 조사 데이터 (예: `research/country/PL/PL_latest.json`)
- `internal/` - 사내 데이터
  - `internal_latest.json` - 스코어링 룰셋(가중치·FX·유사도 구간·quick_win_rules 등) 및 사내 자산 정보(country_assets)

> 생성된 리포트 결과물은 `../report/`에 저장됩니다.
