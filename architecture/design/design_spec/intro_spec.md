# 메인 화면 3D 지구본 + 시네마틱 인트로 — 설계 스펙

> 목적: 새 프로젝트/화면에 **"우주의 자전하는 3D 지구본 → 평면 세계지도로 펼쳐짐 → UI·첫 팝업 등장"**(디즈니 인트로식) 연출을 그대로 재현하기 위한 자급식 명세.
> 이 문서만 보고 처음부터 구현 가능하도록, 의도·기술선택·핵심 코드·튜닝값을 모두 포함한다.

---

## 1. 한눈에 보는 결과물

진입 시 3단계 시퀀스가 자동 재생된다.

1. **등장 + 자전** — 별이 은은히 반짝이는 **라이트(화이트) 배경**에 3D 지구본(orthographic)이 천천히 자전 (~1.6초)
2. **펼침(morph)** — 지구본이 옆으로 늘어나며 평면 세계지도(NaturalEarth)로 변형 (~2.0초)
3. **착지** — 평면 지도 완성 → 범례 등 UI 페이드인 → 화면 중앙에 첫 팝업(챗봇 등) 등장

> 핵심: **영상이 아니라 D3 실시간 렌더링**. 한 프레임도 미리 만들지 않고, 매 프레임 좌표를 계산해 SVG path로 그린다. 그래서 데이터 연동·인터랙션·무한 회전이 가능하다.

---

## 2. 기술 스택 / 의존성

| 항목 | 사용 |
|---|---|
| 렌더 | **D3.js v7** (`d3.geo*`, `d3.timer`, `d3.drag`, `d3.easeCubicInOut`, `d3.interpolate`) |
| 지도 데이터 | **world-atlas TopoJSON** (`countries-110m.json`) + **topojson-client** |
| DOM | SVG (육지·바다·위경도선·마커·아크), CSS keyframes(별 반짝임) |
| 빌드 | 없음. CDN 스크립트 + 순수 JS면 충분 |

CDN:
```html
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
```
데이터:
```js
const TOPO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";
```

> ⚠️ 첫 로드는 CDN 스크립트+지도 데이터를 받느라 1~2초 걸릴 수 있다. 캐시 후엔 즉시. 인트로 시작을 `MAP.ready`(데이터 로드 완료) 이후로 트리거할 것.

---

## 3. 핵심 아이디어 — 투영 모핑(projection morph)

구체 ↔ 평면 전환의 비밀은 **두 투영의 raw 함수를 t로 선형 보간**하는 것이다.

- 구체: `d3.geoOrthographicRaw`
- 평면: `d3.geoNaturalEarth1Raw` (가로로 긴 세계지도)
- 보간기를 `d3.geoProjectionMutator`로 감싸면, **같은 projection 객체를 유지한 채** `mutate(t)`로 모양만 바꿀 수 있다(rotate/scale/translate 보존).

```js
// t=0 → 구체, t=1 → 평면
function interpolatedRaw(t) {
  const a = d3.geoOrthographicRaw, b = d3.geoNaturalEarth1Raw;
  return (lambda, phi) => {
    const pa = a(lambda, phi), pb = b(lambda, phi);
    return [pa[0] * (1 - t) + pb[0] * t, pa[1] * (1 - t) + pb[1] * t];
  };
}
M.mutate = d3.geoProjectionMutator((t) => interpolatedRaw(t));
M.proj = M.mutate(0);                  // 처음엔 구체
M.proj.rotate([0, -12, 0]).precision(0.4);
```

### 모핑 중 주의점 (실제로 겪은 함정들)
1. **클립 각도**: 구체일 땐 뒷면을 가려야(`clipAngle(90)`), 펼쳐지면 해제(`clipAngle(null)`). 안 그러면 평면에서 절반이 잘린다.
   ```js
   M.applyClip = () => M.morphT < 0.5 ? M.proj.clipAngle(90) : M.proj.clipAngle(null);
   ```
2. **스케일 점프**: 구체와 평면은 적정 배율이 다르다. mode가 바뀌는 순간 튀므로 **morphT로 연속 보간**한다.
   ```js
   function baseScale() {
     const globe = Math.min(W, H) * 0.42;   // 구체: 단변 기준
     const flat  = W / 5.4;                 // 평면(NaturalEarth): 폭에 꽉 차게
     return globe + (flat - globe) * M.morphT;
   }
   ```
