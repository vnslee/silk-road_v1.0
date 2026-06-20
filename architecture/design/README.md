# Design

웹 서비스의 디자인·UX 설계 문서와 화면 목업을 포함하는 디렉토리입니다.

## 디렉토리 구조

```
architecture/design/
├── README.md              # (현재 문서) 디자인 산출물 인덱스
├── design_spec/           # 설계 명세 (Markdown)
│   ├── web_design_spec.md # 웹 디자인 가이드 — 화면 체계·공통 규칙·화면 흐름
│   └── intro_spec.md      # 메인 화면 3D 지구본 시네마틱 인트로 구현 명세
└── stitch/                # 화면 디자인 산출물 (목업)
    ├── DESIGN.md          # 디자인 시스템 토큰 (색상·타이포그래피·컴포넌트)
    ├── html/              # 화면별 HTML 목업
    └── images/            # 화면별 스크린샷
```

## 문서 안내

### 설계 명세 (`design_spec/`)

| 문서 | 내용 |
|------|------|
| [web_design_spec.md](design_spec/web_design_spec.md) | 전체 화면 목록·관계도, 화면별 상세 명세, 공통 규칙(진입 모드·챗봇·프로그레스), 화면 흐름(User Flow). mermaid 다이어그램 포함 |
| [intro_spec.md](design_spec/intro_spec.md) | 메인 화면 진입 시 "3D 지구본 자전 → 평면 지도 펼침 → UI 등장" 시네마틱 인트로의 기술 스택·핵심 로직·튜닝값·디자인 토큰 |

### 디자인 시스템 (`stitch/`)

| 항목 | 내용 |
|------|------|
| [DESIGN.md](stitch/DESIGN.md) | Kinetic Enterprise 팔레트 기반 디자인 토큰 — 색상, 타이포그래피(Hanken Grotesk), 간격, 라운딩, 컴포넌트(버튼·인풋·모달·카드 등) 규칙 |
| `html/` | 화면별 HTML 목업 (Tailwind 기반) |
| `images/` | 화면별 스크린샷 |

## 화면 목록

| ID | 화면명 | HTML 목업 | 스크린샷 |
|----|--------|-----------|----------|
| M1 | 메인화면 (지도) | [M1.html](stitch/html/M1.html) | [M1_screen.png](stitch/images/M1_screen.png) |
| C1 | 챗봇 | [C1.html](stitch/html/C1.html) | [C1_screen.png](stitch/images/C1_screen.png) |
| P1 | 국가 정보 | [P1.html](stitch/html/P1.html) | [P1_screen.png](stitch/images/P1_screen.png) |
| P2 | 권역 정보 | [P2.html](stitch/html/P2.html) | [P2_screen.png](stitch/images/P2_screen.png) |
| PR1 | 국가 진단 보고서 | [PR1.html](stitch/html/PR1.html) | [PR1_screen.png](stitch/images/PR1_screen.png) |
| PR2 | 권역 진단 보고서 | [PR2.html](stitch/html/PR2.html) | [PR2_screen.png](stitch/images/PR2_screen.png) |
| PS1 | 룰셋 설정 | [PS1.html](stitch/html/PS1.html) | [PS1_screen.png](stitch/images/PS1_screen.png) |
| PS2 | 프로그레스 | [PS2.html](stitch/html/PS2.html) | [PS2_screen.png](stitch/images/PS2_screen.png) |

> 화면별 상세 명세와 화면 간 흐름은 [web_design_spec.md](design_spec/web_design_spec.md)를 참조하세요.

## 참고

- 디자인 스킬: <https://github.com/uxjoseph/supanova-design-skill>
- 디자인·색감 레퍼런스: <https://about.hyundaicapital.com/au/cintd/IRAUCI0101.hc> (+ 현대캐피탈 CI 로고)
- mermaid 다이어그램이 텍스트로 보이면 미리보기 도구의 mermaid 렌더링 지원이 필요합니다 (VS Code: `bierner.markdown-mermaid` 확장).
