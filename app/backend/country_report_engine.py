#!/usr/bin/env python3
"""
Country Report Engine: Single-Country TCO (Total Cost of Ownership) Analysis

Converts single country research JSON (schema v1.1) into country-level reports
with tabs for market analysis, regulatory requirements, IT infrastructure,
and competitive landscape.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class CountryReportEngine:
    """Generate country-level (single-country TCO) reports from country research data."""

    TYPE1_TABS = {
        "1-1": {
            "name": "Similarity Scoring (vs Baseline)",
            "required_fields": [
                "솔루션 유형", "디지털 채널 성숙도", "디지털 딜러 성숙도",
                "라이선스 체제(세그먼트별)", "데이터 현지화 의무", "차량회수 절차 용이성"
            ],
            "data_characteristics": ["score_multiaxis", "single_value"]
        },
        "1-2": {
            "name": "System Decision Tree",
            "required_fields": ["금리 상한 규제", "외환·배당 송금 자유도",
                              "의무보험 규제", "신용생명보험 규제"],
            "data_characteristics": ["qualitative", "status_matrix"]
        },
        "1-3": {
            "name": "Contract Volume & 10Y TCO",
            "required_fields": ["신차 판매대수", "금융 이용률(신차)", "구매 패턴(할부·리스 비중)",
                              "캡티브 강도(점유율)", "평균 신차가격"],
            "data_characteristics": ["single_value", "composition", "timeseries"]
        },
        "1-4": {
            "name": "Market & Competition Background",
            "required_fields": ["금융사 순위", "1위사 점유율", "경쟁사 금리 범위",
                              "OEM 순위", "EV 보급률", "EV·ICE 잔존가치 리스크"],
            "data_characteristics": ["ranking", "timeseries", "qualitative"]
        }
    }

    def __init__(self, country_data_path: str, output_base_path: str = "storage/report"):
        """Initialize country report engine with country data.

        Args:
            country_data_path: Path to single country JSON file
            output_base_path: Base output directory for reports
        """
        self.country_data_path = country_data_path
        self.output_base = output_base_path
        self.country_data: Optional[Dict] = None
        self.report_type = "TYPE1"

    def load_country_data(self) -> bool:
        """Load country research JSON file."""
        try:
            with open(self.country_data_path, 'r', encoding='utf-8') as f:
                self.country_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading country data: {e}")
            return False

    def analyze_data_structure(self) -> Dict[str, Any]:
        """Analyze country data structure and identify gaps."""
        if not self.country_data:
            return {"error": "No country data loaded"}

        analysis = {
            "country": self.country_data.get("country", "N/A"),
            "code": self.country_data.get("code", "N/A"),
            "schema_version": self.country_data.get("schema_version", "N/A"),
            "total_items": len(self.country_data.get("items", [])),
            "items_by_category": {},
            "data_quality": {}
        }

        # Categorize items
        for item in self.country_data.get("items", []):
            category = item.get("category", "unknown")
            if category not in analysis["items_by_category"]:
                analysis["items_by_category"][category] = []
            analysis["items_by_category"][category].append({
                "item": item.get("item", ""),
                "role": item.get("role", ""),
                "has_timeseries": "timeseries" in item,
                "source_tier": item.get("tier", "N/A")
            })

        # Analyze completeness
        analysis["data_quality"] = self._assess_data_quality()

        return analysis

    def _assess_data_quality(self) -> Dict[str, Any]:
        """Assess completeness and quality of country data."""
        quality = {
            "overall_completeness": "N/A",
            "timeseries_coverage": 0,
            "source_tiers": {"tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0},
            "data_sources": set(),
            "gaps_by_tab": {}
        }

        items = self.country_data.get("items", [])
        total_items = len(items)

        if total_items == 0:
            return quality

        timeseries_count = sum(1 for item in items if "timeseries" in item)
        quality["timeseries_coverage"] = (timeseries_count / total_items) * 100

        for item in items:
            tier = item.get("tier", 0)
            tier_key = f"tier{tier}"
            if tier_key in quality["source_tiers"]:
                quality["source_tiers"][tier_key] += 1

            source = item.get("source", "unknown")
            quality["data_sources"].add(source)

        quality["gaps_by_tab"] = self._identify_tab_gaps(items)
        quality["data_sources"] = list(quality["data_sources"])
        return quality

    def _identify_tab_gaps(self, items: List[Dict]) -> Dict[str, List[str]]:
        """Identify which tab data requirements are not met."""
        gaps = {}
        item_names = {item.get("item", ""): item for item in items}

        for tab_id, tab_spec in self.TYPE1_TABS.items():
            missing = []
            for required_field in tab_spec.get("required_fields", []):
                if required_field not in item_names:
                    missing.append(required_field)
            if missing:
                gaps[f"Type1-Tab-{tab_id}"] = missing

        return gaps

    def generate_gap_report(self) -> Dict[str, Any]:
        """Generate comprehensive gap analysis report for Type 1."""
        self.load_country_data()
        analysis = self.analyze_data_structure()

        report = {
            "report_type": "gap_analysis",
            "analysis_type": "TYPE1",
            "country": analysis["country"],
            "country_code": analysis["code"],
            "generated_at": datetime.now().isoformat(),
            "schema_version": analysis["schema_version"],

            "summary": {
                "total_items": analysis["total_items"],
                "target_items": 48,
                "completeness_pct": (analysis["total_items"] / 48 * 100) if analysis["total_items"] <= 48
                                   else (48 / analysis["total_items"] * 100)
            },

            "by_category": analysis["items_by_category"],
            "data_quality": analysis["data_quality"],
            "critical_gaps": self._identify_critical_gaps(analysis),
            "type1_readiness": self._assess_type1_readiness(analysis)
        }

        return report

    def _identify_critical_gaps(self, analysis: Dict) -> List[Dict[str, Any]]:
        """Identify critical data gaps blocking report generation."""
        critical = []
        gaps_by_tab = analysis["data_quality"].get("gaps_by_tab", {})

        for tab, missing_fields in gaps_by_tab.items():
            if len(missing_fields) > 0:
                critical.append({
                    "tab": tab,
                    "missing_fields": missing_fields,
                    "count": len(missing_fields),
                    "severity": "HIGH" if len(missing_fields) > 3 else "MEDIUM"
                })

        return critical

    def _assess_type1_readiness(self, analysis: Dict) -> Dict[str, Any]:
        """Assess readiness to generate Type 1 report."""
        readiness = {
            "can_generate": True,
            "tabs": {}
        }

        gaps_by_tab = analysis["data_quality"].get("gaps_by_tab", {})

        for tab_id in self.TYPE1_TABS.keys():
            tab_key = f"Type1-Tab-{tab_id}"
            missing = gaps_by_tab.get(tab_key, [])

            readiness["tabs"][tab_id] = {
                "name": self.TYPE1_TABS[tab_id]["name"],
                "ready": len(missing) == 0,
                "missing_count": len(missing),
                "missing_fields": missing
            }

            if len(missing) > 0:
                readiness["can_generate"] = False

        return readiness

    def save_gap_report(self, gap_report: Dict[str, Any]) -> str:
        """Save gap analysis report to file with RPT_CTR_{code}_nnn.json naming."""
        country_code = gap_report["country_code"]
        output_dir = Path(self.output_base) / "analysis" / country_code
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find next sequence number
        existing_files = list(output_dir.glob(f"RPT_CTR_{country_code}_*.json"))
        next_num = 1
        if existing_files:
            max_num = max(
                int(f.stem.split("_")[-1])
                for f in existing_files
                if f.stem.split("_")[-1].isdigit()
            )
            next_num = max_num + 1

        output_file = output_dir / f"RPT_CTR_{country_code}_{next_num:03d}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(gap_report, f, ensure_ascii=False, indent=2)

        return str(output_file)

    def generate_readable_gap_report(self, gap_report: Dict[str, Any]) -> str:
        """Generate human-readable gap analysis report."""
        lines = [
            f"\n{'='*70}",
            f"COUNTRY GAP ANALYSIS: {gap_report['country']} ({gap_report['country_code']})",
            f"{'='*70}",
            f"Generated: {gap_report['generated_at']}",
            f"Schema Version: {gap_report['schema_version']}",
            ""
        ]

        summary = gap_report["summary"]
        lines.append("SUMMARY")
        lines.append(f"  Total Items Present: {summary['total_items']}/{summary['target_items']}")
        lines.append(f"  Completeness: {summary['completeness_pct']:.1f}%")
        lines.append("")

        lines.append("ITEMS BY CATEGORY:")
        for category, items in gap_report["by_category"].items():
            lines.append(f"  {category}: {len(items)} items")
            for item in items[:3]:
                lines.append(f"    - {item['item']} (role: {item['role']}, tier: {item.get('source_tier')})")
            if len(items) > 3:
                lines.append(f"    ... and {len(items)-3} more")
        lines.append("")

        lines.append("DATA QUALITY METRICS:")
        quality = gap_report["data_quality"]
        lines.append(f"  Timeseries Coverage: {quality.get('timeseries_coverage', 0):.1f}%")
        lines.append(f"  Source Tiers: {quality.get('source_tiers', {})}")
        lines.append("")

        lines.append("CRITICAL GAPS:")
        critical = gap_report["critical_gaps"]
        if critical:
            for gap in critical:
                lines.append(f"  [{gap['severity']}] {gap['tab']}")
                lines.append(f"    Missing {gap['count']} fields: {', '.join(gap['missing_fields'][:3])}")
                if gap['count'] > 3:
                    lines.append(f"    ... and {gap['count']-3} more")
        else:
            lines.append("  None - all required fields present!")
        lines.append("")

        lines.append("COUNTRY REPORT (SINGLE-COUNTRY TCO) READINESS:")
        type1 = gap_report["type1_readiness"]
        lines.append(f"  Can Generate: {'YES ✓' if type1['can_generate'] else 'NO ✗'}")
        for tab_id, status in type1["tabs"].items():
            ready_icon = "✓" if status["ready"] else "✗"
            lines.append(f"  Tab {tab_id}: {ready_icon} {status['name']}")
            if not status["ready"]:
                lines.append(f"           Missing: {', '.join(status['missing_fields'][:2])}")
        lines.append("")

        lines.append(f"{'='*70}\n")

        return "\n".join(lines)


def main():
    """CLI entry point for country report generation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python country_report_engine.py <country_data_json> [output_base_path]")
        print("Example: python country_report_engine.py data/country/ES_latest.json")
        sys.exit(1)

    country_data_path = sys.argv[1]
    output_base = sys.argv[2] if len(sys.argv) > 2 else "storage/report"

    engine = CountryReportEngine(country_data_path, output_base)

    if not engine.load_country_data():
        sys.exit(1)

    gap_report = engine.generate_gap_report()
    readable = engine.generate_readable_gap_report(gap_report)
    print(readable)

    json_path = engine.save_gap_report(gap_report)
    print(f"📁 Country gap analysis JSON saved: {json_path}")

    return 0 if gap_report.get("type1_readiness", {}).get("can_generate") else 1


if __name__ == "__main__":
    main()
