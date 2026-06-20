# AI 리서치 — 조사 항목 + 프롬프트 (해커톤)

> "조사 버튼" 누르면 국가명을 넣고 이 프롬프트로 AI 리서치 → country.json 생성.
> **internal.json(베이스라인·구간표·가중치)은 조사 대상 아님** — 사람이 관리.

---

## 1. AI가 조사할 항목 목록

### MVP (필수 — 기본 화면)
| 항목 | category | role | 수치/시계열 |
|---|---|---|---|
| 오토금융/리스 시장규모 | business | score | ✅ 시계열 |
| 오토금융 성장률(CAGR) | business | score | ✅ 시계열 |
| 금융 이용률(신차) | business | score | ✅ 시계열 |
| 평균 금리/APR | business | score | ✅ 시계열 |
| 캡티브 강도(점유율) | business | score | 단일값 |
| 1위사 점유율 | business | score | 단일값 |
| 해당국 정성 요약 | business | context | 서술 |
| 외국인 지분 한도 | shared | gate | 상태 |
| 외환 송금 자유도 | shared | gate | 상태 |
| 라이선스 취득 가능 여부(외국사) | shared | gate(segment) | 상태 |
| 금리 상한 규제 | shared | gate→score | 상태/값 |
| 최저자본금 | shared | score | 단일값 |
| 데이터 현지화 의무 | shared | gate(op_model) | 상태 |
| 솔루션 벤더 | it | score(similarity) | 상태 |
| 솔루션 유형 | it | score(similarity) | 상태 |
| 신용정보(CB) 인프라 | it | score(similarity) | 등급1~5 |
| 디지털 채널 성숙도 | it | score(similarity) | 등급1~5 |
| 라이선스 체제(세그먼트별) | shared | gate→score | 상태 |
| 차량회수 절차 용이성 | shared | score(similarity) | 등급1~5 |

### 확장 1축 — IT 유사도 정밀화 (score)
추심 규제 · 법적 회수 소요기간 · 충당금 규정 · 연체 분류 기준 · 국외이전 제한 · 결제·정산 인프라 · 디지털 딜러 성숙도

### 확장 2축 — Biz 매력도 정밀화 (score, 시계열)
신차 판매대수 · 금융 이용률(중고차) · 구매 패턴(할부·리스 비중) · 법인세율 · 이자소득 원천징수 · 배당 원천징수

### 확장 3축 — 보고서 서술 (context)
브랜드 Top10 · OEM 순위 · 경쟁사 리스트 · 경쟁사 진출 형태 · 경쟁사 금리 범위 · 평균 신차가격 · 규제기관 식별

---

## 2. 리서치 프롬프트 (그대로 사용)

```
역할: 너는 20년차 글로벌 오토파이낸스 진출 컨설턴트다.
대상 국가: {COUNTRY}
권역: {REGION}  (EU | AMERICAS | APAC)
타깃 세그먼트: {SEGMENT}  (예: 개인 신차 / B2B 리스)

아래 항목을 조사해 지정된 JSON 스키마로만 출력하라. 설명·마크다운·코드펜스 없이 순수 JSON만.

[조사 항목]
(위 1번 표의 항목. MVP 필수 + 확장 1·2·3축 전부 조사)

[각 항목 규칙]
1. value: 최신 실측치 우선. 없으면 추정하고 아래 tier·estimated로 표시.
2. tier (출처 신뢰도, 점수에 곱하지 말 것):
   1 = 법령·관보·감독기관 공식·중앙은행·통계청
   2 = 산업협회·대형 컨설팅/회계법인 리포트
   3 = 업계 매체·시장조사 추정치
   4 = 블로그·뉴스·AI 추정
3. source: 출처를 구체적으로 명시(기관·문서명).
4. insight: 컨설턴트 코멘트 1~2문장. 진출 함의 중심. insight_ai_generated=true 고정.
5. 수치+추세 항목(시장규모·성장률·침투율·APR·판매대수 등)은 timeseries 필수:
   - history: 과거 5년(2021~2025) {year,value}
   - forecast: 향후 5년(2026~2030) {year,value}
   - cagr_hist, cagr_forecast 계산
   - 실측 아니면 estimated:true
6. gate 항목은 gate_result(PASS/FAIL/FLAG)·gate_scope(country/segment/operating_model) 판정.
   ★ 단, 출처 tier가 3 이하면 FAIL 금지 → FLAG(실사 보류)로.
7. 세그먼트 의존 항목(라이선스·금리상한·회수)은 세그먼트별 차이를 value/insight에 명시.

[국가 종합]
overall_insight: 진출 전략 관점 3~4문장. 보고서 도입부용.

[출력 형식]
country_schema.md 의 country JSON 구조를 그대로 따른다.
최상위에 country, region, is_baseline(기본 false), currency, schema_version="1.0",
data_year, fetched_by="ai" 포함. (fetched_at은 시스템이 주입하므로 비워둬도 됨)
items 배열에 위 모든 항목을 객체로.
```

---

## 3. 운영 팁
- **2단계 검토**: AI 1차 → 컨설턴트 보정(특히 tier1 게이트·라이선스). 보정 시 fetched_by="consultant_reviewed".
- **세그먼트 우선 고지**: 프롬프트에 타깃 세그먼트(예: 개인 신차 / B2B 리스)를 함께 주면 게이트·유사도 정확도↑.
- **JSON 강제**: "순수 JSON만, 코드펜스 금지"를 안 지키면 파싱 깨짐 → 받은 뒤 ```json 펜스 제거 후 parse.
- **추정 투명성**: estimated:true·tier4는 화면에서 "추정" 배지 + 실사 체크리스트행으로.