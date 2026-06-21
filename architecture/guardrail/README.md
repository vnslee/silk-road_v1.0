# Guardrail

챗봇 답변의 품질·안전을 보장하기 위한 가드레일 명세 문서를 포함하는 디렉토리입니다.
ROADMAP 2차(챗봇 + 리서치) 설계의 일부이며, **Amazon Bedrock Guardrails** 채택을 전제로 합니다.

## 문서

| 문서 | 내용 |
|------|------|
| `PLAN.md` | 가드레일 도구 조사(GitHub 스타순)·채택 결정(Bedrock Guardrails, Standard tier)·구현 방향·검증 방법 |

## 가드레일 4개 영역

| 요구 영역 | Bedrock Guardrails 기능 |
|-----------|--------------------------|
| 답변 범위 제한 | Denied topics + 챗봇 "제한된 질문 리스트" UX |
| 프롬프트 인젝션 방어 | Prompt attack filter + prompt leakage detection |
| 출처/사실성 검증 | Contextual grounding check (+ 출처 tier 코드 검증 이중 방어) |
| PII/개인정보 | Sensitive information filter (내장 PII + 한국 특화 커스텀 regex) |

## 산출물 연계

- LLM은 AWS Bedrock(Claude, 리전 `ap-northeast-2`)을 사용하므로, 별도 패키지 없이 `boto3`로 가드레일을 연결합니다.
- Guardrail 리소스 정의는 ROADMAP 4차에서 CloudFormation(`AWS::Bedrock::Guardrail`)으로 IaC 관리합니다.
- 추가 예정 문서(정책 확정 시): denied topics 목록, PII 커스텀 regex 패턴, contextual grounding 임계값 정의.
