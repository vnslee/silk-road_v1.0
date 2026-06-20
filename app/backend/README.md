# Backend

백엔드 서버 코드를 포함하는 디렉토리입니다.

## 구조

- `engine/` - 핵심 비즈니스 로직 엔진
  - `calculation/` - 단일국 스코어링
  - `generation/` - 권역 리포트 데이터(JSON) 생성
  - `rendering/` - 리포트 HTML 렌더링
- `storage/` - 데이터 저장 및 관리
  - `data/` - 입력 원본 (AI 조사 데이터 + 사내 데이터)
  - `report/` - 생성 결과물 (JSON · HTML)
