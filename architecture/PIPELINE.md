# 파이프라인 & 흐름 명세

silk-road의 **런타임 흐름**과 **산출물 라인**을 정의한다.
화면 정적 명세(화면별 구성·진입 모드)는 `design/design_spec/web_design_spec.md`가 source of truth이고,
이 문서는 그 화면들이 **어떤 데이터·산출물을 소비/생성하며 어떻게 이어지는지**(end-to-end)를 담당한다.

> 엔진 내부 규칙은 중복 작성하지 않는다. 생성/렌더 엔진의 상세 규칙은 아래 명세를 참조:
> - 리포트 생성: [`research/report_generate_req.md`](research/report_generate_req.md)
> - 보고서 렌더링: [`research/report_render_req.md`](research/report_render_req.md)
> - 리서치 데이터: [`research/country_research_prompt.md`](research/country_research_prompt.md) · [`research/country_research_schema.md`](research/country_research_schema.md)
> - 화면 명세·User Flow: [`design/design_spec/web_design_spec.md`](design/design_spec/web_design_spec.md)

---

## 0. 개요 — 4개 런타임 흐름과 산출물 라인

<!-- 작성 가이드:
  - 4개 흐름(화면 플로우 / 리서치 수행 / 리포트 생성 / 렌더 HTML 생성)을 한 그림으로 요약.
  - 산출물 라인 2개를 명확히: 진단 보고서(PR1/PR2 → report/), 상세화면(P1/P2 → detail/).
  - 어떤 산출물이 어떤 화면에 들어가는지 1:1 매핑 표 한 개. -->

| 화면 | 산출물 | 생성 주체 | 저장 위치 |
|------|--------|-----------|-----------|
| P1 (국가 정보) | 상세화면 HTML | `rendering/country_detail_renderer.py` | `storage/detail/country/<CODE>/html/` |
| P2 (권역 정보) | 상세화면 HTML | `rendering/region_detail_renderer.py` | `storage/detail/region/<REGION>/html/` |
| PR1 (국가 보고서) | 리포트 JSON → 보고서 HTML | `generation/country_report_engine.py` → `rendering/country_report_renderer.py` | `storage/report/country/<CODE>/{data,html}/` |
| PR2 (권역 보고서) | 리포트 JSON → 보고서 HTML | `generation/region_report_engine.py` → `rendering/region_report_renderer.py` | `storage/report/region/<REGION>/{data,html}/` |

---

## 1. 화면 플로우 (데이터/산출물 관점)

<!-- 작성 가이드:
  - web_design_spec §6(User Flow)을 "화면 전환"이 아니라 "어떤 산출물을 언제 만들고 소비하나" 관점으로 보완.
  - 예: P1에서 [보고서 생성] → generation 트리거 → PS2 프로그레스 → PR1 HTML 표시.
  - 데이터가 없을 때 분기(리서치 트리거)는 §2와 연결. -->

---

## 2. 리서치 수행 흐름 (research → storage/data)

<!-- 작성 가이드:
  - 트리거: 챗봇 질의(web_design_spec §6.5) 또는 신규 국가/권역 요청.
  - Bedrock 호출 → schema 검증(country_research_schema.md) → 저장.
  - 저장 위치: storage/data/research/{country,region}/<ID>/<ID>_latest.json.
  - region 리서치 프롬프트·스키마는 ROADMAP 2차에서 추가 예정(현재 country만 정식). -->

---

## 3. 리포트 생성 흐름 (generation → report/.../data)

<!-- 작성 가이드:
  - 입력: 리서치 JSON. 출력: RPT_CTR_<CODE>_<NNN>.json / RPT_RGN_<REGION>_<NNN>.json.
  - 데이터 원천 플래그·데이터 성격(nature)까지만 JSON에 담는다 — 상세는 report_generate_req.md.
  - "차트 유형·배지·레이아웃은 생성의 책임 밖"이라는 경계 명시. -->

---

## 4. 렌더 HTML 생성 흐름 (rendering → report/.../html · detail/.../html)

<!-- 작성 가이드:
  - 보고서 라인: 리포트 JSON → *_report_renderer → PR1/PR2 standalone HTML (nature→차트 매핑은 report_render_req.md).
  - 상세화면 라인: 리서치 JSON → *_detail_renderer → P1/P2 standalone HTML (generation 단계 없이 직접 렌더).
  - 두 렌더러가 공유 헬퍼(render_helpers.py)·templates/를 쓰는 점 명시. -->

---

## 5. 프론트엔드 표시 방식 ★핵심 / web_design_spec 보완 지점★

<!-- 작성 가이드 (이 절이 이번 작업의 핵심):
  - web_design_spec §4는 P1/P2/PR1/PR2 콘텐츠를 "표·차트로 적절히 구성"이라고만 적어 프론트가 직접 그리는 것처럼 읽힌다.
    실제 구상은 "render 엔진이 만든 standalone HTML을 프론트가 embed(iframe 등)해서 보여준다".
  - 정해야 할 경계(1차 작성 시 결정):
    1) 렌더 HTML이 책임지는 영역 = 콘텐츠 본문(표/차트/탭 내부).
    2) 프론트 chrome이 책임지는 영역 = 헤더(국기·국가명·버튼), 닫기, 진입 모드(팝업/풀사이즈) 래핑, [보고서 생성]/[시뮬레이션]/[PDF]/[메일] 버튼.
    3) embed 방식: iframe vs 직접 DOM 삽입 vs 서버 프록시 — 선택과 이유.
    4) 진입 모드(web_design_spec §5.1)와 embed의 관계(팝업/풀사이즈에서 동일 HTML 재사용).
  - 결정 결과는 web_design_spec §5에 보완 노트(예: §5.5 "렌더 HTML embed")로 역링크 예정. -->

---

## 6. 시퀀스 다이어그램 (mermaid)

<!-- 작성 가이드:
  - 최소 2개: (A) 리서치 없는 국가 보고서 생성 end-to-end, (B) 기존 데이터 있는 상세화면 표시.
  - 참여자: 사용자 / 프론트 / API / generation / rendering / storage / Bedrock. -->
