#!/usr/bin/env python3
"""rendering 공유 표현/차트/포맷 헬퍼 (detail·report 렌더러 공용)

이 모듈은 계산을 하지 않고 "표현"만 담당한다(관심사 분리). country/region 양쪽
상세화면(detail) 렌더러가 `import render_helpers as rre`로 이 헬퍼를 재사용한다
(중복 작성 금지).

제공 헬퍼:
- 디자인 토큰: TOK (Kinetic Enterprise 팔레트, architecture/design/stitch/DESIGN.md)
- 포맷: esc · fmt_num · fmt_value · fmt_dt · freshness_badge
- 배지: badge · conf_badge · gate_badge
- 점수/막대: score_color · bar
- 접근성: sr_table · figure
- SVG 차트: vbar_chart · quadrant_chart · line_chart · stacked_bar ·
  contribution_breakdown · bullet_chart · radar_chart · share_bars
- 카드/섹션: card · section_title
"""
import html, datetime, math, re


# ─────────────────────────────────────────────────────────────────────────────
# Kinetic Enterprise 디자인 토큰 미러 (architecture/design/stitch/DESIGN.md)
#   inline SVG·style= 는 Tailwind 클래스가 안 먹으므로, 디자인 토큰값을 여기서 단일
#   상수로 들고 매직 hex 리터럴 대신 참조한다(출처 일원화 — 값은 DESIGN.md와 동일).
#   신호색(success/info/warn/error)은 기존 차트가 쓰던 Google 신호 팔레트를 유지한다.
# ─────────────────────────────────────────────────────────────────────────────
TOK = {
    "primary": "#00204e", "secondary": "#005db7", "on_surface": "#1b1c1c",
    "text_secondary": "#555555", "border": "#DCDCDC", "outline": "#747782",
    "muted": "#9aa0aa", "surface": "#fbf9f9", "white": "#ffffff",
    "success": "#137333", "info": "#1967d2", "warn": "#b06000", "error": "#c5221f",
}


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
        c, t = TOK["success"], "🟢 최신"
    elif days <= 90:
        c, t = TOK["warn"], f"🟡 {days}일 경과"
    else:
        c, t = TOK["error"], "🔴 재조사 권장"
    return badge(t, c + "1a", c)


# 사분면/신뢰도/게이트 색 토큰
QUAD_COLOR = {
    "즉시 진출": TOK["success"], "선별 진출": TOK["info"],
    "기회 탐색": TOK["warn"], "JV/제휴 필요": TOK["error"],
}
CONF_COLOR = {"상": TOK["success"], "중": TOK["warn"], "하": TOK["error"]}
GATE_COLOR = {"PASS": ("#e6f4ea", TOK["success"]), "FLAG": ("#fef7e0", TOK["warn"]),
              "FAIL": ("#fce8e6", TOK["error"])}


def badge(text, bg, fg):
    return (f'<span class="px-2 py-1 rounded-md font-label-sm text-label-sm '
            f'whitespace-nowrap" style="background:{bg};color:{fg}">{esc(text)}</span>')


def conf_badge(c):
    fg = CONF_COLOR.get(c, TOK["text_secondary"])
    return badge(f"신뢰도 {c}", fg + "1a", fg)


def gate_badge(result):
    bg, fg = GATE_COLOR.get(result, ("#eee", "#555"))
    return badge(result, bg, fg)


def score_color(v):
    """0-100 점수 → 신호색."""
    return (TOK["success"] if v >= 70 else TOK["info"] if v >= 50
            else TOK["warn"] if v >= 35 else TOK["error"])


def bar(value, vmax=100, color=None, label=None):
    """수평 진행 막대. label 제공 시 부모에 role=img+aria-label(SR 접근성)."""
    color = color or TOK["secondary"]
    pct = 0 if not vmax else max(0, min(100, value / vmax * 100))
    a11y = f' role="img" aria-label="{esc(label)}"' if label else ""
    return (f'<div class="w-full h-base bg-surface-border rounded-full overflow-hidden"{a11y}>'
            f'<div class="h-full rounded-full" style="width:{pct:.0f}%;background:{color}"></div></div>')


