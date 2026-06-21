# Internal Configuration (`internal_latest.json`)

리포트 엔진이 사용하는 **정책·가중치·환율·자산 데이터** 스냅샷. 외부 조사 데이터(`storage/data/research/...`)와 달리 **내부 입력값**이며, 운영자가 직접 수정한다.

## 운영 원칙

- **단일 파일·단일 진실**: 모든 산식 파라미터가 이 파일 하나에 모여 있다. 엔진은 매 실행마다 디스크에서 새로 읽는다 (캐싱 없음).
- **즉시 반영**: 값을 수정하고 엔진을 다시 돌리면 다음 보고서부터 바로 반영된다. 코드 수정 불필요.
- **스냅샷 보존**: 보고서 생성 시 `internal_latest.json`의 값이 보고서 JSON에 복사되어 박힌다 → 같은 보고서는 같은 결과로 재현 가능.
- **변경 후 검증**: 수정 후 JSON 유효성 확인 권장
  ```bash
  python3 -c "import json; json.load(open('storage/data/internal/internal_latest.json')); print('OK')"
  ```

## 적용 흐름

```
1. internal_latest.json 수정 (예: tier_weights.tier2: 0.85 → 0.6)
       ↓
2. 엔진 재실행 → 새 RPT_*.json 생성 (새 점수로)
       python3 engine/generation/region_report_engine.py <region_data.json>
       python3 engine/generation/country_report_engine.py <country_data.json>
       ↓
3. 렌더러 재실행 → HTML 재생성
       python3 engine/rendering/region_report_renderer.py <RPT_RGN_*.json>
       python3 engine/rendering/country_report_renderer.py <RPT_CTR_*.json>
```

> 주의: HTML만 재생성하면 점수는 안 바뀐다. **엔진 → 렌더러** 순서를 지킬 것.

---

## 키 분류표

### 메타

| 키 | 타입 | 용도 |
|---|---|---|
| `version` | string | 컨피그 버전 (예: "1.2") |
| `updated_at` | ISO datetime | 마지막 수정 시각 |

### 1. 권역·국가 구조 (Region · Country)

| 키 | 타입 | 설명 |
|---|---|---|
| `country_assets` | `{ISO2: {solution, build_cost, build_months, reuse_factor}}` | **기진출국**의 시스템·구축비·기간. 유형1 TCO 산식에서 `B 구축비용·기간`으로 사용. |
| `region_baselines` | `{region: ISO2}` | 권역별 기준국(B국) — `EU=GB, NA=US, APAC=AU`. 권역 보고서에서 IT 유사도 비교 기준. |
| `country_to_region` | `{ISO2: region}` | 국가 → 권역 매핑. 신규 국가 추가 시 여기에 등록. |
| `country_status` | `{ISO2: "운영중"\|"준비중"\|"미진출"}` | 진출 단계 표시 (UI 용). |

### 2. 베이스라인 채점 (탭1-1 유사도 비교 기준)

| 키 | 타입 | 설명 |
|---|---|---|
| `baseline_scoring` | `{ISO2: {country_name, system_solution, as_of, items: {...}}}` | **기준국별 디멘전 점수표**. 신규국 country JSON에는 `target_score`만 두고, 엔진이 여기서 `base_score`를 매칭해 유사도 산정. |
| `baseline_scoring.{ISO2}.items.{항목}.dimensions` | `{디멘전명: {score:1~5, note}}` | 6개 항목(솔루션 유형·디지털 성숙도·구매패턴·라이선스·데이터현지화·차량회수)별 4~5개 디멘전 점수. |
| `baseline_scoring.{ISO2}.items.{항목}.similarity_axis` | `"system"\|"product"\|"regulatory"\|"risk"` | 항목이 속한 유사도 축. |
| `baseline_scoring.{ISO2}.items.{항목}.similarity_weight` | float | 종합 유사도 산정 시 항목 가중치. |

> 현재 GB는 채워져 있고 US/AU는 `[TODO]` MOCK 값. 운영자 검증·보강 필요.

#### 점수 척도 (1~5 공통)

| 점수 | 의미 |
|---|---|
| **5** | 매우 강함 / 매우 용이 / 장벽 거의 없음 |
| **4** | 강함 / 대체로 용이 |
| **3** | 중간 / 보통 |
| **2** | 약함 / 부담 있음 |
| **1** | 매우 약함 / 거의 불가 / 매우 까다로움 |

#### 디멘전별 채점 루브릭 (Rubric)

