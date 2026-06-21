# AI 리서치 — 권역 글로벌 뉴스 조사 + 프롬프트 (v1)

> "권역 조사 버튼" 누르면 권역코드를 넣고 이 프롬프트로 AI 리서치 → region(news) JSON 생성.
> **보고서(PR2) 또는 단일국 보고서(PR1)의 "외부 이슈 스캔" 블록에 쓸, 해당 국가가 속한 권역의 글로벌·권역 뉴스**를 조사한다.
> **internal.json·country 사실값(시장·규제·시계열)은 조사 대상 아님** — 이 프롬프트는 **뉴스(NEWS)만** 조사한다.
>
> **설계 원칙 (country 대칭)**
> - 출력 JSON은 **country 리서치 결과와 동일한 최상위 구조 + items 배열** 형태(`country_research_schema.md` 준수). 단 country 식별 필드(`country`/`code`/`is_baseline`/`currency`/`data_year`) 대신 **권역 식별 필드**(`region`/`region_ko`/`code`)를 쓴다.
> - items에는 **NEWS item만** 담는다(시장·게이트·유사도 score item 없음). NEWS item의 `value`(이슈 객체 배열)·화이트리스트·tier 규칙은 country 프롬프트 [NEWS 규칙]과 **완전히 동일**.
> - 이렇게 하면 country 렌더러의 `context_type=news` 카드 렌더 로직을 그대로 재사용한다.

---

## 1. 리서치 프롬프트 (그대로 사용)