# ─────────────────────────────────────────────────────────────────────────────
# 접근성 헬퍼 — SVG 차트 표 대체본 / figure 래퍼 (스크린리더 대응)
#   charts.csv: line=AA, bar=AAA여도 "값 표/데이터 표 제공" 권장 → 모든 차트에 적용.
# ─────────────────────────────────────────────────────────────────────────────
def sr_table(headers, rows, caption=""):
    """스크린리더 전용 데이터 표. headers=[..], rows=[[..], ..]. (sr-only 클래스로 시각 숨김)"""
    if not rows:
        return ""
    cap = f'<caption>{esc(caption)}</caption>' if caption else ""
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<table class="sr-only">{cap}<thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table>')


def figure(svg, label, table=""):
    """SVG 차트를 figure로 감싸고 접근성 라벨 + 표 대체본을 동반."""
    if not svg:
        return ""
    return (f'<figure class="m-0" role="group" aria-label="{esc(label)}">{svg}{table}</figure>')


# ─────────────────────────────────────────────────────────────────────────────
# SVG 차트
# ─────────────────────────────────────────────────────────────────────────────
def vbar_chart(series, vmax=100, height=180, unit="", title="막대 비교 차트"):
    """세로 막대 비교 차트. series=[(label, value, color)]. 접근성 표 대체본 동반."""
    if not series:
        return ""
    n = len(series)
    bw, gap, pad = 54, 28, 28
    w = pad * 2 + n * bw + (n - 1) * gap
    h = height
    base = h - 34
    top = 16
    # y축 가이드라인(0·중간·최대) — 스케일 가독성
    grid = []
    for frac in (0.0, 0.5, 1.0):
        gy = base - frac * (base - top)
        grid.append(
            f'<line x1="{pad-8}" y1="{gy:.1f}" x2="{w-pad+8}" y2="{gy:.1f}" '
            f'stroke="{TOK["border"]}" stroke-width="1" '
            f'{"" if frac == 0 else "stroke-dasharray=&quot;3 3&quot;"}/>'
            f'<text x="{pad-12}" y="{gy+4:.1f}" text-anchor="end" font-size="10" '
            f'fill="{TOK["text_secondary"]}">{fmt_num(round(vmax*frac))}</text>')
    bars = []
    for i, (label, val, color) in enumerate(series):
        x = pad + i * (bw + gap)
        bh = 0 if not vmax else max(2, (val / vmax) * (base - top))
        y = base - bh
        bars.append(
            f'<rect x="{x}" y="{y:.1f}" width="{bw}" height="{bh:.1f}" rx="4" fill="{color}"/>'
            f'<text x="{x+bw/2}" y="{y-6:.1f}" text-anchor="middle" font-size="13" '
            f'font-weight="700" fill="{TOK["on_surface"]}">{fmt_num(val)}{esc(unit)}</text>'
            f'<text x="{x+bw/2}" y="{base+18}" text-anchor="middle" font-size="12" '
            f'fill="{TOK["text_secondary"]}">{esc(label)}</text>')
    svg = (f'<svg viewBox="0 0 {w} {h}" class="w-full" style="max-height:{h}px" '
           f'role="img" aria-label="{esc(title)}" preserveAspectRatio="xMidYMid meet">'
           f'<title>{esc(title)}</title>'
           f'{"".join(grid)}{"".join(bars)}</svg>')
    tbl = sr_table(["항목", "값"],
                   [[lbl, f"{fmt_num(val)}{unit}"] for lbl, val, _ in series],
                   caption=title)
    return figure(svg, title, tbl)


