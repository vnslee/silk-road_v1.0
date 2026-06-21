# 오토파이낸스 추천 엔진 — 데이터 스키마 (v1.1)

> 원칙: **데이터는 국가당 1개 JSON, 뷰는 화면단 필터.**
> 각 item에 `category`(biz/it/shared) + `role`(gate/score/context) + `tier` 태그.
> 화면은 이 태그로 필터·렌더 분기. 데이터 물리 분리 없음.
>
> **v1.1 변경점**
> - `tier_group` 필드 **삭제**. (MVP/ext 4단 분류 폐기 → 노출 제어는 화면 config가 항목명으로 관리)
> - §6 렌더규칙에서 tier_group 관련 항(구 7번) 삭제.
> - `context_type`에 **`news` 값 추가**. NEWS(외부 이슈 스캔) item의 `value` 구조 명시.
> - 필수/노출 메타는 데이터에 박지 않음 (산식 필수성=엔진, 노출=화면 config가 항목명으로 판정).
> - schema_version 1.0 → 1.1.

---

## 0. 파일 구성 — 2종, 둘 다 버전 스냅샷

```
country/<CODE>/                국가별 외부 리서치 데이터. <CODE>=ISO alpha-2 (예: PL)
  PL_2026-06-18T1432.json     → "조사 버튼" 누를 때마다 스냅샷 한 벌 (국가 단위·독립)
  PL_2026-05-02T0910.json     → 한 국가 안 모든 항목이 같은 fetched_at으로 한 덩어리 갱신
  PL_latest.json              → 최신 포인터 (화면은 이걸 읽음)

internal/                      자사 자산·계산 파라미터. 국가 무관, 사람이 관리.
  v1.2_2026-06-01.json        → 자산 추가/파라미터 변경 때마다 스냅샷 한 벌
  v1.1_2026-03-15.json
  latest.json                 → 최신 포인터
```

> **파일명 규칙:** `<CODE>_<fetched_at>.json` — 국가 코드(ISO alpha-2) prefix + 조사 시각.
> 폴더에서 분리돼도 국가 식별 가능, 여러 국가를 한 디렉터리에 모아도 안 섞임. 포인터도 `<CODE>_latest.json`.
> fetched_at의 콜론(`:`)은 파일명에 못 쓰므로 압축 표기(`2026-06-18T1432`). CODE는 country.json의 `code` 필드와 일치.

| | country | internal |
|---|---|---|
| 새 버전 트리거 | 조사 버튼 (국가별, AI) | 진출/자산추가·파라미터 변경 (사람) |
| 단위 | 국가별 독립 스냅샷 | 전체 1벌 |
| 파일명 | `<CODE>_<fetched_at>` | version + updated_at |

> **자산은 internal에 둔다.** 자산은 "조사"가 아니라 **"진출"로 생기기 때문**(트리거가 다름).
> 진출 예정국이 실제 진출하면 → internal.country_assets에 한 줄 추가 = 후보→베이스라인 승격.
> country 파일에 자산을 두면 조사 버튼이 자산을 덮어쓸 위험 → 분리.

비용은 두 파일이 만나서 계산: `country(유사도 점수) × internal(자산 비용·구간표)`.

**아티팩트 데모 주의:** React 아티팩트는 파일/스토리지 불가 → 실제 폴더 누적 안 됨.
데모는 메모리(state) 버전 배열로 흉내: `versions:[{code,fetched_at,data},...]`, 조사=push, 최신=화면/과거=드롭다운. 국가 구분은 `code`로. (새로고침 시 소멸 — 데모용)

---

## 1. country 최상위 구조

```json
{
  "country": "Poland",
  "country_ko": "폴란드",
  "code": "PL",                    // ISO 3166-1 alpha-2. 파일명과 매칭
  "region": "EU",                  // EU | NORTH_AMERICA | SOUTH_AMERICA | APAC
  "is_baseline": false,            // 이 국가가 자사 베이스라인인지 (모든 국가 공통 필드)
  "currency": "PLN",

  "schema_version": "1.1",         // 스키마 구조 버전
  "data_year": 2025,               // 데이터가 가리키는 연도
  "fetched_at": "2026-06-18T14:32:00+09:00",  // 조사 버튼 누른 시각 (국가 전체 공유)
  "fetched_by": "ai",              // ai | consultant_reviewed

  "overall_insight": "...",        // 보고서 도입부 앵커 (국가 종합 코멘트, AI 교차해석 흡수)
  "items": [ /* 아래 item 객체 배열 — 전부 같은 fetched_at */ ]
}
```