3. **마커 가시성**: 구체일 땐 앞면 점만 보이고(뒷면 숨김), 평면이면 전부 보인다.
   ```js
   function isVisible(lonlat) {
     if (M.morphT > 0.6) return true;                  // 거의 평면 → 다 보임
     const r = M.proj.rotate(), c = [-r[0], -r[1]];
     return d3.geoDistance(lonlat, c) < Math.PI/2 - 0.02; // 구체 앞면만
   }
   ```

---

## 4. 레이어 구조 (그리는 순서 = z-order)

SVG `#map` 안에 아래 순서로 append (뒤로 갈수록 위):

1. `circle.atm` — 대기광(radialGradient `#atmGlow`). 구체일 때만, `opacity = max(0, 1 - morphT*1.6)`
2. `path.ocean` — 바다 = `path({type:"Sphere"})` (radialGradient `#oceanGrad`)
3. `path.graticule` — 위경도선 `d3.geoGraticule10()`
4. `g.map-layer` — 국가 육지 path들 (`country-land`)
5. `g.arc-layer` — 서울 HQ ↔ 각국 연결 점선(`geoDistance` 곡선)
6. `g.marker-layer` — 수도 마커(코어 점 + halo + 라벨)

별 배경은 **별도 SVG `#starfield`** (지도 svg 뒤). 화면 크기에 비례해 점 생성:
```js
const n = Math.round((W*H)/9000);   // 별 개수
// 각 별: 랜덤 위치/반지름 + CSS @keyframes twinkle, 랜덤 animation-delay
```

---

## 5. 인트로 시퀀스 구현

`requestAnimationFrame`은 헤드리스/백그라운드 탭에서 throttle될 수 있으므로 **`d3.timer` 단일 루프**로 구현(안정적).

```js
M.runIntro = function (onDone) {
  M.mode = "globe"; M.scale = 1; M.morphT = 0; M.applyClip(); M.fit();
  M.proj.rotate([0, -12, 0]);
  M.render();
  M.svg.style("opacity", 1);          // 즉시 보이게 (별 위에 지구본)
  if (M.spinTimer) M.spinTimer.stop();

  const SPIN = 1600, MORPH = 2000;    // 자전 1.6s → 펼침 2.0s
  const ease = d3.easeCubicInOut;
  const r0 = [0, -12, 0], r1 = [-10, -8, 0];   // 펼칠 때 정면(경도 ~0)으로
  let called = false;

  M.spinTimer = d3.timer((t) => {
    if (t < SPIN) {                                  // ── 자전 구간 ──
      M.proj.rotate([r0[0] + t * 0.02, -12, 0]);
      M.render();
    } else {                                         // ── 펼침 구간 ──
      const k = Math.min((t - SPIN) / MORPH, 1), e = ease(k);
      M.mode = (e > 0.5) ? "flat" : "globe";
      const rs = M.proj.rotate();
      M.proj.rotate([rs[0] + (r1[0]-rs[0])*0.12, r0[1] + (r1[1]-r0[1])*e, 0]);
      M.setMorph(e);                                 // morphT 갱신 + 클립 + fit
      M.render();
      if (k >= 1 && !called) {
        called = true; M.spinTimer.stop();
        M.mode = "flat"; M.introDone = true; M.setMorph(1); M.render();
        onDone && onDone();                          // → UI 페이드인, 첫 팝업 노출
      }
    }
  });
};
```

부트 연결:
```js
await MAP.init();                 // 지도 데이터 로드까지 끝난 뒤
setOverlayHidden(true);           // 범례 등 숨김
if (location.hash) {              // 딥링크 진입 → 인트로 생략, 바로 평면
  MAP.mode="flat"; MAP.introDone=true; MAP.setMorph(1); MAP.render();
  setOverlayHidden(false); showFirstPopup();
} else {
  MAP.runIntro(() => { setOverlayHidden(false); showFirstPopup(); });
}
```

---

## 6. 인트로 이후 인터랙션

- **자전 정지**: 인트로 후 `autorotate=false`(평면에선 자전 안 함).
- **드래그**: 구체일 땐 회전(`proj.rotate`), 평면에선 회전이 곧 패닝처럼 동작.
- **휠 줌**: `M.scale` 1~6 clamp.
- **국가/권역 포커스**: `rotateTo(lonlat, scale, dur)` — `proj.rotate`를 목표 경위도(`[-lon,-lat,0]`)로 트윈하며 줌. 해당국 `region-active` 하이라이트.
- **리셋(전체 보기)**: 평면이면 `[-10,-8,0]`로 복귀(자전 재개 안 함), 구체면 복귀 후 자전 재개.

