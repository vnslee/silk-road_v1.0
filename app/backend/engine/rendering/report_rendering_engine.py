#!/usr/bin/env python3
"""
Report Rendering Engine (U5) — 보고서 JSON → 완성형 HTML (PDF용).

U3(country)·U4(region) 가 생산한 동일 형태 보고서 JSON
  {report_id, title, target, based_on, tabs:[{tab,name,blocks:[block,...]}]}
을 받아 Kinetic Enterprise(DESIGN.md) 스타일의 self-contained HTML 로 렌더한다.

설계 원칙:
  - 계산하지 않는다(관심사 분리). 표현만.
  - nature → 차트 (render_req §1), source_flag → 뱃지 (render_req §2).
  - "배지 없는 수치 = 렌더 오류" → 모든 데이터 블록에 source_flag 뱃지를 단다.
  - weasyprint(JS 미실행) 호환: 외부 JS 0, 차트는 인라인 SVG/CSS.

입력: report/<country|region>/<CODE>/<ID>/data/<...>.json
출력: report/<country|region>/<CODE>/<ID>/html/<...>.html
"""

import html
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
STORAGE = BASE.parent.parent / "storage"
REPORT = STORAGE / "report"
TEMPLATE = BASE / "templates" / "report_template.html"

FLAG_LABEL = {"EXT": "외부조사", "INT": "내부자료", "CALC": "계산값",
              "AI": "AI 인사이트", "NEWS": "외부이슈"}


def esc(s):
    return html.escape(str(s), quote=True)


def flag_badge(flag):
    """source_flag → 신뢰도 뱃지. 모든 데이터 블록 필수(배지 없는 수치=오류)."""
    f = flag if flag in FLAG_LABEL else "EXT"
    return f'<span class="flag flag-{f}">{esc(FLAG_LABEL[f])}</span>'


def fmt_num(v):
    if isinstance(v, bool):
        return "예" if v else "아니오"
    if isinstance(v, (int, float)):
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        return f"{v:,}" if isinstance(v, int) else f"{v:,.2f}"
    return esc(v)


# ── nature 별 값 렌더러 ───────────────────────────────────────────────────
def render_single_value(b):
    v = b.get("value")
    if v is None:
        note = b.get("source", {}).get("note", "조사 필요")
        return f'<div class="kpi-value placeholder">— {esc(note)}</div>'
    return f'<div class="kpi-value">{fmt_num(v)}</div>'


def render_timeseries(b):
    """history 실선 + forecast 점선 인라인 SVG."""
    v = b.get("value") or {}
    hist = v.get("history", []) if isinstance(v, dict) else []
    fore = v.get("forecast", []) if isinstance(v, dict) else []
    pts = [(p["year"], p["value"]) for p in hist + fore if "year" in p and "value" in p]
    if not pts:
        return '<div class="kpi-value placeholder">— 추세 데이터 없음</div>'
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
    W, H, pad = 320, 120, 24

    def X(x): return pad + (0 if xmax == xmin else (x - xmin) / (xmax - xmin)) * (W - 2 * pad)
    def Y(y): return (H - pad) - (0 if ymax == ymin else (y - ymin) / (ymax - ymin)) * (H - 2 * pad)

    def path(seq):
        return " ".join(("M" if i == 0 else "L") + f"{X(x):.1f} {Y(y):.1f}"
                        for i, (x, y) in enumerate(seq))
    hist_pts = [(p["year"], p["value"]) for p in hist]
    fore_seq = ([hist_pts[-1]] if hist_pts else []) + [(p["year"], p["value"]) for p in fore]
    svg = [f'<svg class="spark" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="시계열 추이">']
    if len(hist_pts) > 1:
        svg.append(f'<path d="{path(hist_pts)}" fill="none" stroke="var(--primary)" stroke-width="2"/>')
    if len(fore_seq) > 1:
        svg.append(f'<path d="{path(fore_seq)}" fill="none" stroke="var(--secondary)" '
                   f'stroke-width="2" stroke-dasharray="4 3"/>')
    for x, y in pts:
        svg.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="2.5" fill="var(--primary)"/>')
    svg.append('</svg>')
    est = " · 추정" if (isinstance(v, dict) and v.get("estimated")) else ""
    cagr = v.get("cagr_hist") if isinstance(v, dict) else None
    cap = f'<p class="muted">{xmin}–{xmax}{est}' + (f' · CAGR {cagr}%' if cagr is not None else '') + '</p>'
    return "".join(svg) + cap


