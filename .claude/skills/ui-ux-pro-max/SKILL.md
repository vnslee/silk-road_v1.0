---
name: ui-ux-pro-max
description: UI/UX 검증·보강 보조 레퍼런스. 접근성·인터랙션·반응형·폼·차트 점검 체크리스트와 차트 25종 선택 가이드를 제공한다. 사용자가 "UX 점검", "접근성 검토", "차트 선택", "디자인 시스템 검증", "UI 리뷰", "ui ux pro max"를 언급하거나 PR1/PR2 보고서 데이터 시각화를 다룰 때 사용. ⚠️ 기존 Kinetic Enterprise 팔레트/mockup을 교체하지 않는다 — 검증·보강 전용. (출처: nextlevelbuilder/ui-ux-pro-max-skill, MIT — LICENSE.txt)
---

# UI/UX Pro Max — 검증·보강 보조 (silk-road 적용판)

원본은 브리프에서 **새 디자인 시스템을 생성**하는 CLI 스킬(`uipro`)이다. 하지만 silk-road는 이미 확정된 디자인이 있으므로, 이 vendored 판은 **디자인 생성 기능을 제외**하고 다음 용도로만 쓴다:

1. **품질 검증** — 구현한 화면을 접근성·인터랙션·반응형·폼 체크리스트로 점검.
2. **차트 선택** — PR1/PR2 보고서 데이터 시각화에서 데이터 유형 → 차트 유형 매핑(`reference/charts.csv`).
3. **안티패턴 점검** — 흔히 놓치는 UI 결함 회피.

> 🚫 **하지 않는 것**: 신규 팔레트·폰트·스타일을 *제안·적용*하지 않는다. 색/타이포/간격의 source of truth는 항상 `architecture/design/stitch/DESIGN.md`(Kinetic Enterprise)와 8개 mockup이다. 신규 스타일 제안이 떠오르면 적용하지 말고 기존 디자인과의 **대비 검토 자료**로만 쓰고 사용자에게 확인한다. 구현 심미·충실도 게이트는 [[frontend-design]] 스킬을 함께 본다.
>
> 📝 원본 체크리스트 상당수는 iOS/Android/React Native 네이티브 앱 기준이다. silk-road는 **React + Vite 웹**이므로, 아래 항목 중 웹에 해당하는 것만 적용한다(터치 타깃 44pt → 웹은 클릭/포커스 영역, safe-area → 웹은 불필요 등).

## 적용 시점

화면이 **보이는 방식·느낌·움직임·인터랙션을 바꿀 때** 사용한다. 순수 백엔드/API/인프라 작업에는 쓰지 않는다.

---

## Quick Reference 체크리스트 (우선순위 1→10)

### 1. 접근성 (CRITICAL)
- 본문 대비 4.5:1 이상(큰 텍스트 3:1) — Kinetic Enterprise `text-primary #000` on `surface #fbf9f9`는 통과, `text-secondary #555`/`text-disabled #BEBEBE`는 용도 확인.
- 아이콘 전용 버튼에 `aria-label`. Material Symbols 아이콘에 접근성 라벨.
- 키보드 Tab 순서 = 시각 순서. 포커스 링 가시화(2–4px) — **절대 제거 금지**.
- `<label for>`로 폼 라벨. 제목 위계 h1→h6 건너뛰지 않기.
- 색만으로 의미 전달 금지(아이콘/텍스트 병행).
- `prefers-reduced-motion` 존중 — D3 인트로/모션에 필수.
- 모달·다단계 흐름에 취소/뒤로(escape route).

### 2. 인터랙션 (CRITICAL)
- 클릭/탭을 1차 인터랙션으로(hover 단독 의존 금지).
- 비동기 중 버튼 비활성 + 스피너/진행 표시.
- 클릭 가능 요소에 `cursor: pointer`.
- 에러 메시지는 문제 위치 근처에.
- press 시 시각 피드백(상태 레이어/스케일 0.95–1.05).

### 3. 성능 (HIGH)
- 이미지 WebP/AVIF + `srcset`, below-fold는 `loading="lazy"`.
- `width/height` 또는 `aspect-ratio` 선언 → CLS 방지.
- `font-display: swap`. 라우트/기능별 코드 스플리팅(React Suspense/dynamic import).
- 50+ 항목 리스트는 가상화. 프레임당 작업 ~16ms 이하(60fps).
- >1s 작업은 스켈레톤/시머.

### 4. 스타일 선택 (HIGH)
- **이 프로젝트는 스타일이 고정**(Kinetic Enterprise). 신규 스타일 선택 금지.
- SVG/벡터 아이콘만(이모지를 구조 아이콘으로 금지). 한 아이콘 세트로 통일(stroke·radius 일관).
- hover/pressed/disabled 상태 시각적 구분. elevation/shadow 스케일 일관(DESIGN.md elevation 토큰).
- 화면당 primary CTA 1개, 나머지는 시각적으로 종속.

