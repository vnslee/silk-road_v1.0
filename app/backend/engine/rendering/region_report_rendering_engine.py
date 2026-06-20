#!/usr/bin/env python3
"""권역(region) 진단 보고서 렌더링 엔진 (PR2)

- generation/region_report_generation_engine.py 가 생성한 권역 퀵윈 리포트 JSON을 입력으로 받아,
  웹 디자인 스펙(architecture/design/stitch/html/PR2.html, "권역 진단 보고서")에 맞춘
  완성형 standalone HTML 보고서로 렌더링한다.
- 탭 구성(스펙 PR2): 요약(Summary) · 시장(Market) · 규제(Regulation) ·
  상품(Product) · 시스템(System).
- 데이터 주도(region-agnostic) — 어떤 권역 리포트든 동일 로직으로 렌더.
- 출력: report/region/<REGION>/<REGION>_rpt_<TS>.html (+ _latest.html 포인터)

입력 리포트 스키마: report/region/README.md, generation/region_report_generation_engine.py 참조.
스코어링/계산은 일절 하지 않고 "표현"만 담당한다 (관심사 분리).
"""
import json, os, sys, glob, html, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
REPORT = os.path.join(REPO, "report")

# ─────────────────────────────────────────────────────────────────────────────
# 탭 매핑 — 항목(item)을 5개 탭 중 하나로 분류. 명시 매핑 + 휴리스틱 폴백.
# ─────────────────────────────────────────────────────────────────────────────
TAB_MARKET = "market"
TAB_REG = "regulation"
TAB_PRODUCT = "product"
TAB_SYSTEM = "system"
TAB_SUMMARY = "summary"

TABS = [
    ("summary", "요약", "Summary", "summarize"),
    ("market", "시장", "Market", "trending_up"),
    ("regulation", "규제", "Regulation", "gavel"),
    ("product", "상품", "Product", "inventory_2"),
    ("system", "시스템", "System", "dns"),
]

ITEM_TAB = {
    # 시장
    "오토금융/리스 시장규모": TAB_MARKET, "오토금융 성장률(CAGR)": TAB_MARKET,
    "금융 이용률(신차)": TAB_MARKET, "금융 이용률(중고차)": TAB_MARKET,
    "신차 판매대수": TAB_MARKET, "캡티브 강도(점유율)": TAB_MARKET,
    "1위사 점유율": TAB_MARKET, "OEM 순위": TAB_MARKET,
    "브랜드 Top10": TAB_MARKET, "경쟁사 리스트": TAB_MARKET,
    # 규제
    "외국인 지분 한도": TAB_REG, "외환 송금 자유도": TAB_REG,
    "라이선스 취득 가능 여부(외국사)": TAB_REG, "금리 상한 규제": TAB_REG,
    "최저자본금": TAB_REG, "데이터 현지화 의무": TAB_REG,
    "라이선스 체제(세그먼트별)": TAB_REG, "국외이전 제한": TAB_REG,
    "법인세율": TAB_REG, "이자소득 원천징수(비거주자)": TAB_REG,
    "배당 원천징수(비거주자)": TAB_REG, "이자소득 원천징수": TAB_REG,
    "규제기관 식별": TAB_REG,
    # 상품
    "평균 금리/APR": TAB_PRODUCT, "구매 패턴(할부·리스 비중)": TAB_PRODUCT,
    "추심 규제": TAB_PRODUCT, "차량회수 절차 용이성": TAB_PRODUCT,
    "법적 회수 소요기간": TAB_PRODUCT, "충당금 규정": TAB_PRODUCT,
    "연체 분류 기준": TAB_PRODUCT,
    # 시스템
    "솔루션 벤더": TAB_SYSTEM, "솔루션 유형": TAB_SYSTEM,
    "신용정보(CB) 인프라": TAB_SYSTEM, "디지털 채널 성숙도": TAB_SYSTEM,
    "결제·정산 인프라": TAB_SYSTEM, "디지털 딜러 성숙도": TAB_SYSTEM,
}

_REG_KEYS = ("세율", "원천징수", "라이선스", "자본금", "규제", "현지화",
             "지분", "송금", "국외이전", "감독")


def tab_for(it):
    """항목을 탭으로 분류. 명시 매핑 우선, 없으면 role/category/키워드 폴백."""
    name = it.get("item", "")
    if name in ITEM_TAB:
        return ITEM_TAB[name]
    if it.get("role") == "context":
        return TAB_SUMMARY
    if it.get("role") == "gate":
        return TAB_REG
    if any(k in name for k in _REG_KEYS):
        return TAB_REG
    cat = it.get("category")
    if cat == "it":
        return TAB_SYSTEM
    if cat == "business":
        return TAB_MARKET
    return TAB_PRODUCT


# ─────────────────────────────────────────────────────────────────────────────
# 포맷 헬퍼
# ─────────────────────────────────────────────────────────────────────────────
def esc(s):
    return html.escape("" if s is None else str(s))


def fmt_num(v):
    if isinstance(v, float):
        return f"{v:,.1f}".rstrip("0").rstrip(".") if v % 1 else f"{int(v):,}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def fmt_value(it):
    """항목 value를 단위에 맞게 사람이 읽는 문자열로 변환."""
    v = it.get("value")
    unit = it.get("unit")
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if v is None:
        return "—"
    if isinstance(v, (int, float)):
        if unit == "%":
            return f"{fmt_num(v)}%"
        if isinstance(unit, str) and unit.endswith("_1to5"):
            return f"{v}/5"
        if unit == "days":
            return f"{fmt_num(v)}일"
        if unit == "units":
            return f"{fmt_num(v)}대"
        if isinstance(unit, str) and unit.endswith("_M"):
            return f"{fmt_num(v)} {unit[:-2]}M"
        return fmt_num(v)
    return str(v)


def fmt_dt(iso):
    try:
        s = iso.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(s)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso or ""


def freshness_badge(fetched_at):
    """fetched_at 기준 신선도 신호등 (스키마 규칙 10): 🟢방금/🟡30일/🔴90일+."""
    if not fetched_at:
        return ""
    try:
        s = fetched_at.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(s)
        now = datetime.datetime.now(dt.tzinfo)
        days = (now - dt).days
    except Exception:
        return ""
    if days <= 30:
        c, t = "#137333", "🟢 최신"
    elif days <= 90:
        c, t = "#b06000", f"🟡 {days}일 경과"
    else:
        c, t = "#c5221f", "🔴 재조사 권장"
    return badge(t, c + "1a", c)


