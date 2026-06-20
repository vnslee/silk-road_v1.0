# Storage

데이터 저장 및 관리를 담당하는 디렉토리입니다. 입력 원본(`data/`)과 생성 결과물(`report/`)을 분리해 관리합니다.

## 구조

```
storage/
├── data/                  # 입력 원본 JSON (출처 기준 구분)
│   ├── research/country/<CODE>/<CODE>_latest.json  # AI 조사 국가 데이터
│   └── internal/internal_latest.json               # 사내 데이터(룰셋·FX·자산)
└── report/                # 엔진이 생성한 결과물 (도메인 → 형식 구조)
    ├── country/<CODE>/
    │   └── data/           # 국가 진단 리포트 (JSON)
    └── region/<REGION>/
        ├── data/           # 권역 진단 리포트 (JSON, index)
        └── html/           # 권역 진단 보고서 (HTML)
```

## 엔진 연동

`app/backend/engine`의 엔진들이 이 디렉토리를 입출력 경로로 사용합니다.

- `calculation` (스코어링): `data/`에서 읽어 `report/country/`에 국가 리포트 출력
- `generation` (권역 데이터 생성): `data/`에서 읽어 `report/region/`에 권역 리포트 JSON 출력
- `rendering` (HTML 렌더링): `report/region/`의 JSON을 읽어 같은 위치에 HTML 출력

> 각 엔진은 자신의 위치 기준으로 `app/backend/storage`를 찾아 `data/`·`report/` 경로를 해석합니다.
