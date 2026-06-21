#!/usr/bin/env python3
"""국가(country) 상세화면 렌더링 엔진 (P1)

- AI 리서치 국가 데이터(data/research/country/<CODE>/<CODE>_latest.json)를 입력으로 받아,
  웹 디자인 스펙(architecture/design/stitch/html/P1.html, "국가 정보")에 맞춘
  완성형 standalone HTML 상세화면으로 렌더링한다.
- 구성(스펙 §4 P1): 국기·국가명·진출여부 → 국가 일반(통화·시장규모 등) +
  시계열 차트 + 시장/핵심규제/특화요건·시스템 섹션.
- 데이터 주도(country-agnostic) — 어떤 국가 리서치 데이터든 동일 로직으로 렌더.
- 입력: data/research/country/<CODE>/<CODE>_latest.json
- 출력: detail/country/<CODE>/html/<CODE>_detail_<TS>.html

스코어링/계산은 일절 하지 않고 "표현"만 담당한다 (관심사 분리).
포맷·차트 헬퍼는 region_report_rendering_engine(rre)을 재사용한다.
"""
import json, os, sys, glob, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
# engine/rendering → app/backend  (storage가 위치한 backend 루트)
BACKEND = os.path.dirname(os.path.dirname(BASE))
STORAGE = os.path.join(BACKEND, "storage")
DATA = os.path.join(STORAGE, "data")
DETAIL = os.path.join(STORAGE, "detail")

# 같은 rendering/ 폴더의 포맷·차트 헬퍼 재사용 (중복 작성 금지)
sys.path.insert(0, BASE)
import region_report_rendering_engine as rre  # noqa: E402

TPL_PATH = os.path.join(BASE, "templates", "country_detail_template.html")


# ─────────────────────────────────────────────────────────────────────────────
# 진출여부 — 사내 자산(country_assets)에 해당 국가코드 존재 여부로 도출 (스펙 §4)
# ─────────────────────────────────────────────────────────────────────────────
def entry_status(code):
    """(있음→기진출/Operational, 없음→미진출) 배지 HTML 반환."""
    path = os.path.join(DATA, "internal", "internal_latest.json")
    assets = {}
    try:
        with open(path, encoding="utf-8") as f:
            assets = json.load(f).get("country_assets", {})
    except Exception:
        pass
    if code in assets:
        a = assets[code]
        sol = a.get("solution", "")
        label = f"기진출 · {sol}" if sol else "기진출"
        badge = (
            '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-label-sm '
            'bg-[#e8f5e9] text-[#2e7d32] border border-[#a5d6a7]">'
            '<span class="w-1.5 h-1.5 rounded-full bg-[#2e7d32] mr-1.5"></span>'
            f'{rre.esc(label)}</span>')
    else:
        badge = (
            '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-label-sm '
            'bg-surface-container text-on-surface-variant border border-surface-border">'
            '<span class="w-1.5 h-1.5 rounded-full bg-outline mr-1.5"></span>'
            '미진출 · 진단 대상</span>')
    return badge


# ─────────────────────────────────────────────────────────────────────────────
# 빌더
# ─────────────────────────────────────────────────────────────────────────────
def stat_card(label, value):
    return (
        '<div class="p-md border border-surface-border rounded-lg bg-surface flex flex-col gap-xs">'
        f'<span class="font-label-sm text-label-sm text-outline uppercase tracking-wider">{rre.esc(label)}</span>'
        f'<span class="font-body-lg text-body-lg font-semibold text-on-surface">{rre.esc(value)}</span>'
        '</div>')


def general_cards(data):
    """국가 일반 stat 카드 — 통화 + 매력도 축 대표 지표 일부."""
    cards = [stat_card("Currency", data.get("currency", "—"))]
    # 매력도(attractiveness) score 항목 중 앞쪽 3개를 요약 카드로
    picked = [it for it in data.get("items", [])
              if it.get("axis") == "attractiveness" and it.get("role") == "score"][:3]
    for it in picked:
        cards.append(stat_card(it["item"], rre.fmt_value(it)))
    return "".join(cards)


def chart_block(it):
    """timeseries 보유 항목 → 라인차트 카드."""
    ts = it.get("timeseries") or {}
    svg = rre.line_chart(ts.get("history"), ts.get("forecast"))
    if not svg:
        return ""
    return (
        '<div class="border border-surface-border rounded-lg p-md bg-surface">'
        '<div class="flex justify-between items-center mb-md">'
        f'<h4 class="font-label-md text-label-md text-on-surface-variant">{rre.esc(it["item"])}</h4>'
        f'<span class="font-label-sm text-label-sm text-secondary bg-secondary-fixed px-2 py-0.5 rounded">{rre.esc(rre.fmt_value(it))}</span>'
        '</div>'
        f'<div class="h-24 relative w-full overflow-hidden">{svg}</div>'
        '</div>')


def charts(data):
    """시계열 보유 항목들을 차트 카드로 (최대 4개)."""
    blocks = [chart_block(it) for it in data.get("items", []) if it.get("timeseries")]
    blocks = [b for b in blocks if b][:4]
    if not blocks:
        return ('<p class="font-body-sm text-body-sm text-on-surface-variant">시계열 데이터 없음.</p>')
    return '<div class="flex flex-col gap-md">' + "".join(blocks) + "</div>"


