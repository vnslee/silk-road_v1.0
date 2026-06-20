# AI 리서치 — 조사 항목 + 프롬프트 (v2 확정본)

> "조사 버튼" 누르면 국가명을 넣고 이 프롬프트로 AI 리서치 → country.json 생성.
> **internal.json(베이스라인·구간표·가중치)은 조사 대상 아님** — 사람이 관리.
>
> **v2 변경점**
> - MVP/확장1·2·3축 4단 분류 제거 → 평면 나열. (노출 제어는 화면 config가 담당)
> - `tier_group` 필드 삭제. required/optional 태그도 데이터에 안 박음 (산식 필수성은 엔진이 항목명으로 매핑).
> - `tier`(출처 신뢰도 1~4)는 **유지** — 모든 조사 항목 필수. (※ 노출용 tier_group과 다른 축)
> - AI 교차 인사이트 블록 → 별도 item 아님. `overall_insight`로 흡수. 항목별 `insight`는 유지.
> - NEWS 외부 이슈 스캔 신규 item. 출처는 화이트리스트로 강제. credit_abs=tier2 / 그 외 언론=tier3.

---

## 1. 리서치 프롬프트 (그대로 사용)

```
역할: 너는 20년차 글로벌 오토파이낸스 진출 컨설턴트다.
대상 국가: {COUNTRY}
권역: {REGION}  (EU | AMERICAS | APAC)
타깃 세그먼트: {SEGMENT}  (예: 개인 신차 / B2B 리스)

아래 항목을 조사해 지정된 JSON 스키마로만 출력하라.
설명·마크다운·코드펜스 없이 순수 JSON만.

[조사 항목]
각 항목은 [category / role]을 지정값으로 출력하라. (필수/노출 여부는 시스템이 관리하므로 신경 쓰지 말 것)

■ 시장·매력도
  오토금융/리스 시장규모        [business / score]  ※시계열
  오토금융 성장률(CAGR)         [business / score]  ※시계열
  금융 이용률(신차)             [business / score]  ※시계열
  금융 이용률(중고차)           [business / score]
  평균 금리/APR                 [business / score]  ※시계열
  신차 판매대수                 [business / score]  ※시계열
  구매 패턴(할부·리스 비중)     [business / score]
  캡티브 강도(점유율)           [business / score]
  1위사 점유율                  [business / score]
  법인세율                      [business / score]
  이자소득 원천징수             [business / score]
  배당 원천징수                 [business / score]

■ 게이트(진입 가부)
  외국인 지분 한도              [shared / gate]
  외환·배당 송금 자유도         [shared / gate]
  데이터 현지화 의무            [shared / gate]
  국가신용등급                  [shared / gate]
  라이선스 취득 가능 여부(외국사) [shared / gate]
  라이선스 체제(세그먼트별)      [shared / gate]
  금리 상한 규제                [shared / gate]
  최저자본금                    [shared / score]

■ IT·유사도(베이스라인 대비)
  솔루션 벤더                   [it / score]
  솔루션 유형                   [it / score]
  디지털 채널 성숙도            [it / score]
  신용정보(CB) 인프라           [it / score]
  결제·정산 인프라             [it / score]
  디지털 딜러 성숙도           [it / score]
  국외이전 제한                 [it / score]

■ 회수·규제(상품/리스크)
  차량회수 절차 용이성          [shared / score]
  법적 회수 소요기간            [shared / score]
  추심 규제                     [shared / score]
  충당금 규정                   [shared / score]
  연체 분류 기준                [shared / score]

■ 특화요건(베이스라인 시스템에 없는 A국 고유 규제)
  의무보험 규제                 [shared / score]
  신용생명보험 규제             [shared / score]
  보험 끼워팔기 규제            [shared / score]
  AI 신용평가 규제              [shared / score]

■ 리스 손익(EV/잔가)
  EV 보급률                     [business / score]  ※시계열
  EV·ICE 잔존가치 리스크        [business / score]  ※시계열

■ 서술·배경(context)
  해당국 정성 요약              [business / context]
  브랜드 Top10                  [business / context]
  OEM 순위                      [business / context]
  금융사 순위                   [business / context]
  경쟁사 리스트                 [business / context]
  경쟁사 진출 형태              [business / context]
  경쟁사 금리 범위              [business / context]
  평균 신차가격                 [business / context]
  규제기관 식별                 [shared  / context]

■ 외부 이슈 스캔(NEWS) — 아래 [NEWS 규칙] 별도 적용

[각 항목 규칙]
1. value: 최신 실측치 우선. 없으면 추정하고 tier·estimated로 표시.
2. tier (출처 신뢰도, 점수에 곱하지 말 것):
   1 = 법령·관보·감독기관 공식·중앙은행·통계청
   2 = 산업협회·대형 컨설팅/회계법인 리포트
   3 = 업계 매체·시장조사 추정치
   4 = 블로그·뉴스·AI 추정
   ★ 모든 조사 항목에 tier 필수.
3. source: 출처를 구체적으로 명시(기관·문서명).
4. insight: 컨설턴트 코멘트 1~2문장. 진출 함의 중심. insight_ai_generated=true 고정.
5. 수치+추세 항목(※시계열 표시)은 timeseries 필수. 대상:
   시장규모 · 성장률 · 금융이용률(신차) · APR · 신차 판매대수 · EV 보급률 · EV·ICE 잔존가치
   - history: 과거 5년(2021~2025) {year,value}
   - forecast: 향후 5년(2026~2030) {year,value}
   - cagr_hist, cagr_forecast 계산
   - 실측 아니면 estimated:true
   ※ 시계열 항목은 전 국가 동일 윈도(2021~2030)·동일 단위로 통일.
6. gate 항목은 gate_result(PASS/FAIL/FLAG)·gate_scope(country/segment/operating_model) 판정.
   ★ 단, 출처 tier가 3 이하면 FAIL 금지 → FLAG(실사 보류)로.
7. 세그먼트 의존 항목(라이선스·금리상한·회수)은 세그먼트별 차이를 value/insight에 명시.
8. score 항목 중 등급형(CB인프라·디지털성숙도·회수용이성 등)은 1~5 정수,
   unit에 "maturity_1to5" / "ease_1to5" 등 명시. direction·axis 지정.

[NEWS 규칙] — 외부 이슈 스캔 (신규)
- 단일 item으로 출력.
  item="외부 이슈 스캔", category="business", role="context",
  context_type="news".
- value는 이슈 객체 배열. 각 객체:
  { news_category, headline(한 줄), so_what(진출 함의 한 줄),
    publisher, pub_date(YYYY-MM-DD), url }
- 형식 강제: 이슈 한 줄 + 진출 함의(so_what) 한 줄 + 출처.
  함의 없는 단순 뉴스 나열 금지.
- ★ 출처는 아래 화이트리스트로 제한. 화이트리스트 밖 매체는 채택 금지.
  geopolitical : Reuters · Bloomberg · AP
  finance      : Financial Times · Wall Street Journal
  auto_market  : Automotive News(Europe) · Just Auto · WardsAuto ·
                 Automobilwoche · Nikkei Asia
  auto_finance : Auto Finance News · American Banker ·
                 Cox Automotive/Manheim(MUVVI) · S&P Global Mobility
  credit_abs   : Moody's · S&P · Fitch 의 auto loan ABS·딜린퀀시 리포트
- ★ NEWS의 tier:
  credit_abs 카테고리(무디스·S&P·피치 정량 리포트) = tier 2
  그 외 모든 언론 카테고리 = tier 3
- 각 news_category당 1~2건. {COUNTRY} 또는 {REGION} 직접 관련 이슈만.
- 해당 카테고리에서 화이트리스트 출처로 못 찾으면 그 항목은 비우고
  so_what="조사 필요"로 표기. 절대 지어내지 말 것(환각 금지).
- pub_date는 가급적 최근 6개월 내. 오래된 이슈는 진출 함의가 살아있을 때만.

[국가 종합 — overall_insight]
진출 전략 관점 4~6문장. 보고서 도입부용.
아래 교차 해석을 녹여라(별도 item 아님, overall_insight 안에서 서술):
- 비용/난이도 드라이버: 어느 축·요건이 진입 부담을 키우나
- 불일치 포착: 비즈니스 매력도와 IT 유사도가 엇갈리는 지점과 함의
- 다크호스/리스크 플래그: 특정 축이 매우 강하거나(재검토 가치)
  매우 약한(실행 리스크) 지점
- ★ 새 수치를 지어내지 말 것 — 위에서 조사한 항목 값만 근거로 해석.

[출력 형식]
country_schema.md 의 country JSON 구조를 그대로 따른다.
최상위: country, region, is_baseline(기본 false), currency,
schema_version="1.0", data_year, fetched_by="ai".
(fetched_at은 시스템이 주입하므로 비워둬도 됨)
items 배열에 위 모든 항목 + 외부 이슈 스캔(NEWS)을 객체로.
★ tier_group·required/optional 등 노출·필수성 메타는 출력하지 말 것
  (시스템이 항목명으로 관리).
순수 JSON만 출력. 코드펜스·설명 금지.
```

