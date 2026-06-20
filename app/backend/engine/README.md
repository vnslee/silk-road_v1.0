# Engine

핵심 비즈니스 로직을 처리하는 엔진 모듈입니다. 권역(region) 진단 보고서 생성 파이프라인을 단계별로 구성합니다.

## 파이프라인 단계

```
calculation → generation → rendering
 (스코어링)    (데이터 생성)   (HTML 렌더링)
```

| 폴더 | 파일 | 역할 |
|------|------|------|
| `calculation/` | `scoring_engine.py` | 단일국 스코어링 엔진. 활성 항목 기반으로 매력도·난이도·유사도 등을 계산 |
| `generation/` | `region_report_generation_engine.py` | 권역 퀵윈 스코어링. `scoring_engine`을 재사용해 권역 내 국가를 일괄 평가하고 리포트 JSON 생성 |
| `rendering/` | `region_report_rendering_engine.py` | 리포트 JSON을 받아 권역 진단 보고서(PR2) standalone HTML로 렌더링. 계산은 하지 않고 표현만 담당 |
| `rendering/templates/` | `region_report_template.html` | 렌더링 엔진이 읽는 HTML 템플릿. `{{PAGE_TITLE}}`·`{{TAB_NAV}}`·`{{TAB_PANELS}}` 등 플레이스홀더를 치환해 최종 보고서 생성 |

## 모듈 의존 관계

- `generation`은 형제 폴더의 `calculation`(스코어링)과 `rendering`(렌더링)을 import 합니다.
- 크로스 폴더 import를 위해 `generation` 엔진이 실행 시 형제 폴더 경로를 `sys.path`에 추가합니다.
- `rendering` 엔진은 `rendering/templates/region_report_template.html`을 읽어 플레이스홀더를 치환하는 방식으로 HTML을 생성합니다 (템플릿 경로: `<엔진폴더>/templates/`).

## 실행

```bash
# 권역 리포트 데이터 생성 (+ 내부적으로 렌더링까지 위임)
python3 generation/region_report_generation_engine.py <REGION>

# 렌더링만 단독 실행 (리포트 JSON이 이미 있는 경우)
python3 rendering/region_report_rendering_engine.py <REGION>
```

> 출력물: `report/region/<REGION>/data/<REGION>_rpt_<TS>.json` (generation) 및 `report/region/<REGION>/html/<REGION>_rpt_<TS>.html` (rendering)
