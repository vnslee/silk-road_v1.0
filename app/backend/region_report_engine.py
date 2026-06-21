#!/usr/bin/env python3
"""
Region Report Engine: Region-Based Ranking and Comparative Analysis

Converts region research data (aggregating multiple countries) into region-level reports
with tabs for market ranking, attractiveness scoring, competitive positioning,
and strategic recommendations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class RegionReportEngine:
    """Generate region-level (ranking and comparative) reports from regional research data."""

    TYPE2_TABS = {
        "2-0": {
            "name": "Kill Switch Filter",
            "required_fields": ["외국인지분한도", "외환송금", "데이터현지화",
                              "국가신용등급"],
            "data_characteristics": ["status_matrix"]
        },
        "2-1": {
            "name": "Business Attractiveness",
            "required_fields": ["GDP성장률", "자동차판매CAGR", "금융침투율",
                              "경쟁강도", "디지털성숙도"],
            "data_characteristics": ["ranking", "composition", "timeseries"]
        },
        "2-2": {
            "name": "IT/Speed-to-Market Similarity",
            "required_fields": ["솔루션유형", "디지털채널성숙도",
                              "라이선스종류", "데이터현지화", "상품판매현황"],
            "data_characteristics": ["score_multiaxis", "ranking"]
        },
        "2-3": {
            "name": "Market Background",
            "required_fields": ["OEM순위", "브랜드Top10", "구매유형",
                              "화이트스페이스"],
            "data_characteristics": ["ranking", "composition", "qualitative"]
        }
    }

    def __init__(self, region_data_path: str, output_base_path: str = "storage/report"):
        """Initialize region report engine with region data.

        Args:
            region_data_path: Path to region JSON file (containing multiple countries)
            output_base_path: Base output directory for reports
        """
        self.region_data_path = region_data_path
        self.output_base = output_base_path
        self.region_data: Optional[Dict] = None
        self.report_type = "TYPE2"

    def load_region_data(self) -> bool:
        """Load region research JSON file."""
        try:
            with open(self.region_data_path, 'r', encoding='utf-8') as f:
                self.region_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading region data: {e}")
            return False

    def analyze_region_structure(self) -> Dict[str, Any]:
        """Analyze region data structure and identify gaps across countries."""
        if not self.region_data:
            return {"error": "No region data loaded"}

        analysis = {
            "region": self.region_data.get("region", "N/A"),
            "code": self.region_data.get("code", "N/A"),
            "schema_version": self.region_data.get("schema_version", "N/A"),
            "countries": [],
            "total_countries": 0,
            "items_by_category": {},
            "data_quality": {}
        }

        # Get list of countries in region
        countries = self.region_data.get("countries", [])
        analysis["total_countries"] = len(countries)
        analysis["countries"] = [c.get("code") for c in countries]

        # Aggregate items across all countries
        all_items = []
        for country in countries:
            all_items.extend(country.get("items", []))

        # Categorize items
        for item in all_items:
            category = item.get("category", "unknown")
            if category not in analysis["items_by_category"]:
                analysis["items_by_category"][category] = []
            analysis["items_by_category"][category].append({
                "item": item.get("item", ""),
                "country": item.get("country", ""),
                "role": item.get("role", ""),
                "has_timeseries": "timeseries" in item,
                "source_tier": item.get("tier", "N/A")
            })

        # Analyze quality across region
        analysis["data_quality"] = self._assess_region_data_quality(countries)

        return analysis

    def _assess_region_data_quality(self, countries: List[Dict]) -> Dict[str, Any]:
        """Assess data quality across all countries in region."""
        quality = {
            "countries_coverage": len(countries),
            "timeseries_coverage_avg": 0,
            "source_tiers": {"tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0},
            "data_sources": set(),
            "gaps_by_tab": {},
            "country_completeness": {}
        }

        all_items = []
        for country in countries:
            country_code = country.get("code", "N/A")
            items = country.get("items", [])
            all_items.extend(items)

            # Track completeness per country
            quality["country_completeness"][country_code] = {
                "total_items": len(items),
                "target_items": 48,
                "completeness": (len(items) / 48 * 100) if len(items) <= 48 else (48 / len(items) * 100)
            }

        # Aggregate statistics
        if all_items:
            total_items = len(all_items)
            timeseries_count = sum(1 for item in all_items if "timeseries" in item)
            quality["timeseries_coverage_avg"] = (timeseries_count / total_items) * 100

            for item in all_items:
                tier = item.get("tier", 0)
                tier_key = f"tier{tier}"
                if tier_key in quality["source_tiers"]:
                    quality["source_tiers"][tier_key] += 1

                source = item.get("source", "unknown")
                quality["data_sources"].add(source)

            # Identify gaps by tab across all countries
            quality["gaps_by_tab"] = self._identify_region_gaps(countries)

        quality["data_sources"] = list(quality["data_sources"])
        return quality

    def _identify_region_gaps(self, countries: List[Dict]) -> Dict[str, List[str]]:
        """Identify gaps at region level."""
        gaps = {}

        for tab_id, tab_spec in self.TYPE2_TABS.items():
            # Check if any country has all required fields for this tab
            all_items = {}
            for country in countries:
                for item in country.get("items", []):
                    all_items[item.get("item", "")] = item

            missing = []
            for required_field in tab_spec.get("required_fields", []):
                if required_field not in all_items:
                    missing.append(required_field)

            if missing:
                gaps[f"Type2-Tab-{tab_id}"] = missing

        return gaps

    def generate_gap_report(self) -> Dict[str, Any]:
        """Generate comprehensive gap analysis report for Type 2."""
        self.load_region_data()
        analysis = self.analyze_region_structure()

        report = {
            "report_type": "gap_analysis",
            "analysis_type": "TYPE2",
            "region": analysis["region"],
            "region_code": analysis["code"],
            "generated_at": datetime.now().isoformat(),
            "schema_version": analysis["schema_version"],

            "summary": {
                "total_countries": analysis["total_countries"],
                "countries": analysis["countries"],
                "avg_completeness_pct": sum(
                    c["completeness"] for c in analysis["data_quality"]["country_completeness"].values()
                ) / len(analysis["data_quality"]["country_completeness"]) if analysis["data_quality"]["country_completeness"] else 0
            },

            "by_category": analysis["items_by_category"],
            "data_quality": analysis["data_quality"],
            "critical_gaps": self._identify_critical_gaps(analysis),
            "type2_readiness": self._assess_type2_readiness(analysis)
        }

        return report

    def _identify_critical_gaps(self, analysis: Dict) -> List[Dict[str, Any]]:
        """Identify critical data gaps blocking region analysis."""
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

    def _assess_type2_readiness(self, analysis: Dict) -> Dict[str, Any]:
        """Assess readiness to generate Type 2 region ranking report."""
        readiness = {
            "can_generate": True,
            "tabs": {}
        }

        gaps_by_tab = analysis["data_quality"].get("gaps_by_tab", {})

        for tab_id in self.TYPE2_TABS.keys():
            tab_key = f"Type2-Tab-{tab_id}"
            missing = gaps_by_tab.get(tab_key, [])

            readiness["tabs"][tab_id] = {
                "name": self.TYPE2_TABS[tab_id]["name"],
                "ready": len(missing) == 0,
                "missing_count": len(missing),
                "missing_fields": missing
            }

            if len(missing) > 0:
                readiness["can_generate"] = False

        return readiness

    def save_gap_report(self, gap_report: Dict[str, Any]) -> str:
        """Save gap analysis report to file with RPT_RGN_{code}_nnn.json naming."""
        region_code = gap_report["region_code"]
        output_dir = Path(self.output_base) / "analysis" / region_code
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find next sequence number
        existing_files = list(output_dir.glob(f"RPT_RGN_{region_code}_*.json"))
        next_num = 1
        if existing_files:
            max_num = max(
                int(f.stem.split("_")[-1])
                for f in existing_files
                if f.stem.split("_")[-1].isdigit()
            )
            next_num = max_num + 1

        output_file = output_dir / f"RPT_RGN_{region_code}_{next_num:03d}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(gap_report, f, ensure_ascii=False, indent=2)

        return str(output_file)

    def generate_readable_gap_report(self, gap_report: Dict[str, Any]) -> str:
        """Generate human-readable gap analysis report."""
        lines = [
            f"\n{'='*70}",
            f"REGION GAP ANALYSIS: {gap_report['region']} ({gap_report['region_code']})",
            f"{'='*70}",
            f"Generated: {gap_report['generated_at']}",
            f"Schema Version: {gap_report['schema_version']}",
            ""
        ]

        summary = gap_report["summary"]
        lines.append("SUMMARY")
        lines.append(f"  Countries Analyzed: {summary['total_countries']}")
        lines.append(f"  Countries: {', '.join(summary['countries'])}")
        lines.append(f"  Average Completeness: {summary['avg_completeness_pct']:.1f}%")
        lines.append("")

        lines.append("ITEMS BY CATEGORY:")
        for category, items in gap_report["by_category"].items():
            lines.append(f"  {category}: {len(items)} items")
            for item in items[:3]:
                lines.append(f"    - {item['item']} ({item.get('country', 'N/A')}, tier: {item.get('source_tier')})")
            if len(items) > 3:
                lines.append(f"    ... and {len(items)-3} more")
        lines.append("")

        lines.append("DATA QUALITY METRICS:")
        quality = gap_report["data_quality"]
        lines.append(f"  Average Timeseries Coverage: {quality.get('timeseries_coverage_avg', 0):.1f}%")
        lines.append(f"  Source Tiers: {quality.get('source_tiers', {})}")
        lines.append("")

        lines.append("COUNTRY COMPLETENESS:")
        for country, comp in quality.get("country_completeness", {}).items():
            lines.append(f"  {country}: {comp['total_items']}/{comp['target_items']} ({comp['completeness']:.1f}%)")
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
            lines.append("  None - all required fields present across region!")
        lines.append("")

        lines.append("REGION REPORT (RANKING & COMPARATIVE) READINESS:")
        type2 = gap_report["type2_readiness"]
        lines.append(f"  Can Generate: {'YES ✓' if type2['can_generate'] else 'NO ✗'}")
        for tab_id, status in type2["tabs"].items():
            ready_icon = "✓" if status["ready"] else "✗"
            lines.append(f"  Tab 2-{tab_id}: {ready_icon} {status['name']}")
            if not status["ready"]:
                lines.append(f"           Missing: {', '.join(status['missing_fields'][:2])}")
        lines.append("")

        lines.append(f"{'='*70}\n")

        return "\n".join(lines)


def main():
    """CLI entry point for region report generation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python region_report_engine.py <region_data_json> [output_base_path]")
        print("Example: python region_report_engine.py data/region/EU_region.json")
        sys.exit(1)

    region_data_path = sys.argv[1]
    output_base = sys.argv[2] if len(sys.argv) > 2 else "storage/report"

    engine = RegionReportEngine(region_data_path, output_base)

    if not engine.load_region_data():
        sys.exit(1)

    gap_report = engine.generate_gap_report()
    readable = engine.generate_readable_gap_report(gap_report)
    print(readable)

    json_path = engine.save_gap_report(gap_report)
    print(f"📁 Region gap analysis JSON saved: {json_path}")

    return 0 if gap_report.get("type2_readiness", {}).get("can_generate") else 1


if __name__ == "__main__":
    main()