def quadrant_chart(rows):
    """매력도(x) × 난이도(y, 위쪽이 낮음) 사분면 버블. 버블=구축비, 색=퀵윈. 표 대체본 동반."""
    title = "매력도 × 진입난이도 사분면"
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
        col = TOK["secondary"] if r["quick_win"] else TOK["muted"]
        pts.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" fill="{col}" '
            f'fill-opacity="0.78" stroke="{TOK["white"]}" stroke-width="2"/>'
            f'<text x="{cx:.1f}" y="{cy+4:.1f}" text-anchor="middle" font-size="12" '
            f'font-weight="700" fill="{TOK["white"]}">{esc(r["code"])}</text>')
    # 사분면 라벨
    labels = [
        (sx(75), sy(25), "즉시 진출"), (sx(25), sy(25), "기회 탐색"),
        (sx(75), sy(78), "선별 진출"), (sx(25), sy(78), "JV/제휴 필요"),
    ]
    lab = "".join(f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle" '
                  f'font-size="11" fill="{TOK["muted"]}" font-weight="600">{esc(t)}</text>'
                  for lx, ly, t in labels)
    svg = (f'<svg viewBox="0 0 {w} {h}" class="w-full" role="img" aria-label="{esc(title)}" '
           f'preserveAspectRatio="xMidYMid meet"><title>{esc(title)}</title>'
           f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="{TOK["white"]}" '
           f'stroke="{TOK["border"]}"/>'
           f'<line x1="{mx:.0f}" y1="{y0}" x2="{mx:.0f}" y2="{y1}" stroke="{TOK["border"]}" stroke-dasharray="4 4"/>'
           f'<line x1="{x0}" y1="{my:.0f}" x2="{x1}" y2="{my:.0f}" stroke="{TOK["border"]}" stroke-dasharray="4 4"/>'
           f'{lab}{"".join(pts)}'
           f'<text x="{(x0+x1)/2:.0f}" y="{h-12}" text-anchor="middle" font-size="12" '
           f'fill="{TOK["text_secondary"]}">매력도 →</text>'
           f'<text x="14" y="{(y0+y1)/2:.0f}" text-anchor="middle" font-size="12" '
           f'fill="{TOK["text_secondary"]}" transform="rotate(-90 14 {(y0+y1)/2:.0f})">← 진입난이도(낮을수록 위)</text>'
           f'</svg>')
    tbl = sr_table(["국가", "매력도", "난이도", "사분면", "퀵윈"],
                   [[r["code"], r["attractiveness"], r["difficulty"],
                     r.get("quadrant", "-"), "예" if r["quick_win"] else "아니오"]
                    for r in rows], caption=title)
    return figure(svg, title, tbl)


