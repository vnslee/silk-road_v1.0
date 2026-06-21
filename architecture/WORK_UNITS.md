# 작업 단위 (Work Units) — 구체화 산출물

> `ROADMAP.md`의 4덩어리(Phase)를 **독립 테스트 가능한 작업 단위(U#)**로 쪼갠 목록.
> ROADMAP이 "무엇을 만드나(WHAT)"라면, 이 문서는 "어떤 순서로 어떻게 검증하며 만드나(HOW)"다.
> 구체화(Elaboration) 단계에서 확정됨. 단위 번호(U#)는 이 프로젝트 내부 작업 추적용.

## 확정된 설계 결정 (모든 단위에 적용)

| # | 항목 | 결정 |
|---|---|---|
| C1 | country 스키마 버전 | **v1.1 정본** (프롬프트의 1.0 표기 수정 완료) |
| C2 | 유사도 채점 주체 | **엔진이 CALC** (AI 리서치는 원시값만, 점수화는 결정론적 엔진) |
| C3 | PS1 룰셋 구조 | **4카테고리(시장/환경/규제/시스템)** = `market/finance/regulation/system`. 상위 blend 유지(A구조): (시장+환경)→매력도풀, 규제→난이도풀, 시스템→유사도풀. 게이트류는 슬라이더 제외(킬스위치 PASS/FAIL) |
| D1 | PR1 탭 구성 | **render_req 기준** (1-0요약/1-1유사도/1-2결정트리/1-3TCO/1-4시장배경) |
| D2 | PDF 생성 | **백엔드 HTML→weasyprint** |
| D3 | 화면 차트 | **프론트(React)가 렌더**. 백엔드 HTML 렌더링 엔진은 PDF용 |
| A1 | 데이터 저장소 | **파일시스템 JSON 유지** (storage/) |
| A3 | 산출물 경로 | **data/html 분리** (`report/<country\|region>/<ID>/data·html`) |
| B1 | region 리서치 | **country 모아 계산** (별도 region 리서치 프롬프트 불필요). 권역 메타(name·members·baseline)는 internal.json `regions`에 사람이 관리 |
| B2 | 리서치 실행 | **비동기 + 진행률 폴링** (PS2 5종 프로그레스바와 매핑) |
| B3 | NEWS 수집 | **Bedrock 호출만으로 리서치** (md 명세 준수: ROADMAP "프롬프트를 실제 Bedrock 호출로 연결", guardrail PLAN "보유 JSON grounding 주입"). 외부 검색 API 없음. NEWS는 화이트리스트 출처로 채우되 불확실하면 "조사 필요"로 비움(country_research_prompt 환각 금지). ※ 초기 "외부 검색 API" 안은 명세에 없어 폐기 |
| E1 | 인증 | **없음** (데모) |
| E2 | 다국어(i18n) | **본문·AI 인사이트까지 한/영 전체**. 횡단 작업. 스키마는 additive 확장(`_en` 류)이라 지금 잠그지 않음 |
| E3 | 배포 | **단일 EC2 데모** |
| FX | 기준통화 | **KRW** (internal.json fx.base=KRW) |

---

## Phase 1 — 백엔드 진단 파이프라인

| # | 목적 | 완료 조건 (테스트 가능) | 의존 | 상태 |
|---|---|---|---|---|
| **U1** | 스키마 v1.1·경로(data/html 분리)·internal.json 4카테고리 룰셋·권역 메타 정본화 + 검증 픽스처 | 검증기가 존재하는 country 전부 + internal PASS / 오염 픽스처 3종(가중치≠100·tier=5·화이트리스트 밖) FAIL 검출 / py_compile 통과 | — | ✅ 완료 |
| **U2** | 스코어링 코어(유사도·매력도·게이트·TCO) — AI 원시값→CALC | 픽스처 입력 → 알려진 유사도/TCO 값과 단위테스트 일치 | U1 | ✅ 완료 |
| **U3** | 유형1(국가) 보고서 JSON 생성 (탭 1-0~1-4) | 국가 → `report/country/<CODE>/<ID>/data/*.json` 생성, 각 블록에 nature/source_flag 존재 | U2 | ✅ 완료 |
| **U4** | 유형2(권역) 보고서 JSON 생성 (킬스위치·순위·카드) | 권역 → `report/region/<RGN>/<ID>/data/*.json`, regions 메타로 소속국·baseline 해석 | U2 | ✅ 완료 |
| **U5** | 렌더링 엔진 JSON→HTML (PDF용 정적 차트 포함) | 보고서 JSON 입력 → 차트매핑·배지규칙 적용된 HTML, 배지 없는 수치 0건 | U3,U4 | ✅ 완료 |
| **U6** | 채번(NNN)·스냅샷·재현성 도장(based_on) | 폴더 스캔→신규번호, 동일 스냅샷+config→동일 산출물 | U3,U4 | ✅ 완료 |

## Phase 2 — API 레이어

| # | 목적 | 완료 조건 | 의존 | 상태 |
|---|---|---|---|---|
| **U7** | FastAPI 골격 + `requirements.txt` (인증 없음) | `uvicorn` 기동, `/health` 200, 설치 패키지 고정 | — | ✅ 완료 |
| **U8** | 조회 API (국가/권역/보고서 목록·상세) | 픽스처로 GET 응답 스키마 검증 통과 | U7,U3~U6 | ✅ 완료 |
| **U9** | 보고서 생성 트리거 + 진행률 폴링 (비동기) | POST→작업ID, 폴링 상태전이(대기→진행→완료), 완료 시 산출물 존재 | U8 | ✅ 완료 |
| **U10** | 보고서 제공(JSON/HTML) + weasyprint PDF | HTML→PDF 바이트 생성, PDF 페이지 ≥1 | U8,U5 | ✅ 완료 |

## Phase 3 — 챗봇 + 리서치 (Bedrock)

| # | 목적 | 완료 조건 | 의존 | 상태 |
|---|---|---|---|---|
| **U11** | Bedrock 호출 모듈 (boto3 Converse) + 도구루프 골격 | 모킹 파싱·tool_use·도구루프·JSON추출 단위테스트 + 실 Bedrock 스모크 | U7 | ✅ 완료 |
| **U12** | country 리서치 Agent (Bedrock 호출, NEWS는 화이트리스트/조사필요) | 신규국 코드→v1.1 스키마 준수 JSON 저장, U1 검증 통과 + 실 Bedrock E2E(FR 생성 검증) | U11,U1 | ✅ 완료 |
| **U13** | Guardrails 정책(denied topics·PII·grounding) + 호출 연결 | 정책 4영역·한국 PII regex·ApplyGuardrail 모킹 BLOCK·tier 이중방어. 실 리소스 생성은 4차 CFN | U11 | ✅ 완료 |
| **U14** | 챗봇 응답 로직 + API (§6.5 분기, 리서치 트리거) | 정보 유무별 분기·리서치 트리거 E2E, 거부메시지 매핑 일치 | U12,U13,U9 | ✅ 완료 |

## Phase 4 — 프론트엔드 (React + Vite)

| # | 목적 | 완료 조건 | 의존 | 상태 |
|---|---|---|---|---|
| **U15** | Vite 골격 + Kinetic 토큰(Tailwind) + i18n 프레임 + `package.json` | `vite build` 성공, 한/영 토글로 UI 라벨 전환 | — | ✅ 완료 |
| **U16** | M1 지구본 시네마틱 인트로 (three.js+D3) | 인트로 재생 + 딥링크 생략 + WebGL 폴백. vite build·평면지도 렌더 검증 | U15 | ✅ 완료 |
| **U17** | 공통 셸: 상단바·메뉴·진입모드(팝업/풀사이즈)·라우팅 | 경로 A/B/C 진입 전환, 팝업↔풀사이즈 모드 전환 + 딥링크 hash | U16 | ✅ 완료 |
| **U18** | P1/P2 정보 화면 (API 연동) | 실 API로 ES(국가)·EU(권역) 렌더 검증(섹션·게이트배지·국기·보고서버튼) | U17,U8 | ✅ 완료 |
| **U19** | PR1/PR2 보고서 + 차트(Recharts) | 보고서 JSON→nature별 차트+원천 배지 렌더, 탭 네비, PDF/메일. ES 보고서 라이브 렌더 검증 | U18,U8/U10 | ✅ 완료 |
| **U20** | C1 챗봇 위젯 + PS2 프로그레스 + 메일공유(mailto) | 챗봇 §6.5 분기·진행바 5종·메일. 챗봇 E2E(실 Bedrock grounding 답변) 검증 | U17,U14,U9 | ✅ 완료 |
| **U21** | PS1 룰셋 설정 (4카테고리 슬라이더) | 슬라이더 합=100 강제, 저장→internal 반영. ruleset API(GET/PUT) + PS1 라이브 렌더 검증 | U17,U8 | ✅ 완료 |

## Phase 5 — 배포

| # | 목적 | 완료 조건 | 의존 | 상태 |
|---|---|---|---|---|
| **U22** | Dockerfile(백/프론트) | 로컬 컨테이너 기동, 헬스체크 통과 | 전체 | ⬜ |
| **U23** | 단일 EC2 배포 + Guardrail IaC | EC2에 스택 배포 후 외부 접속 200, Guardrail 리소스 생성 | U22,U13 | ⬜ |

---

## 횡단(cross-cutting)
- **i18n(E2)**: touch-point는 U15(프론트 i18n 프레임)·U3/U4(보고서 텍스트 이중언어 생성 여부). 스키마는 additive 확장 지점만 명시(U1 완료).
- **메일공유(mailto)**: U20 주구현. 신규 발송 API 불필요(클라이언트 위임).

## 알아둘 점 (구현 중 발견)
1. **실데이터는 ES 1개국뿐** — BR·DE·IN·PL·UK는 git pull 때 삭제됨. 검증기·엔진은 "존재하는 국가 전부" 자동 순회. 리서치(U12)로 추가되면 자동 포함.
2. **U2 산식 변경 예약**: 차량회수 2항목(차량회수 절차 용이성·법적 회수 소요기간)이 weights상 regulation으로 이동했으나, country 데이터의 `axis`는 아직 `similarity`. U2에서 IT유사도 산식 입력 재정의 + axis 갱신 필요.
3. **pytest 미설치**: 환경에 pytest 없음. 검증 테스트는 standalone 폴백으로 동작. → U7 에서 `.venv` + requirements.txt 로 해결(pytest 포함).
4. **venv 위치**: `app/backend/.venv` (gitignore 됨). 실행은 `.venv/bin/uvicorn main:app`. ROADMAP "설치됨" 명시와 달리 실제론 U7 에서 처음 설치함.
5. **weasyprint(U10) 시스템 라이브러리**: macOS 에서 `brew install pango` 필요 + 실행 시 `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` 환경변수 필요. Docker(U22)에서는 apt 로 libpango 설치.
6. **시스템 curl 깨짐**: brew node 설치 부작용으로 libunistring 누락 → `curl` 동작 안 함. 작업엔 무영향(httpx/Python 으로 우회). 필요 시 `brew reinstall libunistring`.
7. **Python 3.9 호환**: `.venv` 가 Python 3.9.6. `str | None` 신택스 안 됨 → `Optional[str]` 사용. `list[X]`/`dict[X]` 는 PEP585 로 3.9 OK(단 클래스 본문 annotation 의 `|` union 은 불가). 라우터·모델 작성 시 주의.
8. **Bedrock inference profile 필수**: Claude 모델은 on-demand 직접 호출 불가(ValidationException). ap-northeast-2 에서 `global.anthropic.claude-opus-4-8` (global cross-region 프로파일) ACTIVE — 이걸 modelId 로 사용. `anthropic.claude-opus-4-8`(접두사만) 은 실패. 실 호출 검증됨(U11).