> **`data_year` ≠ `fetched_at`**: "2025년 시장 데이터를 2026-06-18에 조사했다". 둘 다 유지.
> 항목별 시각은 두지 않음 — 한 국가는 한 번에 갱신되므로 최상위 하나로 충분.
> **모든 국가가 동일 구조** (items + is_baseline). 베이스라인국도 별도 형식 없음.
> **비교는 별도 프로세스**가 담당: 같은 region의 `is_baseline:true` 국가를 찾아 신규국.items와 비교 → 유사도 산출. country엔 비교 대상을 명시하지 않음(region으로 자동 매칭).
> **freshness(신선도) 신호등**은 `fetched_at` 기준 자동 계산: 🟢방금 / 🟡30일 / 🔴90일+ 재조사 권장. (tier=출처 신뢰도와 별개 축)
> **`overall_insight`**: 국가 종합 코멘트. AI 교차 해석(비용/난이도 드라이버 · 매력도↔IT 불일치 · 다크호스/리스크)을 여기에 녹임 — 별도 item 아님. 새 수치 생성 금지(조사 항목 값만 근거).

---

## 2. item 공통 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| `item` | string | 항목명 (예: "오토금융 시장규모") |
| `category` | enum | `business` \| `it` \| `shared` — 탭 필터용 |
| `role` | enum | `gate` \| `score` \| `context` — 렌더 방식 분기 |
| `region` | enum | `EU` \| `NORTH_AMERICA` \| `SOUTH_AMERICA` \| `APAC` |
| `tier` | int(1~4) | 출처 신뢰도. 1=법령/공식, 4=AI추정 |
| `source` | string | 출처 명시 |
| `insight` | string | 컨설턴트 코멘트 (★AI 생성 — 검토 필요) |
| `insight_ai_generated` | bool | true면 "AI 해석" 배지 |

→ role에 따라 아래 필드가 **추가**된다.

> **삭제됨 (v1.1):** `tier_group`. 노출/우선순위는 데이터에 박지 않고 화면 config가 항목명으로 관리.
> **필수/선택(required/optional)도 데이터에 두지 않음** — 산식 필수성은 엔진이 항목명으로 매핑(국가 무관 고정 사실).

---

## 3. role별 추가 필드

### role = "score" (정량 점수)
| 필드 | 타입 | 설명 |
|---|---|---|
| `value` | number | 원시값 |
| `unit` | string | 단위 (USD_M, %, days, PLN, maturity_1to5, ease_1to5 등) |
| `direction` | enum | `up`(클수록 좋음) \| `down`(작을수록 좋음) |
| `axis` | enum | `attractiveness`(매력도 X) \| `difficulty`(난이도 Y) \| `similarity`(IT 유사도) |
| `timeseries` | object\|null | 수치+추세 항목만. 아니면 null |

`timeseries` 객체 (수치형만):
```json
"timeseries": {
  "history":  [{"year":2021,"value":2800}, ... 2025까지],
  "forecast": [{"year":2026,"value":4620}, ... 2030까지],
  "cagr_hist": 10.7,
  "cagr_forecast": 10.0,
  "estimated": true          // 실측 아닌 CAGR 역산/추정이면 true
}
```
> 시계열 대상(전 국가 동일 윈도 2021~2030):
> 시장규모 · 성장률 · 금융이용률(신차) · APR · 신차 판매대수 · EV 보급률 · EV·ICE 잔존가치.

### role = "gate" (Pass/Fail)
| 필드 | 타입 | 설명 |
|---|---|---|
| `value` | string | 상태 서술 (예: "100% 허용") |
| `gate_result` | enum | `PASS` \| `FAIL` \| `FLAG`(저신뢰 보류) |
| `gate_scope` | enum | `country` \| `segment` \| `operating_model` — 조건부 게이트 층위 |
| `segment` | string\|null | segment 조건부일 때 대상 (예: "consumer_credit") |

