# 챗봇 답변 가드레일 — Amazon Bedrock Guardrails 채택 계획

> 범위: ROADMAP 2차(챗봇 + 리서치)의 가드레일 설계. 구현은 2차/4차에서 진행.

## Context (왜 이 작업을 하는가)

ROADMAP 2차에서 사용자 질의 챗봇(C1)을 구현한다. 챗봇이 LLM으로 답변을 생성하므로,
답변 품질·안전을 보장할 **가드레일 정책**을 먼저 정해야 한다. "활용할 만한 가드레일
도구"를 GitHub 스타순으로 조사한 결과, **이 프로젝트의 LLM이 AWS Bedrock(Claude,
리전 `ap-northeast-2`)** 이라는 점이 결정적이었다. 따라서 OSS 라이브러리보다
**Bedrock에 내장된 매니지드 가드레일**이 가장 적합하다.

### 프로젝트 현재 상태 (조사 결과)
- 챗봇은 **아직 코드 없음**. 흐름만 설계됨:
  `architecture/design/design_spec/web_design_spec.md` §6.5 "챗봇 질의응답 분기" — 보유정보 있으면
  기존 정보로 답변, 없으면 리서치 Agent 트리거. 챗봇은 **제한된 질문 리스트**(칩)
  제공(§C1) → 답변 범위 제한이 UX에 일부 내장.
- LLM 호출 코드도 아직 없음(ROADMAP 2차에서 Bedrock 호출 모듈 신규 작성 예정).
- 출처 **tier 시스템**(1=법령/공식 … 4=AI추정)이 데이터 스키마에 이미 존재:
  `architecture/research/country_research_schema.md`. tier≤3이면 FAIL 대신 FLAG(실사 보류).
- 기술스택: FastAPI 백엔드(설치됨), React+Vite 프론트(예정), LLM=Bedrock Claude.

## GitHub 조사 결과 (스타순) — 그리고 Bedrock 환경 결론

| 옵션 | 형태 | ⭐ / 출처 | 비고 |
|---|---|---|---|
| **Amazon Bedrock Guardrails** | AWS 매니지드 (이미 쓰는 Bedrock 내장) | `aws-samples/*` 예제 다수 | ✅ **채택** — 4개 영역 네이티브 |
| guardrails-ai/guardrails | OSS (Apache-2.0) | 7.0k | OSS 대안 1순위(미채택) |
| microsoft/presidio | OSS PII (MIT) | 9.3k | PII 한국어 보강용 OSS(미채택) |
| NVIDIA-NeMo/Guardrails | OSS (Apache-2.0) | 6.5k | Claude 직접지원 X → 제외 |
| Portkey gateway / superagent | 게이트웨이형 | 12k / 6.6k | 프록시 구조 — 우리 인프로세스 호출과 불일치 |
| hyeonsangjeon/Amazon-Bedrock-Guardrails-Toolkit | Bedrock용 Python 툴킷 | 소형 | 참고 예제 |

**채택 결론: Amazon Bedrock Guardrails (Standard tier)**
이미 쓰는 Bedrock 안에서 API 한 번에 4개 영역을 모두 커버하고, 별도 인프라/모델
서빙이 필요 없다. OSS 대비 운영 부담이 가장 작다.

### 4개 영역 → Bedrock Guardrails 기능 매핑
| 요구 영역 | Bedrock Guardrails 기능 |
|---|---|
| 답변 범위 제한 | **Denied topics**(투자권유·법률자문·오토금융 진단 외 주제 거부) + 기존 "제한된 질문 리스트" UX |
| 프롬프트 인젝션 방어 | **Prompt attack filter** + **prompt leakage detection**(Standard tier) |
| 출처/사실성 검증 | **Contextual grounding check**(grounding + relevance 임계값) — 답변이 주입 컨텍스트에 근거하는지 |
| PII/개인정보 | **Sensitive information filter**(내장 PII + **커스텀 정규식**) |

## 한국어 보강 — 핵심 질문에 대한 답

**별도 한국어 OSS 없이 Bedrock Guardrails만으로 해결된다.** 근거(AWS 공식 문서 확인):

1. **Standard tier가 한국어 포함 다국어 지원**. Classic tier는 영어/프랑스어/스페인어만.
   → 콘텐츠 필터·프롬프트 공격·거부 주제 모두 **Standard tier로 설정**.
2. Standard tier는 **cross-Region inference 필수**. tier 지원 리전 목록에
   **Asia Pacific (Seoul, `ap-northeast-2`)** 포함 → 우리 리전에서 동작 ✅.