# 사분면/신뢰도/게이트 색 토큰
QUAD_COLOR = {
    "즉시 진출": "#137333", "선별 진출": "#1967d2",
    "기회 탐색": "#b06000", "JV/제휴 필요": "#c5221f",
}
CONF_COLOR = {"상": "#137333", "중": "#b06000", "하": "#c5221f"}
GATE_COLOR = {"PASS": ("#e6f4ea", "#137333"), "FLAG": ("#fef7e0", "#b06000"),
              "FAIL": ("#fce8e6", "#c5221f")}


def badge(text, bg, fg):
    return (f'<span class="px-2 py-1 rounded-md font-label-sm text-label-sm '
            f'whitespace-nowrap" style="background:{bg};color:{fg}">{esc(text)}</span>')


def conf_badge(c):
    fg = CONF_COLOR.get(c, "#555555")
    return badge(f"신뢰도 {c}", fg + "1a", fg)


def gate_badge(result):
    bg, fg = GATE_COLOR.get(result, ("#eee", "#555"))
    return badge(result, bg, fg)


def score_color(v):
    """0-100 점수 → 신호색."""
    return "#137333" if v >= 70 else "#1967d2" if v >= 50 else "#b06000" if v >= 35 else "#c5221f"


def bar(value, vmax=100, color="#005db7"):
    pct = 0 if not vmax else max(0, min(100, value / vmax * 100))
    return (f'<div class="w-full h-base bg-surface-border rounded-full overflow-hidden">'
            f'<div class="h-full rounded-full" style="width:{pct:.0f}%;background:{color}"></div></div>')


# ─────────────────────────────────────────────────────────────────────────────
# SVG 차트
# ─────────────────────────────────────────────────────────────────────────────
def vbar_chart(series, vmax=100, height=180, unit=""):
    """세로 막대 비교 차트. series=[(label, value, color)]."""
    if not series:
        return ""
    n = len(series)
    bw, gap, pad = 54, 28, 28
    w = pad * 2 + n * bw + (n - 1) * gap
    h = height
    base = h - 34
    top = 16
    bars = []
    for i, (label, val, color) in enumerate(series):
        x = pad + i * (bw + gap)
        bh = 0 if not vmax else max(2, (val / vmax) * (base - top))
        y = base - bh
        bars.append(
            f'<rect x="{x}" y="{y:.1f}" width="{bw}" height="{bh:.1f}" rx="4" fill="{color}"/>'
            f'<text x="{x+bw/2}" y="{y-6:.1f}" text-anchor="middle" font-size="13" '
            f'font-weight="700" fill="#1b1c1c">{fmt_num(val)}{esc(unit)}</text>'
            f'<text x="{x+bw/2}" y="{base+18}" text-anchor="middle" font-size="12" '
            f'fill="#555555">{esc(label)}</text>')
    return (f'<svg viewBox="0 0 {w} {h}" class="w-full" style="max-height:{h}px" '
            f'preserveAspectRatio="xMidYMid meet">'
            f'<line x1="{pad-8}" y1="{base}" x2="{w-pad+8}" y2="{base}" '
            f'stroke="#DCDCDC" stroke-width="1"/>{"".join(bars)}</svg>')


def quadrant_chart(rows):
    """매력도(x) × 난이도(y, 위쪽이 낮음) 사분면 버블. 버블=구축비, 색=퀵윈."""
    w, h, pad = 520, 380, 44
    x0, y0 = pad, 16
    x1, y1 = w - 16, h - pad
    def sx(a): return x0 + (a / 100) * (x1 - x0)
    def sy(d): return y0 + (d / 100) * (y1 - y0)  # 난이도 클수록 아래
    mx, my = sx(50), sy(50)
    builds = [r["cost"]["build"] for r in rows] or [1]
    bmax = max(builds) or 1
    pts = []
    for r in rows:
        a, d = r["attractiveness"], r["difficulty"]
        cx, cy = sx(a), sy(d)
        rad = 9 + (r["cost"]["build"] / bmax) * 17
        col = "#005db7" if r["quick_win"] else "#9aa0aa"
        pts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" fill="{col}" '
            f'fill-opacity="0.78" stroke="#fff" stroke-width="2"/>'
            f'<text x="{cx:.1f}" y="{cy+4:.1f}" text-anchor="middle" font-size="12" '
            f'font-weight="700" fill="#fff">{esc(r["code"])}</text>')
    # 사분면 라벨
    labels = [
        (sx(75), sy(25), "즉시 진출"), (sx(25), sy(25), "기회 탐색"),
        (sx(75), sy(78), "선별 진출"), (sx(25), sy(78), "JV/제휴 필요"),
    ]
    lab = "".join(f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle" '
                  f'font-size="11" fill="#9aa0aa" font-weight="600">{esc(t)}</text>'
                  for lx, ly, t in labels)
    return (f'<svg viewBox="0 0 {w} {h}" class="w-full" preserveAspectRatio="xMidYMid meet">'
            f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#fff" '
            f'stroke="#DCDCDC"/>'
            f'<line x1="{mx:.0f}" y1="{y0}" x2="{mx:.0f}" y2="{y1}" stroke="#DCDCDC" stroke-dasharray="4 4"/>'
            f'<line x1="{x0}" y1="{my:.0f}" x2="{x1}" y2="{my:.0f}" stroke="#DCDCDC" stroke-dasharray="4 4"/>'
            f'{lab}{"".join(pts)}'
            f'<text x="{(x0+x1)/2:.0f}" y="{h-12}" text-anchor="middle" font-size="12" '
            f'fill="#555555">매력도 →</text>'
            f'<text x="14" y="{(y0+y1)/2:.0f}" text-anchor="middle" font-size="12" '
            f'fill="#555555" transform="rotate(-90 14 {(y0+y1)/2:.0f})">← 진입난이도(낮을수록 위)</text>'
            f'</svg>')


def line_chart(history, forecast, color="#00204e"):
    """시계열 라인차트(실적+전망). history/forecast=[{year,value}]."""
    pts_all = (history or []) + (forecast or [])
    if len(pts_all) < 2:
        return ""
    w, h, pad = 300, 96, 8
    xs = [p["year"] for p in pts_all]
    ys = [p["value"] for p in pts_all]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    def X(x): return pad + (0 if xmax == xmin else (x - xmin) / (xmax - xmin)) * (w - 2 * pad)
    def Y(y): return (h - pad) - (0 if ymax == ymin else (y - ymin) / (ymax - ymin)) * (h - 2 * pad)
    def path(pp): return " ".join(("M" if i == 0 else "L") + f"{X(p['year']):.1f} {Y(p['value']):.1f}"
                                  for i, p in enumerate(pp))
    segs = []
    if history:
        segs.append(f'<path d="{path(history)}" fill="none" stroke="{color}" stroke-width="2"/>')
    if forecast:
        link = [history[-1]] + forecast if history else forecast
        segs.append(f'<path d="{path(link)}" fill="none" stroke="{color}" '
                    f'stroke-width="2" stroke-dasharray="4 3" opacity="0.6"/>')
    dots = "".join(f'<circle cx="{X(p["year"]):.1f}" cy="{Y(p["value"]):.1f}" r="2" fill="{color}"/>'
                   for p in pts_all)
    return (f'<svg viewBox="0 0 {w} {h}" class="w-full" style="max-height:96px">'
            f'{"".join(segs)}{dots}</svg>')


