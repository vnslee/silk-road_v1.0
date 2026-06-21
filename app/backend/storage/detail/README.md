# Detail

상세화면(P1/P2) 렌더링 엔진이 생성한 **정적 HTML 산출물**을 저장하는 디렉토리입니다.
진단 **보고서**(PR1/PR2)는 `../report/`에, 상세 **화면**(P1/P2)은 여기에 둡니다.
도메인(country/region) 아래에서 ID별로 한 번 더 구분하고, 그 아래 `html/`에 결과물을 둡니다.

## 구조

```
detail/
├── country/<CODE>/
│   └── html/                       # 국가 상세화면(P1) — country_detail_rendering_engine 산출
│       └── <CODE>_detail_<TS>.html
└── region/<REGION>/
    └── html/                       # 권역 상세화면(P2) — region_detail_rendering_engine 산출
        └── <REGION>_detail_<TS>.html
```

- 렌더링 엔진은 `../data/research/{country,region}/<ID>/<ID>_latest.json`(리서치 데이터)를 읽어
  `detail/<도메인>/<ID>/html/`에 HTML을 씁니다. 계산은 하지 않고 표현만 담당합니다.
- `report/`와 동일한 컨벤션(`<ID>/html/`)을 따르되, 산출물이 진단 보고서가 아니라 상세화면이므로
  루트를 `detail/`로 분리합니다.

## 입력

- P1(국가): `../data/research/country/<CODE>/<CODE>_latest.json`
- P2(권역): `../data/research/region/<REGION>/<REGION>_latest.json`
  - ⚠️ 권역 리서치 데이터·스키마는 **잠정**입니다. 정식 region 리서치 프롬프트·스키마는
    ROADMAP 2차(`architecture/research/`에 country↔region 대칭 추가)에서 확정됩니다.
    현재 `region/EU/EU_latest.json`은 P2 렌더 검증용 잠정 샘플입니다.
