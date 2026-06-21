# Report

엔진이 생성한 **진단 보고서(PR1/PR2)** 결과물을 저장하는 디렉토리입니다. 도메인(country/region) 아래에서 산출물 형식(`data/` JSON, `html/` HTML)으로 한 번 더 구분합니다.

> 상세화면(P1/P2) HTML은 별개 산출 라인으로 `../detail/`에 저장됩니다 (`../detail/README.md` 참조).

## 구조

```
report/
├── country/<CODE>/
│   ├── data/                  # 국가 진단 리포트 (JSON) — country_report_engine 산출
│   │   └── RPT_CTR_<CODE>_<NNN>.json
│   └── html/                  # 국가 진단 보고서 (HTML, PR1) — country_report_renderer 산출
│       └── RPT_CTR_<CODE>_<NNN>.html
├── region/<REGION>/
│   ├── data/                  # 권역 진단 리포트 (JSON) — region_report_engine 산출
│   │   └── RPT_RGN_<REGION>_<NNN>.json
│   └── html/                  # 권역 진단 보고서 (HTML, PR2) — region_report_renderer 산출
│       └── RPT_RGN_<REGION>_<NNN>.html
└── analysis/<REGION>/         # 권역 갭 분석(유형2) JSON — region_report_engine의 gap 산출물
    └── RPT_RGN_<REGION>_<NNN>.json
```

> `analysis/`는 정식 권역 리포트(`region/<REGION>/data/`)와 파일 ID 규칙(`RPT_RGN_<REGION>_<NNN>`)은 같지만 **별개 산출 라인**입니다. 키 구조가 달라(`report_type`·`analysis_type=TYPE2`·`by_category`·`type2_readiness`·`critical_gaps` 등) 정식 리포트(`report_id`·`tabs` 구조)와 섞이지 않습니다. 현재 `analysis/EU`에 `RPT_RGN_EU_001~011.json`이 존재합니다.

- `data/`는 generation 엔진(`country_report_engine.py`·`region_report_engine.py`)의 JSON 산출물, `html/`은 rendering 엔진의 HTML 산출물입니다.
- 파일 ID는 `RPT_CTR_<CODE>_<NNN>`(국가)·`RPT_RGN_<REGION>_<NNN>`(권역)이며 `<NNN>`은 기존 파일 수에 따라 증가하는 3자리 번호입니다.
- rendering 엔진은 같은 도메인의 `data/`에서 JSON 경로를 인자로 받아 같은 ID로 `html/`에 HTML을 씁니다.

> 입력 원본 데이터는 `../data/`에 있습니다.
