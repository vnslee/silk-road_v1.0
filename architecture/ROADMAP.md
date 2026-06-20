# 구현 로드맵 (AI-DLC 진행용)

이 문서는 silk-road 구현을 **4개 덩어리(unit)**로 나눈 작업 분할 계획이다.
AI-DLC 워크플로우는 한 번에 전체가 아니라 **이 로드맵의 한 덩어리씩** 진행한다.

> 활성화 예: `Using AI-DLC, ROADMAP의 1차(백엔드 API + 진단 파이프라인) 범위를 진행하자`

## 현재 상태 요약 (착수 전 기준선)

- **있음**: 엔진 코어(calculation 단일국 스코어링, generation/rendering은 **region 전용**), research country 데이터 6개국(BR·DE·ES·IN·PL·UK), internal 룰셋, 화면 디자인 명세 8종(`architecture/design/stitch/html`), Claude Code 워크플로우(.claude/)
- **설치됨**: FastAPI, uvicorn, boto3, pydantic, Jinja2, requests, weasyprint(+pango/cairo)
- **없음(구현 대상)**: 백엔드 API 레이어, **country 전용 generation/rendering 엔진**, region/country 리서치 실행 코드(Bedrock), 프론트엔드, requirements.txt, Dockerfile, CloudFormation 템플릿
- **예정**: region 리서치 프롬프트·스키마(`architecture/research/`에 country만 있음 → region 추가 예정)

## 공통 제약 (모든 덩어리에 적용)

- 서비스는 **country / region 두 축**으로 대칭 구성한다. 한쪽(주로 region)이 먼저 구현돼 있으면 **다른 쪽을 동일 구조·네이밍·경로로 복제**한다.
- 엔진/스토리지 경로 규칙은 `CLAUDE.md` 및 `app/backend/storage/README.md` 준수.
- 프론트엔드 스택: **React + Vite** (`app/frontend/`).
- 리전 `ap-northeast-2`, LLM은 AWS Bedrock(Claude) 사용.
- 의존성 추가 시 `requirements.txt`(백엔드) / `package.json`(프론트)에 반영.

## 덩어리 분할

### 1차 — 백엔드 API + 진단 파이프라인 정합화 (country ↔ region 대칭)
- **목표**: 프론트가 호출할 HTTP API와, country/region **양쪽** 진단 파이프라인을 대칭으로 완성.
- **범위**:
  - FastAPI 앱(`app/backend/api/` 또는 `main.py`): **country/region 공통** 엔드포인트 — 국가/권역 조회, 리포트 생성 트리거, 리포트(JSON/HTML/PDF) 제공
  - **region**: 기존 generation/rendering 엔진을 API에 연결(엔진 자체는 존재).
  - **country**: 누락된 country 전용 generation/rendering 엔진을 region 패턴 대칭 복제 → PR1 보고서 HTML 생성, API 연결.
  - 두 축이 같은 API 형태/경로 규칙(`report/<country|region>/<ID>/data·html·pdf`)을 공유하도록 정합.
  - `requirements.txt` 생성(현재 설치 패키지 고정).
- **산출물**: API 서버, `engine/`의 country 엔진(region 대칭), country/region 리포트 산출 경로 통일
- **의존**: 없음(가장 먼저)

### 2차 — 챗봇 + 리서치 (Bedrock, country/region 공통)
- **목표**: `architecture/research/`의 프롬프트·스키마를 실제 Bedrock 호출로 연결. country는 정의됨, **region 리서치 프롬프트·스키마도 이 단계에서 추가**(country 대칭).
- **범위**:
  - 리서치 Agent: 신규 **국가/권역** 데이터를 Bedrock으로 생성 → `storage/data/research/{country,region}/` 스키마 준수 저장
  - 챗봇 응답 로직: 보유 정보 기반 답변 + 정보 없을 때 리서치 트리거(`web_design_spec.md` 5-3 국가 / 5-4 권역 분기 따름)
  - 1차 API에 챗봇/리서치 엔드포인트 추가
- **산출물**: Bedrock 호출 모듈, 챗봇 API, region 리서치 명세
- **의존**: 1차(API 레이어)

### 3차 — 프론트엔드 (React + Vite)
- **목표**: 지도 UI + 8개 팝업 + 챗봇 위젯을 실제 앱으로 구현.
- **범위**:
  - 지도: D3 지구본 시네마틱 인트로(`architecture/design/design_spec/intro_spec.md`)
  - 화면: M1·C1·P1(국가)·P2(권역)·PR1·PR2·PS1·PS2 — stitch HTML 목업을 React 컴포넌트화, `web_design_spec.md`의 흐름·진입 모드(팝업/풀사이즈)·country·region 분기 준수
  - 1·2차 API 연동
- **산출물**: `app/frontend/` React+Vite 앱, `package.json`
- **의존**: 1차·2차(API)

### 4차 — 배포 (Docker → ECR → CloudFormation)
- **목표**: 로컬 빌드 → ECR 푸시 → CFN(EC2/ECS/ELB) 배포 시연.
- **범위**:
  - 백엔드/프론트 Dockerfile, (필요시) docker-compose
  - CloudFormation 템플릿(EC2/ECS/ELB)
  - 배포는 `deploy` 스킬 절차 사용
- **산출물**: Dockerfile(s), CFN 템플릿, 배포된 스택
- **의존**: 1~3차(빌드 대상)

## 산출물 위치 (AI-DLC `aidlc-docs/`)
- AI-DLC가 생성하는 요구사항·설계 문서 위치는 시작 시 확인하되, 기본은 프로젝트 루트 `aidlc-docs/` 권장.