원본 수치를 1~5점 척도로 환산할 때 참고할 가이드. 운영자가 베이스라인 점수를 매기거나 신규국 `target_score`를 검증할 때 사용.

##### 솔루션 유형 (axis: `system`)

| 디멘전 | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| 배포형태(패키지/SI/SaaS) | 표준 SaaS, 즉시 사용 | 패키지 + 일부 커스텀 | 패키지 + 자체 코어 혼재 | 대부분 SI 커스텀 | 완전 자체구축 |
| 커스터마이징 자유도 | 모듈·확장 자유 | 핵심 모듈 자유 | 일부 제한 | 벤더 의존 큼 | 거의 불가 |
| 벤더 종속도 | 멀티 벤더·교체 용이 | 일부 종속 | 중간 | 단일 벤더 강한 종속 | 완전 락인 |
| 멀티테넌시 여부 | 기본 제공 | 부분 지원 | 옵션 | 제한적 | 미지원 |

##### 디지털 채널 성숙도 (axis: `system`)

| 디멘전 | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| 온라인 신청 연동 | 핵심 채널 100% 연동 | 주요 채널 연동 | 일부 연동 | 제한적 | 없음 |
| 비대면 계약 가능 | 풀 디지털 | 일부 대면 필요 | 절반 대면 | 대면 위주 | 전부 대면 |
| API 개방도 | Open Banking급 표준 | 광범위 공개 | 일부 공개 | 제한적 | 폐쇄 |
| 페이퍼리스 수준 | 100% 디지털 | 대부분 디지털 | 혼재 | 종이 위주 | 종이 |

##### 구매 패턴(할부·리스 비중) (axis: `product`)

| 디멘전 | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| 리스 취급 일치도 | 두 시장 모두 활성·구조 동일 | 활성·일부 차이 | 한쪽만 활성 | 미성숙 | 시장 없음 |
| 렌탈 취급 일치도 | 동일 | 유사 | 부분 일치 | 차이 큼 | 없음 |
| 플릿 취급 일치도 | 동일 | 유사 | 부분 일치 | 차이 큼 | 없음 |
| 상품별 비중 유사도 | ±5%p 이내 | ±10%p | ±15%p | ±25%p | ±25%p 초과 |

##### 라이선스 체제 (axis: `regulatory`)

| 디멘전 | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| 취득방식(등록 vs 인가) | 등록제, 신고 수준 | 등록 + 신원확인 | 인가, 절차 명확 | 인가, 까다로움 | 사실상 불가 |
| 외국인 취득 가능 | 100% 외국인 OK | 일부 제한 | 합작 권장 | 합작 강제 | 외국인 불가 |
| 처리기간(개월) | 1~3M | 3~6M | 6~12M | 12~24M | 24M+ |
| 최저자본금 수준 | 매우 낮음 | 합리적 | 중간 | 부담 | 매우 큼 |
| 감독 강도 | 단일·일관 | 명확·예측 가능 | 다중·복합 | 모호·재량 큼 | 자의적 |

##### 데이터 현지화 의무 (axis: `regulatory`)

| 디멘전 | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| 현지 저장 강제 | 강제 없음 | 일부 카테고리 | 핵심 데이터만 | 광범위 강제 | 전면 강제 |
| 국외 이전 허용도 | 완전 자유(EU 역내) | 적정성·SCC로 가능 | 동의/승인 필요 | 매우 제한적 | 사실상 금지 |
| 동의·보관 규제 | GDPR 동등 수준 | 명확·합리 | 복잡 | 까다로움 | 매우 엄격·재량 |
| GDPR 동등성 | 동등 | 부분 동등 | 일부 차이 | 차이 큼 | 비동등 |

##### 차량회수 절차 용이성 (axis: `risk`)

| 디멘전 | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| 사법절차 필요 | 사적/자력 회수 | 약식 절차 | 통상 사법절차 | 본안 소송 필요 | 회수 사실상 불가 |
| 회수 소요기간(일) | ≤30일 | 30~90일 | 90~180일 | 180~365일 | 365일+ |
| 자력구제 허용 | 광범위 허용 | 조건부 허용 | 제한적 | 거의 불가 | 금지 |
| 회수율 | 90%+ | 70~90% | 50~70% | 30~50% | <30% |

> **사용 원칙**
> - raw 수치(개월·일·%)는 위 표로 자동 환산 후, 운영자가 추가 보정 필요시 ±1점 조정.
> - **2점 이하**는 점수만 두지 말고 `note`에 사유 명시 (예: "사적 회수 금지로 본안 소송 필요").
> - 디멘전이 추가되면 위 표에 같은 형식으로 등록.

