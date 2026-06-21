---
name: frontend-design
description: 프론트엔드 UI 구현 품질·심미 게이트. mockup/디자인을 React 컴포넌트로 옮기거나 화면을 구현·다듬을 때 타이포그래피·색·여백·모션을 의도적으로 선택하고 제네릭 기본값을 피하도록 안내한다. 사용자가 "프론트 컴포넌트", "화면 구현", "mockup을 React로", "UI 구현", "디자인 충실도", "frontend design", "컴포넌트 다듬기"를 언급할 때 사용. (출처: anthropics/skills, Apache-2.0 — LICENSE.txt)
license: Complete terms in LICENSE.txt
---

# Frontend Design

Approach this as the design lead at a small studio known for giving every client a visual identity that could not be mistaken for anyone else's. This client has already rejected proposals that felt templated, and is paying for a distinctive point of view: make deliberate, opinionated choices about palette, typography, and layout that are specific to this brief, and take one real aesthetic risk you can justify.

## Ground it in the subject

If the brief does not pin down what the product or subject is, pin it yourself before designing: name one concrete subject, its audience, and the page's single job, and state your choice. If there's any information in your memory about the human's preferences, context about what they're building, or designs you've made before – use that as a hint. The subject's own world, its materials, instruments, artifacts, and vernacular, is where distinctive choices come from. Build with the brief's real content and subject matter throughout.

## Design principles

For web designs, the hero is a thesis. Open with the most characteristic thing in the subject's world, in whatever form makes sense for it: a headline, an image, an animation, a live demo, an interactive moment. Be deliberate with your choice: a big number with a small label, supporting stats, and a gradient accent is the template answer, only use if that's truly the best option.

Typography carries the personality of the page. Pair the display and body faces deliberately, not the same families you would reach for on any other project, and set a clear type scale with intentional weights, widths, and spacing. Make the type treatment itself a memorable part of the design, not a neutral delivery vehicle for the content.

Structure is information. Structural devices, numbering, eyebrows, dividers, labels, should encode something true about the content, not decorate it. Many generic designs use numbered markers (01 / 02 / 03), but that's only appropriate if the content actually is a sequence - like a real process or a typed timeline where order carries information the reader needs. Question if choices like numbered markers actually make sense before incorporating them.

Leverage motion deliberately. Think about where and if animation can serve the subject: a page-load sequence, a scroll-triggered reveal, hover micro-interactions, ambient atmosphere. An orchestrated moment usually lands harder than scattered effects; choose what the direction calls for. However, sometimes less is more, and extra animation contributes to the feeling that the design is AI-generated.

Match complexity to the vision. Maximalist directions need elaborate execution; minimal directions need precision in spacing, type, and detail. Elegance is executing the chosen vision well.

Consider written content carefully. Often a design brief may not contain real content, and it's up to you to come up with copy. Copy can make a design feel as templated as the design itself. See the below section on writing for more guidance.

## Process: brainstorm, explore, plan, critique, build, critique again

For calibration: AI-generated design right now clusters around three looks: (1) a warm cream background (near #F4F1EA) with a high-contrast serif display and a terracotta accent; (2) a near-black background with a single bright acid-green or vermilion accent; (3) a broadsheet-style layout with hairline rules, zero border-radius, and dense newspaper-like columns. All three are legitimate for some briefs, but they are defaults rather than choices, and they appear regardless of subject. Where the brief pins down a visual direction, follow it exactly — the brief's own words always win, including when it asks for one of these looks. Where it leaves an axis free, don't spend that freedom on one of these defaults. Just like a human designer who's hired, there's often a careful balance between doing what you're good at and taking each project as a chance to experiment and learn.

Work in two passes. First, brainstorm a short design plan based on the human's design brief: create a compact token system with color, type, layout, and signature. Color: describe the palette as 4–6 named hex values. Type: the typefaces for 2+ roles (a characterful display face that's used with restraint, a complementary body face, and a utility face for captions or data if needed). Layout: a layout concept, using one-sentence prose descriptions and ASCII wireframes to ideate and compare. Signature: the single unique element this page will be remembered by that embodies the brief in an appropriate way.

Then review that plan against the brief before building: if any part of it reads like the generic default you would produce for any similar page (work through a similar prompt to see if you arrive somewhere similar) rather than a choice made for this specific brief — revise that part, say what you changed and why. Only after you've confirmed the relative uniqueness of your design plan should you start to write the code, following the revised plan exactly and deriving every color and type decision from it.

When writing the code, be careful of structuring your CSS selector specificities. It's easy to generate CSS classes that cancel each other out (especially with a type-based selector like .section and a element-based selector like .cta). This can happen often with paddings/margins between sections.

