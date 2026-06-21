#!/usr/bin/env python3
"""권역(region) 상세화면 렌더링 엔진 (P2)

- 권역 리서치 데이터(data/research/region/<REGION>/<REGION>_latest.json)를 입력으로 받아,
  웹 디자인 스펙(architecture/design/stitch/html/P2.html, "권역 정보")에 맞춘
  완성형 standalone HTML 상세화면으로 렌더링한다.
- 구성(스펙 §4 P2): 권역명 → KPI 카드 → 기진출 국가 리스트 →
  진출 예정국 quick-win 순위(유사도/난이도/종합점수) → 권역 차트.
- 데이터 주도(region-agnostic) — 어떤 권역 리서치 데이터든 동일 로직으로 렌더.
- 입력: data/research/region/<REGION>/<REGION>_latest.json
- 출력: detail/region/<REGION>/html/<REGION>_detail_<TS>.html

⚠️ 권역 리서치 데이터·스키마는 잠정(ROADMAP 2차에서 정식화). 상세는 storage/detail/README.md.
스코어링/계산은 일절 하지 않고 "표현"만 담당한다 (관심사 분리).
포맷·차트 헬퍼는 region_report_rendering_engine(rre)을 재사용한다.
"""
import json, os, sys, glob

BASE = os.path.dirname(os.path.abspath(__file__))
# engine/rendering → app/backend  (storage가 위치한 backend 루트)
BACKEND = os.path.dirname(os.path.dirname(BASE))
STORAGE = os.path.join(BACKEND, "storage")
DATA = os.path.join(STORAGE, "data")
DETAIL = os.path.join(STORAGE, "detail")

# 같은 rendering/ 폴더의 포맷·차트 헬퍼 재사용 (중복 작성 금지)
sys.path.insert(0, BASE)
import region_report_rendering_engine as rre  # noqa: E402

TPL_PATH = os.path.join(BASE, "templates", "region_detail_template.html")


# ─────────────────────────────────────────────────────────────────────────────
# 빌더
# ─────────────────────────────────────────────────────────────────────────────
def kpi_card(k):
    icon = k.get("icon", "insights")
    label = k.get("label", "")
    value = k.get("value", "—")
    note = k.get("note", "")
    # delta 배지 (trend up=녹색, down=녹색 화살표 — 디자인 목업 기준)
    delta = k.get("delta")
    delta_html = ""
    if delta:
        arrow = "trending_up" if k.get("trend") == "up" else "trending_down"
        delta_html = (
            '<span class="font-label-sm text-label-sm text-[#006A4E] bg-[#E6F4EA] px-2 py-1 rounded flex items-center gap-[2px]">'
            f'<span class="material-symbols-outlined text-[12px]">{arrow}</span>{rre.esc(delta)}</span>')
    target = k.get("target")
    bottom = ""
    if target:
        bottom = f'<span class="font-label-sm text-label-sm text-on-surface-variant">Target: {rre.esc(target)}</span>'
    elif note:
        bottom = f'<span class="font-label-sm text-label-sm text-on-surface-variant">{rre.esc(note)}</span>'
    return (
        '<div class="bg-surface rounded-lg p-md border border-surface-border custom-shadow-level-2 flex flex-col justify-between h-[120px]">'
        '<div class="flex justify-between items-start">'
        f'<span class="font-label-md text-label-md text-on-surface-variant">{rre.esc(label)}</span>'
        f'<span class="material-symbols-outlined text-secondary text-[20px]">{rre.esc(icon)}</span></div>'
        '<div class="flex items-end justify-between">'
        f'<span class="font-headline-md text-headline-md text-primary font-bold">{rre.esc(value)}</span>'
        f'{delta_html}</div>'
        f'{bottom}</div>')


def kpi_cards(data):
    kpis = data.get("kpis", [])
    if not kpis:
        return ""
    return "".join(kpi_card(k) for k in kpis)


