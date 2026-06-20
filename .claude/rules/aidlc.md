# AI-DLC 워크플로우 (AI-Driven Development Life Cycle)

awslabs/aidlc-workflows(MIT-0) 기반의 적응형 소프트웨어 개발 방법론. 큰 기능을 구조적으로 진행할 때 사용한다.

## 활성화

사용자가 채팅에서 **"Using AI-DLC, ..."** 로 시작하면 이 워크플로우를 적용한다. 일반/소규모 작업에는 적용하지 않는다.

## 룰 로딩

1. 메인 워크플로우: `@.claude/aidlc/aws-aidlc-rules/core-workflow.md` 를 먼저 읽는다.
2. core-workflow.md가 참조하는 **rule details 경로는 이 프로젝트에서 다음으로 해석한다**:
   `.claude/aidlc/aws-aidlc-rule-details/`
   - core-workflow.md 본문이 언급하는 `.aidlc-rule-details/`, `.kiro/...`, `.amazonq/...` 등 후보 경로는 무시하고 위 경로를 사용한다.
   - 예: `common/process-overview.md` → `.claude/aidlc/aws-aidlc-rule-details/common/process-overview.md`
3. 산출물(`aidlc-docs/` 등) 생성 위치는 사용자에게 먼저 확인한다.

## 단계 (Inception → Construction → Operations)

- **Inception**: 요구사항·설계 (WHAT/WHY) — 적극 활용.
- **Construction**: 구현·빌드·테스트 (HOW) — 적극 활용. AI-DLC 워크플로우는 현재 이 단계의 Build & Test에서 끝난다.
- **Operations**: ⚠️ AI-DLC 원본에서 이 단계는 **빈 placeholder**(배포·모니터링은 "향후 확장"으로만 명시, 실질 룰 없음)이다.
  - 따라서 **배포(deployment)는 AI-DLC에 의존하지 말고 이 프로젝트 전용 배포 워크플로우를 사용한다.**
  - 배포 절차: Docker 로컬 빌드 → ECR 이미지 푸시 → CloudFormation(EC2/ECS/ELB) 배포. 상세는 **deploy 스킬**(`.claude/skills/deploy/SKILL.md`) 참조.
  - 인프라/배포 전문 작업은 infra 계열 subagent에 위임할 수 있다.