Try to do a lot of this planning and iteration in your thinking, and only show ideas to the user when you have higher confidence it'll delight them.

## Restraint and self-critique

Spend your boldness in one place. Let the signature element be the one memorable thing, keep everything around it quiet and disciplined, and cut any decoration that does not serve the brief. Not taking a risk can be a risk itself! Build to a quality floor without announcing it: responsive down to mobile, visible keyboard focus, reduced motion respected. Critique your own work as you build, taking screenshots if your environment supports it – a picture is worth 1000 tokens. Consider Chanel's advice: before leaving the house, take a look in the mirror and remove one accessory. Human creators have memory and always try to do something new, so if you have a space to quickly jot down notes about what you've tried, it can help you in future passes.

## More on writing in design

Words appear in a design for one reason: to make it easier to understand, and therefore easier to use. They are design material, not decoration. Bring the same intentionality to copy that you would bring to spacing and color. Before writing anything, ask what the design needs to say, and how it can best be said to help the person navigate the experience.

Write from the end user's side of the screen. Name things by what people control and recognize, never by how the system is built. A person manages notifications, not webhook config. Describe what something does in plain terms rather than selling it. Being specific is always better than being clever.

Use active voice as default. A control should say exactly what happens when it's used: "Save changes," not "Submit." An action keeps the same name through the whole flow, so the button that says "Publish" produces a toast that says "Published." The vocabulary of an interface is the signposting for someone navigating the product. Cohesion and consistency are how people learn their way around.

Treat failure and emptiness as moments for direction, not mood. Explain what went wrong and how to fix it, in the interface's voice rather than a person's. Errors don't apologize, and they are never vague about what happened. An empty screen is an invitation to act.

Keep the register conversational and tuned: plain verbs, sentence case, no filler, with tone matched to the brand and the audience. Let each element do exactly one job. A label labels, an example demonstrates, and nothing quietly does double duty.

---

## 🟦 silk-road 프로젝트 적용 (중요 — 위 원문보다 우선)

이 프로젝트에는 **이미 확정된 디자인 시스템**이 있다. 위 원문은 "새 디자인을 만드는" 전제로 쓰였지만, **여기서는 디자인을 새로 만들지 않는다.** 다음 truth source가 모든 시각 결정을 지배한다:

- **`architecture/design/stitch/DESIGN.md`** — "Kinetic Enterprise" 팔레트·타이포·여백 토큰 (예: `primary #00204e`, `secondary #005db7`, `surface #fbf9f9`, Hanken Grotesk, 8px 컴포넌트 라운드). 색·폰트·간격은 여기서만 가져온다.
- **`architecture/design/stitch/html/*.html`** — 8개 화면 mockup(M1/C1/P1/P2/PR1/PR2/PS1/PS2). 각 mockup의 인라인 Tailwind config가 토큰의 구현 형태다.
- **`architecture/design/design_spec/web_design_spec.md`** — 흐름·진입모드(팝업/풀사이즈)·country/region 분기.
- **`architecture/design/design_spec/intro_spec.md`** — D3 지구본 인트로.

### 2-pass를 이 프로젝트에 맞게 재해석

- **Pass 1 (design plan)** → "새 팔레트/타이포 발명"이 아니라 **DESIGN.md + mockup에서 토큰을 추출·정리**하는 단계. 신규 색·폰트를 만들지 않는다. (Tailwind config 1회 이식: 8 mockup이 동일 config를 갖고 있어 리프트가 쉽다.)
- **Pass 2 (critique)** → "제네릭 기본값 점검"을 **mockup 대비 충실도 점검**으로 대체. 구현 결과가 해당 화면 mockup과 어긋나면 mockup 쪽이 이긴다.

### 그대로 적용되는 부분 (원문 그대로 유효)

- **품질 게이트(quality floor)**: 반응형(모바일까지), 키보드 포커스 가시성, `prefers-reduced-motion` 존중 — 모든 화면에서 필수.
- **CSS specificity 관리**: 섹션/요소 셀렉터 충돌(특히 padding/margin) 주의.
- **copy/문구 원칙**: 능동태, sentence case, 동일 액션은 흐름 전체에서 같은 이름. 단, 한국어 UI 문구는 `web_design_spec.md`의 표기를 우선한다.

### 보강

- 보고서(PR1/PR2)의 차트·지표 시각화는 [[ui-ux-pro-max]] 스킬의 `reference/charts.csv`(차트 25종 + 접근성 등급)로 점검한다.
- 디자인 변경 제안이 필요하면 **임의로 바꾸지 말고** 먼저 사용자에게 확인한다 (DESIGN.md/mockup이 source of truth).