> Tier 3 이하 데이터로는 `FAIL` 금지 → `FLAG`로 보류 (실사 체크리스트행)

### role = "context" (서술/세분화)
| 필드 | 타입 | 설명 |
|---|---|---|
| `value` | string \| array \| object[] | 서술 텍스트, 목록(예: 브랜드 Top10), 또는 NEWS 이슈 객체 배열 |
| `context_type` | enum | `descriptive`(서술) \| `segmenting`(타깃 필터) \| `news`(외부 이슈 스캔) |

#### context_type = "news" 일 때 (v1.1 신규)
`value`는 **이슈 객체 배열**. 각 객체:

| 필드 | 타입 | 설명 |
|---|---|---|
| `news_category` | enum | `geopolitical` \| `finance` \| `auto_market` \| `auto_finance` \| `credit_abs` |
| `headline` | string | 이슈 한 줄 |
| `so_what` | string | 진출 함의 한 줄. 못 찾으면 "조사 필요" |
| `publisher` | string | 출처 매체 (화이트리스트 내에서만) |
| `pub_date` | string | YYYY-MM-DD (가급적 최근 6개월) |
| `url` | string | 기사 URL |

> **출처 화이트리스트 (밖 매체 채택 금지):**
> - geopolitical : Reuters · Bloomberg · AP
> - finance      : Financial Times · Wall Street Journal
> - auto_market  : Automotive News(Europe) · Just Auto · WardsAuto · Automobilwoche · Nikkei Asia
> - auto_finance : Auto Finance News · American Banker · Cox Automotive/Manheim(MUVVI) · S&P Global Mobility
> - credit_abs   : Moody's · S&P · Fitch (auto loan ABS·딜린퀀시 리포트)
>
> **NEWS item의 `tier`:** credit_abs 카테고리 = **tier 2**, 그 외 언론 카테고리 = **tier 3**.
> 화이트리스트 출처로 못 찾으면 해당 객체는 비우고 so_what="조사 필요". 지어내지 말 것(환각 금지).

---

## 4. internal.json — 자사 자산·계산 파라미터 (국가 무관, 1개)

> 조사 버튼과 무관. 사람이 관리하며 갱신 드묾. 자체 `version`·`updated_at`.

```json
{
  "version": "1.2",
  "updated_at": "2026-06-01T00:00:00+09:00",

  "country_assets": {               // 진출국별 자사 구축 실적. 진출하면 한 줄 추가.
    "UK":    { "solution": "NetSol",     "build_cost": 5000, "build_months": 18, "reuse_factor": 0.70 },
    "USA":   { "solution": "Salesforce", "build_cost": 6000, "build_months": 20, "reuse_factor": 0.50 },
    "Korea": { "solution": "Self-built", "build_cost": 4500, "build_months": 16, "reuse_factor": 1.00 }
    // 폴란드 진출 시 → "Poland": {...} 추가 = 후보→베이스라인 승격
  },

  "similarity_brackets": [
    { "min": 80, "max": 100, "discount": 0.40 },
    { "min": 70, "max": 79,  "discount": 0.30 },
    { "min": 60, "max": 69,  "discount": 0.20 },
    { "min": 50, "max": 59,  "discount": 0.10 },
    { "min": 0,  "max": 49,  "discount": 0.00 }
  ],

  "maintenance_rate": 0.18,         // 운영비 = 구축비 × 이 비율

  "weights": {
    "business": { "시장규모": 0.30, "성장률": 0.20, "침투율": 0.20, "APR": 0.15, "캡티브강도": 0.15 },
    "it":       { "솔루션벤더": 0.40, "CB인프라": 0.20, "디지털채널": 0.15, "라이선스체제": 0.15, "차량회수": 0.10 }
  }
}
```

> **베이스라인 식별:** country 파일의 `is_baseline` 필드가 가짐. 비교 프로세스가 같은 region에서 `is_baseline:true`인 국가를 기준선으로 사용.
> **자산 식별:** `country_assets`에 키가 있으면 자산 보유국. 보통 is_baseline:true 국가와 일치하나, 트리거가 달라 분리 유지.
> build_cost 단위는 통화 통일(예: USD_K).

