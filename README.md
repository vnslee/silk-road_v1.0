# silk-road_v1.0

글로벌 오토파이낸스 진출 진단 서비스. 국가·권역 데이터를 기반으로 진출 매력도·난이도·퀵윈을 스코어링하고, 인터랙티브 지도 UI에서 진단 보고서를 제공한다.

## 디렉토리 구조

```
silk-road_v1.0/
├── app/                        # 애플리케이션 소스 코드
│   ├── backend/
│   │   ├── engine/             # 핵심 로직 엔진 (generation · rendering)
│   │   └── storage/            # 데이터 저장소 (data 입력 · report/detail 출력)
│   └── frontend/               # 프론트엔드 클라이언트 코드
└── architecture/               # 아키텍처·설계 문서
    ├── design/                 # 화면 디자인·UX 명세 (design_spec, stitch 목업)
    └── research/               # AI 리서치 명세 (국가 데이터 생성용 프롬프트·스키마)
```

## 구성 안내

| 영역 | 경로 | 내용 |
|------|------|------|
| 엔진 | [app/backend/engine](app/backend/engine/README.md) | 리포트 생성(generation)·HTML 렌더링(rendering) 파이프라인 |
| 저장소 | [app/backend/storage](app/backend/storage/README.md) | 입력 데이터(`data/`)와 생성 결과물(진단 보고서 `report/`·상세화면 `detail/`) |
| 프론트엔드 | [app/frontend](app/frontend/README.md) | 클라이언트 코드 |
| 디자인 | [architecture/design](architecture/design/README.md) | 화면 명세, 디자인 시스템, 화면 목업 |
| 리서치 | [architecture/research](architecture/research/README.md) | 국가 데이터 생성용 프롬프트·스키마 명세 |

## 데이터 흐름

```
research 명세 → AI 리서치 → storage/data (국가·권역·내부 데이터)

# 진단 보고서(PR1/PR2) 라인
   → engine/generation (country·region report engine) → storage/report/.../data (리포트 JSON)
   → engine/rendering (report renderer) → storage/report/.../html (HTML 보고서)

# 상세화면(P1/P2) 라인 — 리서치 원본을 직접 렌더
   → engine/rendering (detail renderer) → storage/detail/.../html (HTML 상세화면)
```