```
역할: 너는 20년차 글로벌 오토파이낸스 진출 컨설턴트다.
대상 권역: {REGION}  (EU | NORTH_AMERICA | SOUTH_AMERICA | APAC)
권역 베이스라인 국가: {BASELINE_COUNTRY}  (예: EU→UK)
타깃 세그먼트: {SEGMENT}  (예: 개인 신차 / B2B 리스)

아래 [조사 항목]은 오직 하나 — "권역 외부 이슈 스캔(NEWS)"이다.
{REGION} 권역 전체에 영향을 주는 권역 공통 이슈 + 글로벌 이슈를 조사해
지정된 JSON 스키마로만 출력하라.
설명·마크다운·코드펜스 없이 순수 JSON만.

[조사 항목]
■ 권역 외부 이슈 스캔(NEWS) — 아래 [NEWS 규칙] 적용
  단일 item으로 출력.
  item="권역 외부 이슈 스캔", category="business", role="context",
  context_type="news".

[NEWS 규칙] — 권역·글로벌 이슈 스캔
- value는 이슈 객체 배열. 각 객체:
  { news_category, scope, headline(한 줄), so_what(진출 함의 한 줄),
    publisher, pub_date(YYYY-MM-DD), url }
  ※ scope = "region"(권역 공통) | "global"(글로벌이나 권역에 파급) — country 객체엔 없던 신규 필드.
- 형식 강제: 이슈 한 줄 + 진출 함의(so_what) 한 줄 + 출처.
  함의 없는 단순 뉴스 나열 금지.
- ★ 범위: {REGION} 권역 전체 공통 이슈 + 권역에 파급되는 글로벌 이슈.
  특정 한 나라에만 국한된 이슈는 제외(그건 country 조사가 담당).
  - region : {REGION} 권역 다수 국가에 공통으로 작용하는 이슈
             (예: EU 차원 규제·ECB 정책·역내 ABS 동향)
  - global : 권역 밖에서 발생했으나 {REGION}에 파급되는 이슈
             (예: 호르무즈 해협·미 금리·글로벌 OEM 전동화 전략)
- ★ 출처는 아래 화이트리스트로 제한. 화이트리스트 밖 매체는 채택 금지.
  카테고리별 허용 매체와 그 **공식 도메인**은 다음과 같다. url은 반드시
  해당 매체의 공식 도메인(서브도메인 포함)에서만 인용한다.
  geopolitical : Reuters (reuters.com) · Bloomberg (bloomberg.com) · AP (apnews.com)
  finance      : Financial Times (ft.com) · Wall Street Journal (wsj.com)
  auto_market  : Automotive News Europe (europe.autonews.com) · Just Auto (just-auto.com) ·
                 WardsAuto (wardsauto.com) · Automobilwoche (automobilwoche.de) ·
                 Nikkei Asia (asia.nikkei.com)
  auto_finance : Auto Finance News (autofinancenews.net) · American Banker (americanbanker.com) ·
                 Cox Automotive/Manheim·MUVVI (coxautoinc.com · manheim.com) ·
                 S&P Global Mobility (spglobal.com)
  credit_abs   : Moody's (moodys.com) · S&P (spglobal.com) · Fitch (fitchratings.com)
                 의 auto loan ABS·딜린퀀시 리포트
- ★★ 출처 검증(강제): 채택 전 각 이슈마다 다음을 모두 만족해야 한다.
  ① publisher가 위 화이트리스트의 이름과 정확히 일치할 것.
  ② url의 호스트가 그 매체의 공식 도메인(또는 그 서브도메인)과 일치할 것
     — 도메인이 일치하지 않으면(예: 화이트리스트 매체를 인용한 제3자 블로그·
     집계 사이트·소셜 링크) 채택 금지.
  ③ url은 실재하는 기사/리포트를 가리킬 것 — url·headline·pub_date를 지어내지 말 것.
  위 ①②③ 중 하나라도 충족 못 하면 그 객체는 비우고
  so_what="조사 필요", publisher="", pub_date="", url="" 로 표기(환각 금지).
- ★ NEWS의 tier:
  credit_abs 카테고리(무디스·S&P·피치 정량 리포트) = tier 2
  그 외 모든 언론 카테고리 = tier 3
- 각 news_category당 1~2건. 반드시 {REGION} 권역에 작용하는 이슈만.
- 해당 카테고리에서 화이트리스트 출처로 못 찾으면 그 항목은 비우고
  so_what="조사 필요"로 표기. 절대 지어내지 말 것(환각 금지).
- pub_date는 가급적 최근 6개월 내. 오래된 이슈는 진출 함의가 살아있을 때만.

[권역 종합 — overall_insight]
권역 진출 전략 관점 3~5문장. 보고서 외부이슈 섹션 도입부용.
조사한 뉴스 이슈들이 {REGION} 진출에 주는 공통 함의를 녹여라.
(지정학·금리·규제·전동화·신용 리스크가 권역에 어떻게 겹쳐 작용하는지)
- ★ 새 수치를 지어내지 말 것 — 조사한 뉴스 이슈만 근거로 해석.

[출력 형식]
country_research_schema.md 의 JSON 구조를 따르되 권역 축으로 식별 필드를 바꾼다.
최상위:
  region        ("European Union" 등 권역 영문명),
  region_ko     ("유럽권역" 등),
  code          (EU | NORTH_AMERICA | SOUTH_AMERICA | APAC),
  baseline_country ({BASELINE_COUNTRY}),
  schema_version="1.0",
  fetched_by="ai",
  overall_insight,
  items
(fetched_at은 시스템이 주입하므로 비워둬도 됨)
items 배열에는 위 "권역 외부 이슈 스캔(NEWS)" item **하나만** 넣는다.
(country와 달리 시장·게이트·유사도 score item은 넣지 않는다 — 뉴스 전용.)
★ tier_group·required/optional 등 노출·필수성 메타는 출력하지 말 것.
순수 JSON만 출력. 코드펜스·설명 금지.

[저장 경로]
생성된 region(news) JSON은 아래 경로에 저장한다:
  app/backend/storage/data/research/region/{권역코드}/{권역코드}_news_{타임스탬프}.json
- {권역코드}: 사내 권역 코드 (EU | NORTH_AMERICA | SOUTH_AMERICA | APAC).
- {타임스탬프}: ISO 8601 형식 YYYY-MM-DDTHHMM (예: 2026-06-21T1200).
- 해당 권역 폴더가 없으면 새로 생성한다.
- 동일 폴더의 {권역코드}_news_latest.json 포인터를 방금 생성한 파일 내용으로 갱신한다.
  예: app/backend/storage/data/research/region/EU/EU_news_2026-06-21T1200.json
      app/backend/storage/data/research/region/EU/EU_news_latest.json (최신본 복사)
★ 파일명에 반드시 `_news_` 토큰을 넣는다 — 같은 폴더의 country 집계본
  ({권역코드}_{타임스탬프}.json / {권역코드}_latest.json, fetched_by="aggregator")과
  물리적으로 분리·구분하기 위함. 집계본을 덮어쓰지 말 것.
```

---

## 2. 출력 예시 (EU 권역 뉴스)