def render_ranking(b):
    rows = b.get("value")
    if not isinstance(rows, list) or not rows:
        return '<div class="kpi-value placeholder">— 데이터 없음</div>'
    # 숫자 키 자동 탐지(점수/순위)
    def numkey(r):
        for k in ("attractiveness", "quick_win_score", "value", "market_share", "score"):
            if isinstance(r, dict) and isinstance(r.get(k), (int, float)):
                return r[k]
        return None
    vals = [numkey(r) for r in rows if isinstance(r, dict)]
    vals = [x for x in vals if x is not None]
    vmax = max(vals) if vals else 100
    out = []
    for r in rows:
        if not isinstance(r, dict):
            out.append(f'<div class="rank-row"><span class="name">{esc(r)}</span></div>')
            continue
        name = r.get("country_ko") or r.get("name") or r.get("code") or "—"
        nv = numkey(r)
        if nv is not None and vmax:
            w = max(2, nv / vmax * 100)
            band = r.get("quick_win_band")
            valtxt = band if band else fmt_num(nv)
            out.append(f'<div class="rank-row"><span class="name">{esc(name)}</span>'
                       f'<span class="track"><span class="fill" style="width:{w:.0f}%"></span></span>'
                       f'<span class="val">{esc(valtxt)}</span></div>')
        else:
            out.append(f'<div class="rank-row"><span class="name">{esc(name)}</span></div>')
    return "".join(out)


def render_status_matrix(b):
    rows = b.get("value")
    if not isinstance(rows, list) or not rows:
        return '<div class="kpi-value placeholder">— 데이터 없음</div>'
    out = ['<table class="matrix"><thead><tr><th>국가</th><th>판정</th>'
           '<th>탈락 항목</th><th>보류(FLAG)</th></tr></thead><tbody>']
    for r in rows:
        passed = r.get("passed")
        cls = "" if passed else ' class="row-failed"'
        mark = ('<span class="dot-pass">● 통과</span>' if passed
                else '<span class="dot-fail">✕ 탈락</span>')
        fails = ", ".join(r.get("fail_items", [])) or "—"
        flags = ", ".join(r.get("flag_items", [])) or "—"
        nm = r.get("country_ko") or r.get("code", "—")
        out.append(f'<tr{cls}><td>{esc(nm)}</td><td>{mark}</td>'
                   f'<td>{esc(fails)}</td><td>{esc(flags)}</td></tr>')
    out.append('</tbody></table>')
    return "".join(out)


def render_news(value):
    if not isinstance(value, list) or not value:
        return '<p class="muted">조사된 이슈 없음</p>'
    out = ['<div class="news">']
    for obj in value:
        # country 보고서: 이슈 객체 / region 보고서: {code, issues:[...]}
        issues = obj.get("issues", [obj]) if "issues" in obj else [obj]
        prefix = f'[{obj["code"]}] ' if obj.get("code") else ""
        for it in issues:
            head = it.get("headline", "—")
            sw = it.get("so_what", "")
            pub = it.get("publisher", ""); date = it.get("pub_date", "")
            out.append(f'<div class="news-item"><div class="headline">{esc(prefix)}{esc(head)}</div>'
                       f'<div class="sowhat">{esc(sw)}</div>'
                       f'<div class="src">{esc(pub)} {esc(date)}</div></div>')
    out.append('</div>')
    return "".join(out)


def render_qualitative(b):
    v = b.get("value")
    key = b.get("key", "")
    if "news" in key and isinstance(v, list):
        return render_news(v)
    if v is None:
        note = b.get("source", {}).get("note", "조사 필요")
        return f'<div class="kpi-value placeholder">— {esc(note)}</div>'
    if isinstance(v, dict):
        # decision / 카드류 — key:value 줄
        parts = [f'<div class="muted"><strong>{esc(k)}</strong>: {esc(val)}</div>'
                 for k, val in v.items()]
        return "".join(parts)
    if isinstance(v, list):
        # 프로파일 카드/리스트
        chips = []
        for el in v:
            if isinstance(el, dict):
                nm = el.get("country_ko") or el.get("name") or el.get("code") or ""
                extra = el.get("quick_win_band") or ""
                chips.append(f'<span class="chip">{esc(nm)} {esc(extra)}</span>')
            else:
                chips.append(f'<span class="chip">{esc(el)}</span>')
        return '<div style="display:flex;flex-wrap:wrap;gap:8px;">' + "".join(chips) + '</div>'
    return f'<p class="muted">{esc(v)}</p>'


def render_score_multiaxis(b):
    """레이더/히트맵 대체 — 인쇄 안정 위해 축별 수평바 표로."""
    v = b.get("value")
    if isinstance(v, dict):  # {축명: 점수}
        rows = [{"name": k, "value": val} for k, val in v.items()]
        return render_ranking({"value": rows})
    if isinstance(v, list):  # [{code, similarity, difficulty}, ...]
        out = ['<table class="matrix"><thead><tr><th>국가</th>'
               '<th>유사도</th><th>난이도</th></tr></thead><tbody>']
        for r in v:
            out.append(f'<tr><td>{esc(r.get("code","—"))}</td>'
                       f'<td>{fmt_num(r.get("similarity"))}</td>'
                       f'<td>{fmt_num(r.get("difficulty"))}</td></tr>')
        out.append('</tbody></table>')
        return "".join(out)
    return '<div class="kpi-value placeholder">— 데이터 없음</div>'


