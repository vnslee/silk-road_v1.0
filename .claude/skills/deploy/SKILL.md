---
name: deploy
description: silk-road 앱을 AWS에 배포한다. Docker 로컬 빌드 → ECR 이미지 푸시 → CloudFormation(EC2/ECS/ELB) 배포 절차. 사용자가 "배포", "deploy", "ECR", "도커 이미지 올리기", "스택 배포"를 언급할 때 사용.
---

# silk-road 배포 워크플로우

AWS CloudFormation으로 구성된 인프라(EC2 / ECS / ELB)에 컨테이너 이미지를 배포한다.
리전은 `ap-northeast-2`(서울), 자격증명은 AWS CLI 환경에 설정돼 있다고 가정한다.

> 이 스킬은 절차·규약 가이드다. 실제 Dockerfile/CloudFormation 템플릿은 아직 없으면 먼저 생성해야 하며, 인프라 설계·작성은 `deployment-engineer` / `devops-engineer` / `docker-expert` / `cloud-architect` 서브에이전트에 위임할 수 있다.

## 전제 확인 (시작 전 점검)

- `aws sts get-caller-identity` 로 자격증명·계정 확인
- `AWS_REGION=ap-northeast-2` (또는 `--region` 명시)
- 대상 ECR 리포지토리, CloudFormation 스택 이름, ECS 클러스터/서비스 이름을 사용자에게 확인 (값이 불명확하면 추측하지 말고 질문)

## 단계

### 1. Docker 로컬 빌드
```bash
# 앱 루트에서 (linux/amd64 — Fargate/EC2 호환)
docker build --platform linux/amd64 -t silk-road:<TAG> .
```
- 멀티 컴포넌트(backend/frontend)면 각각 빌드하고 태그를 구분한다.
- `<TAG>`는 git short SHA 또는 버전 사용(`latest` 단독 사용 지양).

### 2. ECR 푸시
```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=ap-northeast-2
REPO=<ECR_REPO_NAME>
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com
# 리포지토리 없으면 생성
aws ecr describe-repositories --repository-names $REPO --region $REGION >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name $REPO --region $REGION
docker tag silk-road:<TAG> $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:<TAG>
docker push $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:<TAG>
```

### 3. CloudFormation 배포 (EC2 / ECS / ELB)
```bash
aws cloudformation deploy \
  --stack-name <STACK_NAME> \
  --template-file <TEMPLATE>.yaml \
  --parameter-overrides ImageUri=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:<TAG> \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION
```
- ECS 서비스가 새 이미지를 받도록 task definition의 이미지 URI를 갱신한다(파라미터로 주입).
- 이미 떠 있는 서비스를 강제 재배포해야 하면:
  `aws ecs update-service --cluster <CLUSTER> --service <SERVICE> --force-new-deployment --region $REGION`

### 4. 배포 검증
```bash
aws cloudformation describe-stacks --stack-name <STACK_NAME> --region $REGION \
  --query 'Stacks[0].StackStatus'
# ELB DNS(또는 출력값)로 헬스 체크
aws cloudformation describe-stacks --stack-name <STACK_NAME> --region $REGION \
  --query 'Stacks[0].Outputs'
```
- ELB 엔드포인트에 curl로 200 확인. ECS 서비스 `runningCount`가 desired와 일치하는지 확인.

## 주의

- 비가역/외부 영향 작업(스택 생성·삭제, 이미지 푸시)은 실행 전 사용자에게 확인한다.
- 리소스 이름/스택 이름을 임의로 만들지 말고 기존 명명 규칙을 따르거나 사용자에게 확인한다.
- 빌드 플랫폼은 배포 타깃(Fargate=amd64 등)과 일치시킨다.