### 3. 가중치 (Weights) — **자주 조정**

| 키 | 타입 | 사용처 | 합계 규칙 |
|---|---|---|---|
| `similarity_item_weights` | `{항목: {axis, weight}}` | **탭 1-1 유사도** 6개 항목 가중치 (화면에서 편집) | 합 = 1.0 |
| `values.biz_attractiveness` | `{항목: weight}` | 탭 2-1 매력도 6개 항목 가중치 | 합 = 1.0 |
| `values.it_readiness` | `{축: weight}` | 탭 2-2 IT 유사도 5개 축 가중치 | 합 = 1.0 |
| `values.report_blend` | `{w_biz, w_it}` | 퀵윈 = 매력도 × w_biz + IT × w_it | 합 = 1.0 |
| `tier_weights` | `{tier1~4: multiplier, _note}` | 출처 신뢰도별 점수 가중 배수 | Tier1=1.0 고정, 나머지 조정 가능 |

> **탭 1-1 가중치는 `similarity_item_weights` 한 곳에서만 관리**. 과거에는 `baseline_scoring.{ISO2}.items.{항목}.similarity_weight`와 country JSON에 중복되어 있었으나, v1.3부터 단일화. baseline_scoring과 country JSON의 weight/axis 필드는 무시됨.

**Tier 가중치 적용 산식**:
```
유효 가중치 = 항목 가중치 × Tier 멀티플라이어
종합 점수 = Σ(정규화 × 유효가중치) ÷ Σ(유효가중치)
```

### 4. 임계값·승수표 (Thresholds & Multipliers) — **정책 조정**

| 키 | 타입 | 사용처 |
|---|---|---|
| `similarity_brackets` | `[{min, max, discount}]` | 유사도 → discount 매핑 (`calculate_similarity_discount`) |
| `similarity_multiplier_table` | `[{min, max, multiplier, band}]` | **유형1 탭1-3 산식1** — 유사도 → B 구축비용·기간에 곱하는 승수 (50%~100%) |
| `decision_thresholds` | `{expansion_min_score, hq_build_min_score}` | **유형1 탭1-2** — 시스템 결정 트리 임계값 (≥70 확산, ≥50 본사구축, 그 외 외부솔루션) |

### 5. TCO·비용 파라미터 (유형1 전용)

| 키 | 타입 | 설명 |
|---|---|---|
| `subscription_tiers` | `[{min_volume, max_volume, price_per_unit, currency}]` | 구독료 단가 구간표 — 누적 건수에 단가 소급 적용 |
| `existing_total_volume` | int | 현재 진출 시스템 전체국 누적 계약 건수 (구독료 산식 기준) |
| `expected_market_share` | float | 우리사 예상 점유율 (산식2 예상 계약건수 계산) |
| `maintenance_rate` | float | 연 유지보수율 (구축비 대비) |
| `maintenance_cost_annual` | `{amount, currency, note}` | 연간 유지보수 비용 절대값 |
| `operational_cost_10y` | `{amount, currency, note}` | 시스템과 별개인 10년 운영비 통금액 |
| `hq_build_baseline` | `{cost, months, currency, note}` | 본사 자체구축 시 기본 비용·기간 (참고용 병기) |

### 6. 통화·환율 (FX) — **다국 비교 핵심**

| 키 | 타입 | 설명 |
|---|---|---|
| `fx.base` | string | 기준통화 (`"KRW"` 고정) |
| `fx.as_of` | YYYY-MM-DD | 환율 적용일 (보고서 푸터에 표기) |
| `fx.rates` | `{currency: rate_to_KRW}` | 각 통화 1단위당 KRW 환산율 |

**원칙**: 환율은 **관리자가 직접 입력**한 값을 스냅샷에 고정한다. 실시간 환율 조회 금지(재현성 깨짐). 유형2 다국 비교는 동일 스냅샷 환율로 KRW 환산해야 비교 성립.

### 7. 레거시·미사용

| 키 | 상태 | 비고 |
|---|---|---|
| `scoring_rules` | ⚠️ 부분 사용 | `default_active`/`always_excluded`만 정의, 엔진에서 적극 사용 안 함 |
| `quick_win_rules` | ⚠️ 옛 country 엔진 잔재 | 현재 region 엔진은 `values.report_blend`를 사용. 향후 정리 대상 |

---

## 산식 위치 → Config 키 매핑