# ─────────────────────────────────────────────────────────────────────────────
# 기여도 분해 (누적 수평 막대) — *_contributions[].weighted 표현
#   막대 길이 = 해당 축 점수(0~100), 색 구간 = 항목별 가중 기여(weighted).
#   계산은 하지 않고 리포트가 이미 박아둔 weighted를 그대로 쌓는다.
# ─────────────────────────────────────────────────────────────────────────────
CONTRIB_PALETTE = ["#00204e", "#005db7", "#1967d2", "#4a90d9", "#7cb342",
                   "#00897b", "#b06000", "#8e44ad", "#c5221f", "#5f6368"]


def _contrib_color_map(names):
    return {n: CONTRIB_PALETTE[i % len(CONTRIB_PALETTE)] for i, n in enumerate(names)}


def stacked_bar(segments, scale=100, height=16):
    """누적 수평 막대. segments=[(label, value, color)]. width%는 scale 기준."""
    parts = []
    for label, val, color in segments:
        if not val or val <= 0:
            continue
        wpct = max(0.0, min(100.0, val / scale * 100))
        parts.append(f'<div style="width:{wpct:.1f}%;background:{color}" '
                     f'title="{esc(label)}: {fmt_num(val)}" class="h-full"></div>')
    inner = "".join(parts) or '<div class="h-full w-0"></div>'
    return (f'<div class="flex w-full rounded-full overflow-hidden bg-surface-border" '
            f'style="height:{height}px">{inner}</div>')


def contribution_breakdown(rows, kind):
    """국가별 기여도 누적 막대 + 공유 범례.
    kind='attractiveness'|'difficulty'(business_contributions) | 'similarity'(it_contributions)."""
    if kind == "similarity":
        get_contribs = lambda r: r.get("it_contributions", [])
        keep = lambda c: True
    else:
        get_contribs = lambda r: r.get("business_contributions", [])
        keep = lambda c: c.get("axis") == kind
    # 항목명 union (등장 순서 유지, weighted>0만)
    names, seen = [], set()
    for r in rows:
        for c in get_contribs(r):
            if keep(c) and (c.get("weighted") or 0) > 0 and c["item"] not in seen:
                names.append(c["item"])
                seen.add(c["item"])
    if not names:
        return ""
    cmap = _contrib_color_map(names)

    bars = []
    for r in rows:
        segs, total = [], 0.0
        for c in get_contribs(r):
            if not keep(c):
                continue
            w = c.get("weighted") or 0
            if w <= 0:
                continue
            segs.append((c["item"], w, cmap.get(c["item"], "#9aa0aa")))
            total += w
        if not segs:
            continue
        bars.append(
            f'<div class="flex items-center gap-sm">'
            f'<span class="font-label-md text-label-md text-primary w-8 shrink-0">{esc(r["code"])}</span>'
            f'<div class="flex-1">{stacked_bar(segs)}</div>'
            f'<span class="font-label-md text-label-md text-primary w-10 text-right shrink-0">'
            f'{fmt_num(round(total, 1))}</span></div>')
    if not bars:
        return ""
    legend = "".join(
        f'<span class="flex items-center gap-xs font-label-sm text-label-sm text-text-secondary">'
        f'<span class="w-3 h-3 rounded-sm shrink-0" style="background:{cmap[n]}"></span>{esc(n)}</span>'
        for n in names)
    return (f'<div class="flex flex-col gap-sm mb-md">{"".join(bars)}</div>'
            f'<div class="flex flex-wrap gap-md pt-sm border-t border-surface-border">{legend}</div>')


# ─────────────────────────────────────────────────────────────────────────────
# 공통 카드/섹션 헬퍼
# ─────────────────────────────────────────────────────────────────────────────
def card(inner, extra=""):
    return (f'<div class="bg-surface-container-lowest border border-surface-border rounded-lg '
            f'p-lg shadow-[0_4px_8px_rgba(0,32,78,0.04)] {extra}">{inner}</div>')


def section_title(t, sub=""):
    s = (f'<p class="font-body-sm text-body-sm text-on-surface-variant mt-xs">{esc(sub)}</p>'
         if sub else "")
    return f'<h2 class="font-headline-md text-headline-md text-primary m-0">{esc(t)}</h2>{s}'


def country_maps(row):
    """ranking row → (항목명→item, 항목명→biz기여, 항목명→it기여)."""
    items = {it["item"]: it for it in row.get("items", [])}
    biz = {c["item"]: c for c in row.get("business_contributions", [])}
    itc = {c["item"]: c for c in row.get("it_contributions", [])}
    return items, biz, itc


# ─────────────────────────────────────────────────────────────────────────────
# 실사 체크리스트 (due_diligence) · 국가별 종합 인사이트 (overall_insight)
# ─────────────────────────────────────────────────────────────────────────────
def due_diligence_block(rpt):
    """국가별 due_diligence 항목을 실사 체크리스트 테이블로 (스키마 규칙 9)."""
    rows = rpt["ranking"]
    if not any(r.get("due_diligence") for r in rows):
        return ""
    summ = {d["code"]: d.get("count") for d in rpt.get("due_diligence_summary", [])}
    sub = []
    for r in rows:
        dds = r.get("due_diligence") or []
        if not dds:
            continue
        body = "".join(
            f'<tr class="border-b border-surface-border">'
            f'<td class="py-xs px-sm font-medium text-on-surface align-top">{esc(d["item"])}</td>'
            f'<td class="py-xs px-sm align-top">'
            f'{badge("T" + str(d.get("tier", "-")), "#fef7e0", "#b06000")}</td>'
            f'<td class="py-xs px-sm text-on-surface-variant align-top">{esc(d.get("action", ""))}</td>'
            f'</tr>' for d in dds)
        cnt = summ.get(r["code"], len(dds))
        sub.append(
            f'<div class="mb-md">'
            f'<div class="flex items-center gap-sm mb-xs">'
            f'<h3 class="font-label-md text-label-md uppercase text-primary m-0">'
            f'{esc(r["country_ko"])} ({esc(r["code"])})</h3>'
            f'{badge(str(cnt) + "건", "#eef0f2", "#555555")}</div>'
            f'<table class="w-full text-left border-collapse"><thead>'
            f'<tr class="border-b border-surface-border">'
            f'<th class="py-xs px-sm font-label-sm text-label-sm text-text-secondary uppercase">항목</th>'
            f'<th class="py-xs px-sm font-label-sm text-label-sm text-text-secondary uppercase">신뢰도</th>'
            f'<th class="py-xs px-sm font-label-sm text-label-sm text-text-secondary uppercase">권장 액션</th>'
            f'</tr></thead><tbody class="font-body-sm text-body-sm">{body}</tbody></table></div>')
    return card(
        f'<div class="flex items-center gap-sm mb-xs">'
        f'<span class="material-symbols-outlined text-secondary">fact_check</span>'
        f'<h2 class="font-headline-md text-headline-md text-primary m-0">실사 체크리스트 (Due Diligence)</h2></div>'
        f'<p class="font-body-sm text-body-sm text-on-surface-variant mt-0 mb-md">'
        f'저신뢰(T3+) 지표·FLAG 게이트 — 진출 확정 전 1차 출처·현지 실사로 확인 필요.</p>'
        f'{"".join(sub)}')