---

## 7. 디자인 토큰 (색/스타일) — 라이트 테마 (DESIGN.md Kinetic Enterprise 팔레트)

> 기준 색: **primary-container `#003478`** (딥 네이비, DESIGN.md 기준). 다크모드 아님 — 화이트~라이트그레이 배경.
> 색상 토큰은 `../stitch/DESIGN.md`의 Kinetic Enterprise 팔레트를 따른다.
> 핵심 원칙: ① 배경은 화이트~라이트그레이(surface 계열), ② 육지는 primary-container 네이비, ③ **경계선은 흰색이 아니라 육지보다 진한 같은 계열 반투명**(흰선이 튀는 것 방지), ④ 바다는 육지보다 **밝게**(육지가 위로 떠 보이게, primary-fixed 계열).

```css
/* 배경: surface 계열 → 화이트 */
.map-stage { background: radial-gradient(1200px 760px at 68% 18%, #f5f3f3 0%, #fbf9f9 48%, #ffffff 100%); }
/* 별 (라이트 배경에 거슬리지 않게 톤다운, outline-variant) */
@keyframes twinkle { 0%,100%{opacity:.15} 50%{opacity:.5} }
.star { fill:#c4c6d2; animation: twinkle 4.5s ease-in-out infinite; }
/* 육지: primary-container. 경계선은 같은 계열 진한색 반투명 → 자연스럽게 구분(흰선처럼 튀지 않음) */
.country-land { fill:#003478; stroke:rgba(0,32,78,.45); stroke-width:.4px;
                vector-effect:non-scaling-stroke; transition:fill .25s; }
.country-land.region-active { fill:#00204e; stroke:rgba(0,16,40,.55); } /* 포커스/하이라이트, primary */
.country-land.land-hover    { fill:#005db7; cursor:pointer; }           /* secondary */
```

> ⚠️ **경계선에 `vector-effect:non-scaling-stroke`** 필수 — 줌인해도 선 두께가 일정하게 유지되어 확대 시 선이 뭉치지 않는다.

SVG defs / 런타임 stroke:
- `#oceanGrad` (radial): `#F8F9FA → #d8e2ff → #aec6ff` (육지보다 밝은 surface-light → primary-fixed → primary-fixed-dim)
- `#atmGlow`  (radial): 80% 투명 → 93% `rgba(57,93,162,.22)` → 100% 투명 (surface-tint 푸른빛)
- `#mkGlow`   (filter): `feGaussianBlur stdDeviation=2.5` + merge (마커 발광)
- 바다 외곽선: `rgba(57,93,162,.35)` / 위경도선: `rgba(57,93,162,.18)`
- 아크선: 베이스라인 `rgba(57,93,162,.55)` 굵게, 후보 `rgba(57,93,162,.28)`, `stroke-dasharray:3,4`

### 마커 (라이트 배경 대응)
- halo: `stroke #005db7` (secondary), opacity 0.45
- core: 베이스라인 `fill #00204e` (primary) / 후보 `fill #ffffff` + `stroke #005db7` (secondary)
- 라벨: `fill #00204e` + **흰색 외곽선** `stroke rgba(255,255,255,.95) width 3.5px` (밝은 배경 위 가독성)

> 💡 다크 테마로 되돌리려면: DESIGN.md의 inverse/dark 토큰을 사용 — 배경 `inverse-surface #303031` 계열, 육지 `secondary #005db7`/경계 어둡게, 바다 어두운 네이비, 글로우/선은 `inverse-primary #aec6ff` 계열, 라벨은 밝은 글자(`inverse-on-surface #f2f0f0`)+어두운 외곽선으로 반전.

---

## 8. 데이터 계약 (마커/아크가 기대하는 형태)

지도는 카탈로그 1개로 마커를 그린다:
```jsonc
{
  "countries": [
    { "code":"UK", "country_ko":"영국", "capital":[-0.1276,51.5074],
      "is_baseline":true,  "region":"EU" },
    { "code":"DE", "country_ko":"독일", "capital":[13.405,52.52],
      "is_baseline":false, "region":"EU" }
  ],
  "regions": [
    { "id":"EU", "name_ko":"유럽", "bbox":[[-11,35],[31,60]],
      "baseline":"UK", "candidates":["DE","ES","PL"] }
  ]
}
```
- `capital`: **[경도, 위도]** (D3 순서). 없으면 마커 생략.
- `is_baseline`: 진출국(채운 점) vs 후보(점선 테두리 빈 점) 구분.
- 마커는 화면 좌표가 아니라 **경위도 → `proj()`** 로 매 프레임 재투영.
- ISO A2 → world-atlas 수치 id 매핑 필요(하이라이트용):
  ```js
  const ISO_NUM = { UK:826, GB:826, DE:276, ES:724, PL:616, FR:250, US:840, KR:410, /* ... */ };
  ```