| 산식 (명세 §) | 위치 | Config 키 |
|---|---|---|
| 탭2-1 매력도 = Σ(정규화 × 유효가중치) | `region_report_engine.compute_attractiveness` | `values.biz_attractiveness`, `tier_weights` |
| 탭2-2 IT 유사도 = Σ(raw × 유효가중치) | `region_report_engine.compute_it_similarity` | `values.it_readiness`, `tier_weights` |
| 퀵윈 = 매력도 × w_biz + IT × w_it | `region_report_engine.compute_quickwin` | `values.report_blend` |
| 기준국 식별 | `region_report_engine._baseline_country_code` | `region_baselines` |
| 탭1-1 유사도 (디멘전 채점) | `country_report_engine.calculate_similarity_score` | `baseline_scoring`, `values.similarity_axis_weights` (있을 시) |
| 탭1-2 시스템 결정 | `country_report_engine.determine_system_decision` | `decision_thresholds`, `country_assets`, `hq_build_baseline` |
| 탭1-3 산식1 승수 | `country_report_engine.calculate_similarity_multiplier` | `similarity_multiplier_table` |
| 탭1-3 산식2 예상 건수 | `country_report_engine.calculate_expected_contracts` | `expected_market_share` |
| 탭1-3 산식3 구독료 | `country_report_engine.calculate_subscription_fee` | `subscription_tiers`, `existing_total_volume` |
| 탭1-3 산식4 10년 TCO | `country_report_engine.calculate_tco_10y` | `country_assets`, `maintenance_cost_annual`, `operational_cost_10y`, `hq_build_baseline` |
| 통화 환산 | both engines | `fx.rates`, `fx.as_of` |

---

## 자주 하는 작업

### 매력도 가중치 재배분
```jsonc
// values.biz_attractiveness — 항목 가중치 (합=1.0)
{
  "GDP 성장률": 0.30,         // 25 → 30 (성장성 중시)
  "자동차 판매대수": 0.20,
  "시장규모(CAGR)": 0.20,
  "금융 이용률": 0.15,
  "금융이용유형": 0.10,
  "경쟁강도": 0.05            // 10 → 5
}
```

### Tier 신뢰도 강화 (Tier3 이하 점수 영향 축소)
```jsonc
"tier_weights": {
  "tier1": 1.0,    // 고정
  "tier2": 0.85,
  "tier3": 0.5,    // 기존 0.7 → 0.5 (참고치 영향력 축소)
  "tier4": 0.2     // 기존 0.5 → 0.2 (추정치 거의 무시)
}
```

### 시스템 결정 트리 보수화
```jsonc
"decision_thresholds": {
  "expansion_min_score": 80,   // 기존 70 → 80 (확산 더 엄격)
  "hq_build_min_score": 60     // 기존 50 → 60
}
```

### 새 국가 추가
1. `country_to_region`에 `"DE": "EU"` 등록
2. `country_status`에 `"DE": "미진출"` 등록
3. 필요 시 `baseline_scoring`에 디멘전 점수 추가 (기준국만)
4. `storage/data/research/country/DE/DE_latest.json` 리서치 데이터 별도 작성

### 환율 갱신
```jsonc
"fx": {
  "as_of": "2026-09-01",       // 날짜 갱신
  "rates": {
    "EUR": 1480.0,             // 1450 → 1480
    "PLN": 345.0,
    ...
  }
}
```

---

## 폴백 안전망 (키 누락 시)

엔진은 누락된 키에 대해 안전한 폴백을 적용한다 (작동은 하되 명시적 정책 적용 안 됨):

| 키 누락 | 폴백 동작 |
|---|---|
| `tier_weights` 통째 | 모든 항목 ×1.0 (가중 없음) |
| `tier_weights.tierN` 개별 | 해당 tier ×1.0 |
| `decision_thresholds` | 명세 기본 70/50 사용 |
| `similarity_multiplier_table` | 빈 표 → multiplier 1.0 (재사용 없음) |
| `expected_market_share` | 0.02 (=2%) |
| `region_baselines.{region}` | "GB" |

폴백이 작동한다 ≠ 의도된 결과. 변경 후 보고서를 확인해 폴백이 발동했는지 점검할 것.

---

## 관련 파일

- `engine/generation/region_report_engine.py` — 권역(유형2) 보고서 엔진
- `engine/generation/country_report_engine.py` — 국가(유형1) 보고서 엔진
- `engine/rendering/ruleset_config_renderer.py` — 이 config를 UI로 시각화하는 페이지 생성기
- `architecture/research/report_generate_req.md` — 보고서 생성 명세서 (정책 출처)
- `architecture/research/report_render_req.md` — 렌더링 명세서