def line_chart(history, forecast, color=None, show_axis=True, unit="", title="시계열 추이"):
    """시계열 라인차트(실적+전망). history/forecast=[{year,value}].
    show_axis=True면 연도(x)·최소/최대(y) 라벨 + 실적/전망 범례를 SVG 안에 표기.
    표 대체본(sr_table)을 동반해 스크린리더 접근성 확보."""
    color = color or TOK["primary"]
    pts_all = (history or []) + (forecast or [])
    if len(pts_all) < 2:
        return ""
    if show_axis:
        w, h = 300, 132
        pad_l, pad_r, pad_t, pad_b = 30, 8, 22, 20
    else:
        w, h = 300, 96
        pad_l = pad_r = pad_t = pad_b = 8
    xs = [p["year"] for p in pts_all]
    ys = [p["value"] for p in pts_all]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    def X(x): return pad_l + (0 if xmax == xmin else (x - xmin) / (xmax - xmin)) * (w - pad_l - pad_r)
    def Y(y): return (h - pad_b) - (0 if ymax == ymin else (y - ymin) / (ymax - ymin)) * (h - pad_t - pad_b)
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
    axis = ""
    if show_axis:
        ts_, bs_ = TOK["text_secondary"], 10
        axis = (
            # y 최대/최소
            f'<text x="{pad_l-4}" y="{Y(ymax)+3:.1f}" text-anchor="end" font-size="{bs_}" '
            f'fill="{ts_}">{fmt_num(ymax)}{esc(unit)}</text>'
            f'<text x="{pad_l-4}" y="{Y(ymin)+3:.1f}" text-anchor="end" font-size="{bs_}" '
            f'fill="{ts_}">{fmt_num(ymin)}{esc(unit)}</text>'
            # x 시작/끝 연도
            f'<text x="{X(xmin):.1f}" y="{h-6}" text-anchor="start" font-size="{bs_}" '
            f'fill="{ts_}">{esc(xmin)}</text>'
            f'<text x="{X(xmax):.1f}" y="{h-6}" text-anchor="end" font-size="{bs_}" '
            f'fill="{ts_}">{esc(xmax)}</text>'
            # 범례 (실적 실선 / 전망 점선)
            f'<line x1="{pad_l}" y1="10" x2="{pad_l+16}" y2="10" stroke="{color}" stroke-width="2"/>'
            f'<text x="{pad_l+20}" y="13" font-size="{bs_}" fill="{ts_}">실적</text>'
            f'<line x1="{pad_l+58}" y1="10" x2="{pad_l+74}" y2="10" stroke="{color}" '
            f'stroke-width="2" stroke-dasharray="4 3" opacity="0.6"/>'
            f'<text x="{pad_l+78}" y="13" font-size="{bs_}" fill="{ts_}">전망</text>')
    svg = (f'<svg viewBox="0 0 {w} {h}" class="w-full" style="max-height:{h}px" '
           f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
           f'{axis}{"".join(segs)}{dots}</svg>')
    tbl = sr_table(["연도", "값", "구분"],
                   [[p["year"], f'{fmt_num(p["value"])}{unit}',
                     "실적" if p in (history or []) else "전망"] for p in pts_all],
                   caption=title)
    return figure(svg, title, tbl)


# ─────────────────────────────────────────────────────────────────────────────
# 기여도 분해 (누적 수평 막대) — *_contributions[].weighted 표현
#   막대 길이 = 해당 축 점수(0~100), 색 구간 = 항목별 가중 기여(weighted).
#   계산은 하지 않고 리포트가 이미 박아둔 weighted를 그대로 쌓는다.
# ─────────────────────────────────────────────────────────────────────────────
CONTRIB_PALETTE = ["#00204e", "#005db7", "#1967d2", "#4a90d9", "#7cb342",
                   "#00897b", "#b06000", "#8e44ad", "#c5221f", "#5f6368"]


def _contrib_color_map(names):
    return {n: CONTRIB_PALETTE[i % len(CONTRIB_PALETTE)] for i, n in enumerate(names)}


def stacked_bar(segments, scale=100, height=16, label=None):
    """누적 수평 막대. segments=[(label, value, color)]. width%는 scale 기준.
    label 제공 시 부모에 role=img+aria-label(SR이 세그먼트 합을 읽도록)."""
    parts = []
    for seg_label, val, color in segments:
        if not val or val <= 0:
            continue
        wpct = max(0.0, min(100.0, val / scale * 100))
        parts.append(f'<div style="width:{wpct:.1f}%;background:{color}" '
                     f'title="{esc(seg_label)}: {fmt_num(val)}" class="h-full"></div>')
    inner = "".join(parts) or '<div class="h-full w-0"></div>'
    if label is None:
        label = "; ".join(f"{lbl} {fmt_num(val)}" for lbl, val, _ in segments if val and val > 0)
    a11y = f' role="img" aria-label="{esc(label)}"' if label else ""
    return (f'<div class="flex w-full rounded-full overflow-hidden bg-surface-border" '
            f'style="height:{height}px"{a11y}>{inner}</div>')


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
            f'<div class="flex-1">{stacked_bar(segs, label=esc(r["code"]) + " 기여 분해: " + "; ".join(f"{l} {fmt_num(v)}" for l, v, _ in segs))}</div>'
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
# 신규 차트 — gauge/bullet · radar · share bars
#   charts.csv 근거: KPI vs target → bullet(AAA)/gauge(AA), 다축 비교 → radar,
#   비율/점유율 → 정렬 bar(AAA) (pie/donut=C등급 금지). 모두 표 대체본 동반.
#   "계산은 하지 않고 표현만" 원칙 — 입력 수치를 그대로 시각화.
# ─────────────────────────────────────────────────────────────────────────────
def _to_number(v):
    """'94%' · '€4.2B' · 60.1 등에서 첫 수치를 float로 추출. 실패 시 None."""
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", v.replace(",", ""))
    return float(m.group()) if m else None