def entered_list(data):
    rows = data.get("entered_countries", [])
    if not rows:
        return ""
    body = "".join(
        '<tr class="border-b border-surface-border last:border-0 hover:bg-surface-variant transition-colors">'
        f'<td class="p-sm font-mono text-xs text-on-surface">{rre.esc(r.get("code", ""))}</td>'
        f'<td class="p-sm text-on-surface">{rre.esc(r.get("name_ko", ""))} '
        f'<span class="text-on-surface-variant">{rre.esc(r.get("name_en", ""))}</span></td>'
        f'<td class="p-sm">{rre.badge(r.get("status", "-"), "#e8f0fe", "#1967d2")}</td>'
        f'<td class="p-sm text-on-surface-variant">{rre.esc(r.get("solution", "—"))}</td>'
        f'<td class="p-sm text-right text-on-surface-variant">{rre.esc(r.get("since", "—"))}</td>'
        '</tr>' for r in rows)
    return (
        '<div class="bg-surface rounded-lg p-lg border border-surface-border custom-shadow-level-2">'
        '<h3 class="font-headline-md text-[18px] leading-[24px] text-primary font-bold mb-md flex items-center gap-sm">'
        '<span class="material-symbols-outlined text-secondary text-[20px]">flag</span>기진출 국가</h3>'
        '<table class="w-full text-left border-collapse font-body-sm text-body-sm">'
        '<thead><tr class="bg-surface-light border-b border-surface-border">'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">Code</th>'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">국가</th>'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">상태</th>'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">솔루션</th>'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold text-right">진출연도</th>'
        f'</tr></thead><tbody>{body}</tbody></table></div>')


def quickwin_table(data):
    """진출 예정국 quick-win 순위 — 유사도(IT준비도)/난이도(BIZ난이도)/종합점수."""
    rows = sorted(data.get("candidate_countries", []),
                  key=lambda r: r.get("quick_win_rank", 999))
    if not rows:
        return ""

    def score_cell(v):
        col = rre.score_color(v)
        return (f'<td class="p-sm w-32"><div class="flex items-center gap-sm">'
                f'<div class="flex-1">{rre.bar(v, 100, col)}</div>'
                f'<span class="font-label-md text-label-md font-semibold w-8 text-right" style="color:{col}">{rre.fmt_num(round(v,1))}</span>'
                f'</div></td>')

    def diff_cell(v):
        # 난이도는 낮을수록 좋음 → ease(100-v) 색
        col = rre.score_color(100 - v)
        return (f'<td class="p-sm w-32"><div class="flex items-center gap-sm">'
                f'<div class="flex-1">{rre.bar(v, 100, col)}</div>'
                f'<span class="font-label-md text-label-md font-semibold w-8 text-right" style="color:{col}">{rre.fmt_num(round(v,1))}</span>'
                f'</div></td>')

    body = "".join(
        '<tr class="border-b border-surface-border last:border-0 hover:bg-surface-variant transition-colors">'
        f'<td class="p-sm font-label-md text-label-md text-primary font-bold">{rre.esc(r.get("quick_win_rank", "—"))}</td>'
        f'<td class="p-sm text-on-surface whitespace-nowrap">{rre.esc(r.get("name_ko", ""))} '
        f'<span class="font-mono text-xs text-on-surface-variant">{rre.esc(r.get("code", ""))}</span></td>'
        f'{score_cell(r.get("similarity", 0))}'
        f'{diff_cell(r.get("difficulty", 0))}'
        f'{score_cell(r.get("composite_score", 0))}'
        f'<td class="p-sm">{rre.badge("퀵윈" if r.get("quick_win") else r.get("quadrant", "-"), "#e6f4ea" if r.get("quick_win") else "#eef0f2", "#137333" if r.get("quick_win") else "#555555")}</td>'
        '</tr>' for r in rows)
    return (
        '<div class="bg-surface rounded-lg p-lg border border-surface-border custom-shadow-level-2">'
        '<h3 class="font-headline-md text-[18px] leading-[24px] text-primary font-bold mb-md flex items-center gap-sm">'
        '<span class="material-symbols-outlined text-secondary text-[20px]">leaderboard</span>진출 예정국 Quick-Win 순위</h3>'
        '<table class="w-full text-left border-collapse font-body-sm text-body-sm">'
        '<thead><tr class="bg-surface-light border-b border-surface-border">'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">#</th>'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">국가</th>'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">IT 준비도(유사도)</th>'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">BIZ 난이도</th>'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">종합점수</th>'
        '<th class="p-sm font-label-md text-label-md text-outline font-semibold">판정</th>'
        f'</tr></thead><tbody>{body}</tbody></table></div>')