---

## 9. 튜닝 파라미터 (취향대로 조절)

| 변수 | 기본값 | 의미 |
|---|---|---|
| `SPIN` | `1600` ms | 펼치기 전 자전 시간 |
| `MORPH` | `2000` ms | 구체→평면 펼침 시간 |
| 자전 속도 | `t * 0.02` (인트로) / `dt * 0.006` (상시) | 클수록 빠름 |
| `baseScale` 구체 | `min(W,H)*0.42` | 지구본 크기 |
| `baseScale` 평면 | `W/5.4` | 평면 지도 가로 꽉참 정도 |
| 평면 세로 중심 | `H*0.46` | 살짝 위로 → 하단 팝업 공간 |
| `r1` | `[-10,-8,0]` | 펼칠 때 정면에 올 경위도(=대서양/유럽 중심) |
| 별 밀도 | `(W*H)/9000` | 작을수록 별 많음 |
| `clipAngle` 전환점 | `morphT < 0.5` | 뒷면 클립 해제 시점 |
| `isVisible` 전환점 | `morphT > 0.6` | 마커 전체표시 시점 |

---

## 10. 공개 API (다른 모듈이 쓰는 표면)

지도 모듈 `M = window.__MAP__` 가 노출하는 함수 — 이 시그니처를 지키면 호출부 변경 불필요:

```
M.init()                  // 비동기. SVG/투영/데이터 로드, ready=true
M.runIntro(onDone)        // 인트로 재생, 끝나면 onDone()
M.render()                // 1프레임 그리기
M.setMorph(t)             // morphT 설정(0~1) + 클립/fit
M.flyToRegion(regionId)   // 권역으로 줌/회전 + 후보국 하이라이트
M.focusCountry(code)      // 특정국으로 줌/회전 + 하이라이트
M.blinkCountry(code)      // 마커 깜빡임
M.reset()                 // 전체 보기 복귀
상태: M.ready, M.introDone, M.mode("globe"|"flat"), M.morphT, M.autorotate
```

---

## 11. 재구현 체크리스트

- [ ] CDN: d3@7, topojson-client@3 로드
- [ ] `#starfield`(뒤) + `#map`(앞) 두 SVG, `.map-stage` 라이트 배경(화이트~옅은 하늘빛)
- [ ] world-atlas TopoJSON 로드 → `topojson.feature(...).features`
- [ ] `geoProjectionMutator(interpolatedRaw)` 로 모핑 투영 생성
- [ ] 레이어 6종 append(대기광/바다/위경도선/육지/아크/마커)
- [ ] `baseScale`을 morphT로 연속 보간, `applyClip`로 클립 토글
- [ ] `runIntro`: d3.timer로 SPIN→MORPH, 끝나면 onDone
- [ ] onDone에서 UI 페이드인 + 첫 팝업 노출
- [ ] 딥링크(hash) 진입 시 인트로 생략 분기
- [ ] 드래그/휠/포커스/리셋 인터랙션
- [ ] 마커 데이터 계약(capital=[lon,lat], is_baseline) 충족

---

## 12. 알아둘 함정 (디버깅 노트)

- **헤드리스/백그라운드에서 rAF throttle** → 인트로는 `d3.timer`로. (캡처 시 cold-cache로 지도 로딩 지연되어 "별만 보임"처럼 보일 수 있음 — 코드 문제 아님)
- **모핑 투영에 `geoOrthographic()` 인스턴스를 쓰지 말 것** — 반드시 `geoProjectionMutator`로 같은 객체를 갱신해야 rotate/scale이 보존됨.
- **평면 스케일을 단변 기준으로 잡으면** 세계지도가 동그랗게 쪼그라듦 → **폭 기준(`W/5.4`)** 으로.
- **마커 transform**: 줌 transform에 곱하지 말고 매 프레임 `proj(capital)`로 재계산(구체 회전 반영).
```