def bullet_chart(value, target, unit="", title="목표 대비 KPI", vmax=None):
    """불릿 차트(KPI vs target) — charts.csv #18 AAA. 수치·목표대비% 항상 텍스트 표기.
    value/target는 수치 또는 '94%' 같은 문자열 모두 허용."""
    v = _to_number(value)
    t = _to_number(target)
    if v is None:
        return ""
    scale = vmax or max(x for x in (v, t, 1) if x is not None) * 1.15
    w, h = 280, 46
    pad_l, pad_r = 8, 8
    track_y, track_h = 14, 12
    def X(x): return pad_l + max(0.0, min(1.0, x / scale)) * (w - pad_l - pad_r)
    meets = (t is None) or (v >= t)
    fill = TOK["success"] if meets else TOK["warn"]
    bar_w = X(v) - pad_l
    tgt = ""
    pct_txt = ""
    if t is not None:
        tx = X(t)
        tgt = (f'<line x1="{tx:.1f}" y1="{track_y-4}" x2="{tx:.1f}" y2="{track_y+track_h+4}" '
               f'stroke="{TOK["primary"]}" stroke-width="2"/>')
        pct = (v / t * 100) if t else 0
        pct_txt = f' · 목표대비 {fmt_num(round(pct))}%'
    label_val = f'{fmt_num(v)}{esc(unit)}'
    label_tgt = f' / 목표 {fmt_num(t)}{esc(unit)}' if t is not None else ''
    svg = (f'<svg viewBox="0 0 {w} {h}" class="w-full" style="max-height:{h}px" '
           f'role="img" aria-label="{esc(title)}: {label_val}{label_tgt}{pct_txt}">'
           f'<title>{esc(title)}</title>'
           f'<rect x="{pad_l}" y="{track_y}" width="{w-pad_l-pad_r}" height="{track_h}" '
           f'rx="6" fill="{TOK["border"]}"/>'
           f'<rect x="{pad_l}" y="{track_y}" width="{max(0,bar_w):.1f}" height="{track_h}" '
           f'rx="6" fill="{fill}"/>{tgt}'
           f'<text x="{pad_l}" y="10" font-size="11" fill="{TOK["text_secondary"]}">{label_val}'
           f'{esc(label_tgt)}{esc(pct_txt)}</text></svg>')
    rows = [["현재", label_val]]
    if t is not None:
        rows.append(["목표", f'{fmt_num(t)}{unit}'])
    tbl = sr_table(["구분", "값"], rows, caption=title)
    return figure(svg, title, tbl)