def perf_chart(data):
    """권역 시계열 지표 차트 카드."""
    blocks = []
    for it in data.get("items", []):
        ts = it.get("timeseries") or {}
        svg = rre.line_chart(ts.get("history"), ts.get("forecast"))
        if not svg:
            continue
        val = rre.fmt_value(it) if it.get("value") is not None else ""
        blocks.append(
            '<div class="bg-surface rounded-lg p-lg border border-surface-border custom-shadow-level-2 flex flex-col">'
            '<div class="flex justify-between items-center mb-md">'
            f'<h3 class="font-headline-md text-[18px] leading-[24px] text-primary font-bold">{rre.esc(it["item"])}</h3>'
            f'<span class="font-label-sm text-label-sm text-secondary bg-secondary-fixed px-2 py-0.5 rounded">{rre.esc(val)}</span></div>'
            f'<div class="h-40 w-full overflow-hidden">{svg}</div>'
            + (f'<p class="font-body-sm text-body-sm text-on-surface-variant mt-md">{rre.esc(it.get("insight",""))}</p>' if it.get("insight") else "")
            + '</div>')
    if not blocks:
        return ""
    return '<div class="grid grid-cols-1 md:grid-cols-2 gap-md">' + "".join(blocks) + "</div>"


# ─────────────────────────────────────────────────────────────────────────────
# HTML 렌더
# ─────────────────────────────────────────────────────────────────────────────
def render_html(data):
    code = data.get("code", "")
    en = data.get("region", code)
    ko = data.get("region_ko", "")
    title = f"{ko}({en}) 권역 상세 — 진출 진단"
    footer = (f"리서치 데이터 — {rre.esc(code)} · schema v{rre.esc(data.get('schema_version', '-'))} · "
              f"조사 {rre.esc(rre.fmt_dt(data.get('fetched_at', '')))} {rre.freshness_badge(data.get('fetched_at', ''))}")

    with open(TPL_PATH, encoding="utf-8") as f:
        tpl = f.read()

    return (tpl
            .replace("{{PAGE_TITLE}}", rre.esc(title))
            .replace("{{REGION_EN}}", rre.esc(en))
            .replace("{{REGION_KO}}", rre.esc(ko))
            .replace("{{KPI_CARDS}}", kpi_cards(data))
            .replace("{{ENTERED_LIST}}", entered_list(data))
            .replace("{{QUICKWIN_TABLE}}", quickwin_table(data))
            .replace("{{PERF_CHART}}", perf_chart(data))
            .replace("{{FOOTER_META}}", footer))


# ─────────────────────────────────────────────────────────────────────────────
# 입출력
# ─────────────────────────────────────────────────────────────────────────────
def load_detail(region, version=None):
    datadir = os.path.join(DATA, "research", "region", region)
    if version:
        path = os.path.join(datadir, f"{region}_{version}.json")
    else:
        path = os.path.join(datadir, f"{region}_latest.json")
    if not os.path.exists(path):
        cand = sorted(glob.glob(os.path.join(datadir, f"{region}_*.json")))
        if not cand:
            raise SystemExit(f"[안내] region '{region}' 리서치 데이터 없음 — data/research/region/{region}/ 확인 필요 (잠정 스키마, README 참조).")
        path = cand[-1]
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def render(region="EU", version=None):
    data, src = load_detail(region, version)
    out_html = render_html(data)

    outdir = os.path.join(DETAIL, "region", region, "html")
    os.makedirs(outdir, exist_ok=True)
    ts = (data.get("fetched_at") or "latest").replace(":", "").replace("+", "_")
    out = os.path.join(outdir, f"{region}_detail_{ts}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(out_html)

    print(f"[{region}] 권역 상세화면 렌더 완료 — 입력 {os.path.relpath(src, STORAGE)}")
    print(f"  KPI {len(data.get('kpis', []))}개 · 기진출 {len(data.get('entered_countries', []))}개 · 후보 {len(data.get('candidate_countries', []))}개")
    print(f"→ {os.path.relpath(out, STORAGE)}")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    region = args[0] if args else "EU"
    version = args[1] if len(args) > 1 else None
    render(region, version)