---

## 5. 샘플 — 폴란드 (v1.1 스키마 검증)

> 신규/변경 항목 위주로 발췌(EV·판매대수·국가신용등급·NEWS + 기존 대표 항목). 실제론 §1 프롬프트의 전체 항목이 items에 들어감.

```json
{
  "country": "Poland",
  "country_ko": "폴란드",
  "code": "PL",
  "region": "EU",
  "is_baseline": false,
  "currency": "PLN",
  "schema_version": "1.1",
  "data_year": 2025,
  "fetched_at": "2026-06-18T14:32:00+09:00",
  "fetched_by": "ai",
  "overall_insight": "할부 중심에서 리스 침투가 시작되는 변곡점 시장. EU 규제 정합성이 높아 NetSol 베이스라인 재사용률이 양호하나, 소비자신용 면허(KNF)·감사회 요건이 진입 부담을 키우는 핵심 드라이버다. 비즈니스 매력도(두 자릿수 성장)는 상위권이나 차량회수의 상품별 편차(리스 용이 vs 대출 집행관 절차)가 IT 유사도를 일부 갉아먹는 불일치 지점. EV 보급 가속은 잔가 리스크를 키워 리스 손익의 변수로 부상. B2B 리스 우선 진입 후 소비자신용 확장 전략이 유효하다.",
  "items": [
    {
      "item": "오토금융/리스 시장규모",
      "category": "business", "role": "score",
      "value": 4200, "unit": "USD_M", "direction": "up", "axis": "attractiveness",
      "timeseries": {
        "history":  [{"year":2021,"value":2800},{"year":2022,"value":3100},{"year":2023,"value":3500},{"year":2024,"value":3850},{"year":2025,"value":4200}],
        "forecast": [{"year":2026,"value":4620},{"year":2027,"value":5080},{"year":2028,"value":5590},{"year":2029,"value":6150},{"year":2030,"value":6760}],
        "cagr_hist": 10.7, "cagr_forecast": 10.0, "estimated": true
      },
      "tier": 2, "source": "폴란드 리스협회(ZPL) 2025 리포트",
      "insight": "두 자릿수 성장 지속 전망. 단 캡티브 선점이 성장 과실 분배의 변수.",
      "insight_ai_generated": true
    },
    {
      "item": "신차 판매대수",
      "category": "business", "role": "score",
      "value": 475, "unit": "units_K", "direction": "up", "axis": "attractiveness",
      "timeseries": {
        "history":  [{"year":2021,"value":446},{"year":2022,"value":418},{"year":2023,"value":475},{"year":2024,"value":497},{"year":2025,"value":510}],
        "forecast": [{"year":2026,"value":525},{"year":2027,"value":540},{"year":2028,"value":555},{"year":2029,"value":568},{"year":2030,"value":580}],
        "cagr_hist": 3.4, "cagr_forecast": 2.6, "estimated": true
      },
      "tier": 2, "source": "ACEA 신차 등록 통계",
      "insight": "회복세 진입. 건수 산식의 기준 모수로, 금융침투율·우리사 점유율과 결합해 예상 계약건수 환산.",
      "insight_ai_generated": true
    },
    {
      "item": "EV 보급률",
      "category": "business", "role": "score",
      "value": 4.5, "unit": "%", "direction": "up", "axis": "attractiveness",
      "timeseries": {
        "history":  [{"year":2021,"value":1.2},{"year":2022,"value":1.9},{"year":2023,"value":2.8},{"year":2024,"value":3.6},{"year":2025,"value":4.5}],
        "forecast": [{"year":2026,"value":5.8},{"year":2027,"value":7.4},{"year":2028,"value":9.5},{"year":2029,"value":12.0},{"year":2030,"value":15.0}],
        "cagr_hist": 39.2, "cagr_forecast": 27.2, "estimated": true
      },
      "tier": 3, "source": "PSPA(폴란드 대체연료협회) 추정",
      "insight": "보급 가속 구간 진입. 리스 잔가 모델에 EV 별도 곡선 반영 필요 — 손익 변수.",
      "insight_ai_generated": true
    },
    {
      "item": "EV·ICE 잔존가치 리스크",
      "category": "business", "role": "score",
      "value": 58, "unit": "%", "direction": "down", "axis": "difficulty",
      "timeseries": {
        "history":  [{"year":2021,"value":64},{"year":2022,"value":63},{"year":2023,"value":61},{"year":2024,"value":59},{"year":2025,"value":58}],
        "forecast": [{"year":2026,"value":56},{"year":2027,"value":54},{"year":2028,"value":52},{"year":2029,"value":51},{"year":2030,"value":50}],
        "cagr_hist": -2.4, "cagr_forecast": -2.9, "estimated": true
      },
      "tier": 3, "source": "Cox Automotive/Manheim 잔가 추정(3년 EV 기준)",
      "insight": "EV 3년 잔가 하락 추세 — ICE 대비 리스 손익 압박. 잔가 보증·바이백 조건 보수적 설계 권장.",
      "insight_ai_generated": true
    },
    {
      "item": "외국인 지분 한도",
      "category": "shared", "role": "gate",
      "value": "100% 허용", "gate_result": "PASS", "gate_scope": "country", "segment": null,
      "tier": 1, "source": "폴란드 외국인투자법",
      "insight": "지분 제한 없음. 단독 진출 가능, JV 불필요.",
      "insight_ai_generated": false
    },
    {
      "item": "국가신용등급",
      "category": "shared", "role": "gate",
      "value": "A- (S&P) / A2 (Moody's), 안정적", "gate_result": "PASS", "gate_scope": "country", "segment": null,
      "tier": 1, "source": "S&P·Moody's 국가신용등급 (2025)",
      "insight": "투자등급 안정권. 송금·자본회수 리스크 낮아 킬스위치 통과.",
      "insight_ai_generated": false
    },
    {
      "item": "라이선스 취득 가능 여부(외국사)",
      "category": "shared", "role": "gate",
      "value": "소비자신용=KNF 등록 필요/취득가능, B2B리스=무면허",
      "gate_result": "PASS", "gate_scope": "segment", "segment": "consumer_credit",
      "tier": 1, "source": "KNF 규정",
      "insight": "B2B 리스는 무면허로 즉시 가능. 소비자신용은 KNF 등록+100만 PLN+감사회 — 단계적 진입 권장.",
      "insight_ai_generated": false
    },
    {
      "item": "솔루션 벤더",
      "category": "it", "role": "score",
      "value": "NetSol 계열 다수 / 일부 자체", "unit": "match", "direction": "up", "axis": "similarity",
      "timeseries": null,
      "tier": 2, "source": "시장 조사",
      "insight": "EU 베이스라인(NetSol)과 동일 생태계 — 재사용률 높음. 유사도 점수 견인 핵심.",
      "insight_ai_generated": true
    },
    {
      "item": "차량회수 절차 용이성",
      "category": "shared", "role": "score",
      "value": 3, "unit": "ease_1to5", "direction": "up", "axis": "similarity",
      "timeseries": null,
      "tier": 2, "source": "현지 법무 자문",
      "insight": "리스는 소유권 기반 회수 용이, 대출은 komornik(집행관) 수개월~년. 상품별 회수 모듈 분기 필요.",
      "insight_ai_generated": true
    },
    {
      "item": "금융사 순위",
      "category": "business", "role": "context",
      "value": ["Santander Consumer Bank", "Volkswagen Financial Services", "mBank/mLeasing", "PKO Leasing", "Toyota Bank"],
      "context_type": "descriptive",
      "tier": 3, "source": "업계 순위 추정(ZPL/시장조사)",
      "insight": "캡티브(VW·Toyota)와 은행계(Santander·PKO) 혼재. 독립계 진입 시 가격·디지털 경험으로 차별화 필요.",
      "insight_ai_generated": true
    },
    {
      "item": "브랜드 Top10",
      "category": "business", "role": "context",
      "value": ["Toyota","VW","Skoda","Kia","Hyundai","BMW","Audi","Mercedes","Ford","Renault"],
      "context_type": "descriptive",
      "tier": 3, "source": "ACEA 등록 통계",
      "insight": "독일·일본·한국 브랜드 혼재. 캡티브 강한 VW·Toyota 비중 주목.",
      "insight_ai_generated": true
    },
    {
      "item": "외부 이슈 스캔",
      "category": "business", "role": "context", "context_type": "news",
      "value": [
        {
          "news_category": "geopolitical",
          "headline": "발트·중동부 유럽 물류망 긴장으로 차량 부품 조달 리드타임 변동",
          "so_what": "조달 코스트·납기 변동 → 차량가·재고금융 부담. 초기 물량 가정 보수적으로.",
          "publisher": "Reuters",
          "pub_date": "2026-05-30",
          "url": "https://www.reuters.com/..."
        },
        {
          "news_category": "credit_abs",
          "headline": "중동부 유럽 auto loan ABS 딜린퀀시 소폭 상승 관측",
          "so_what": "연체 상승 신호 → 충당금·심사기준 보수화 필요. 진입 초기 신용정책 타이트하게.",
          "publisher": "Moody's",
          "pub_date": "2026-04-18",
          "url": "https://www.moodys.com/..."
        },
        {
          "news_category": "auto_finance",
          "headline": "조사 필요",
          "so_what": "조사 필요",
          "publisher": "",
          "pub_date": "",
          "url": ""
        }
      ],
      "tier": 3, "source": "화이트리스트(Reuters·Moody's 등)",
      "insight": "지정학·신용 리스크가 동시에 보수적 진입을 가리킴. auto_finance 카테고리는 화이트리스트 출처 미확보 — 실사 단계 보강.",
      "insight_ai_generated": true
    }
  ]
}
```

