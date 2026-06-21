#!/usr/bin/env python3
"""
Country Report Renderer: Convert Type 1 TCO JSON to HTML

Renders Type 1 report JSON into HTML following PR1.html design template.
Implements data nature -> chart type mapping from render spec.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class CountryReportRenderer:
    """Render Type 1 (single country TCO) reports to HTML."""

    def __init__(self, report_json_path: str, template_path: Optional[str] = None):
        """Initialize renderer with report JSON.

        Args:
            report_json_path: Path to Type 1 report JSON
            template_path: Optional custom HTML template path
        """
        self.report_json_path = report_json_path
        self.template_path = template_path
        self.report_data: Optional[Dict] = None

    def load_report(self) -> bool:
        """Load report JSON file."""
        try:
            with open(self.report_json_path, 'r', encoding='utf-8') as f:
                self.report_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading report: {e}")
            return False

    def get_country_flag_url(self, country_code: str) -> str:
        """Get country flag image URL.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Flag image URL
        """
        # Placeholder - would use actual flag service
        return f"https://flagcdn.com/w160/{country_code.lower()}.png"

    def get_country_name(self, country_code: str) -> str:
        """Get full country name from code.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Country name
        """
        country_names = {
            "ES": "스페인",
            "PL": "폴란드",
            "CZ": "체코",
            "HU": "헝가리",
            "GB": "영국",
            "DE": "독일",
            "FR": "프랑스",
            "IT": "이탈리아",
            "US": "미국",
            "CA": "캐나다",
            "MX": "멕시코",
            "AU": "호주",
            "NZ": "뉴질랜드",
            "JP": "일본",
            "KR": "한국",
            "SG": "싱가포르"
        }
        return country_names.get(country_code, country_code)

    def _decision_label(self, decision_type: str, base_country_name: str) -> str:
        """Translate decision type into a human-friendly Korean label."""
        labels = {
            "baseline_system_expansion": f"권역 내 확산 ({base_country_name} 시스템)",
            "external_solution": "외부솔루션 도입",
            "hq_build": "본사 자체구축",
        }
        return labels.get(decision_type, decision_type.replace('_', ' ').title())

    def format_currency(self, amount: float, currency: str = "EUR") -> str:
        """Format currency amount.

        Args:
            amount: Numeric amount
            currency: Currency code

        Returns:
            Formatted currency string
        """
        symbols = {"EUR": "€", "GBP": "£", "USD": "$", "KRW": "₩"}
        symbol = symbols.get(currency, currency)
        # Sub-unit amounts (< 10) keep 2 decimals so 구독료 단가(0.9 등)가 1로 반올림되지 않게.
        if amount and abs(amount) < 10:
            return f"{symbol}{amount:,.2f}"
        return f"{symbol}{amount:,.0f}"

    def get_source_badge(self, source_flag: str) -> Dict[str, str]:
        """Get badge styling for source flag.

        Args:
            source_flag: Source flag (EXT/INT/CALC/AI/NEWS)

        Returns:
            Dict with label and color class
        """
        badges = {
            "EXT": {"label": "외부조사", "color": "bg-gray-100 text-gray-700 border-gray-300"},
            "INT": {"label": "내부자료", "color": "bg-blue-100 text-blue-700 border-blue-300"},
            "CALC": {"label": "계산값", "color": "bg-green-100 text-green-700 border-green-300"},
            "AI": {"label": "AI 인사이트", "color": "bg-purple-100 text-purple-700 border-purple-300"},
            "NEWS": {"label": "외부이슈", "color": "bg-orange-100 text-orange-700 border-orange-300"}
        }
        return badges.get(source_flag, {"label": source_flag, "color": "bg-gray-100 text-gray-700"})

    def _format_item_value(self, item: Dict[str, Any]) -> str:
        """Render an item value (scalar, list, or dict) as readable HTML."""
        value = item.get("value")
        unit = item.get("unit") or ""

        if value is None:
            return '<span class="text-text-secondary italic">N/A</span>'

        if isinstance(value, list):
            if value and isinstance(value[0], dict):
                rows = []
                for entry in value:
                    parts = []
                    if "rank" in entry:
                        parts.append(f'<span class="text-text-secondary">#{entry["rank"]}</span>')
                    parts.append(f'<span class="font-semibold">{entry.get("name", "")}</span>')
                    if "market_share" in entry:
                        parts.append(f'<span class="text-text-secondary">{entry["market_share"]}</span>')
                    rows.append(f'<li class="flex items-center gap-xs">{" ".join(parts)}</li>')
                return f'<ul class="flex flex-col gap-xs font-body-sm text-body-sm">{"".join(rows)}</ul>'
            return ", ".join(str(v) for v in value)

        if isinstance(value, (int, float)) and unit not in ("type", "match", "regime"):
            unit_suffix = f' <span class="text-text-secondary font-body-sm">{unit}</span>' if unit else ""
            return f'<span class="font-semibold">{value:,}</span>{unit_suffix}'

        return f'<span>{value}</span>'

    def _render_item_card(self, item: Dict[str, Any]) -> str:
        """Render a single item with value, source, and insight."""
        if item.get("status") == "missing":
            return f'''
            <div class="p-md bg-yellow-50 border border-yellow-200 rounded-lg">
                <div class="flex items-center gap-xs">
                    <span class="material-symbols-outlined text-yellow-700 text-[18px]">warning</span>
                    <span class="font-label-md text-label-md text-yellow-800">{item.get("item", "")}</span>
                </div>
                <p class="font-body-sm text-body-sm text-yellow-700 mt-xs">데이터 미수집 — 실사 단계 보강 필요</p>
            </div>
            '''

        name = item.get("item", "")
        tier = item.get("tier", "")
        tier_color = {1: "emerald", 2: "blue", 3: "yellow", 4: "gray"}.get(tier, "gray")
        source = item.get("source") or ""
        insight = item.get("insight") or ""
        ai_flag = item.get("insight_ai_generated")
        gate_result = item.get("gate_result")

        gate_badge = ""
        if gate_result:
            gate_color = {"PASS": "emerald", "FLAG": "yellow", "FAIL": "red"}.get(gate_result, "gray")
            gate_badge = f'<span class="bg-{gate_color}-100 text-{gate_color}-800 border border-{gate_color}-200 px-2 py-0.5 rounded-full font-label-sm text-label-sm uppercase">{gate_result}</span>'

        ai_badge = ""
        if ai_flag:
            ai_badge = '<span class="bg-purple-100 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full font-label-sm text-label-sm uppercase">AI</span>'

        timeseries_html = ""
        ts = item.get("timeseries")
        if isinstance(ts, dict):
            cagr_h = ts.get("cagr_hist")
            cagr_f = ts.get("cagr_forecast")
            if cagr_h is not None or cagr_f is not None:
                timeseries_html = f'''
                <div class="flex gap-md mt-xs font-label-sm text-label-sm text-text-secondary">
                    <span>CAGR(과거): <span class="font-semibold text-text-primary">{cagr_h}%</span></span>
                    <span>CAGR(전망): <span class="font-semibold text-text-primary">{cagr_f}%</span></span>
                </div>
                '''

        return f'''
        <div class="p-md bg-surface rounded-lg border border-surface-container-highest flex flex-col gap-sm">
            <div class="flex items-start justify-between gap-sm">
                <div class="flex items-center gap-xs flex-wrap">
                    <span class="font-label-md text-label-md text-text-primary uppercase tracking-wide">{name}</span>
                    <span class="bg-{tier_color}-100 text-{tier_color}-800 border border-{tier_color}-200 px-2 py-0.5 rounded-full font-label-sm text-label-sm uppercase">Tier {tier}</span>
                    {gate_badge}
                </div>
                <div class="font-body-md text-body-md text-primary text-right max-w-[60%]">{self._format_item_value(item)}</div>
            </div>
            {timeseries_html}
            <div class="border-t border-surface-container-highest pt-sm">
                <div class="flex items-center gap-xs mb-xs">
                    <span class="material-symbols-outlined text-text-secondary text-[14px]">source</span>
                    <span class="font-label-sm text-label-sm text-text-secondary uppercase">근거</span>
                </div>
                <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{source}</p>
            </div>
            <div class="bg-surface-container/60 p-sm rounded-md border-l-4 border-primary">
                <div class="flex items-center gap-xs mb-xs">
                    <span class="material-symbols-outlined text-primary text-[14px]">lightbulb</span>
                    <span class="font-label-sm text-label-sm text-primary uppercase">인사이트</span>
                    {ai_badge}
                </div>
                <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{insight}</p>
            </div>
        </div>
        '''

    def render_items_section(self, items: list, title: str = "상세 항목 및 근거",
                              icon: str = "fact_check") -> str:
        """Render a section listing detailed item cards."""
        if not items:
            return ""
        cards = "".join(self._render_item_card(it) for it in items)
        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">{icon}</span>
                <h2 class="font-headline-md text-headline-md text-primary">{title}</h2>
            </div>
            <div class="flex flex-col gap-md">
                {cards}
            </div>
        </section>
        '''

    def render_kpi_card(self, label: str, value: str, trend: Optional[str] = None,
                       trend_value: Optional[str] = None) -> str:
        """Render KPI card HTML.

        Args:
            label: Metric label
            value: Metric value
            trend: Trend icon (up/down/flat)
            trend_value: Trend percentage

        Returns:
            HTML string
        """
        trend_icons = {
            "up": ("trending_up", "text-emerald-800"),
            "down": ("trending_down", "text-accent-red"),
            "flat": ("trending_flat", "text-text-secondary")
        }
        icon, icon_class = trend_icons.get(trend, ("trending_flat", "text-text-secondary"))

        trend_html = ""
        if trend_value:
            trend_html = f'<span class="font-label-sm text-label-sm {icon_class}">{trend_value}</span>'

        return f'''
        <div class="flex flex-col p-sm bg-surface rounded-lg border border-surface-container-highest">
            <div class="flex justify-between items-start mb-xs">
                <span class="font-label-sm text-label-sm text-text-secondary uppercase">{label}</span>
                <span class="material-symbols-outlined {icon_class} text-[18px]">{icon}</span>
            </div>
            <div class="flex items-baseline gap-xs">
                <span class="font-headline-md text-headline-md text-primary">{value}</span>
                {trend_html}
            </div>
        </div>
        '''

    def _similarity_multiplier(self, score: float) -> float:
        """명세서 산식1: 종합 유사도 → 승수 % (탭1-3 입력)."""
        if score >= 90:
            return 0.50
        if score >= 80:
            return 0.60
        if score >= 70:
            return 0.70
        if score >= 60:
            return 0.80
        if score >= 50:
            return 0.90
        return 1.00

    def _multiplier_band_label(self, score: float) -> str:
        if score >= 90:
            return "유사도 90~100 → 50% 적용"
        if score >= 80:
            return "유사도 80~90 → 60% 적용"
        if score >= 70:
            return "유사도 70~80 → 70% 적용"
        if score >= 60:
            return "유사도 60~70 → 80% 적용"
        if score >= 50:
            return "유사도 50~60 → 90% 적용"
        return "유사도 50 미만 → 100% (감점 없음)"

    # -----------------------------------------------------------------
    # Chart helpers (inline SVG, no external libs)
    # -----------------------------------------------------------------

    def _find_tab14_item(self, name: str) -> Optional[Dict[str, Any]]:
        if not self.report_data:
            return None
        for it in self.report_data.get("tabs", {}).get("tab_1_4_market", {}).get("items", []) or []:
            if it.get("item") == name:
                return it
        return None

    def render_horizontal_bar_chart(self, title: str, icon: str,
                                     rows: List[Dict[str, Any]],
                                     value_label: str = "점유율(%)") -> str:
        """Render a horizontal bar chart from a list of {label, value, sub?} dicts."""
        if not rows:
            return ""
        max_v = max((r.get("value") or 0) for r in rows) or 1
        bar_h = 28
        gap = 12
        height = len(rows) * (bar_h + gap) + 20
        bars = ""
        for i, r in enumerate(rows):
            y = 10 + i * (bar_h + gap)
            v = r.get("value") or 0
            width = (v / max_v) * 540
            label = r.get("label", "")
            sub = r.get("sub")
            bars += f'''
            <g>
                <text x="0" y="{y + bar_h/2 + 4}" font-size="13" fill="#1b1c1c" font-weight="600">{i+1}. {label}</text>
                <rect x="180" y="{y}" width="{width}" height="{bar_h}" rx="4" fill="#00204e" opacity="0.85"/>
                <text x="{180 + width + 8}" y="{y + bar_h/2 + 4}" font-size="12" fill="#434751" font-weight="600">{v}%{f' · {sub}' if sub else ''}</text>
            </g>
            '''
        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">{icon}</span>
                <h2 class="font-headline-md text-headline-md text-primary">{title}</h2>
            </div>
            <svg class="w-full" viewBox="0 0 760 {height}" preserveAspectRatio="xMidYMid meet">
                {bars}
            </svg>
        </section>
        '''

    def render_range_bar_chart(self, title: str, icon: str, ranges: List[Dict[str, Any]],
                                axis_label: str = "%") -> str:
        """Render a horizontal range bar chart from list of {label, lo, hi, accent?} dicts."""
        if not ranges:
            return ""
        all_lo = min(r["lo"] for r in ranges)
        all_hi = max(r["hi"] for r in ranges)
        span = (all_hi - all_lo) or 1
        bar_h = 24
        gap = 16
        height = len(ranges) * (bar_h + gap) + 40
        items_html = ""
        for i, r in enumerate(ranges):
            y = 20 + i * (bar_h + gap)
            x1 = 160 + ((r["lo"] - all_lo) / span) * 540
            x2 = 160 + ((r["hi"] - all_lo) / span) * 540
            color = r.get("accent", "#005db7")
            items_html += f'''
            <g>
                <text x="0" y="{y + bar_h/2 + 4}" font-size="13" fill="#1b1c1c" font-weight="600">{r['label']}</text>
                <line x1="{x1}" y1="{y + bar_h/2}" x2="{x2}" y2="{y + bar_h/2}" stroke="{color}" stroke-width="6" stroke-linecap="round"/>
                <circle cx="{x1}" cy="{y + bar_h/2}" r="5" fill="{color}"/>
                <circle cx="{x2}" cy="{y + bar_h/2}" r="5" fill="{color}"/>
                <text x="{x1 - 6}" y="{y + bar_h/2 + 4}" font-size="11" fill="#434751" font-weight="600" text-anchor="end">{r['lo']}{axis_label}</text>
                <text x="{x2 + 8}" y="{y + bar_h/2 + 4}" font-size="11" fill="#434751" font-weight="600">{r['hi']}{axis_label}</text>
            </g>
            '''
        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">{icon}</span>
                <h2 class="font-headline-md text-headline-md text-primary">{title}</h2>
            </div>
            <svg class="w-full" viewBox="0 0 760 {height}" preserveAspectRatio="xMidYMid meet">
                {items_html}
            </svg>
        </section>
        '''

    def render_line_chart(self, title: str, icon: str, series: List[Dict[str, Any]],
                           y_label: str = "%") -> str:
        """Render line chart. Each series: {name, color, history:[{year,value}], forecast:[...]}.
        history는 실선, forecast는 점선으로 표시."""
        if not series:
            return ""
        all_points = []
        for s in series:
            for pt in s.get("history", []) + s.get("forecast", []):
                all_points.append(pt)
        if not all_points:
            return ""
        years = sorted({p["year"] for p in all_points})
        y_min = min(p["value"] for p in all_points)
        y_max = max(p["value"] for p in all_points)
        if y_min == y_max:
            y_max = y_min + 1
        pad = (y_max - y_min) * 0.1
        y_min -= pad
        y_max += pad

        W, H = 760, 280
        ml, mr, mt, mb = 50, 20, 20, 36
        chart_w = W - ml - mr
        chart_h = H - mt - mb

        def x_of(year):
            return ml + (years.index(year) / max(len(years) - 1, 1)) * chart_w

        def y_of(v):
            return mt + chart_h - ((v - y_min) / (y_max - y_min)) * chart_h

        # gridlines (4 horizontal)
        grid = ""
        for i in range(5):
            gy = mt + chart_h * i / 4
            val = y_max - (y_max - y_min) * i / 4
            grid += f'<line x1="{ml}" y1="{gy}" x2="{ml + chart_w}" y2="{gy}" stroke="#e3e2e2" stroke-width="1"/>'
            grid += f'<text x="{ml - 6}" y="{gy + 4}" font-size="10" fill="#747782" text-anchor="end">{val:.0f}</text>'

        # x axis labels
        x_labels = ""
        for y in years:
            xp = x_of(y)
            x_labels += f'<text x="{xp}" y="{mt + chart_h + 16}" font-size="10" fill="#747782" text-anchor="middle">{y}</text>'

        series_paths = ""
        legend_items = ""
        for s in series:
            color = s.get("color", "#00204e")
            hist = s.get("history", [])
            fc = s.get("forecast", [])
            if hist:
                d_hist = "M " + " L ".join(f"{x_of(p['year'])} {y_of(p['value'])}" for p in hist)
                series_paths += f'<path d="{d_hist}" fill="none" stroke="{color}" stroke-width="2.5"/>'
                for p in hist:
                    series_paths += f'<circle cx="{x_of(p["year"])}" cy="{y_of(p["value"])}" r="3" fill="{color}"/>'
            if fc:
                # connect last hist to first fc
                start = hist[-1] if hist else fc[0]
                d_fc = f"M {x_of(start['year'])} {y_of(start['value'])}"
                for p in fc:
                    d_fc += f" L {x_of(p['year'])} {y_of(p['value'])}"
                series_paths += f'<path d="{d_fc}" fill="none" stroke="{color}" stroke-width="2.5" stroke-dasharray="6 4"/>'
                for p in fc:
                    series_paths += f'<circle cx="{x_of(p["year"])}" cy="{y_of(p["value"])}" r="3" fill="{color}" opacity="0.6"/>'
            legend_items += f'<div class="flex items-center gap-xs"><span class="w-3 h-3 rounded-full" style="background:{color}"></span><span class="font-label-sm text-label-sm text-text-secondary">{s.get("name", "")}</span></div>'

        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center justify-between gap-sm mb-md pb-sm border-b border-surface-border">
                <div class="flex items-center gap-sm">
                    <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">{icon}</span>
                    <h2 class="font-headline-md text-headline-md text-primary">{title}</h2>
                </div>
                <div class="flex items-center gap-md">{legend_items}</div>
            </div>
            <svg class="w-full" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
                {grid}
                {x_labels}
                {series_paths}
            </svg>
            <p class="font-label-sm text-label-sm text-text-secondary mt-xs">실선=과거, 점선=전망 · 단위: {y_label}</p>
        </section>
        '''

    def render_waterfall_chart(self, title: str, icon: str, steps: List[Dict[str, Any]],
                                currency: str = "EUR") -> str:
        """steps: list of {label, value, is_total?}.
        Each non-total contributes additively; is_total resets the running total visually."""
        if not steps:
            return ""
        # Determine y range
        running = 0
        peaks = []
        for s in steps:
            if s.get("is_total"):
                peaks.append(s["value"])
                running = s["value"]
            else:
                running += s["value"]
                peaks.append(running)
        y_max = max(peaks)
        if y_max <= 0:
            y_max = 1

        W = 760
        chart_h = 260
        col_w = (W - 60) / len(steps) * 0.7
        col_gap = (W - 60) / len(steps) * 0.3
        baseline_y = chart_h + 20
        bars = ""
        running = 0
        for i, s in enumerate(steps):
            x = 40 + i * (col_w + col_gap)
            if s.get("is_total"):
                top = s["value"]
                top_y = baseline_y - (top / y_max) * chart_h
                bars += f'<rect x="{x}" y="{top_y}" width="{col_w}" height="{baseline_y - top_y}" fill="#00204e" rx="3"/>'
                bars += f'<text x="{x + col_w/2}" y="{top_y - 6}" font-size="11" fill="#00204e" font-weight="700" text-anchor="middle">{self.format_currency(top, currency)}</text>'
                running = top
            else:
                start = running
                running += s["value"]
                end = running
                top_y = baseline_y - (max(start, end) / y_max) * chart_h
                bot_y = baseline_y - (min(start, end) / y_max) * chart_h
                fill = "#10b981" if s["value"] >= 0 else "#E63946"
                bars += f'<rect x="{x}" y="{top_y}" width="{col_w}" height="{bot_y - top_y}" fill="{fill}" opacity="0.85" rx="3"/>'
                bars += f'<text x="{x + col_w/2}" y="{top_y - 6}" font-size="11" fill="{fill}" font-weight="700" text-anchor="middle">+{self.format_currency(s["value"], currency)}</text>'
            bars += f'<text x="{x + col_w/2}" y="{baseline_y + 16}" font-size="11" fill="#434751" text-anchor="middle">{s["label"]}</text>'

        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">{icon}</span>
                <h2 class="font-headline-md text-headline-md text-primary">{title}</h2>
            </div>
            <svg class="w-full" viewBox="0 0 {W} {baseline_y + 40}" preserveAspectRatio="xMidYMid meet">
                <line x1="40" y1="{baseline_y}" x2="{W - 20}" y2="{baseline_y}" stroke="#c4c6d2" stroke-width="1"/>
                {bars}
            </svg>
        </section>
        '''

    def render_cumulative_area_chart(self, title: str, icon: str,
                                      one_off: float, annual_recurring: float,
                                      operations_10y: float, years: int = 10,
                                      currency: str = "EUR") -> str:
        """Render cumulative 10-year cost area chart.
        - one_off paid at year 0
        - annual_recurring + (operations_10y/years) accumulate over time
        Two stacked layers: 일회성(구축+특화) vs 반복(유지+운영)."""
        W, H = 760, 280
        ml, mr, mt, mb = 60, 20, 20, 36
        chart_w = W - ml - mr
        chart_h = H - mt - mb
        op_annual = operations_10y / years
        # cumulative arrays
        years_axis = list(range(0, years + 1))
        cum_oneoff = [one_off for _ in years_axis]
        cum_recurring = [(annual_recurring + op_annual) * y for y in years_axis]
        cum_total = [cum_oneoff[i] + cum_recurring[i] for i in range(len(years_axis))]
        y_max = max(cum_total) or 1

        def x_of(y):
            return ml + (y / years) * chart_w

        def y_of(v):
            return mt + chart_h - (v / y_max) * chart_h

        # area paths
        # bottom layer: one_off
        oneoff_path = f"M {x_of(0)} {y_of(0)} "
        for i, y in enumerate(years_axis):
            oneoff_path += f"L {x_of(y)} {y_of(cum_oneoff[i])} "
        oneoff_path += f"L {x_of(years)} {y_of(0)} Z"

        # top layer: total (recurring stacks above one_off)
        total_path = f"M {x_of(0)} {y_of(cum_oneoff[0])} "
        for i, y in enumerate(years_axis):
            total_path += f"L {x_of(y)} {y_of(cum_total[i])} "
        for i in range(len(years_axis) - 1, -1, -1):
            total_path += f"L {x_of(years_axis[i])} {y_of(cum_oneoff[i])} "
        total_path += "Z"

        # gridlines
        grid = ""
        for i in range(5):
            gy = mt + chart_h * i / 4
            val = y_max - y_max * i / 4
            grid += f'<line x1="{ml}" y1="{gy}" x2="{ml + chart_w}" y2="{gy}" stroke="#e3e2e2"/>'
            grid += f'<text x="{ml - 6}" y="{gy + 4}" font-size="10" fill="#747782" text-anchor="end">{self.format_currency(val, currency)}</text>'

        x_labels = ""
        for y in years_axis:
            xp = x_of(y)
            x_labels += f'<text x="{xp}" y="{mt + chart_h + 16}" font-size="10" fill="#747782" text-anchor="middle">Y{y}</text>'

        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center justify-between gap-sm mb-md pb-sm border-b border-surface-border">
                <div class="flex items-center gap-sm">
                    <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">{icon}</span>
                    <h2 class="font-headline-md text-headline-md text-primary">{title}</h2>
                </div>
                <div class="flex items-center gap-md">
                    <div class="flex items-center gap-xs"><span class="w-3 h-3 rounded-full" style="background:#00204e"></span><span class="font-label-sm text-label-sm text-text-secondary">일회성(구축+특화)</span></div>
                    <div class="flex items-center gap-xs"><span class="w-3 h-3 rounded-full" style="background:#599bfe"></span><span class="font-label-sm text-label-sm text-text-secondary">반복(유지+운영)</span></div>
                </div>
            </div>
            <svg class="w-full" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
                {grid}
                <path d="{oneoff_path}" fill="#00204e" opacity="0.6"/>
                <path d="{total_path}" fill="#599bfe" opacity="0.5"/>
                {x_labels}
            </svg>
        </section>
        '''

    def render_step_chart(self, title: str, icon: str, tiers: List[Dict[str, Any]],
                          current_volume: int, currency: str = "EUR") -> str:
        """Step chart showing subscription price per unit as cumulative volume crosses tier thresholds."""
        if not tiers:
            return ""
        W, H = 760, 260
        ml, mr, mt, mb = 60, 20, 20, 40
        chart_w = W - ml - mr
        chart_h = H - mt - mb
        # x range
        x_max = max(t["max_volume"] for t in tiers if t["max_volume"] < 999999) * 1.05
        x_max = max(x_max, current_volume * 1.2)
        prices = [t["price_per_unit"] for t in tiers]
        y_max = max(prices) * 1.15
        y_min = 0

        def x_of(v):
            return ml + min(v / x_max, 1.0) * chart_w

        def y_of(v):
            return mt + chart_h - (v / y_max) * chart_h

        # Build step path
        path = ""
        for t in tiers:
            x1 = x_of(t["min_volume"])
            x2 = x_of(min(t["max_volume"], x_max))
            y = y_of(t["price_per_unit"])
            path += f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#00204e" stroke-width="3" stroke-linecap="round"/>'
        # Current volume marker
        cx = x_of(current_volume)
        marker_price = None
        for t in tiers:
            if t["min_volume"] <= current_volume <= t["max_volume"]:
                marker_price = t["price_per_unit"]
                break
        marker = ""
        if marker_price is not None:
            cy = y_of(marker_price)
            marker = f'''
                <line x1="{cx}" y1="{mt}" x2="{cx}" y2="{mt + chart_h}" stroke="#10b981" stroke-width="1.5" stroke-dasharray="4 4"/>
                <circle cx="{cx}" cy="{cy}" r="6" fill="#10b981"/>
                <text x="{cx + 10}" y="{cy + 4}" font-size="12" fill="#065f46" font-weight="700">현재 {current_volume:,}건 → {self.format_currency(marker_price, currency)}</text>
            '''

        # Gridlines and labels (Y)
        grid = ""
        for i in range(5):
            gy = mt + chart_h * i / 4
            val = y_max - y_max * i / 4
            grid += f'<line x1="{ml}" y1="{gy}" x2="{ml + chart_w}" y2="{gy}" stroke="#e3e2e2"/>'
            grid += f'<text x="{ml - 6}" y="{gy + 4}" font-size="10" fill="#747782" text-anchor="end">{self.format_currency(val, currency)}</text>'

        # X labels (tier thresholds)
        x_labels = ""
        for t in tiers:
            xv = t["min_volume"]
            xp = x_of(xv)
            x_labels += f'<text x="{xp}" y="{mt + chart_h + 16}" font-size="10" fill="#747782" text-anchor="middle">{xv:,}</text>'

        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">{icon}</span>
                <h2 class="font-headline-md text-headline-md text-primary">{title}</h2>
            </div>
            <svg class="w-full" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
                {grid}
                {x_labels}
                {path}
                {marker}
            </svg>
            <p class="font-label-sm text-label-sm text-text-secondary mt-xs">X=누적 계약건수, Y=건당 단가 · 누적 증가 시 자동 하향 (전 물량 소급)</p>
        </section>
        '''

    def render_tab_0_summary(self) -> str:
        """Render Tab 1-0: Executive Summary."""
        if not self.report_data:
            return ""

        target = self.report_data.get("target", {})
        tabs = self.report_data.get("tabs", {})
        similarity = tabs.get("tab_1_1_similarity", {})
        tco = tabs.get("tab_1_3_tco", {})
        decision = tabs.get("tab_1_2_decision", {})

        country_name = self.get_country_name(target.get("country", ""))
        base_country_code = decision.get("base_country") or target.get("base_country", "GB")
        base_country_name = self.get_country_name(base_country_code)
        decision_type = decision.get("decision", "")
        decision_label = self._decision_label(decision_type, base_country_name)
        overall_insight = self.report_data.get("overall_insight") or ""

        # Extract key metrics for KPI cards
        similarity_score = similarity.get("overall_score", 0)
        total_tco = tco.get("total_tco_10y", 0)
        build_months = tco.get("build_months", 0)
        currency = tco.get("currency", "EUR")

        kpi_items = [
            ("유사도 점수", f"{similarity_score:.1f}", "trending_up", "text-emerald-800"),
            ("예상 10년 TCO", self.format_currency(total_tco, currency), "payments", "text-primary"),
            ("예상 구축 기간", f"{build_months:.1f}M", "schedule", "text-primary"),
        ]
        big_kpi_html = ""
        for label, value, icon, icon_class in kpi_items:
            big_kpi_html += f'''
            <div class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow flex flex-col h-full">
                <div class="flex items-center justify-between mb-md">
                    <span class="font-headline-md text-headline-md text-primary tracking-tight">{label}</span>
                    <span class="material-symbols-outlined {icon_class} text-[32px]">{icon}</span>
                </div>
                <div class="flex-1 flex items-end">
                    <span class="font-display-lg text-display-lg text-primary leading-none">{value}</span>
                </div>
            </div>
            '''

        decision_tree_html = self.render_decision_tree_section(include_outer=True)

        executive_summary_html = f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">description</span>
                <h2 class="font-headline-md text-headline-md text-primary">요약</h2>
            </div>
            <div class="prose max-w-none font-body-md text-body-md text-on-surface-variant leading-relaxed">
                <p class="mb-sm">
                    {country_name}은(는) 베이스라인 국가 {base_country_name} 대비 유사도 점수 {similarity_score:.1f}점으로 평가되어,
                    <strong>{decision_label}</strong> 전략이 권고됩니다.
                </p>
                <p>
                    10년 총소유비용(TCO)은 {self.format_currency(total_tco, currency)}이며, 예상 구축 기간은 약 {build_months:.1f}개월입니다.
                    예상 신규 계약건수는 약 {tco.get('expected_contracts', 0)}건입니다.
                </p>
            </div>
            {f'<div class="bg-surface-container/60 p-md rounded-lg border-l-4 border-primary mt-md"><div class="flex items-center gap-xs mb-xs"><span class="material-symbols-outlined text-primary text-[18px]">lightbulb</span><span class="font-semibold font-label-md text-label-md text-primary uppercase">국가 종합 인사이트</span></div><p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{overall_insight}</p></div>' if overall_insight else ''}
            <div class="bg-surface-container p-md rounded-lg border-l-4 border-primary mt-md">
                <div class="flex items-center gap-xs mb-xs">
                    <span class="material-symbols-outlined text-primary text-[18px]">lightbulb</span>
                    <span class="font-semibold font-label-md text-label-md text-primary uppercase">전략 권고</span>
                </div>
                <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">
                    {decision.get("recommendation", "")} (유사도 {similarity_score:.1f}점, 베이스라인: {base_country_name})
                </p>
            </div>
        </section>
        '''

        return f'''
        <div class="grid grid-cols-12 gap-gutter">
            <div class="col-span-8 flex flex-col gap-xl">
                <div class="grid grid-cols-3 gap-gutter">
                    {big_kpi_html}
                </div>
                {decision_tree_html}
            </div>
            <div class="col-span-4 flex flex-col gap-xl">
                <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
                    <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                        <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">fact_check</span>
                        <h2 class="font-headline-md text-headline-md text-primary">결정 요약</h2>
                    </div>
                    <div class="flex flex-col gap-md">
                        <div class="flex justify-between items-center p-sm bg-surface rounded-lg border border-surface-container-highest">
                            <div class="flex items-center gap-sm">
                                <div class="w-8 h-8 rounded-full bg-secondary-container/20 flex items-center justify-center">
                                    <span class="material-symbols-outlined text-secondary text-[18px]">account_tree</span>
                                </div>
                                <span class="font-label-md text-label-md text-text-primary">시스템 결정</span>
                            </div>
                            <div class="flex items-center gap-xs bg-emerald-100/50 text-emerald-800 px-2 py-1 rounded-full border border-emerald-200">
                                <span class="material-symbols-outlined text-[14px]">check_circle</span>
                                <span class="font-label-sm text-label-sm uppercase tracking-wide">{decision_label}</span>
                            </div>
                        </div>
                        <div class="flex justify-between items-center p-sm bg-surface rounded-lg border border-surface-container-highest">
                            <div class="flex items-center gap-sm">
                                <div class="w-8 h-8 rounded-full bg-secondary-container/20 flex items-center justify-center">
                                    <span class="material-symbols-outlined text-secondary text-[18px]">flag</span>
                                </div>
                                <span class="font-label-md text-label-md text-text-primary">베이스라인 국가</span>
                            </div>
                            <span class="font-label-md text-label-md text-text-primary font-semibold">{base_country_name} ({base_country_code})</span>
                        </div>
                    </div>
                </section>
                {self.render_subscription_tier_table()}
                {executive_summary_html}
            </div>
        </div>
        '''

    def _render_dimension_scoring_card(self, item: Dict[str, Any], base_country_name: str, target_country_name: str) -> str:
        """Render a single item with its dimension-by-dimension scoring breakdown."""
        name = item.get("item", "")
        axis = item.get("axis", "")
        item_score = item.get("item_similarity", 0)
        weight = item.get("weight", 0)
        dims = item.get("dimensions", []) or []

        rows = ""
        for d in dims:
            dim_name = d.get("dimension", "")
            t = d.get("target_score", 0)
            b = d.get("base_score", 0)
            gap = d.get("gap", 0)
            sim = d.get("similarity", 0)
            note = d.get("note", "")
            # bar widths max 5 → 0-100%
            t_pct = (float(t) / 5.0) * 100.0
            b_pct = (float(b) / 5.0) * 100.0
            rows += f'''
            <tr class="border-b border-surface-container-highest align-top">
                <td class="py-sm pr-sm">
                    <div class="font-body-sm text-body-sm text-text-primary font-semibold">{dim_name}</div>
                    {f'<div class="font-body-sm text-body-sm text-text-secondary mt-xs">{note}</div>' if note else ''}
                </td>
                <td class="py-sm px-sm w-[110px]">
                    <div class="flex items-center gap-xs">
                        <div class="flex-1 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                            <div class="h-full bg-primary" style="width: {t_pct:.0f}%"></div>
                        </div>
                        <span class="font-label-sm text-label-sm text-text-primary w-[20px] text-right">{t}</span>
                    </div>
                </td>
                <td class="py-sm px-sm w-[110px]">
                    <div class="flex items-center gap-xs">
                        <div class="flex-1 h-2 bg-surface-container-highest rounded-full overflow-hidden">
                            <div class="h-full bg-secondary" style="width: {b_pct:.0f}%"></div>
                        </div>
                        <span class="font-label-sm text-label-sm text-text-primary w-[20px] text-right">{b}</span>
                    </div>
                </td>
                <td class="py-sm px-sm w-[60px] text-right font-label-sm text-label-sm {('text-emerald-700' if gap <= 1 else ('text-yellow-700' if gap <= 2 else 'text-accent-red'))}">{gap:.0f}</td>
                <td class="py-sm pl-sm w-[80px] text-right font-label-md text-label-md text-primary font-bold">{sim:.0f}</td>
            </tr>
            '''

        score_color = "emerald" if item_score >= 70 else ("yellow" if item_score >= 50 else "red")

        return f'''
        <div class="bg-surface border border-surface-container-highest rounded-lg p-md">
            <div class="flex items-start justify-between gap-md mb-sm">
                <div>
                    <div class="font-label-md text-label-md text-text-primary uppercase tracking-wider">{name}</div>
                    <div class="font-label-sm text-label-sm text-text-secondary mt-xs">축: {axis or '-'} · 가중치 {weight*100:.0f}%</div>
                </div>
                <div class="flex flex-col items-end">
                    <div class="font-headline-md text-headline-md text-{score_color}-700">{item_score:.0f}</div>
                    <div class="font-label-sm text-label-sm text-text-secondary">/ 100</div>
                </div>
            </div>
            <table class="w-full font-body-sm text-body-sm">
                <thead>
                    <tr class="text-text-secondary border-b border-surface-container-highest">
                        <th class="py-xs pr-sm text-left font-label-sm text-label-sm uppercase">디멘전</th>
                        <th class="py-xs px-sm text-left font-label-sm text-label-sm uppercase">{target_country_name} (A)</th>
                        <th class="py-xs px-sm text-left font-label-sm text-label-sm uppercase">{base_country_name} (B)</th>
                        <th class="py-xs px-sm text-right font-label-sm text-label-sm uppercase">격차</th>
                        <th class="py-xs pl-sm text-right font-label-sm text-label-sm uppercase">유사도</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        '''

    def render_similarity_scoring_section(self) -> str:
        """Render dimension-by-dimension similarity scoring tables for each item."""
        if not self.report_data:
            return ""
        tabs = self.report_data.get("tabs", {})
        similarity = tabs.get("tab_1_1_similarity", {})
        items = similarity.get("items", []) or []
        if not items:
            return ""

        target_country_code = self.report_data.get("target", {}).get("country", "")
        base_country_code = self.report_data.get("target", {}).get("base_country", "GB")
        target_country_name = self.get_country_name(target_country_code)
        base_country_name = self.get_country_name(base_country_code)

        cards = "".join(
            self._render_dimension_scoring_card(it, base_country_name, target_country_name)
            for it in items
        )

        scale_note = similarity.get("scale", "")
        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">calculate</span>
                <h2 class="font-headline-md text-headline-md text-primary">디멘전별 채점 ({target_country_name} vs {base_country_name})</h2>
            </div>
            <p class="font-body-sm text-body-sm text-text-secondary mb-md">각 디멘전을 1~5점 척도로 양국 평가 후, 격차에 따라 유사도를 산출합니다. {scale_note}</p>
            <div class="flex flex-col gap-md">
                {cards}
            </div>
        </section>
        '''

    def render_tab_1_1_similarity(self) -> str:
        """Render Tab 1-1: Similarity Scoring (vs Baseline)."""
        if not self.report_data:
            return ""

        tabs = self.report_data.get("tabs", {})
        similarity = tabs.get("tab_1_1_similarity", {})
        axes = similarity.get("axes", {})
        overall_score = similarity.get("overall_score", 0)
        scoring_section = self.render_similarity_scoring_section()
        evidence_section = self.render_items_section(
            similarity.get("evidence_items", []),
            title="유사도 산정 근거 항목 (원천 데이터)",
            icon="fact_check",
        )

        axis_labels = {
            "system":     ("top-0 left-1/2 -translate-x-1/2", "시스템"),
            "product":    ("right-0 top-1/2 -translate-y-1/2", "상품"),
            "regulatory": ("bottom-0 left-1/2 -translate-x-1/2", "규제"),
            "risk":       ("left-0 top-1/2 -translate-y-1/2", "리스크"),
        }
        # Defensive: cover legacy keys if present
        legacy_alias = {"solution_type": "system", "digital_maturity": "system", "product_mix": "product"}
        normalized_axes = {legacy_alias.get(k, k): v for k, v in axes.items()}

        labels_html = ""
        for axis_key, (position, label) in axis_labels.items():
            labels_html += f'<span class="absolute {position} font-label-sm text-label-sm text-text-secondary uppercase tracking-wider">{label}</span>\n'

        metrics_html = ""
        for axis_key, (_, label) in axis_labels.items():
            score = normalized_axes.get(axis_key, 0)
            metrics_html += f'''
            <div class="flex flex-col p-sm bg-surface rounded-lg border border-surface-container-highest">
                <span class="font-label-sm text-label-sm text-text-secondary uppercase">{label}</span>
                <span class="font-headline-md text-headline-md text-primary">{score:.1f}</span>
            </div>
            '''

        radar_axes = {
            "system": normalized_axes.get("system", 0),
            "product": normalized_axes.get("product", 0),
            "regulatory": normalized_axes.get("regulatory", 0),
            "risk": normalized_axes.get("risk", 0),
        }

        return f'''
        <div class="grid grid-cols-12 gap-gutter">
            <div class="col-span-8 flex flex-col gap-xl">
                <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
                    <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                        <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">radar</span>
                        <h2 class="font-headline-md text-headline-md text-primary">유사도 점수 (A vs B)</h2>
                    </div>
                    <div class="relative flex flex-col items-center">
                        <div class="w-full aspect-square relative flex items-center justify-center mb-md max-w-md mx-auto">
                            <svg class="w-full h-full overflow-visible" viewBox="0 0 200 200">
                                <polygon fill="none" points="100,20 180,100 100,180 20,100" stroke="#DCDCDC" stroke-width="1"/>
                                <polygon fill="none" points="100,40 160,100 100,160 40,100" stroke="#DCDCDC" stroke-width="1"/>
                                <polygon fill="none" points="100,60 140,100 100,140 60,100" stroke="#DCDCDC" stroke-width="1"/>
                                <polygon fill="none" points="100,80 120,100 100,120 80,100" stroke="#DCDCDC" stroke-width="1"/>
                                <line stroke="#DCDCDC" stroke-width="1" x1="100" y1="20" x2="100" y2="180"/>
                                <line stroke="#DCDCDC" stroke-width="1" x1="20" y1="100" x2="180" y2="100"/>
                                <polygon fill="rgba(0, 32, 78, 0.15)" points="100,{100-radar_axes['system']*0.8} {100+radar_axes['product']*0.8},100 100,{100+radar_axes['regulatory']*0.8} {100-radar_axes['risk']*0.8},100" stroke="#00204e" stroke-width="2"/>
                                <circle cx="100" cy="{100-radar_axes['system']*0.8}" fill="#00204e" r="3"/>
                                <circle cx="{100+radar_axes['product']*0.8}" cy="100" fill="#00204e" r="3"/>
                                <circle cx="100" cy="{100+radar_axes['regulatory']*0.8}" fill="#00204e" r="3"/>
                                <circle cx="{100-radar_axes['risk']*0.8}" cy="100" fill="#00204e" r="3"/>
                            </svg>
                            {labels_html}
                        </div>
                    </div>
                </section>
            </div>
            <div class="col-span-4 flex flex-col gap-xl">
                <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
                    <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                        <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">assessment</span>
                        <h2 class="font-headline-md text-headline-md text-primary">축별 점수</h2>
                    </div>
                    <div class="grid grid-cols-2 gap-sm mb-md">
                        {metrics_html}
                    </div>
                    <div class="p-md bg-surface-container rounded-lg border-l-4 border-primary mb-sm">
                        <div class="flex items-center gap-xs mb-xs">
                            <span class="material-symbols-outlined text-primary text-[18px]">grade</span>
                            <span class="font-semibold font-label-md text-label-md text-primary uppercase">Overall Score</span>
                        </div>
                        <div class="flex items-baseline gap-xs">
                            <span class="font-headline-lg text-headline-lg text-primary">{overall_score:.1f}</span>
                            <span class="font-body-sm text-body-sm text-text-secondary">/ 100</span>
                        </div>
                    </div>
                    <div class="p-md bg-emerald-50/60 rounded-lg border-l-4 border-emerald-600">
                        <div class="flex items-center gap-xs mb-xs">
                            <span class="material-symbols-outlined text-emerald-700 text-[18px]">percent</span>
                            <span class="font-semibold font-label-md text-label-md text-emerald-800 uppercase">탭1-3 승수</span>
                        </div>
                        <div class="flex items-baseline gap-xs">
                            <span class="font-headline-lg text-headline-lg text-emerald-700">{self._similarity_multiplier(overall_score) * 100:.0f}%</span>
                        </div>
                        <p class="font-label-sm text-label-sm text-text-secondary mt-xs">{self._multiplier_band_label(overall_score)}</p>
                    </div>
                </section>
            </div>
            <div class="col-span-12">{scoring_section}</div>
            <div class="col-span-12">{evidence_section}</div>
        </div>
        '''

    def render_decision_tree_section(self, include_outer: bool = True) -> str:
        """Render reusable decision tree flowchart section.

        Args:
            include_outer: When True, wraps the flowchart in the standard panel/card
        """
        if not self.report_data:
            return ""

        tabs = self.report_data.get("tabs", {})
        decision = tabs.get("tab_1_2_decision", {})
        similarity_score = decision.get("similarity_score", 0)
        recommendation = decision.get("recommendation", "")
        base_system = decision.get("base_system", "N/A")
        base_country = decision.get("base_country") or self.report_data.get("target", {}).get("base_country", "GB")
        base_country_name = self.get_country_name(base_country)
        hq_cost = decision.get("hq_baseline_cost", 0)
        hq_months = decision.get("hq_baseline_months", 0)
        currency = decision.get("hq_baseline_currency", "EUR")

        decision_type = decision.get("decision", "")

        external_passes = decision.get("external_passes_criteria")  # optional; None = 미평가
        region_system_exists = decision.get("region_system_exists", True)

        # Score-level path label (independent of region gate)
        score_path = "B" if similarity_score >= 70 else ("EXT_CHECK" if similarity_score < 50 else "HQ_MID")

        # Final outcome — region gate first, then score path
        if not region_system_exists:
            # No region system → external-solution gate (YES=EXT, NO=HQ fallback)
            if external_passes is False:
                final_path = "HQ"
            else:
                final_path = "EXT"
        elif score_path == "B":
            final_path = "B"
        elif score_path == "HQ_MID":
            final_path = "HQ"
        else:  # EXT_CHECK
            if decision_type == "external_solution" or external_passes is True:
                final_path = "EXT"
            elif external_passes is False:
                final_path = "HQ"
            else:
                final_path = "EXT"

        path_b = "active" if final_path == "B" else "inactive"
        path_ext = "active" if final_path == "EXT" else "inactive"
        path_hq = "active" if final_path == "HQ" else "inactive"

        # Color tokens by active path
        active_color = "#10b981" if path_b == "active" else ("#eab308" if path_ext == "active" else "#E63946")
        score_branch_x = {"B": 150, "EXT_CHECK": 450, "HQ_MID": 750}[score_path]

        # Localization requirements (특화요건) — pulled from decision items
        spec_field_names = [
            "상품판매 현황", "개인정보보호법", "데이터 현지화 의무",
            "의무보험 규제", "신용생명보험 규제", "보험 끼워팔기 규제",
            "AI 신용평가 규제",
        ]
        decision_items = decision.get("items", []) or []
        items_by_name = {it.get("item", ""): it for it in decision_items}
        spec_chips_html = ""
        for name in spec_field_names:
            it = items_by_name.get(name)
            present = it is not None and it.get("status") != "missing"
            chip_color = "emerald" if present else "yellow"
            icon = "check_circle" if present else "warning"
            spec_chips_html += f'''
            <span class="inline-flex items-center gap-xs bg-{chip_color}-100/60 text-{chip_color}-800 border border-{chip_color}-200 px-2 py-1 rounded-full font-label-sm text-label-sm">
                <span class="material-symbols-outlined text-[14px]">{icon}</span>
                {name}
            </span>
            '''

        # Action text per branch
        action_b = f"권역 내 확산 시스템({base_country_name} - {base_system}) + 현지 특화 추가개발 → 탭1-3 비용 산정"
        action_ext = "현지 사용 솔루션 + 로컬 솔루션 2~3종 추천 (기준점 통과 시)"
        action_hq = f"본사 시스템 사용 ({self.format_currency(hq_cost, currency)} / {hq_months}M 기준)"

        inner = f'''
            <style>
                @keyframes dt-pulse {{
                    0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(0,32,78,0.25); }}
                    70% {{ transform: scale(1.04); box-shadow: 0 0 0 16px rgba(0,32,78,0); }}
                    100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(0,32,78,0); }}
                }}
                @keyframes dt-pop {{
                    0% {{ transform: scale(0.85); opacity: 0; }}
                    60% {{ transform: scale(1.08); opacity: 1; }}
                    100% {{ transform: scale(1); opacity: 1; }}
                }}
                @keyframes dt-spin {{
                    from {{ transform: rotate(0deg); }}
                    to {{ transform: rotate(360deg); }}
                }}
                @keyframes dt-flow {{
                    to {{ stroke-dashoffset: -24; }}
                }}
                @keyframes dt-dash {{
                    from {{ stroke-dashoffset: 1000; }}
                    to {{ stroke-dashoffset: 0; }}
                }}
                @keyframes dt-glow {{
                    0%, 100% {{ filter: drop-shadow(0 0 6px rgba(16,185,129,0.45)); }}
                    50% {{ filter: drop-shadow(0 0 14px rgba(16,185,129,0.9)); }}
                }}
                .dt-node-start {{ animation: dt-pulse 2.4s ease-in-out infinite; }}
                .dt-diamond {{ animation: dt-pop 0.6s ease-out 0.3s both; transform-origin: center; }}
                .dt-flow-line {{
                    stroke: #00204e;
                    stroke-width: 2;
                    stroke-dasharray: 6 6;
                    animation: dt-flow 1.2s linear infinite;
                    fill: none;
                }}
                .dt-active-path {{
                    stroke: {active_color};
                    stroke-width: 4;
                    stroke-linecap: round;
                    fill: none;
                    stroke-dasharray: 1000;
                    stroke-dashoffset: 1000;
                    animation: dt-dash 1.6s ease-out 0.6s forwards, dt-glow 2s ease-in-out 2.2s infinite;
                }}
                .dt-active-bullet {{ animation: dt-pop 0.5s ease-out 2.0s both, dt-glow 2s ease-in-out 2.4s infinite; transform-origin: center; transform-box: fill-box; }}
                .dt-branch-card {{ animation: dt-pop 0.55s ease-out both; transform-origin: top center; }}
                .dt-branch-b {{ animation-delay: 2.1s; }}
                .dt-branch-ext {{ animation-delay: 2.3s; }}
                .dt-branch-hq {{ animation-delay: 2.5s; }}
                .dt-branch-active {{ box-shadow: 0 6px 18px rgba(0,0,0,0.08); }}
            </style>

            <div class="flex flex-col items-center pt-md gap-sm">
                <!-- 분기 로직 -->
                <div class="w-full max-w-4xl">
                    <div class="flex items-center gap-sm mb-xs">
                        <span class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary text-on-primary font-label-md text-label-md">①</span>
                        <span class="font-label-md text-label-md text-text-secondary uppercase tracking-wider">분기 로직 (권역 내 시스템 → 점수 → 외부솔루션 기준점)</span>
                    </div>
                </div>
                <svg class="w-full max-w-4xl block" viewBox="0 0 900 640" preserveAspectRatio="xMidYMid meet" style="margin-bottom: -8px;">
                    <defs>
                        <marker id="arrow-soft" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                            <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
                        </marker>
                    </defs>

                    <!-- (a) 권역 내 시스템 존재 다이아몬드 (top) -->
                    <g class="dt-diamond">
                        <polygon points="450,20 520,80 450,140 380,80" fill="#fbf9f9" stroke="#00204e" stroke-width="2"/>
                        <text x="450" y="75" text-anchor="middle" font-size="11" fill="#00204e" font-weight="700">권역 내 구축</text>
                        <text x="450" y="92" text-anchor="middle" font-size="11" fill="#00204e" font-weight="700">시스템 존재?</text>
                    </g>

                    <!-- (a) YES → 점수 다이아몬드 -->
                    <path d="M450 140 L450 200" class="dt-flow-line" opacity="0.25" />
                    <text x="465" y="175" text-anchor="start" font-size="11" font-weight="700" fill="#065f46" opacity="{'1' if region_system_exists else '0.3'}">YES ({base_country_name})</text>

                    <!-- (a) NO → 외부솔루션 기준점 다이아몬드 -->
                    <path d="M520 80 L820 80 L820 480 L520 480" class="dt-flow-line" opacity="0.25" />
                    <text x="700" y="70" text-anchor="middle" font-size="11" font-weight="700" fill="#854d0e" opacity="{'1' if not region_system_exists else '0.3'}">NO → 외부솔루션</text>

                    <!-- (b) 점수 분기 다이아몬드 -->
                    <g class="dt-diamond" style="animation-delay: 0.6s; opacity: {'1' if region_system_exists else '0.35'}">
                        <polygon points="450,200 525,260 450,320 375,260" fill="#fbf9f9" stroke="#00204e" stroke-width="2"/>
                        <text x="450" y="255" text-anchor="middle" font-size="10" fill="#00204e" font-weight="700">유사도</text>
                        <text x="450" y="280" text-anchor="middle" font-size="18" fill="#00204e" font-weight="800">{similarity_score:.1f}</text>
                    </g>

                    <!-- (b) Score branch 1: ≥70 → B leaf -->
                    <path d="M450 320 L450 360 L150 360 L150 560" class="dt-flow-line" opacity="0.25" />
                    <text x="300" y="350" text-anchor="middle" font-size="11" font-weight="700" fill="#065f46" opacity="{'1' if (region_system_exists and score_path == 'B') else '0.3'}">≥ 70 → 권역 내 확산</text>

                    <!-- (b) Score branch 2: 50~70 → HQ leaf -->
                    <path d="M450 320 L450 360 L750 360 L750 560" class="dt-flow-line" opacity="0.25" />
                    <text x="600" y="350" text-anchor="middle" font-size="11" font-weight="700" fill="#9f1239" opacity="{'1' if (region_system_exists and score_path == 'HQ_MID') else '0.3'}">50~70 → 본사 자체구축</text>

                    <!-- (b) Score branch 3: <50 → secondary gate (with longer gap) -->
                    <path d="M450 320 L450 420" class="dt-flow-line" opacity="0.25" />
                    <text x="465" y="370" text-anchor="start" font-size="11" font-weight="700" fill="#854d0e" opacity="{'1' if (region_system_exists and score_path == 'EXT_CHECK') else '0.3'}">&lt; 50</text>

                    <!-- (c) 외부솔루션 기준점 다이아몬드 -->
                    <g class="dt-diamond" style="animation-delay: 1.0s; opacity: {'1' if ((not region_system_exists) or (region_system_exists and score_path == 'EXT_CHECK')) else '0.35'}">
                        <polygon points="450,420 520,480 450,540 380,480" fill="#fff7ed" stroke="#9a3412" stroke-width="2"/>
                        <text x="450" y="475" text-anchor="middle" font-size="10" fill="#9a3412" font-weight="700">외부솔루션</text>
                        <text x="450" y="492" text-anchor="middle" font-size="10" fill="#9a3412" font-weight="700">기준점 통과?</text>
                    </g>

                    <!-- (c) Gate → EXT leaf -->
                    <path d="M450 540 L450 615" class="dt-flow-line" opacity="0.25" />
                    <text x="465" y="585" text-anchor="start" font-size="11" font-weight="700" fill="#854d0e" opacity="{'1' if (final_path == 'EXT') else '0.3'}">YES → 외부솔루션</text>

                    <!-- (c) Gate → HQ leaf (fallback) -->
                    <path d="M520 480 L750 480 L750 560" class="dt-flow-line" opacity="0.25" />
                    <text x="640" y="472" text-anchor="middle" font-size="11" font-weight="700" fill="#9f1239" opacity="{'1' if (final_path == 'HQ' and (not region_system_exists or score_path == 'EXT_CHECK')) else '0.3'}">NO (Fallback)</text>

                    <!-- Active path: region NOT exists → gate YES → EXT -->
                    {'<path d="M520 80 L820 80 L820 480 L520 480 M450 540 L450 615" class="dt-active-path" />' if (not region_system_exists and final_path == 'EXT') else ''}

                    <!-- Active path: region NOT exists → gate NO → HQ -->
                    {'<path d="M520 80 L820 80 L820 480 L520 480 L750 480 L750 560" class="dt-active-path" />' if (not region_system_exists and final_path == 'HQ') else ''}

                    <!-- Active path: region exists, ≥70 → B -->
                    {'<path d="M450 140 L450 200 M450 320 L450 360 L150 360 L150 560" class="dt-active-path" />' if (region_system_exists and final_path == 'B') else ''}

                    <!-- Active path: region exists, 50~70 → HQ -->
                    {'<path d="M450 140 L450 200 M450 320 L450 360 L750 360 L750 560" class="dt-active-path" />' if (region_system_exists and score_path == 'HQ_MID' and final_path == 'HQ') else ''}

                    <!-- Active path: region exists, <50, gate YES → EXT -->
                    {'<path d="M450 140 L450 200 M450 320 L450 420 M450 540 L450 615" class="dt-active-path" />' if (region_system_exists and score_path == 'EXT_CHECK' and final_path == 'EXT') else ''}

                    <!-- Active path: region exists, <50, gate NO → HQ -->
                    {'<path d="M450 140 L450 200 M450 320 L450 420 M520 480 L750 480 L750 560" class="dt-active-path" />' if (region_system_exists and score_path == 'EXT_CHECK' and final_path == 'HQ') else ''}

                    <!-- Final bullet at leaf -->
                    <circle class="dt-active-bullet" cx="{ {'B': 150, 'EXT': 450, 'HQ': 750}[final_path] }" cy="{ 615 if final_path == 'EXT' else 560 }" r="7" fill="{active_color}" />
                </svg>

                <!-- 처리 액션 (3 branches) -->
                <div class="w-full max-w-4xl">
                    <div class="flex items-center gap-sm mb-sm">
                        <span class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary text-on-primary font-label-md text-label-md">②</span>
                        <span class="font-label-md text-label-md text-text-secondary uppercase tracking-wider">처리 (Action)</span>
                    </div>
                    <div class="grid grid-cols-3 gap-lg">
                        <div class="dt-branch-card dt-branch-b bg-emerald-100/40 border-2 {'border-emerald-500 dt-branch-active' if path_b == 'active' else 'border-outline-variant opacity-40'} rounded-xl p-md">
                            <div class="flex items-center gap-xs mb-xs">
                                <span class="material-symbols-outlined text-emerald-700 text-[20px]">expand_circle_down</span>
                                <span class="font-label-md text-label-md text-emerald-800 uppercase tracking-wider">권역 내 확산 ({base_country_name} 시스템)</span>
                            </div>
                            <p class="font-body-sm text-body-sm text-emerald-900 leading-relaxed">{action_b}</p>
                        </div>

                        <div class="dt-branch-card dt-branch-ext bg-yellow-100/40 border-2 {'border-yellow-500 dt-branch-active' if path_ext == 'active' else 'border-outline-variant opacity-40'} rounded-xl p-md">
                            <div class="flex items-center gap-xs mb-xs">
                                <span class="material-symbols-outlined text-yellow-700 text-[20px]">extension</span>
                                <span class="font-label-md text-label-md text-yellow-800 uppercase tracking-wider">외부솔루션</span>
                            </div>
                            <p class="font-body-sm text-body-sm text-yellow-900 leading-relaxed">{action_ext}</p>
                        </div>

                        <div class="dt-branch-card dt-branch-hq bg-tertiary-fixed/40 border-2 {'border-accent-red dt-branch-active' if path_hq == 'active' else 'border-outline-variant opacity-40'} rounded-xl p-md">
                            <div class="flex items-center gap-xs mb-xs">
                                <span class="material-symbols-outlined text-accent-red text-[20px]">domain</span>
                                <span class="font-label-md text-label-md text-tertiary uppercase tracking-wider">본사 자체구축</span>
                            </div>
                            <p class="font-body-sm text-body-sm text-tertiary leading-relaxed">{action_hq}</p>
                        </div>
                    </div>
                    <p class="font-body-sm text-body-sm text-text-secondary mt-sm">※ 본사 자체구축 비용·기간은 어느 분기든 참고용으로 병기됩니다.</p>
                </div>
            </div>

            <div class="bg-surface-container p-md rounded-lg border-l-4 border-primary mb-md">
                <div class="flex items-center gap-xs mb-xs">
                    <span class="material-symbols-outlined text-primary text-[18px]">check_circle</span>
                    <span class="font-semibold font-label-md text-label-md text-primary uppercase">최종 결정: {self._decision_label(decision_type, base_country_name)}</span>
                </div>
                <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{recommendation}</p>
            </div>

            <div class="flex flex-col gap-md">
                <div class="flex justify-between items-center p-sm bg-surface rounded-lg border border-surface-container-highest">
                    <span class="font-label-md text-label-md text-text-secondary">베이스라인 국가 / 시스템</span>
                    <span class="font-semibold font-body-md text-body-md text-text-primary">{base_country_name} ({base_system})</span>
                </div>
                <div class="flex justify-between items-center p-sm bg-surface rounded-lg border border-surface-container-highest">
                    <span class="font-label-md text-label-md text-text-secondary">본사 자체구축 (참고)</span>
                    <span class="font-semibold font-body-md text-body-md text-text-primary">{self.format_currency(hq_cost, currency)} / {hq_months}M</span>
                </div>
            </div>
        '''

        if not include_outer:
            return inner

        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">account_tree</span>
                <h2 class="font-headline-md text-headline-md text-primary">시스템 결정 트리</h2>
            </div>
            {inner}
        </section>
        '''

    def render_subscription_tier_table(self) -> str:
        """Render the subscription pricing tier table as a standalone panel."""
        if not self.report_data:
            return ""
        tabs = self.report_data.get("tabs", {})
        tco_tab = tabs.get("tab_1_3_tco", {})
        tiers = tco_tab.get("subscription_tiers", []) or []
        if not tiers:
            return ""

        existing_volume = tco_tab.get("existing_total_volume", 0)
        sub_details = tco_tab.get("subscription_details", {}) or {}
        active_total = sub_details.get("total_volume", 0)
        active_unit_price = sub_details.get("unit_price")

        tier_rows = ""
        for tier in tiers:
            t_min = tier.get("min_volume", 0)
            t_max = tier.get("max_volume", 0)
            t_price = tier.get("price_per_unit", 0)
            t_currency = tier.get("currency", "EUR")
            is_active = (t_min <= active_total <= t_max) if active_total else False
            range_label = f"{t_min:,} ~ {t_max:,}" if t_max < 999999 else f"{t_min:,}+"
            row_class = "bg-emerald-50/60 text-emerald-900 font-semibold" if is_active else "text-text-primary"
            tier_rows += f'''
            <tr class="{row_class}">
                <td class="px-2 py-1 border-b border-surface-container-highest">{range_label}</td>
                <td class="px-2 py-1 border-b border-surface-container-highest text-right">{self.format_currency(t_price, t_currency)}</td>
            </tr>
            '''

        applied_row = (
            f'<div class="flex justify-between"><span class="text-text-secondary">적용 단가</span>'
            f'<span class="text-emerald-700 font-semibold">{self.format_currency(active_unit_price, sub_details.get("currency", "EUR"))}</span></div>'
            if active_unit_price is not None else ''
        )

        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">payments</span>
                <h2 class="font-headline-md text-headline-md text-primary">구독료 구간표</h2>
            </div>
            <table class="w-full font-body-sm text-body-sm">
                <thead>
                    <tr class="text-text-secondary">
                        <th class="px-2 py-1 text-left font-label-sm text-label-sm uppercase">누적건수</th>
                        <th class="px-2 py-1 text-right font-label-sm text-label-sm uppercase">단가</th>
                    </tr>
                </thead>
                <tbody>{tier_rows}</tbody>
            </table>
            <div class="flex flex-col gap-xs mt-md pt-sm border-t border-surface-container-highest font-body-sm text-body-sm">
                <div class="flex justify-between"><span class="text-text-secondary">기존 누적</span><span class="text-text-primary font-semibold">{existing_volume:,}건</span></div>
                <div class="flex justify-between"><span class="text-text-secondary">신규 추가</span><span class="text-text-primary font-semibold">{sub_details.get("new_volume", 0):,}건</span></div>
                <div class="flex justify-between"><span class="text-text-secondary">신규 누적</span><span class="text-emerald-700 font-semibold">{active_total:,}건</span></div>
                {applied_row}
            </div>
        </section>
        '''

    def render_tab_1_2_decision(self) -> str:
        """Render Tab 1-2: System Decision Tree."""
        if not self.report_data:
            return ""

        flowchart = self.render_decision_tree_section(include_outer=True)

        return f'''
        <div class="flex flex-col gap-xl">
            {flowchart}
        </div>
        '''

    def render_tab_1_3_tco(self) -> str:
        """Render Tab 1-3: Contract Volume & 10Y TCO."""
        if not self.report_data:
            return ""

        tabs = self.report_data.get("tabs", {})
        tco = tabs.get("tab_1_3_tco", {})

        build_cost = tco.get("build_cost", 0)
        customization_cost = tco.get("customization_cost", 0)
        annual_subscription = tco.get("annual_subscription", 0)
        annual_maintenance = tco.get("annual_maintenance", 0)
        operations_10y = tco.get("operations_10y", 0)
        total_tco = tco.get("total_tco_10y", 0)
        currency = tco.get("currency", "EUR")

        subscription_details = tco.get("subscription_details", {})

        items_section = self.render_items_section(
            tco.get("items", []),
            title="계약 규모 산정 근거 항목",
            icon="table_chart",
        )

        # Waterfall steps
        wf_steps = [
            {"label": "구축비", "value": build_cost},
            {"label": "특화개발", "value": customization_cost},
            {"label": "유지비(10Y)", "value": annual_maintenance * 10 + annual_subscription * 10},
            {"label": "운영비(10Y)", "value": operations_10y},
            {"label": "총 TCO", "value": total_tco, "is_total": True},
        ]
        waterfall_html = self.render_waterfall_chart(
            "10년 TCO 구성 분해 (워터폴)", "stacked_bar_chart", wf_steps, currency
        )

        # 10-year cumulative area
        one_off = build_cost + customization_cost
        recurring_annual = annual_subscription + annual_maintenance
        area_html = self.render_cumulative_area_chart(
            "10년 누적 비용 추이", "trending_up",
            one_off=one_off, annual_recurring=recurring_annual,
            operations_10y=operations_10y, years=10, currency=currency,
        )

        # Step chart for subscription tiers
        tiers = tco.get("subscription_tiers", []) or []
        active_total = subscription_details.get("total_volume", 0)
        step_html = self.render_step_chart(
            "구독료 구간 (전체 소급)", "stairs",
            tiers=tiers, current_volume=active_total, currency=currency,
        )

        # KPI cards (총 TCO / 구축기간 / 예상 계약건수)
        kpi_html = ""
        for label, value, icon in [
            ("총 10년 TCO", self.format_currency(total_tco, currency), "payments"),
            ("예상 구축 기간", f"{tco.get('build_months', 0):.1f}M", "schedule"),
            ("예상 계약건수", f"{tco.get('expected_contracts', 0):,}건", "fact_check"),
        ]:
            kpi_html += f'''
            <div class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow flex flex-col">
                <div class="flex items-center justify-between mb-sm">
                    <span class="font-label-md text-label-md text-primary uppercase tracking-wider">{label}</span>
                    <span class="material-symbols-outlined text-primary text-[24px]">{icon}</span>
                </div>
                <span class="font-display-lg text-display-lg text-primary leading-none">{value}</span>
            </div>
            '''

        return f'''
        <div class="flex flex-col gap-xl">
            <div class="grid grid-cols-3 gap-gutter">
                {kpi_html}
            </div>
            {waterfall_html}
            <div class="grid grid-cols-12 gap-gutter">
                <div class="col-span-7">{area_html}</div>
                <div class="col-span-5">{step_html}</div>
            </div>
            {items_section}
        </div>
        '''

    def render_data_quality_section(self) -> str:
        """Render data quality indicator section."""
        if not self.report_data:
            return ""

        quality = self.report_data.get("data_quality", {})
        completeness = quality.get("completeness_pct", 0)
        total_items = quality.get("total_items", 0)
        target_items = quality.get("target_items", 0)
        timeseries_coverage = quality.get("timeseries_coverage", 0)

        status_color = "emerald" if completeness >= 95 else "yellow" if completeness >= 80 else "red"

        return f'''
        <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
            <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">fact_check</span>
                <h2 class="font-headline-md text-headline-md text-primary">Data Quality</h2>
            </div>
            <div class="flex flex-col gap-md">
                <div class="flex justify-between items-center p-sm bg-surface rounded-lg border border-surface-container-highest">
                    <div class="flex items-center gap-sm">
                        <div class="w-8 h-8 rounded-full bg-secondary-container/20 flex items-center justify-center">
                            <span class="material-symbols-outlined text-secondary text-[18px]">database</span>
                        </div>
                        <span class="font-label-md text-label-md text-text-primary">Data Completeness</span>
                    </div>
                    <div class="flex items-center gap-xs bg-{status_color}-100/50 text-{status_color}-800 px-2 py-1 rounded-full border border-{status_color}-200">
                        <span class="material-symbols-outlined text-[14px]">check_circle</span>
                        <span class="font-label-sm text-label-sm uppercase tracking-wide">{completeness:.1f}%</span>
                    </div>
                </div>
                <div class="flex justify-between items-center p-sm bg-surface rounded-lg border border-surface-container-highest">
                    <span class="text-body-sm text-text-secondary">Items Present</span>
                    <span class="font-semibold text-body-sm text-text-primary">{total_items} / {target_items}</span>
                </div>
                <div class="flex justify-between items-center p-sm bg-surface rounded-lg border border-surface-container-highest">
                    <span class="text-body-sm text-text-secondary">Timeseries Coverage</span>
                    <span class="font-semibold text-body-sm text-text-primary">{timeseries_coverage:.1f}%</span>
                </div>
            </div>
        </section>
        '''

    def _render_news_card(self, news_item: Dict[str, Any]) -> str:
        """Render a single news entry from the 외부 이슈 스캔 list."""
        category = news_item.get("news_category", "")
        headline = news_item.get("headline", "")
        so_what = news_item.get("so_what", "")
        publisher = news_item.get("publisher", "")
        pub_date = news_item.get("pub_date", "")
        url = news_item.get("url", "")

        is_stub = headline == "조사 필요"
        if is_stub:
            return f'''
            <div class="p-md bg-yellow-50 border border-yellow-200 rounded-lg">
                <div class="flex items-center gap-xs mb-xs">
                    <span class="material-symbols-outlined text-yellow-700 text-[18px]">warning</span>
                    <span class="font-label-md text-label-md text-yellow-800 uppercase">{category}</span>
                </div>
                <p class="font-body-sm text-body-sm text-yellow-700">관련 화이트리스트 이슈 미확보 — 실사 단계 보강 필요</p>
            </div>
            '''

        link = f'<a class="text-primary underline" href="{url}" target="_blank" rel="noopener">원문</a>' if url else ''
        return f'''
        <div class="p-md bg-surface rounded-lg border border-surface-container-highest flex flex-col gap-xs">
            <div class="flex items-center gap-xs flex-wrap">
                <span class="bg-orange-100 text-orange-700 border border-orange-200 px-2 py-0.5 rounded-full font-label-sm text-label-sm uppercase">{category}</span>
                <span class="font-label-sm text-label-sm text-text-secondary">{publisher} · {pub_date}</span>
            </div>
            <h4 class="font-label-md text-label-md text-text-primary leading-relaxed">{headline}</h4>
            <div class="bg-surface-container/60 p-sm rounded-md border-l-4 border-primary">
                <div class="flex items-center gap-xs mb-xs">
                    <span class="material-symbols-outlined text-primary text-[14px]">psychology</span>
                    <span class="font-label-sm text-label-sm text-primary uppercase">So What</span>
                </div>
                <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{so_what}</p>
            </div>
            {link}
        </div>
        '''

    def render_tab_1_4_market(self) -> str:
        """Render Tab 1-4: Market & Competition Background."""
        if not self.report_data:
            return ""

        market = self.report_data.get("tabs", {}).get("tab_1_4_market", {})
        items = market.get("items", [])
        competitors = market.get("competitors")
        entry_form = market.get("competitor_entry_form")
        brand_top10 = market.get("brand_top10")
        news = market.get("news")
        regulators = market.get("regulators")
        country_summary = market.get("country_summary")

        items_section = self.render_items_section(
            items,
            title="시장·경쟁 핵심 지표 (원천 데이터)",
            icon="leaderboard",
        )

        # ---------- Charts ----------
        # 1) 금융사 Top5 + 캡티브 강도 — horizontal bar
        fin_item = self._find_tab14_item("금융사 순위(Top 5)")
        fin_rows = []
        if fin_item and isinstance(fin_item.get("value"), list):
            for r in fin_item["value"][:5]:
                share_raw = str(r.get("market_share", "")).replace("약", "").replace("%", "").strip()
                try:
                    v = float(share_raw)
                except Exception:
                    v = 0
                fin_rows.append({"label": r.get("name", ""), "value": round(v, 1)})
        finance_chart = self.render_horizontal_bar_chart(
            "금융사 Top 5 (점유율)", "account_balance", fin_rows
        )

        # 2) OEM Top5
        oem_item = self._find_tab14_item("OEM 순위(Top 5)")
        oem_rows = []
        if oem_item and isinstance(oem_item.get("value"), list):
            for r in oem_item["value"][:5]:
                share_raw = str(r.get("market_share", "")).replace("약", "").replace("%", "").strip()
                try:
                    v = float(share_raw)
                except Exception:
                    v = 0
                oem_rows.append({"label": r.get("name", ""), "value": round(v, 1)})
        oem_chart = self.render_horizontal_bar_chart(
            "OEM Top 5 (점유율)", "directions_car", oem_rows
        )

        # 3) 경쟁사 금리 범위 — best effort: extract numbers
        rate_item = self._find_tab14_item("경쟁사 금리 범위")
        rate_chart = ""
        if rate_item:
            import re
            text = str(rate_item.get("value", ""))
            ranges = []
            # Patterns like "6~10%" / "0~3%"
            for m in re.finditer(r"(\d+(?:\.\d+)?)\s*[~\-–]\s*(\d+(?:\.\d+)?)\s*%", text):
                ranges.append({"lo": float(m.group(1)), "hi": float(m.group(2))})
            rb_rows = []
            if len(ranges) >= 1:
                rb_rows.append({"label": "신차 자동차대출", "lo": ranges[0]["lo"], "hi": ranges[0]["hi"], "accent": "#00204e"})
            if len(ranges) >= 2:
                rb_rows.append({"label": "캡티브 프로모", "lo": ranges[1]["lo"], "hi": ranges[1]["hi"], "accent": "#10b981"})
            single = re.search(r"평균.*?(\d+(?:\.\d+)?)\s*%", text)
            if single:
                v = float(single.group(1))
                rb_rows.append({"label": "소비자신용 평균", "lo": v, "hi": v, "accent": "#E63946"})
            if rb_rows:
                rate_chart = self.render_range_bar_chart("경쟁사 금리 범위", "percent", rb_rows)

        # 4) EV 보급률 + EV·ICE 잔존가치 라인차트
        ev_item = self._find_tab14_item("EV 보급률")
        rv_item = self._find_tab14_item("EV·ICE 잔존가치 리스크")
        line_series = []
        if ev_item and isinstance(ev_item.get("timeseries"), dict):
            ts = ev_item["timeseries"]
            line_series.append({
                "name": "EV 보급률",
                "color": "#005db7",
                "history": ts.get("history", []),
                "forecast": ts.get("forecast", []),
            })
        if rv_item and isinstance(rv_item.get("timeseries"), dict):
            ts = rv_item["timeseries"]
            line_series.append({
                "name": "EV/ICE 잔존가치(3년)",
                "color": "#E63946",
                "history": ts.get("history", []),
                "forecast": ts.get("forecast", []),
            })
        ev_chart = self.render_line_chart(
            "EV 보급률 · EV/ICE 잔존가치 추이", "battery_charging_full",
            line_series, y_label="%"
        )

        # 5) 평균 신차가격 KPI
        price_item = self._find_tab14_item("평균 신차가격")
        price_kpi_html = ""
        if price_item:
            val = price_item.get("value")
            unit = price_item.get("unit") or ""
            price_kpi_html = f'''
            <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow flex flex-col">
                <div class="flex items-center justify-between mb-sm">
                    <span class="font-label-md text-label-md text-primary uppercase tracking-wider">평균 신차가격</span>
                    <span class="material-symbols-outlined text-primary text-[24px]">sell</span>
                </div>
                <div class="flex items-baseline gap-xs">
                    <span class="font-display-lg text-display-lg text-primary leading-none">{val:,}</span>
                    <span class="font-body-md text-body-md text-text-secondary">{unit}</span>
                </div>
                <p class="font-body-sm text-body-sm text-text-secondary mt-sm leading-relaxed">{price_item.get('insight', '')}</p>
            </section>
            '''

        # Country summary block
        summary_html = ""
        if country_summary:
            summary_html = f'''
            <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
                <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                    <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">summarize</span>
                    <h2 class="font-headline-md text-headline-md text-primary">국가 정성 요약</h2>
                </div>
                <p class="font-body-md text-body-md text-on-surface-variant leading-relaxed mb-md">{country_summary.get("value", "")}</p>
                <div class="bg-surface-container/60 p-md rounded-lg border-l-4 border-primary">
                    <div class="flex items-center gap-xs mb-xs">
                        <span class="material-symbols-outlined text-primary text-[14px]">lightbulb</span>
                        <span class="font-label-sm text-label-sm text-primary uppercase">인사이트</span>
                    </div>
                    <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{country_summary.get("insight", "")}</p>
                </div>
            </section>
            '''

        # Competitors / entry form / brand block
        competitor_cards = ""
        if competitors:
            comp_list = competitors.get("value") or []
            competitor_cards = f'''
            <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
                <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                    <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">groups</span>
                    <h2 class="font-headline-md text-headline-md text-primary">경쟁사 현황</h2>
                </div>
                <div class="grid grid-cols-2 gap-sm mb-md">
                    {"".join(f'<div class="p-sm bg-surface rounded-lg border border-surface-container-highest font-body-sm text-body-sm">{c}</div>' for c in comp_list)}
                </div>
                {f'<p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed mb-sm"><strong>진출 형태:</strong> {entry_form.get("value", "")}</p>' if entry_form else ''}
                <div class="bg-surface-container/60 p-sm rounded-md border-l-4 border-primary">
                    <div class="flex items-center gap-xs mb-xs">
                        <span class="material-symbols-outlined text-primary text-[14px]">lightbulb</span>
                        <span class="font-label-sm text-label-sm text-primary uppercase">인사이트</span>
                    </div>
                    <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{competitors.get("insight", "")}</p>
                </div>
            </section>
            '''

        brand_html = ""
        if brand_top10:
            brands = brand_top10.get("value") or []
            brand_html = f'''
            <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
                <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                    <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">directions_car</span>
                    <h2 class="font-headline-md text-headline-md text-primary">브랜드 Top10</h2>
                </div>
                <ol class="grid grid-cols-2 gap-sm font-body-sm text-body-sm list-decimal list-inside">
                    {"".join(f'<li class="p-xs">{b}</li>' for b in brands)}
                </ol>
                <div class="bg-surface-container/60 p-sm rounded-md border-l-4 border-primary mt-md">
                    <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{brand_top10.get("insight", "")}</p>
                </div>
            </section>
            '''

        regulators_html = ""
        if regulators:
            regulators_html = f'''
            <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
                <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                    <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">policy</span>
                    <h2 class="font-headline-md text-headline-md text-primary">규제기관</h2>
                </div>
                <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed mb-sm">{regulators.get("value", "")}</p>
                <div class="bg-surface-container/60 p-sm rounded-md border-l-4 border-primary">
                    <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{regulators.get("insight", "")}</p>
                </div>
            </section>
            '''

        news_html = ""
        if news:
            news_list = news.get("value") or []
            news_cards = "".join(self._render_news_card(n) for n in news_list)
            news_html = f'''
            <section class="bg-surface-container-lowest border border-surface-border rounded-xl p-lg card-shadow">
                <div class="flex items-center gap-sm mb-md pb-sm border-b border-surface-border">
                    <span class="material-symbols-outlined text-primary" style="font-variation-settings: 'FILL' 1;">newspaper</span>
                    <h2 class="font-headline-md text-headline-md text-primary">외부 이슈 스캔</h2>
                </div>
                <div class="flex flex-col gap-md">
                    {news_cards}
                </div>
                <div class="bg-surface-container/60 p-sm rounded-md border-l-4 border-primary mt-md">
                    <div class="flex items-center gap-xs mb-xs">
                        <span class="material-symbols-outlined text-primary text-[14px]">lightbulb</span>
                        <span class="font-label-sm text-label-sm text-primary uppercase">종합 인사이트</span>
                    </div>
                    <p class="font-body-sm text-body-sm text-on-surface-variant leading-relaxed">{news.get("insight", "")}</p>
                </div>
            </section>
            '''

        return f'''
        <div class="flex flex-col gap-xl">
            {summary_html}
            <div class="grid grid-cols-12 gap-gutter">
                <div class="col-span-6">{finance_chart}</div>
                <div class="col-span-6">{oem_chart}</div>
            </div>
            {ev_chart}
            <div class="grid grid-cols-12 gap-gutter">
                <div class="col-span-8">{rate_chart}</div>
                <div class="col-span-4">{price_kpi_html}</div>
            </div>
            <div class="grid grid-cols-12 gap-gutter">
                <div class="col-span-6">{competitor_cards}</div>
                <div class="col-span-6">{brand_html}</div>
            </div>
            {regulators_html}
            {news_html}
            {items_section}
        </div>
        '''

    def render_tabs_navigation(self) -> str:
        """Render tab navigation bar."""
        tabs = [
            {"id": "tab-0", "label": "요약",                  "icon": "summarize"},
            {"id": "tab-1", "label": "유사도 점수",            "icon": "radar"},
            {"id": "tab-2", "label": "시스템 결정 트리",       "icon": "account_tree"},
            {"id": "tab-3", "label": "계약건수·구독료·TCO",    "icon": "analytics"},
            {"id": "tab-4", "label": "시장·경쟁 배경",         "icon": "public"},
        ]

        tabs_html = ""
        for tab in tabs:
            tabs_html += f'''
            <button class="tab-button flex items-center gap-sm px-md py-sm rounded-lg font-label-md text-label-md uppercase tracking-wider transition-colors hover:bg-surface-container text-text-secondary"
                    data-tab="{tab['id']}">
                <span class="material-symbols-outlined text-[18px]">{tab['icon']}</span>
                <span>{tab['label']}</span>
            </button>
            '''

        return f'''
        <div class="bg-surface-container-lowest border border-surface-border rounded-xl p-sm mb-xl sticky top-0 z-10 card-shadow">
            <div class="flex gap-sm overflow-x-auto">
                {tabs_html}
            </div>
        </div>
        '''

    def generate_html(self) -> str:
        """Generate complete HTML report.

        Returns:
            HTML string
        """
        if not self.report_data:
            self.load_report()

        target = self.report_data.get("target", {})
        country_code = target.get("country", "XX")
        country_name = self.get_country_name(country_code)
        report_id = self.report_data.get("report_id", "RPT_XXX")
        generated_at = self.report_data.get("generated_at", "")

        # Format date
        try:
            dt = datetime.fromisoformat(generated_at)
            formatted_date = dt.strftime("%b %d, %Y")
        except:
            formatted_date = generated_at

        flag_url = self.get_country_flag_url(country_code)

        # Render tab navigation
        tabs_nav = self.render_tabs_navigation()

        # Render all tabs
        tab_0 = self.render_tab_0_summary()
        tab_1 = self.render_tab_1_1_similarity()
        tab_2 = self.render_tab_1_2_decision()
        tab_3 = self.render_tab_1_3_tco()
        tab_4 = self.render_tab_1_4_market()

        return f'''<!DOCTYPE html>
<html class="light" lang="en">
<head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <title>{country_name} - Country TCO Report</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800;900&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
    <script id="tailwind-config">
        tailwind.config = {{
            darkMode: "class",
            theme: {{
                extend: {{
                    "colors": {{
                        "accent-red": "#E63946",
                        "surface-bright": "#fbf9f9",
                        "on-primary-fixed-variant": "#1c4489",
                        "tertiary-fixed": "#ffdad8",
                        "primary-fixed-dim": "#aec6ff",
                        "inverse-surface": "#303031",
                        "surface-container-lowest": "#ffffff",
                        "secondary": "#005db7",
                        "on-tertiary": "#ffffff",
                        "on-primary": "#ffffff",
                        "error": "#ba1a1a",
                        "on-tertiary-fixed-variant": "#92001c",
                        "secondary-fixed": "#d6e3ff",
                        "tertiary": "#4d000a",
                        "inverse-primary": "#aec6ff",
                        "primary-container": "#003478",
                        "on-primary-container": "#7d9fe9",
                        "primary-fixed": "#d8e2ff",
                        "on-secondary-container": "#003268",
                        "surface-dim": "#dbdad9",
                        "surface-container-low": "#f5f3f3",
                        "surface-border": "#DCDCDC",
                        "on-error": "#ffffff",
                        "surface-container-highest": "#e3e2e2",
                        "surface-container": "#efeded",
                        "secondary-fixed-dim": "#a9c7ff",
                        "on-tertiary-fixed": "#410007",
                        "surface-variant": "#e3e2e2",
                        "on-tertiary-container": "#ff7576",
                        "inverse-on-surface": "#f2f0f0",
                        "outline": "#747782",
                        "surface-light": "#F8F9FA",
                        "text-secondary": "#555555",
                        "on-primary-fixed": "#001a43",
                        "surface-tint": "#395da2",
                        "on-secondary-fixed": "#001b3d",
                        "on-surface-variant": "#434751",
                        "on-secondary-fixed-variant": "#00468c",
                        "on-error-container": "#93000a",
                        "outline-variant": "#c4c6d2",
                        "text-disabled": "#BEBEBE",
                        "secondary-container": "#599bfe",
                        "tertiary-fixed-dim": "#ffb3b1",
                        "on-secondary": "#ffffff",
                        "background": "#fbf9f9",
                        "error-container": "#ffdad6",
                        "surface": "#fbf9f9",
                        "on-background": "#1b1c1c",
                        "text-primary": "#000000",
                        "surface-container-high": "#e9e8e7",
                        "primary": "#00204e",
                        "tertiary-container": "#750015",
                        "on-surface": "#1b1c1c"
                    }},
                    "borderRadius": {{
                        "DEFAULT": "0.25rem",
                        "lg": "0.5rem",
                        "xl": "0.75rem",
                        "full": "9999px"
                    }},
                    "spacing": {{
                        "sm": "8px",
                        "margin-desktop": "48px",
                        "gutter": "24px",
                        "base": "4px",
                        "margin-mobile": "16px",
                        "xl": "32px",
                        "lg": "24px",
                        "xs": "4px",
                        "md": "16px"
                    }},
                    "fontFamily": {{
                        "headline-md": ["Hanken Grotesk"],
                        "label-md": ["Hanken Grotesk"],
                        "headline-lg": ["Hanken Grotesk"],
                        "body-sm": ["Hanken Grotesk"],
                        "display-lg": ["Hanken Grotesk"],
                        "label-sm": ["Hanken Grotesk"],
                        "body-lg": ["Hanken Grotesk"],
                        "headline-lg-mobile": ["Hanken Grotesk"],
                        "body-md": ["Hanken Grotesk"]
                    }},
                    "fontSize": {{
                        "headline-md": ["24px", {{"lineHeight": "32px", "fontWeight": "600"}}],
                        "label-md": ["12px", {{"lineHeight": "16px", "letterSpacing": "0.05em", "fontWeight": "600"}}],
                        "headline-lg": ["32px", {{"lineHeight": "40px", "letterSpacing": "-0.01em", "fontWeight": "700"}}],
                        "body-sm": ["14px", {{"lineHeight": "20px", "fontWeight": "400"}}],
                        "display-lg": ["48px", {{"lineHeight": "56px", "letterSpacing": "-0.02em", "fontWeight": "700"}}],
                        "label-sm": ["11px", {{"lineHeight": "14px", "fontWeight": "500"}}],
                        "body-lg": ["18px", {{"lineHeight": "28px", "fontWeight": "400"}}],
                        "headline-lg-mobile": ["24px", {{"lineHeight": "32px", "fontWeight": "700"}}],
                        "body-md": ["16px", {{"lineHeight": "24px", "fontWeight": "400"}}]
                    }}
                }}
            }}
        }}
    </script>
    <style>
        body {{ font-family: 'Hanken Grotesk', sans-serif; }}
        .backdrop-blur-md {{ backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }}
        .card-shadow {{ box-shadow: 0 4px 8px rgba(0, 32, 78, 0.12); }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .tab-button.active {{
            background-color: #00204e;
            color: white;
        }}
    </style>
</head>
<body class="bg-surface min-h-screen font-body-md text-text-primary antialiased">
<div class="w-full flex flex-col relative bg-surface">
    <header class="border-b border-surface-border px-margin-desktop py-lg shrink-0">
        <div class="flex justify-between items-start gap-gutter max-w-7xl mx-auto">
            <div class="flex gap-lg items-center">
                <div class="w-16 h-16 rounded-full overflow-hidden border border-surface-border shrink-0 bg-surface-container flex items-center justify-center">
                    <img alt="{country_name} Flag" class="w-full h-full object-cover" src="{flag_url}"/>
                </div>
                <div>
                    <div class="flex items-center gap-sm mb-xs">
                        <h1 class="font-headline-lg text-headline-lg text-primary tracking-tight">{country_name}</h1>
                        <span class="bg-secondary-container/20 text-secondary px-2 py-1 rounded-sm font-label-sm text-label-sm uppercase tracking-wider">{country_code}</span>
                    </div>
                    <div class="flex items-center gap-md text-text-secondary font-body-sm text-body-sm">
                        <div class="flex items-center gap-xs">
                            <span class="material-symbols-outlined text-[16px]">tag</span>
                            <span>ID: <span class="font-semibold text-text-primary">{report_id}</span></span>
                        </div>
                        <span class="w-[1px] h-4 bg-surface-border"></span>
                        <div class="flex items-center gap-xs">
                            <span class="material-symbols-outlined text-[16px]">calendar_today</span>
                            <span>Generated: <span class="text-text-primary">{formatted_date}</span></span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </header>
    <main class="flex-1 p-margin-desktop">
        <div class="max-w-7xl mx-auto">
            {tabs_nav}

            <div class="tab-content active" id="tab-0">{tab_0}</div>
            <div class="tab-content" id="tab-1">{tab_1}</div>
            <div class="tab-content" id="tab-2">{tab_2}</div>
            <div class="tab-content" id="tab-3">{tab_3}</div>
            <div class="tab-content" id="tab-4">{tab_4}</div>
        </div>
    </main>
</div>

<script>
    // Tab switching functionality
    document.querySelectorAll('.tab-button').forEach(button => {{
        button.addEventListener('click', () => {{
            const tabId = button.getAttribute('data-tab');

            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {{
                content.classList.remove('active');
            }});

            // Remove active class from all buttons
            document.querySelectorAll('.tab-button').forEach(btn => {{
                btn.classList.remove('active');
            }});

            // Show selected tab content
            document.getElementById(tabId).classList.add('active');

            // Add active class to clicked button
            button.classList.add('active');
        }});
    }});

    // Set first tab as active
    document.querySelector('.tab-button').classList.add('active');
</script>
</body>
</html>'''

    def save_html(self, output_path: Optional[str] = None) -> str:
        """Save generated HTML to file.

        Args:
            output_path: Optional custom output path

        Returns:
            Path to saved HTML file
        """
        if not output_path:
            # Default: sibling 'html' directory next to the JSON's 'data' folder
            json_path = Path(self.report_json_path)
            country_root = json_path.parent.parent  # e.g. .../country/ES
            html_dir = country_root / "html"
            html_dir.mkdir(parents=True, exist_ok=True)
            output_path = html_dir / f"{json_path.stem}.html"

        html = self.generate_html()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(output_path)


def main():
    """CLI entry point for rendering."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python country_report_renderer.py <report_json_path> [output_html_path]")
        print("Example: python country_report_renderer.py storage/report/country/data/ES/RPT_CTR_ES_001.json")
        sys.exit(1)

    report_json_path = sys.argv[1]
    output_html_path = sys.argv[2] if len(sys.argv) > 2 else None

    renderer = CountryReportRenderer(report_json_path)

    if not renderer.load_report():
        sys.exit(1)

    html_path = renderer.save_html(output_html_path)
    print(f"✅ HTML report generated: {html_path}")

    return 0


if __name__ == "__main__":
    main()