def country_insight_block(rpt):
    """국가별 종합 인사이트(overall_insight) + freshness 신호등."""
    rows = rpt["ranking"]
    cards = []
    for r in rows:
        meta = r.get("country_meta", {})
        oi = meta.get("overall_insight")
        if not oi:
            continue
        fresh = freshness_badge(meta.get("fetched_at"))
        cards.append(card(
            f'<div class="flex items-center justify-between gap-sm mb-sm">'
            f'<h3 class="font-label-md text-label-md uppercase text-primary m-0">'
            f'{esc(r["country_ko"])} ({esc(r["code"])})</h3>'
            f'<div class="flex items-center gap-xs">{fresh}'
            f'<span class="font-label-sm text-label-sm text-text-secondary">'
            f'{esc(meta.get("data_year", ""))} 데이터</span></div></div>'
            f'<p class="font-body-sm text-body-sm text-on-surface m-0">{esc(oi)}</p>'))
    if not cards:
        return ""
    return (f'<div><h2 class="font-headline-md text-headline-md text-primary mb-md">'
            f'국가별 종합 인사이트</h2>'
            f'<div class="grid grid-cols-1 md:grid-cols-3 gap-md">{"".join(cards)}</div></div>')


# ─────────────────────────────────────────────────────────────────────────────
# 탭: 요약
# ─────────────────────────────────────────────────────────────────────────────
def tab_summary(rpt):
    rows = rpt["ranking"]
    qw = rpt.get("quick_wins", [])
    bcode = rpt.get("baseline")
    top = rows[0] if rows else None

    # Executive cards
    cards = []
    cards.append(card(
        f'<div class="flex items-center gap-sm mb-sm text-secondary">'
        f'<span class="material-symbols-outlined">flag</span>'
        f'<h3 class="font-label-md text-label-md uppercase m-0">후보국 / 퀵윈</h3></div>'
        f'<div class="font-headline-md text-headline-md text-primary mb-xs">'
        f'{rpt.get("candidate_count",len(rows))}개 중 {len(qw)}개</div>'
        f'<p class="font-body-sm text-body-sm text-on-surface-variant m-0">'
        f'퀵윈: {esc(", ".join(qw)) or "없음"}</p>'))
    if top:
        c = top["cost"]
        cards.append(card(
            f'<div class="flex items-center gap-sm mb-sm text-secondary">'
            f'<span class="material-symbols-outlined">military_tech</span>'
            f'<h3 class="font-label-md text-label-md uppercase m-0">최우선 후보</h3></div>'
            f'<div class="font-headline-md text-headline-md text-primary mb-xs">'
            f'{esc(top["country_ko"])} ({esc(top["code"])})</div>'
            f'<p class="font-body-sm text-body-sm text-on-surface-variant m-0">'
            f'QW점수 {top["quick_win_score"]} · 유사도 {top["similarity"]} · '
            f'{int(c["discount"]*100)}% 절감</p>'))
    cards.append(card(
        f'<div class="flex items-center gap-sm mb-sm text-secondary">'
        f'<span class="material-symbols-outlined">hub</span>'
        f'<h3 class="font-label-md text-label-md uppercase m-0">베이스라인 / 기준</h3></div>'
        f'<div class="font-headline-md text-headline-md text-primary mb-xs">{esc(bcode)}</div>'
        f'<p class="font-body-sm text-body-sm text-on-surface-variant m-0">'
        f'internal v{esc(rpt.get("based_on",{}).get("internal_version","-"))} · '
        f'활성 {esc(", ".join(rpt.get("active_groups",[])))}</p>'))

    cards_html = f'<div class="grid grid-cols-1 md:grid-cols-3 gap-md">{"".join(cards)}</div>'

    insight = card(
        f'<div class="flex items-start gap-sm">'
        f'<span class="material-symbols-outlined text-secondary shrink-0">lightbulb</span>'
        f'<div><h3 class="font-label-md text-label-md uppercase text-secondary m-0 mb-xs">권역 인사이트</h3>'
        f'<p class="font-body-md text-body-md text-on-surface m-0">{esc(rpt.get("region_insight",""))}</p>'
        f'</div></div>')

    # 룰셋 패널
    qr = rpt.get("quick_win_rules", {})
    w = qr.get("weights", {})
    th = qr.get("thresholds", {})
    rule_rows = "".join(
        f'<div class="flex justify-between gap-md"><span class="text-on-surface-variant">{esc(k)}</span>'
        f'<span class="font-medium text-primary">{v}</span></div>'
        for k, v in [("유사도 가중", w.get("similarity")), ("매력도 가중", w.get("attractiveness")),
                     ("ease 가중", w.get("ease")), ("QW점수 임계", th.get("quick_win_score")),
                     ("최소 유사도", th.get("min_similarity")), ("최소 매력도", th.get("min_attractiveness")),
                     ("최대 난이도", th.get("max_difficulty"))])
    ruleset = card(
        f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-md">퀵윈 룰셋</h2>'
        f'<div class="flex flex-col gap-sm font-body-sm text-body-sm">{rule_rows}</div>'
        f'<p class="font-body-sm text-body-sm text-on-surface-variant mt-md mb-0">{esc(qr.get("note",""))}</p>',
        extra="h-full")

    quad = card(
        f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-md">매력도 × 진입난이도 사분면</h2>'
        f'{quadrant_chart(rows)}'
        f'<div class="flex items-center gap-lg mt-sm justify-center">'
        f'<span class="flex items-center gap-xs text-label-sm text-text-secondary">'
        f'<span class="w-3 h-3 rounded-full" style="background:#005db7"></span>퀵윈</span>'
        f'<span class="flex items-center gap-xs text-label-sm text-text-secondary">'
        f'<span class="w-3 h-3 rounded-full" style="background:#9aa0aa"></span>비퀵윈</span>'
        f'<span class="text-label-sm text-text-secondary">버블 크기 = 구축비</span></div>',
        extra="h-full")

    grid2 = (f'<div class="grid grid-cols-1 lg:grid-cols-12 gap-lg">'
             f'<div class="lg:col-span-7">{quad}</div>'
             f'<div class="lg:col-span-5">{ruleset}</div></div>')

    # 랭킹 테이블 (핵심)
    head = "".join(f'<th class="py-sm px-sm font-label-md text-label-md text-text-secondary uppercase '
                   f'whitespace-nowrap">{esc(h)}</th>'
                   for h in ["#", "국가", "퀵윈", "QW점수", "매력도", "난이도", "유사도",
                             "사분면", "신뢰도", "구축비(절감)"])
    trs = []
    for r in rows:
        c = r["cost"]
        qb = (badge("QUICK-WIN", "#e6f4ea", "#137333") if r["quick_win"]
              else badge("보류", "#eef0f2", "#555555"))
        flag = (' <span class="material-symbols-outlined text-[16px] align-middle" '
                'style="color:#b06000" title="저신뢰 FLAG">flag</span>') if r.get("gate_flag") else ""
        qcol = QUAD_COLOR.get(r["quadrant"], "#555555")
        trs.append(
            f'<tr class="border-b border-surface-border hover:bg-surface-light transition-colors">'
            f'<td class="py-sm px-sm font-bold text-primary">{r["rank"]}</td>'
            f'<td class="py-sm px-sm font-medium text-primary whitespace-nowrap">'
            f'{esc(r["country_ko"])} <span class="text-text-secondary">({esc(r["code"])})</span>{flag}</td>'
            f'<td class="py-sm px-sm">{qb}</td>'
            f'<td class="py-sm px-sm font-bold" style="color:{score_color(r["quick_win_score"])}">'
            f'{r["quick_win_score"]}</td>'
            f'<td class="py-sm px-sm">{r["attractiveness"]}</td>'
            f'<td class="py-sm px-sm">{r["difficulty"]}</td>'
            f'<td class="py-sm px-sm font-medium" style="color:{score_color(r["similarity"])}">'
            f'{r["similarity"]}</td>'
            f'<td class="py-sm px-sm"><span style="color:{qcol};font-weight:600">{esc(r["quadrant"])}</span></td>'
            f'<td class="py-sm px-sm">{conf_badge(r["confidence"])}</td>'
            f'<td class="py-sm px-sm whitespace-nowrap">{fmt_num(c["build"])} '
            f'<span class="text-text-secondary">({int(c["discount"]*100)}%↓)</span></td>'
            f'</tr>')
        # verdict 행 (+ 퀵윈 판정 근거 / 저해요인)
        rs = "".join(
            f'<span class="inline-flex items-center gap-xs mr-md font-label-sm text-label-sm" '
            f'style="color:#137333"><span class="material-symbols-outlined text-[14px]">'
            f'check_circle</span>{esc(x)}</span>' for x in (r.get("quick_win_reasons") or []))
        bl = "".join(
            f'<span class="inline-flex items-center gap-xs mr-md font-label-sm text-label-sm" '
            f'style="color:#c5221f"><span class="material-symbols-outlined text-[14px]">'
            f'block</span>{esc(x)}</span>' for x in (r.get("blockers") or []))
        extra = (f'<div class="mt-xs flex flex-wrap">{rs}{bl}</div>' if (rs or bl) else "")
        trs.append(
            f'<tr class="border-b border-surface-border bg-surface-light">'
            f'<td></td><td colspan="9" class="py-xs px-sm font-body-sm text-body-sm '
            f'text-on-surface-variant"><span class="italic">{esc(r["verdict"])}</span>'
            f'{extra}</td></tr>')
    table = card(
        f'<div class="flex items-center justify-between mb-md">'
        f'<h2 class="font-headline-md text-headline-md text-primary m-0">퀵윈 스코어링 랭킹</h2>'
        f'<span class="font-label-sm text-label-sm text-text-secondary">베이스라인 {esc(bcode)} 대비</span>'
        f'</div>'
        f'<div class="overflow-x-auto"><table class="w-full text-left border-collapse">'
        f'<thead><tr class="border-b-2 border-surface-border">{head}</tr></thead>'
        f'<tbody class="font-body-sm text-body-sm text-on-surface-variant">{"".join(trs)}</tbody>'
        f'</table></div>')

    return f"{cards_html}{insight}{grid2}{table}{due_diligence_block(rpt)}{country_insight_block(rpt)}"