def radar_chart(axes, series, title="다축 비교", vmax=100):
    """레이더(스파이더) 차트 — 다축 점수 비교. charts.csv 레이더 행.
    axes=[축이름..]; series=[(이름, [값..], 색)] (값 길이 = axes 길이). 표 대체본 동반."""
    n = len(axes)
    if n < 3 or not series:
        return ""
    w = h = 260
    cx, cy = w / 2, h / 2 + 6
    rad = 92
    def pt(i, val):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        rr = max(0.0, min(1.0, val / vmax)) * rad
        return (cx + rr * math.cos(ang), cy + rr * math.sin(ang))
    # 격자(동심 다각형) + 축선
    grid = []
    for ring in (0.5, 1.0):
        poly = " ".join(f"{cx + ring*rad*math.cos(-math.pi/2+2*math.pi*i/n):.1f},"
                        f"{cy + ring*rad*math.sin(-math.pi/2+2*math.pi*i/n):.1f}" for i in range(n))
        grid.append(f'<polygon points="{poly}" fill="none" stroke="{TOK["border"]}" stroke-width="1"/>')
    spokes, labels = [], []
    for i, ax in enumerate(axes):
        ex = cx + rad * math.cos(-math.pi/2 + 2*math.pi*i/n)
        ey = cy + rad * math.sin(-math.pi/2 + 2*math.pi*i/n)
        spokes.append(f'<line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" '
                      f'stroke="{TOK["border"]}" stroke-width="1"/>')
        lx = cx + (rad+14) * math.cos(-math.pi/2 + 2*math.pi*i/n)
        ly = cy + (rad+14) * math.sin(-math.pi/2 + 2*math.pi*i/n)
        anchor = "middle" if abs(lx-cx) < 8 else ("start" if lx > cx else "end")
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="10" '
                      f'fill="{TOK["text_secondary"]}">{esc(ax)}</text>')
    polys, legend = [], []
    for name, vals, color in series:
        pts = [pt(i, vals[i] if i < len(vals) else 0) for i in range(n)]
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        polys.append(f'<polygon points="{poly}" fill="{color}" fill-opacity="0.18" '
                     f'stroke="{color}" stroke-width="2"/>')
        legend.append(f'<span class="flex items-center gap-xs font-label-sm text-label-sm text-text-secondary">'
                      f'<span class="w-3 h-3 rounded-sm shrink-0" style="background:{color}"></span>{esc(name)}</span>')
    svg = (f'<svg viewBox="0 0 {w} {h}" class="w-full" style="max-height:{h}px" '
           f'role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>'
           f'{"".join(grid)}{"".join(spokes)}{"".join(polys)}{"".join(labels)}</svg>')
    legend_html = (f'<div class="flex flex-wrap gap-md justify-center mt-xs">{"".join(legend)}</div>'
                   if len(series) > 1 else "")
    tbl = sr_table(["축"] + [s[0] for s in series],
                   [[axes[i]] + [fmt_num(s[1][i]) if i < len(s[1]) else "—" for s in series]
                    for i in range(n)], caption=title)
    return figure(svg + legend_html, title, tbl)


def share_bars(rows, unit="%", title="점유율", vmax=None):
    """점유율/비율 정렬 수평막대 — charts.csv #2 AAA(pie 대신 권장). rows=[(label, value)].
    값 내림차순 정렬, 값 라벨 항상 표기. 표 대체본 동반."""
    data = [(lbl, _to_number(v)) for lbl, v in rows]
    data = [(lbl, v) for lbl, v in data if v is not None]
    if not data:
        return ""
    data.sort(key=lambda x: x[1], reverse=True)
    scale = vmax or max(v for _, v in data) or 1
    items = []
    for lbl, v in data:
        items.append(
            f'<div class="flex items-center gap-sm">'
            f'<span class="font-body-sm text-body-sm text-on-surface w-28 shrink-0 truncate" '
            f'title="{esc(lbl)}">{esc(lbl)}</span>'
            f'<div class="flex-1">{bar(v, scale, TOK["secondary"], label=f"{esc(lbl)} {fmt_num(v)}{unit}")}</div>'
            f'<span class="font-label-md text-label-md text-primary font-semibold w-12 text-right shrink-0">'
            f'{fmt_num(v)}{esc(unit)}</span></div>')
    tbl = sr_table(["항목", "값"], [[lbl, f"{fmt_num(v)}{unit}"] for lbl, v in data], caption=title)
    return (f'<div role="group" aria-label="{esc(title)}" class="flex flex-col gap-sm">'
            f'{"".join(items)}</div>{tbl}')


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
