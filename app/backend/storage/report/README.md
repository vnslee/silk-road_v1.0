# Report

엔진이 생성한 리포트 결과물을 저장하는 디렉토리입니다. 도메인(country/region) 아래에서 산출물 형식(`data/` JSON, `html/` HTML)으로 한 번 더 구분합니다.

## 구조

```
report/
├── country/<CODE>/
│   └── data/                  # 국가 진단 리포트 (JSON) — calculation 엔진 산출
│       ├── <CODE>_rpt_<TS>.json
│       └── <CODE>_rpt_latest.json
└── region/<REGION>/
    ├── data/                  # 권역 진단 리포트 (JSON, index) — generation 엔진 산출
    │   ├── <REGION>_rpt_<TS>.json
    │   ├── <REGION>_rpt_latest.json
    │   └── index.json         # 버전 매니페스트(화면 드롭다운 소스)
    └── html/                  # 권역 진단 보고서 (HTML) — rendering 엔진 산출
        └── <REGION>_rpt_<TS>.html
```

- `data/`는 generation/calculation 엔진의 JSON 산출물, `html/`은 rendering 엔진의 HTML 산출물입니다.
- rendering 엔진은 같은 도메인의 `data/`에서 JSON을 읽어 `html/`에 HTML을 씁니다.

> 입력 원본 데이터는 `../data/`에 있습니다.