def item_row(it):
    """단일 항목 행 — 값 + 인사이트."""
    insight = it.get("insight") or ""
    ins_html = (f'<p class="font-body-sm text-body-sm text-on-surface-variant mt-xs">{rre.esc(insight)}</p>'
                if insight else "")
    return (
        '<div class="py-sm border-b border-surface-border last:border-0">'
        '<div class="flex items-baseline justify-between gap-md">'
        f'<span class="font-body-md text-body-md text-on-surface">{rre.esc(it["item"])}</span>'
        f'<span class="font-label-md text-label-md text-primary font-semibold whitespace-nowrap">{rre.esc(rre.fmt_value(it))}</span>'
        '</div>'
        f'{ins_html}</div>')


def section(title, icon, items):
    if not items:
        return ""
    rows = "".join(item_row(it) for it in items)
    return (
        '<div>'
        '<h3 class="font-headline-md text-headline-md text-primary mb-md flex items-center gap-sm">'
        f'<span class="material-symbols-outlined text-secondary">{icon}</span>{rre.esc(title)}</h3>'
        '<div class="border border-surface-border rounded-lg bg-surface px-md">'
        f'{rows}</div></div>')


def detail_sections(data):
    """오른쪽 컬럼 — 시장 / 핵심규제 / 특화요건·시스템 섹션."""
    items = data.get("items", [])
    # 시장: business + attractiveness score (차트로 안 쓴 나머지 포함)
    market = [it for it in items
              if it.get("category") == "business" and it.get("role") == "score"]
    # 핵심규제: role=gate (+ difficulty 축 규제성 항목)
    regulation = [it for it in items if it.get("role") == "gate"]
    # 특화요건·시스템: IT 유사도 + 회수/추심 등 shared similarity
    system = [it for it in items
              if it.get("category") == "it"
              or (it.get("category") == "shared" and it.get("axis") == "similarity")]
    out = []
    out.append(section("시장", "trending_up", market[:6]))
    out.append(section("핵심 규제", "gavel", regulation[:8]))
    out.append(section("특화요건 · 시스템", "dns", system[:8]))
    return "".join(s for s in out if s)


def flag_cell(data):
    """국기 셀 — 리서치 데이터에 flag_url 있으면 배경, 없으면 코드 폴백."""
    url = data.get("flag_url")
    if url:
        return f"background-image: url('{rre.esc(url)}'); background-size: cover; background-position: center;", ""
    return "", f'<span class="font-label-md text-label-md text-on-surface-variant">{rre.esc(data.get("code", ""))}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# HTML 렌더
# ─────────────────────────────────────────────────────────────────────────────
def render_html(data):
    code = data.get("code", "")
    en = data.get("country", code)
    ko = data.get("country_ko", "")
    title = f"{ko}({en}) 국가 상세 — 진출 진단"
    flag_style, flag_fallback = flag_cell(data)
    footer = (f"리서치 데이터 — {rre.esc(code)} · schema v{rre.esc(data.get('schema_version', '-'))} · "
              f"조사 {rre.esc(rre.fmt_dt(data.get('fetched_at', '')))} {rre.freshness_badge(data.get('fetched_at', ''))}")

    with open(TPL_PATH, encoding="utf-8") as f:
        tpl = f.read()

    return (tpl
            .replace("{{PAGE_TITLE}}", rre.esc(title))
            .replace("{{FLAG_BG}}", flag_style)
            .replace("{{FLAG_FALLBACK}}", flag_fallback)
            .replace("{{COUNTRY_EN}}", rre.esc(en))
            .replace("{{COUNTRY_KO}}", rre.esc(ko))
            .replace("{{STATUS_BADGE}}", entry_status(code))
            .replace("{{REGION_LABEL}}", rre.esc(data.get("region", "")))
            .replace("{{GENERAL_CARDS}}", general_cards(data))
            .replace("{{CHARTS}}", charts(data))
            .replace("{{DETAIL_SECTIONS}}", detail_sections(data))
            .replace("{{FOOTER_META}}", footer))


# ─────────────────────────────────────────────────────────────────────────────
# 입출력
# ─────────────────────────────────────────────────────────────────────────────
def load_detail(code, version=None):
    datadir = os.path.join(DATA, "research", "country", code)
    if version:
        path = os.path.join(datadir, f"{code}_{version}.json")
    else:
        path = os.path.join(datadir, f"{code}_latest.json")
    if not os.path.exists(path):
        cand = sorted(glob.glob(os.path.join(datadir, f"{code}_*.json")))
        if not cand:
            raise SystemExit(f"[안내] country '{code}' 리서치 데이터 없음 — data/research/country/{code}/ 확인 필요.")
        path = cand[-1]
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def render(code="ES", version=None):
    data, src = load_detail(code, version)
    out_html = render_html(data)

    outdir = os.path.join(DETAIL, "country", code, "html")
    os.makedirs(outdir, exist_ok=True)
    ts = (data.get("fetched_at") or "latest").replace(":", "").replace("+", "_")
    out = os.path.join(outdir, f"{code}_detail_{ts}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(out_html)

    print(f"[{code}] 상세화면 렌더 완료 — 입력 {os.path.relpath(src, STORAGE)}")
    print(f"  항목 {len(data.get('items', []))}개")
    print(f"→ {os.path.relpath(out, STORAGE)}")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    code = args[0] if args else "ES"
    version = args[1] if len(args) > 1 else None
    render(code, version)