---

## 2. 운영 팁
- **2단계 검토**: AI 1차 → 컨설턴트 보정(특히 tier1 게이트·라이선스). 보정 시 `fetched_by="consultant_reviewed"`.
- **세그먼트 우선 고지**: 프롬프트에 타깃 세그먼트(개인 신차 / B2B 리스)를 함께 주면 게이트·유사도 정확도↑.
- **JSON 강제**: "순수 JSON만, 코드펜스 금지"를 안 지키면 파싱 깨짐 → 받은 뒤 ```json 펜스 제거 후 parse.
- **추정 투명성**: `estimated:true`·tier4는 화면에서 "추정" 배지 + 실사 체크리스트행.
- **노출/필수성은 화면 책임**: 어떤 항목을 보고서에 띄울지(참고 항목 포함)·어떤 항목이 산식 필수인지는 view config·엔진이 항목명으로 관리. 조사 JSON엔 그 메타가 없다.

---

## 3. 책임 경계 (보고서 = 3개 소스 합)
- **country.json** (이 프롬프트) — 외부 조사 사실값 + 항목별/국가 insight.
- **internal.json** (사람 관리) — 자사 자산·구축실적·구독료 구간표·가중치. 조사 대상 아님.
- **엔진** — 유사도 점수·승수·게이트 판정·TCO·최종 순위 계산(`[CALC]`).
> 이 프롬프트 결과 단독으로 보고서가 완성되지 않음. 위 3개가 만나야 완성.