```json
{
  "region": "European Union",
  "region_ko": "유럽권역",
  "code": "EU",
  "baseline_country": "UK",
  "schema_version": "1.0",
  "fetched_at": "2026-06-21T12:00:00+09:00",
  "fetched_by": "ai",
  "overall_insight": "EU 권역은 ECB의 점진적 금리 인하와 CO2 규제·ZEV 압박이 동시에 작용하는 국면이다. 전동화 가속은 역내 공통으로 리스 잔가 리스크를 키우는 반면, ABS 신용성과는 대체로 견조해 충당금 기조는 보수적 유지가 합리적이다. 글로벌 차원의 공급망·지정학 변동(부품 리드타임)이 차량가와 재고금융에 파급되므로, 권역 진입 초기 물량·잔가 가정을 보수적으로 잡는 전략이 유효하다.",
  "items": [
    {
      "item": "권역 외부 이슈 스캔",
      "category": "business",
      "role": "context",
      "context_type": "news",
      "value": [
        {
          "news_category": "geopolitical",
          "scope": "global",
          "headline": "중동 해상 물류 긴장으로 유럽향 차량·부품 리드타임 변동",
          "so_what": "조달 코스트·납기 변동 → 차량가·재고금융 부담. EU 권역 초기 물량 가정 보수적으로.",
          "publisher": "Reuters",
          "pub_date": "2026-05-30",
          "url": "https://www.reuters.com/..."
        },
        {
          "news_category": "finance",
          "scope": "region",
          "headline": "ECB 점진적 금리 인하 기조, 유로존 여신 비용 완만한 하락",
          "so_what": "조달금리 하락은 마진에 우호적이나 경쟁사 금리 인하 압박 동반. APR 설계 여지와 경쟁 강도 동시 점검.",
          "publisher": "Financial Times",
          "pub_date": "2026-05-12",
          "url": "https://www.ft.com/..."
        },
        {
          "news_category": "auto_market",
          "scope": "region",
          "headline": "EU CO2·ZEV 규제 강화로 역내 BEV 비중 상승 지속",
          "so_what": "전동화 가속 → 리스 잔가(GFV) 리스크 권역 공통 확대. EV 잔가 곡선 보수적 반영 필요.",
          "publisher": "Automotive News Europe",
          "pub_date": "2026-04-22",
          "url": "https://europe.autonews.com/..."
        },
        {
          "news_category": "credit_abs",
          "scope": "region",
          "headline": "유럽 auto loan/lease ABS 딜린퀀시 안정, 잔가 노출은 모니터링 대상",
          "so_what": "연체 안정적이나 BEV 잔가가 ABS 리스크 요인. 충당금·잔가 가정 보수적 유지 권장.",
          "publisher": "Moody's",
          "pub_date": "2026-04-18",
          "url": "https://www.moodys.com/..."
        },
        {
          "news_category": "auto_finance",
          "scope": "region",
          "headline": "조사 필요",
          "so_what": "조사 필요",
          "publisher": "",
          "pub_date": "",
          "url": ""
        }
      ],
      "tier": 3,
      "source": "화이트리스트(Reuters·FT·Automotive News Europe·Moody's 등)",
      "insight": "지정학·금리·규제·신용 리스크가 권역에 동시에 작용. auto_finance 카테고리는 화이트리스트 출처 미확보 — 실사 단계 보강.",
      "insight_ai_generated": true
    }
  ]
}
```

> ※ NEWS item의 `value` 객체 구조는 `country_research_schema.md` §3 `context_type="news"`와 동일하며, **권역 전용 `scope`(region/global) 필드만 추가**된다. tier·화이트리스트 규칙도 country와 같다.

---

## 3. country ↔ region(news) 대칭 정리

| 구분 | country 리서치 | region(news) 리서치 (이 문서) |
|---|---|---|
| 트리거 | 국가 조사 버튼 | 권역 조사 버튼 |
| 식별 필드 | `country`·`code`(ISO2)·`is_baseline`·`currency`·`data_year` | `region`·`region_ko`·`code`(EU 등)·`baseline_country` |
| items 구성 | 시장·게이트·유사도·context + NEWS | **NEWS item 1개만** |
| NEWS scope | 단일국·해당 권역 이슈 | **권역 공통 + 글로벌**(단일국 한정 이슈 제외) |
| NEWS 객체 | news_category·headline·so_what·publisher·pub_date·url | + **scope(region/global)** |
| 화이트리스트·tier | (공통) | (동일) |
| 저장 경로 | `data/research/country/<ISO2>/<ISO2>_latest.json` | `data/research/region/<REGION>/<REGION>_news_latest.json` |
| 보고서 연계 | PR1 외부 이슈 스캔 | PR2 권역 이슈 / PR1 권역 이슈 섹션 |

> ⚠️ **뉴스 데이터는 집계본과 별도 관리한다.** 같은 `data/research/region/EU/` 폴더에 두 종류의 산출물이 공존한다:
> - **집계본** `EU_latest.json` / `EU_<타임스탬프>.json` (`fetched_by="aggregator"`) — country들을 집계한 유사도·매력도 입력. `region_detail_rendering_engine`·`region_report_engine`이 읽는다. **이 프롬프트는 건드리지 않는다.**
> - **뉴스본** `EU_news_latest.json` / `EU_news_<타임스탬프>.json` (`fetched_by="ai"`) — 이 프롬프트의 산출물. 보고서 외부 이슈 스캔 입력.
>
> 파일명의 `_news_` 토큰 + `fetched_by` 값 두 축으로 구분되므로 서로 덮어쓸 위험이 없다.