# ─────────────────────────────────────────────────────────────────────────────
# 항목 비교 매트릭스 (시장/규제/상품/시스템 공용)
# ─────────────────────────────────────────────────────────────────────────────
def metric_matrix(rpt, tab_key, score_field):
    """탭에 속한 항목들을 (항목 × 국가) 매트릭스로 렌더.
    score_field: 'normalized'(biz) | 'match'(it) | None — 보조 점수 표기."""
    rows = rpt["ranking"]
    bcode = rpt.get("baseline")
    # 탭에 속한 항목명 목록 — 국가들에서 합집합(첫 등장 순서 유지)
    names = []
    seen = set()
    for r in rows:
        for it in r.get("items", []):
            if it["item"] in seen:
                continue
            if tab_for(it) == tab_key:
                names.append(it["item"])
                seen.add(it["item"])
    if not names:
        return '<p class="text-on-surface-variant">해당 탭에 표시할 항목이 없습니다.</p>'

    maps = {r["code"]: country_maps(r) for r in rows}
    head = ('<th class="py-sm px-sm font-label-md text-label-md text-text-secondary uppercase '
            'sticky left-0 bg-surface-container-lowest">항목</th>')
    for r in rows:
        tag = ' <span class="text-[10px]" style="color:#1967d2">★</span>' if r["quick_win"] else ""
        head += (f'<th class="py-sm px-sm font-label-md text-label-md text-text-secondary uppercase '
                 f'whitespace-nowrap">{esc(r["code"])}{tag}</th>')

    body = ""
    for name in names:
        cells = (f'<td class="py-sm px-sm font-medium text-primary sticky left-0 '
                 f'bg-surface-container-lowest align-top">{esc(name)}</td>')
        for r in rows:
            items, biz, itc = maps[r["code"]]
            it = items.get(name)
            if not it:
                cells += '<td class="py-sm px-sm text-text-disabled align-top">—</td>'
                continue
            val = fmt_value(it)
            sc = ""
            contrib = biz.get(name) or itc.get(name)
            if contrib and score_field and contrib.get(score_field) is not None:
                sv = contrib[score_field]
                slabel = "정합" if score_field == "match" else "정규화"
                sc = (f'<div class="mt-xs">{bar(sv, color=score_color(sv))}'
                      f'<span class="text-label-sm" style="color:{score_color(sv)}">'
                      f'{slabel} {sv}</span></div>')
            tier = it.get("tier")
            tflag = (f'<span class="text-label-sm text-text-disabled ml-xs" '
                     f'title="저신뢰(실사 필요)">·T{tier}</span>') if tier and tier >= 3 else ""
            src = it.get("source")
            src_html = (f'<div class="font-label-sm text-label-sm text-text-secondary mt-xs">'
                        f'출처: {esc(src)}</div>') if src else ""
            cells += (f'<td class="py-sm px-sm align-top">'
                      f'<div class="font-medium text-on-surface">{esc(val)}{tflag}</div>{sc}{src_html}</td>')
        body += f'<tr class="border-b border-surface-border hover:bg-surface-light">{cells}</tr>'

    note = ("★ = 퀵윈 국가 · T3+ = 저신뢰(실사 필요)"
            + (f" · 막대=베이스라인({esc(bcode)}) 정합도" if score_field == "match"
               else " · 막대=정규화 점수" if score_field == "normalized" else ""))
    return (f'<div class="overflow-x-auto"><table class="w-full text-left border-collapse">'
            f'<thead><tr class="border-b-2 border-surface-border">{head}</tr></thead>'
            f'<tbody class="font-body-sm text-body-sm text-on-surface-variant">{body}</tbody>'
            f'</table></div>'
            f'<p class="font-label-sm text-label-sm text-text-secondary mt-sm mb-0">{note}</p>')


