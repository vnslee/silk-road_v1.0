# Storage

데이터 저장 및 관리를 담당하는 디렉토리입니다. 입력 원본(`data/`)과 생성 결과물(진단 보고서 `report/`, 상세화면 `detail/`)을 분리해 관리합니다.

## 구조

```
storage/
├── data/                  # 입력 원본 JSON (출처 기준 구분)
│   ├── research/country/<CODE>/<CODE>_latest.json  # AI 조사 국가 데이터
│   ├── research/region/<REGION>/<REGION>_latest.json  # AI 조사 권역 데이터 (잠정 — README 참조)
│   └── internal/internal_latest.json               # 사내 데이터(룰셋·FX·자산)
├── report/                # 진단 보고서(PR1/PR2) 결과물 (도메인 → 형식 구조)
│   ├── country/<CODE>/
│   │   └── data/           # 국가 진단 리포트 (JSON)
│   └── region/<REGION>/
│       ├── data/           # 권역 진단 리포트 (JSON, index)
│       └── html/           # 권역 진단 보고서 (HTML)
└── detail/                # 상세화면(P1/P2) 결과물 (도메인 → html)
    ├── country/<CODE>/html/   # 국가 상세화면 (HTML) — country_detail_rendering_engine 산출
    └── region/<REGION>/html/  # 권역 상세화면 (HTML) — region_detail_rendering_engine 산출
```

## 엔진 연동

`app/backend/engine`의 엔진들이 이 디렉토리를 입출력 경로로 사용합니다.

- `calculation` (스코어링): `data/`에서 읽어 `report/country/`에 국가 리포트 출력
- `generation` (권역 데이터 생성): `data/`에서 읽어 `report/region/`에 권역 리포트 JSON 출력
- `rendering` (보고서 HTML): `report/region/`의 JSON을 읽어 같은 위치 `html/`에 보고서 HTML 출력
- `rendering` (상세화면 HTML): `data/research/{country,region}/`의 리서치 JSON을 읽어 `detail/<도메인>/<ID>/html/`에 상세화면 HTML 출력 (P1·P2)

> 각 엔진은 자신의 위치 기준으로 `app/backend/storage`를 찾아 `data/`·`report/`·`detail/` 경로를 해석합니다.