### 5. 레이아웃 & 반응형 (HIGH)
- `<meta viewport width=device-width initial-scale=1>` (zoom 비활성 금지).
- 모바일 우선 → 태블릿 → 데스크톱. 체계적 브레이크포인트(375/768/1024/1440 — DESIGN.md는 12/8/4 컬럼 그리드).
- 모바일 가로 스크롤 금지. 4/8px 간격 시스템(DESIGN.md spacing).
- 데스크톱 일관 max-width. z-index 스케일 정의(0/10/20/40/100/1000).
- 모바일 `min-h-dvh` 선호(100vh 회피).

### 6. 타이포 & 색 (MEDIUM)
- 본문 line-height 1.5–1.75, 1줄 65–75자.
- 타입 스케일 일관 — DESIGN.md(display-lg 48 / headline 32·24 / body 18·16·14 / label 12·11) 사용.
- **시맨틱 색 토큰만 사용**(컴포넌트에 raw hex 금지) — Tailwind config에 매핑된 Kinetic Enterprise 토큰.
- 데이터 열/가격/타이머는 tabular figures.

### 7. 애니메이션 (MEDIUM)
- 마이크로 인터랙션 150–300ms, 복합 전환 ≤400ms, >500ms 회피.
- `transform`/`opacity`만 애니메이트(width/height/top/left 금지 → reflow).
- enter는 ease-out, exit는 ease-in이며 enter의 ~60–70% 길이.
- 화면당 핵심 1–2개만. **모든 애니메이션 `prefers-reduced-motion` 대응.**
- 모달/시트는 트리거 지점에서 등장(scale+fade/slide).

### 8. 폼 & 피드백 (MEDIUM)
- placeholder가 아닌 가시 라벨. 에러는 해당 필드 아래.
- submit 시 로딩 → 성공/에러 상태. 필수 필드 표시.
- 빈 상태에 도움 메시지 + 액션. 토스트 3–5s 자동 닫힘(`aria-live="polite"`, 포커스 가로채기 금지).
- 파괴적 액션 전 확인 + undo 제공. blur 시 검증(키 입력마다 X).
- 시맨틱 input type(email/tel/number). 에러 메시지 = 원인 + 해결법.
- submit 에러 후 첫 무효 필드로 포커스 이동.

### 9. 내비게이션 (HIGH)
- 현재 위치 시각 강조. 뒤로 가기 예측 가능 + 스크롤/상태 보존.
- 모든 핵심 화면 deep link/URL 도달 가능 — silk-road는 URL 해시로 인트로 스킵/딥링크(`intro_spec.md`).
- 데스크톱(≥1024px) 사이드바, 모바일 상/하단 내비.
- 모달을 1차 내비 흐름으로 쓰지 않기. 모달에 명확한 닫기.

### 10. 차트 & 데이터 (LOW) → PR1/PR2 핵심
- 데이터 유형에 맞는 차트(추세→라인, 비교→바, 비율→파이/도넛 ≤5범주). 상세 매핑: **`reference/charts.csv`**.
- 색만으로 구분 금지(패턴/형태 병행), 색맹 대비 red/green 단독 회피.
- 범례 항상 표시(차트 근처), hover/tap 툴팁으로 정확값.
- 차트의 **표 대체본** 제공(스크린리더). 축 라벨 단위 표기.
- 모바일에서 reflow/단순화. 빈 데이터 상태/로딩 스켈레톤.
- 차트 진입 애니메이션도 `prefers-reduced-motion` 존중.

---

## reference/charts.csv 사용법

PR1/PR2 보고서의 지표를 시각화할 때, 데이터 성격(추세·비교·비율·KPI vs 목표·지리 등)으로 행을 골라 다음 컬럼을 본다:
- **Best Chart Type / Secondary Options** — 권장 차트
- **When to Use / When NOT to Use** — 적용·회피 조건
- **Accessibility Grade / A11y Fallback** — 접근성 등급(A11y가 C/D면 표 대체본 필수)
- **Color Guidance** — 단, 실제 색은 Kinetic Enterprise 토큰으로 매핑(차트 CSV의 hex를 그대로 쓰지 말 것)
- **Library Recommendation** — React 환경이면 Recharts/Chart.js/D3 우선 고려

예: "권역별 성과 비교" → `Compare Categories` 행 → 정렬된 Bar Chart(AAA, 값 라벨 항상 표시). "목표 대비 KPI" → `Performance vs Target` → Gauge/Bullet.

---

## 흔한 비전문가 티 (회피)
- 이모지를 구조 아이콘으로 사용 → SVG 아이콘으로.
- 컴포넌트에 하드코딩 hex → 시맨틱 토큰.
- 포커스 링 제거, hover 단독 의존.
- 레이아웃을 흔드는 press 효과(transform로 위치 변경 시 reflow).
- 색만으로 의미 전달(에러 red 등에 아이콘/텍스트 병행).

## 원본 전체 기능이 필요하면
원본은 161 팔레트 / 67 스타일 / 57 폰트페어 / 99 UX 가이드라인 / 10 스택을 CSV DB + Python 검색 스크립트로 제공한다(`uipro init`). silk-road는 디자인이 고정이라 **생성 기능은 vendoring하지 않았다.** 원본 데이터가 필요하면 `github.com/nextlevelbuilder/ui-ux-pro-max-skill` 참조.
