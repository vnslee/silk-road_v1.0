# Backend

백엔드 서버 코드를 포함하는 디렉토리입니다.

## 구조

- `engine/` - 핵심 비즈니스 로직 엔진
  - `generation/` - 국가·권역 진단 리포트 데이터(JSON) 생성 (`country_report_engine.py` · `region_report_engine.py`)
  - `rendering/` - 보고서(PR1/PR2) HTML + 상세화면(P1/P2) HTML 렌더링 + 공유 헬퍼(`render_helpers.py`)·템플릿
- `storage/` - 데이터 저장 및 관리
  - `data/` - 입력 원본 (AI 조사 데이터 + 사내 데이터)
  - `report/` - 진단 보고서 결과물 (JSON · HTML)
  - `detail/` - 상세화면(P1/P2) 결과물 (HTML)