def insight_list(rpt, tab_key, source):
    """탭 항목들의 insight_compare(또는 insight)를 국가별 콜아웃으로."""
    rows = rpt["ranking"]
    out = []
    for r in rows:
        items, biz, itc = country_maps(r)
        picks = []
        for it in r.get("items", []):
            if tab_for(it) != tab_key:
                continue
            contrib = biz.get(it["item"]) or itc.get(it["item"])
            txt = ""
            if contrib:
                txt = contrib.get("insight_compare") or contrib.get("insight_detail") or ""
            if not txt:
                txt = it.get("insight", "")
            if txt:
                picks.append((it["item"], txt, it.get("insight_ai_generated"), it.get("source")))
        if not picks:
            continue
        ai_badge = ('<span class="px-2 py-0.5 rounded-md font-label-sm text-label-sm align-middle" '
                    'style="background:#ede7f6;color:#5e35b1">AI</span>')
        lis = "".join(
            f'<li class="flex items-start gap-sm">'
            f'<span class="material-symbols-outlined text-secondary text-[18px] mt-xs shrink-0">'
            f'arrow_right</span>'
            f'<div><span class="font-label-md text-label-md text-primary">{esc(name)}</span> '
            f'{ai_badge + " " if ai else ""}'
            f'<span class="font-body-sm text-body-sm text-on-surface-variant">{esc(txt)}</span>'
            + (f'<div class="font-label-sm text-label-sm text-text-secondary mt-xs">출처: {esc(src)}</div>'
               if src else "")
            + '</div></li>'
            for name, txt, ai, src in picks[:5])
        out.append(card(
            f'<h3 class="font-label-md text-label-md uppercase text-secondary m-0 mb-sm">'
            f'{esc(r["country_ko"])} ({esc(r["code"])})</h3>'
            f'<ul class="flex flex-col gap-sm m-0 p-0 list-none">{lis}</ul>'))
    if not out:
        return ""
    return f'<div class="grid grid-cols-1 md:grid-cols-2 gap-md">{"".join(out)}</div>'


# ─────────────────────────────────────────────────────────────────────────────
# 탭: 시장
# ─────────────────────────────────────────────────────────────────────────────
def tab_market(rpt):
    rows = rpt["ranking"]
    # 매력도 비교 막대
    series = [(r["code"], r["attractiveness"],
               "#00204e" if r["quick_win"] else "#9aa0aa") for r in rows]
    chart = card(
        f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-md">시장 매력도 비교</h2>'
        f'{vbar_chart(series, 100)}')

    # 점수 기여도 분해 (매력도/난이도) — business_contributions[].weighted
    attr_bd = contribution_breakdown(rows, "attractiveness")
    diff_bd = contribution_breakdown(rows, "difficulty")
    contrib_card = ""
    if attr_bd or diff_bd:
        attr_sec = (f'<h3 class="font-label-md text-label-md uppercase text-secondary m-0 mb-sm">'
                    f'매력도 (Attractiveness)</h3>{attr_bd}') if attr_bd else ""
        diff_sec = (f'<h3 class="font-label-md text-label-md uppercase text-secondary m-0 mb-sm '
                    f'mt-lg">진입난이도 (Difficulty)</h3>{diff_bd}') if diff_bd else ""
        contrib_card = card(
            f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-xs">점수 기여도 분해</h2>'
            f'<p class="font-body-sm text-body-sm text-on-surface-variant mt-0 mb-md">'
            f'막대 길이 = 해당 축 점수, 색 구간 = 항목별 가중 기여(weighted). '
            f'어떤 지표가 점수를 끌어올리는지 분해해 보여줍니다.</p>'
            f'{attr_sec}{diff_sec}')

    # 시장규모 시계열 (timeseries 보유 항목)
    ts_cards = []
    for r in rows:
        items, _, _ = country_maps(r)
        it = items.get("오토금융/리스 시장규모")
        if it and it.get("timeseries"):
            ts = it["timeseries"]
            est = (' ' + badge("추정", "#fef7e0", "#b06000")) if ts.get("estimated") else ""
            ts_cards.append(card(
                f'<div class="flex items-center justify-between mb-sm">'
                f'<h3 class="font-label-md text-label-md uppercase text-primary m-0">'
                f'{esc(r["code"])} 시장규모{est}</h3>'
                f'<span class="font-label-sm text-label-sm text-text-secondary">'
                f'CAGR {ts.get("cagr_hist","-")}% → {ts.get("cagr_forecast","-")}%</span></div>'
                f'{line_chart(ts.get("history"), ts.get("forecast"))}'
                f'<div class="flex justify-between font-label-sm text-label-sm text-text-secondary mt-xs">'
                f'<span>{ts["history"][0]["year"] if ts.get("history") else ""}</span>'
                f'<span>실적 ─ 전망 ┄</span>'
                f'<span>{ts["forecast"][-1]["year"] if ts.get("forecast") else ""}</span></div>'))
    ts_block = (f'<div><h2 class="font-headline-md text-headline-md text-primary mb-md">'
                f'오토금융 시장규모 추이</h2>'
                f'<div class="grid grid-cols-1 md:grid-cols-3 gap-md">{"".join(ts_cards)}</div></div>'
                if ts_cards else "")

    matrix = card(
        f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-md">시장 지표 매트릭스</h2>'
        f'{metric_matrix(rpt, TAB_MARKET, "normalized")}')

    insights = insight_list(rpt, TAB_MARKET, "biz")
    insights_block = (f'<div><h2 class="font-headline-md text-headline-md text-primary mb-md">'
                      f'시장 인사이트</h2>{insights}</div>') if insights else ""
    return f"{chart}{contrib_card}{ts_block}{matrix}{insights_block}"