> ※ NEWS의 tier는 item 단위로 하나(여기선 혼합이라 보수적으로 3 표기). 카테고리별 신뢰도가 갈리면 객체 단위 해석은 news_category로 구분(credit_abs는 정량 tier2급).

---

## 6. 화면(뷰) 렌더 규칙 — AI에게 줄 지시 요약

```
1. 데이터 하드코딩 금지. country.json(상수)을 읽어 렌더.
2. category로 탭 필터: Biz=[business,shared] / IT=[it,shared] / 통합=전체
3. role로 표시 분기:
     gate    → PASS(초록)/FAIL(빨강)/FLAG(노랑) 배지
     score   → 점수 + 2축 매트릭스 위치 기여
     context → 서술 카드 / context_type=news면 이슈 카드 리스트(이슈+함의+출처배지)
4. timeseries 있으면 라인차트: history 실선 / forecast 점선, estimated면 "추정" 표기
5. tier → 신뢰도 배지(1=공식~4=AI추정). 점수엔 곱하지 않음(라벨만).
6. insight → 코멘트 말풍선. insight_ai_generated=true면 "AI" 배지.
7. 보고서 노출(참고항목 포함)·항목 표시여부 = 화면 config의 항목명 화이트리스트로 제어.
   (데이터엔 노출 메타 없음. 구 tier_group 토글 폐기)
8. 추천 신뢰도 = score 항목 tier 가중평균 → 상/중/하 라벨.
9. FLAG 게이트 + tier≥3 항목 → 자동 "실사 체크리스트" 생성.
10. fetched_at 기준 freshness 신호등(🟢/🟡/🔴) 국가별 표시.
11. 추천 결과에 도장: based_on = { country_versions(국가별 fetched_at), internal_version, schema_version }.
    → "이 추천은 ○○ 시점 데이터 + 파라미터 v1.x 기준". 재조사로 순위 바뀌어도 추적 가능.
12. NEWS 출처는 화이트리스트 밖이면 렌더하지 않음(데이터 단계에서 이미 걸러짐).
```

## 7. 추천 결과 도장 (재현성)

```json
{
  "recommendation": [ { "country": "Poland", "rank": 1, "attractiveness": 78, "confidence": "중" } ],
  "based_on": {
    "country_versions": { "Poland": "2026-06-18T1432", "Vietnam": "2026-06-10T0800" },
    "internal_version": "v1.2_2026-06-01",
    "schema_version": "1.1"
  }
}
```