def render_composition(b):
    # 비율 — 수평바로 표현(도넛 대체, 인쇄 안정)
    return render_ranking(b)


NATURE_RENDERERS = {
    "single_value": render_single_value,
    "timeseries": render_timeseries,
    "ranking": render_ranking,
    "composition": render_composition,
    "score_multiaxis": render_score_multiaxis,
    "qualitative": render_qualitative,
    "status_matrix": render_status_matrix,
}


# ── 블록 → 카드 ───────────────────────────────────────────────────────────
def render_block(b):
    nature = b.get("nature", "qualitative")
    renderer = NATURE_RENDERERS.get(nature, render_qualitative)
    body = renderer(b)
    label = esc(b.get("label", b.get("key", "")))
    badge = flag_badge(b.get("source_flag"))
    src = b.get("source") or {}
    tier = src.get("tier")
    src_line = ""
    if src.get("org"):
        ttxt = f" · Tier {tier}" if tier else ""
        src_line = f'<p class="src" style="font-size:11px;color:var(--text-secondary);margin-top:8px;">출처: {esc(src["org"])}{ttxt}</p>'
    return (f'<div class="card"><div class="block-head"><h3>{label}</h3>{badge}</div>'
            f'{body}{src_line}</div>')


def render_tab(tab, idx):
    blocks_html = "".join(render_block(b) for b in tab.get("blocks", []))
    # KPI(single_value)가 여럿이면 3-그리드, 아니면 단일 컬럼
    n_kpi = sum(1 for b in tab.get("blocks", []) if b.get("nature") == "single_value")
    grid_cls = "grid grid-3" if n_kpi >= 2 else "grid"
    anchor = f"tab-{esc(tab.get('tab',''))}"
    notes = ""
    if tab.get("notes"):
        notes = "".join(f'<p class="muted">⚠ {esc(n)}</p>' for n in tab["notes"])
    return (f'<section class="tabpanel" id="{anchor}">'
            f'<div class="tab-head"><span class="num">{esc(tab.get("tab",""))}</span>'
            f'<h2>{esc(tab.get("name",""))}</h2></div>'
            f'{notes}<div class="{grid_cls}">{blocks_html}</div></section>')


# ── 조립 ──────────────────────────────────────────────────────────────────
def render_report(report):
    is_region = report.get("report_type", "").startswith("type2")
    target = report.get("target", {})
    code = target.get("region") or target.get("country") or ""
    mark = esc(code[:2].upper())

    based = report.get("based_on", {})
    meta_bits = [f'보고서 ID: {esc(report.get("report_id",""))}']
    if based.get("internal_version"):
        meta_bits.append(f'룰셋 v{esc(based["internal_version"])}')
    meta = '<span class="dot"></span>'.join(f'<span>{m}</span>' for m in meta_bits)

    subtitle = ("권역 내 후보국 Quick-Win 진단" if is_region
                else f'기준국 {esc(target.get("base_country") or "—")} 대비 진출 비용·TCO 진단')

    def _tablink(t, i):
        active = ' class="active"' if i == 0 else ''
        return f'<a href="#tab-{esc(t.get("tab",""))}"{active}>{esc(t.get("name",""))}</a>'
    tabnav = "".join(_tablink(t, i) for i, t in enumerate(report.get("tabs", [])))
    content = "".join(render_tab(t, i) for i, t in enumerate(report.get("tabs", [])))

    actions = ('<span class="btn">PDF 다운로드</span>'
               '<span class="btn btn-solid">메일 발송</span>')
    footer = (f'<span>{esc(report.get("title",""))}</span>'
              f'<span>출처 신뢰도: 외부조사·내부자료·계산값·AI·외부이슈 — 각 수치 옆 뱃지 참조</span>')

    tpl = TEMPLATE.read_text(encoding="utf-8")
    for k, val in {
        "{{TITLE}}": esc(report.get("title", "")),
        "{{MARK}}": mark, "{{META}}": meta, "{{SUBTITLE}}": subtitle,
        "{{ACTIONS}}": actions, "{{TABNAV}}": tabnav,
        "{{CONTENT}}": content, "{{FOOTER}}": footer,
    }.items():
        tpl = tpl.replace(k, val)
    return tpl


def render_from_path(json_path):
    json_path = Path(json_path)
    report = json.loads(json_path.read_text(encoding="utf-8"))
    html_out = render_report(report)
    # data/ 형제인 html/ 로 출력
    html_dir = json_path.parent.parent / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    out = html_dir / (json_path.stem + ".html")
    out.write_text(html_out, encoding="utf-8")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: report_rendering_engine.py <report_json_path>")
        sys.exit(1)
    out = render_from_path(sys.argv[1])
    print(f"렌더: {out}")