# ─────────────────────────────────────────────────────────────────────────────
# 탭: 규제
# ─────────────────────────────────────────────────────────────────────────────
def tab_regulation(rpt):
    rows = rpt["ranking"]
    # 게이트 매트릭스
    gate_names = []
    seen = set()
    for r in rows:
        for ck in r.get("gate_checks", []):
            if ck["item"] not in seen:
                gate_names.append(ck["item"])
                seen.add(ck["item"])
    head = ('<th class="py-sm px-sm font-label-md text-label-md text-text-secondary uppercase '
            'sticky left-0 bg-surface-container-lowest">게이트</th>')
    head += "".join(f'<th class="py-sm px-sm font-label-md text-label-md text-text-secondary '
                    f'uppercase">{esc(r["code"])}</th>' for r in rows)
    gmap = {r["code"]: {ck["item"]: ck for ck in r.get("gate_checks", [])} for r in rows}
    scope_ko = {"country": "국가", "segment": "세그먼트", "operating_model": "운영모델"}
    gbody = ""
    for gn in gate_names:
        scope = next((gmap[r["code"]][gn].get("scope") for r in rows
                      if gmap[r["code"]].get(gn)), None)
        sclbl = (f'<div class="font-label-sm text-label-sm text-text-secondary">'
                 f'{esc(scope_ko.get(scope, scope))} 층위</div>') if scope else ""
        cells = (f'<td class="py-sm px-sm font-medium text-primary sticky left-0 '
                 f'bg-surface-container-lowest align-top">{esc(gn)}{sclbl}</td>')
        for r in rows:
            ck = gmap[r["code"]].get(gn)
            cells += (f'<td class="py-sm px-sm align-top">{gate_badge(ck["result"]) if ck else "—"}</td>')
        gbody += f'<tr class="border-b border-surface-border hover:bg-surface-light">{cells}</tr>'
    gate_card = card(
        f'<div class="flex items-center justify-between mb-md">'
        f'<h2 class="font-headline-md text-headline-md text-primary m-0">진입 게이트 점검</h2>'
        f'<span class="font-label-sm text-label-sm text-text-secondary">'
        f'PASS=통과 · FLAG=저신뢰 · FAIL=불가</span></div>'
        f'<div class="overflow-x-auto"><table class="w-full text-left border-collapse">'
        f'<thead><tr class="border-b-2 border-surface-border">{head}</tr></thead>'
        f'<tbody class="font-body-sm text-body-sm">{gbody}</tbody></table></div>')

    # 게이트 실패/저신뢰 경고
    warn = ""
    gf = rpt.get("gate_failed", [])
    flags = [r["code"] for r in rows if r.get("gate_flag")]
    if gf or flags:
        msgs = []
        if gf:
            msgs.append("게이트 FAIL: " + ", ".join(g["code"] for g in gf))
        if flags:
            msgs.append("저신뢰(FLAG) 게이트 보유: " + ", ".join(flags))
        warn = (f'<div class="rounded-lg p-md border" style="background:#fef7e0;border-color:#f0d68a">'
                f'<div class="flex items-center gap-sm" style="color:#b06000">'
                f'<span class="material-symbols-outlined">warning</span>'
                f'<span class="font-label-md text-label-md">{esc(" · ".join(msgs))} — 실사로 확정 필요</span>'
                f'</div></div>')

    matrix = card(
        f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-md">규제·세제 지표</h2>'
        f'{metric_matrix(rpt, TAB_REG, None)}')
    insights = insight_list(rpt, TAB_REG, "biz")
    insights_block = (f'<div><h2 class="font-headline-md text-headline-md text-primary mb-md">'
                      f'규제 인사이트</h2>{insights}</div>') if insights else ""
    return f"{warn}{gate_card}{matrix}{insights_block}"


# ─────────────────────────────────────────────────────────────────────────────
# 탭: 상품
# ─────────────────────────────────────────────────────────────────────────────
def tab_product(rpt):
    matrix = card(
        f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-md">상품·회수 지표</h2>'
        f'<p class="font-body-sm text-body-sm text-on-surface-variant mt-0 mb-md">'
        f'금리·구매패턴·추심·담보회수 등 상품 설계 제약 비교.</p>'
        f'{metric_matrix(rpt, TAB_PRODUCT, "match")}')
    insights = insight_list(rpt, TAB_PRODUCT, "it")
    insights_block = (f'<div><h2 class="font-headline-md text-headline-md text-primary mb-md">'
                      f'상품 인사이트</h2>{insights}</div>') if insights else ""
    return f"{matrix}{insights_block}"