3. **한국 특화 PII(주민등록번호 등)는 PII 필터의 커스텀 정규식 패턴**으로 추가.
   표준 PII(이메일·전화·카드번호 등)는 내장 탐지.
4. 잔여 리스크: contextual grounding의 한국어 정확도는 영어보다 낮을 수 있음 →
   **기존 tier 출처 규칙(코드)으로 이중 방어**(아래 §3). 가드레일 단독에 의존하지 않음.

## 구현 방향 (요약 — 상세는 ROADMAP 2차 구현 단계에서)

### 1. Guardrail 리소스 정의 (IaC / 콘솔)
- `CreateGuardrail`로 Guardrail 생성. **Standard tier + 서울 cross-Region 프로파일**.
- 정책: denied topics(투자권유/법률·세무자문/무관주제), prompt attack=HIGH,
  PII 필터(내장 + 한국 주민번호 regex), contextual grounding(grounding+relevance 임계값).
- 차단 메시지(`blockedInputMessaging`/`blockedOutputsMessaging`)는 기존 챗봇 거부
  문구(§6.5의 "정보가 부족하여 답변하기 어렵습니다" 톤)와 일치시킨다.
- ROADMAP 4차(CloudFormation)에 Guardrail 정의를 IaC로 포함 → 룰셋 버전 관리.

### 2. 챗봇 LLM 호출에 Guardrail 연결
- ROADMAP 2차에서 만들 **Bedrock 호출 모듈**(`app/backend/` 내, region 패턴 따름)에서
  `InvokeModel`/`Converse` 호출 시 `guardrailIdentifier` + `guardrailVersion` 지정.
- contextual grounding을 위해 보유 데이터(`app/backend/storage/data/research/...`의 해당
  국가/권역 JSON)를 **grounding source로 명시 주입**.
- 가드레일 차단 응답(`ASSESSMENT`/`GUARDRAIL_INTERVENED`) 처리 → §6.5 분기의 거부
  메시지로 매핑.

### 3. 기존 출처 tier 규칙과 이중 방어 (코드)
- 답변에 인용되는 데이터의 `tier`/`source`/`freshness`를 코드에서 검증:
  tier≤3 항목은 답변에 "실사 보류/추정" 라벨 부착(`architecture/research/country_research_prompt.md`
  FLAG 규칙 준수).
- 이 검증은 **프롬프트가 아닌 코드**에서 강제(기존 설계 원칙과 동일 철학).

## 영향받는 / 신규 위치
- 신규(2차 구현 시): Bedrock 호출 모듈 + 챗봇 API 라우터 (`app/backend/` 내,
  region 엔진과 동일한 구조·경로 규칙)
- 수정(문서): `architecture/ROADMAP.md` 2차 범위에 "가드레일(Bedrock Guardrails)" 명시,
  `architecture/design/design_spec/web_design_spec.md` §6.5에 가드레일 차단 분기 보강
- 신규(설계): 가드레일 정책 정의 문서 (denied topics 문구, PII regex, 임계값) — tier별
  잠금(룰셋 불변 원칙)
- 의존성: `boto3`(이미 설치됨)로 충분. **신규 Python 패키지 불필요**.
- 4차: CloudFormation에 `AWS::Bedrock::Guardrail` 리소스 추가

## 검증 방법
1. **단위(boto3)**: 생성한 Guardrail에 `ApplyGuardrail` API로 테스트 입력 직접 평가 —
   (a)정상 한국어 질의 (b)프롬프트 인젝션("이전 지시 무시…") (c)무관/투자권유 질의
   (d)PII(주민번호 형식) 포함 → 각각 PASS/BLOCK/마스킹 기대대로인지 pytest.
2. **한국어 확인**: 위 케이스를 한국어로 작성해 Standard tier에서 denied topics·
   prompt attack이 한국어로 동작하는지 확인(핵심 검증 포인트).
3. **그라운딩**: 보유 JSON에 없는 사실을 답하도록 유도 → contextual grounding이
   차단/플래그하는지, 그리고 tier 코드 검증이 추정 라벨을 붙이는지 확인.
4. **통합**: 챗봇 API(2차 구현 후)에 위 4종 질의를 end-to-end 호출 →
   §6.5 분기 메시지와 가드레일 차단 메시지가 일관되게 매핑되는지 확인.

## 미해결 / 구현 전 추가 결정
- denied topics 구체 목록: "투자 권유", "법률·세무 자문" 외에 어디까지 막을지 정책 확정 필요.
- contextual grounding 임계값(grounding/relevance) 초기값 → 한국어 false-positive
  보고 파일럿으로 튜닝.
- Guardrail 버전 관리 주체: 4차 CFN(IaC) vs 콘솔 수동 — IaC 권장.