# ─────────────────────────────────────────────────────────────────────────────
# 탭: 시스템
# ─────────────────────────────────────────────────────────────────────────────
def tab_system(rpt):
    rows = rpt["ranking"]
    bcode = rpt.get("baseline")
    # 유사도 + 비용 비교
    series = [(r["code"], r["similarity"],
               "#00204e" if r["quick_win"] else "#9aa0aa") for r in rows]
    sim_chart = card(
        f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-md">'
        f'IT 유사도 (베이스라인 {esc(bcode)} 재사용률)</h2>{vbar_chart(series, 100)}')

    # 유사도 기여도 분해 — it_contributions[].weighted
    sim_bd = contribution_breakdown(rows, "similarity")
    contrib_card = card(
        f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-xs">유사도 기여도 분해</h2>'
        f'<p class="font-body-sm text-body-sm text-on-surface-variant mt-0 mb-md">'
        f'막대 길이 = 유사도 점수, 색 구간 = IT 항목별 가중 기여(weighted). '
        f'재사용률을 어떤 항목이 견인하는지 분해합니다.</p>{sim_bd}') if sim_bd else ""

    # 비용 카드
    cost_cards = []
    for r in rows:
        c = r["cost"]
        cost_cards.append(card(
            f'<div class="flex items-center justify-between mb-sm">'
            f'<h3 class="font-label-md text-label-md uppercase text-primary m-0">{esc(r["code"])}</h3>'
            f'{badge(str(int(c["discount"]*100))+"% 절감", "#e8f0fe", "#1967d2")}</div>'
            f'<div class="font-headline-md text-headline-md text-primary">{fmt_num(c["build"])} '
            f'<span class="font-body-sm text-body-sm text-text-secondary">{esc(c["unit"])}</span></div>'
            f'<div class="font-body-sm text-body-sm text-on-surface-variant mt-xs">'
            f'기간 {fmt_num(c["months"])}개월 · 연 운영 {fmt_num(c["maintenance_yr"])}</div>'
            f'<div class="mt-sm">{bar(c["build"], c["baseline_build"], "#005db7")}</div>'
            f'<div class="font-label-sm text-label-sm text-text-secondary mt-xs">'
            f'베이스라인 구축비 {fmt_num(c["baseline_build"])} 대비</div>'))
    cost_block = (f'<div><h2 class="font-headline-md text-headline-md text-primary mb-md">'
                  f'구축비·기간 추정 (유사도 기반 절감 적용)</h2>'
                  f'<div class="grid grid-cols-1 md:grid-cols-3 gap-md">{"".join(cost_cards)}</div></div>')

    matrix = card(
        f'<h2 class="font-headline-md text-headline-md text-primary m-0 mb-md">시스템 정합도 매트릭스</h2>'
        f'{metric_matrix(rpt, TAB_SYSTEM, "match")}')
    insights = insight_list(rpt, TAB_SYSTEM, "it")
    insights_block = (f'<div><h2 class="font-headline-md text-headline-md text-primary mb-md">'
                      f'시스템 인사이트</h2>{insights}</div>') if insights else ""
    return f"{sim_chart}{contrib_card}{cost_block}{matrix}{insights_block}"


TAB_BUILDERS = {
    "summary": tab_summary, "market": tab_market, "regulation": tab_regulation,
    "product": tab_product, "system": tab_system,
}

REGION_NAME = {"EU": ("유럽", "Europe"), "AMERICAS": ("미주", "Americas"),
               "APAC": ("아시아·태평양", "Asia-Pacific")}


# ─────────────────────────────────────────────────────────────────────────────
# HTML 렌더 — 템플릿 읽어서 플레이스홀더 치환
# ─────────────────────────────────────────────────────────────────────────────
TPL_PATH = os.path.join(BASE, "templates", "region_report_template.html")


def render_html(rpt):
    region = rpt.get("region", "")
    ko, en = REGION_NAME.get(region, (region, region))
    title = f"{ko}({en}) 권역 Quick-Win 분석 보고서"
    bo = rpt.get("based_on", {})
    cv = ", ".join(f"{k}:{v}" for k, v in (bo.get("country_versions") or {}).items())

    nav = "".join(
        f'<button data-tab="{key}" onclick="showTab(\'{key}\')" '
        f'class="tab-btn py-md font-label-md text-label-md border-b-2 whitespace-nowrap '
        f'flex items-center gap-xs transition-colors '
        f'{"text-primary border-primary" if i==0 else "text-on-surface-variant border-transparent hover:text-primary"}">'
        f'<span class="material-symbols-outlined text-[18px]">{icon}</span>{ko_t} '
        f'<span class="opacity-60">{en_t}</span></button>'
        for i, (key, ko_t, en_t, icon) in enumerate(TABS))

    panels = ""
    for i, (key, ko_t, en_t, icon) in enumerate(TABS):
        inner = TAB_BUILDERS[key](rpt)
        panels += (f'<section data-panel="{key}" class="tab-panel flex-col gap-xl '
                   f'{"flex" if i==0 else "hidden"}">{inner}</section>')

    with open(TPL_PATH, encoding="utf-8") as f:
        tpl = f.read()

    bv = ", ".join(f"{k}:{v}" for k, v in (bo.get("baseline_versions") or {}).items())
    footer_meta = (f"기반 데이터 — internal v{esc(bo.get('internal_version', '-'))} · "
                   f"schema v{esc(bo.get('schema_version', '-'))} · 국가 {esc(cv)}"
                   + (f" · 베이스라인 {esc(bv)}" if bv else ""))

    return (tpl
            .replace("{{PAGE_TITLE}}", esc(title))
            .replace("{{REPORT_ID}}", esc(rpt.get("report_id", "")))
            .replace("{{CREATED_AT}}", esc(fmt_dt(rpt.get("created_at", ""))))
            .replace("{{BASELINE}}", esc(rpt.get("baseline", "")))
            .replace("{{REPORT_HEADING}}", esc(title))
            .replace("{{TAB_NAV}}", nav)
            .replace("{{TAB_PANELS}}", panels)
            .replace("{{FOOTER_META}}", footer_meta))


# ─────────────────────────────────────────────────────────────────────────────
# 입출력
# ─────────────────────────────────────────────────────────────────────────────
def load_report(region, version=None):
    outdir = os.path.join(REPORT, "region", region)
    if version:
        path = os.path.join(outdir, f"{region}_rpt_{version}.json")
    else:
        path = os.path.join(outdir, f"{region}_rpt_latest.json")
    if not os.path.exists(path):
        cand = sorted(glob.glob(os.path.join(outdir, f"{region}_rpt_*.json")))
        if not cand:
            raise SystemExit(f"[안내] region '{region}' 리포트 JSON 없음 — 먼저 region_report_generation_engine.py 실행 필요.")
        path = cand[-1]
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def render(region="EU", version=None):
    rpt, src = load_report(region, version)
    out_html = render_html(rpt)

    outdir = os.path.join(REPORT, "region", region)
    rid = rpt.get("report_id", f"{region}_rpt")
    ts = rid.split("_rpt_")[-1] if "_rpt_" in rid else "latest"
    out = os.path.join(outdir, f"{region}_rpt_{ts}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(out_html)

    print(f"[{region}] 렌더 완료 — 입력 {os.path.relpath(src, REPO)}")
    print(f"  후보 {rpt.get('candidate_count','?')}개 · 퀵윈 {rpt.get('quick_wins',[])} · 탭 {len(TABS)}개")
    print(f"→ {os.path.relpath(out, REPO)}")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    region = args[0] if args else "EU"
    version = args[1] if len(args) > 1 else None
    render(region, version)
