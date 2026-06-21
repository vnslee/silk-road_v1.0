#!/usr/bin/env python3
"""
Report Generation Engine for Country Auto Finance Research

Converts country research JSON (schema v1.1) into Type 1 (single-country TCO)
and Type 2 (region ranking) reports per report_generate_req.md specification.

Identifies data gaps and produces gap analysis reports.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class ReportEngine:
    """Generate Type 1 and Type 2 reports from country research data."""

    # Data requirements mapping
    TYPE1_TABS = {
        "1-1": {
            "name": "Similarity Scoring (vs Baseline)",
            "required_fields": [
                "솔루션_유형", "디지털채널성숙도", "상품판매현황",
                "라이선스종류", "데이터현지화", "차량회수절차"
            ],
            "data_characteristics": ["score_multiaxis", "single_value"]
        },
        "1-2": {
            "name": "System Decision Tree",
            "required_fields": ["특화요건_상품판매", "특화요건_개인정보보호",
                              "특화요건_의무보험", "특화요건_신용생명보험"],
            "data_characteristics": ["qualitative", "status_matrix"]
        },
        "1-3": {
            "name": "Contract Volume & 10Y TCO",
            "required_fields": ["신차판매대수", "금융침투율", "구매패턴",
                              "경쟁사점유율", "평균신차가격"],
            "data_characteristics": ["single_value", "composition", "timeseries"]
        },
        "1-4": {
            "name": "Market & Competition Background",
            "required_fields": ["금융사순위", "캡티브강도", "경쟁사금리범위",
                              "OEM순위", "EV보급률", "잔존가치리스크"],
            "data_characteristics": ["ranking", "timeseries", "qualitative"]
        }
    }

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

    def __init__(self, country_data_path: str, output_base_path: str = "storage/report",
                 report_type: str = "TYPE1"):
        """Initialize report engine with country data.

        Args:
            country_data_path: Path to country data JSON file
            output_base_path: Base output directory for reports
            report_type: "TYPE1" for country TCO or "TYPE2" for region ranking
        """
        self.country_data_path = country_data_path
        self.output_base = output_base_path
        self.report_type = report_type
        self.country_data: Optional[Dict] = None
        self.data_inventory: Dict[str, Any] = {
            "present": {},
            "missing": {},
            "quality_issues": []
        }

    def load_country_data(self) -> bool:
        """Load country research JSON file."""
        try:
            with open(self.country_data_path, 'r', encoding='utf-8') as f:
                self.country_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading country data: {e}")
            return False

    def detect_report_type(self) -> str:
        """Auto-detect report type based on country data structure.

        Returns:
            "TYPE1" if country data is single country, "TYPE2" if region
        """
        if not self.country_data:
            return self.report_type

        # TYPE2: Region-based data contains "region" at top level and lists of countries
        # TYPE1: Country-based data contains "country" code (2-letter) at top level
        if "region" in self.country_data:
            return "TYPE2"
        elif "country" in self.country_data and "code" in self.country_data:
            return "TYPE1"
        else:
            return self.report_type

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

        # Count timeseries items
        timeseries_count = sum(1 for item in items if "timeseries" in item)
        quality["timeseries_coverage"] = (timeseries_count / total_items) * 100

        # Count source tiers
        for item in items:
            tier = item.get("tier", 0)
            tier_key = f"tier{tier}"
            if tier_key in quality["source_tiers"]:
                quality["source_tiers"][tier_key] += 1

            source = item.get("source", "unknown")
            quality["data_sources"].add(source)

        # Identify gaps by tab type
        quality["gaps_by_tab"] = self._identify_tab_gaps(items)

        quality["data_sources"] = list(quality["data_sources"])
        return quality

    def _identify_tab_gaps(self, items: List[Dict]) -> Dict[str, List[str]]:
        """Identify which tab data requirements are not met."""
        gaps = {}

        # Build inventory of available item names
        item_names = {item.get("item", ""): item for item in items}

        # Check Type 1 tabs
        for tab_id, tab_spec in self.TYPE1_TABS.items():
            missing = []
            for required_field in tab_spec.get("required_fields", []):
                if required_field not in item_names:
                    missing.append(required_field)
            if missing:
                gaps[f"Type1-Tab-{tab_id}"] = missing

        # Check Type 2 tabs
        for tab_id, tab_spec in self.TYPE2_TABS.items():
            missing = []
            for required_field in tab_spec.get("required_fields", []):
                if required_field not in item_names:
                    missing.append(required_field)
            if missing:
                gaps[f"Type2-Tab-{tab_id}"] = missing

        return gaps

    def generate_gap_report(self) -> Dict[str, Any]:
        """Generate comprehensive gap analysis report."""
        self.load_country_data()
        analysis = self.analyze_data_structure()

        report = {
            "report_type": "gap_analysis",
            "country": analysis["country"],
            "country_code": analysis["code"],
            "generated_at": datetime.now().isoformat(),
            "schema_version": analysis["schema_version"],

            "summary": {
                "total_items": analysis["total_items"],
                "target_items_type1": 48,  # Standard country research has 48 items
                "target_items_type2": 48,
                "completeness_pct": (analysis["total_items"] / 48 * 100) if analysis["total_items"] <= 48
                                   else (48 / analysis["total_items"] * 100)
            },

            "by_category": analysis["items_by_category"],

            "data_quality": analysis["data_quality"],

            "critical_gaps": self._identify_critical_gaps(analysis),

            "type1_readiness": self._assess_type1_readiness(analysis),

            "type2_readiness": self._assess_type2_readiness(analysis)
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
        """Assess readiness to generate Type 1 (single-country TCO) report."""
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

    def _assess_type2_readiness(self, analysis: Dict) -> Dict[str, Any]:
        """Assess readiness to generate Type 2 (region ranking) report."""
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
        """Save gap analysis report to file."""
        country_code = gap_report["country_code"]

        output_dir = Path(self.output_base) / "analysis" / country_code
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"gap_analysis_{country_code}_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(gap_report, f, ensure_ascii=False, indent=2)

        return str(output_file)

    def generate_readable_gap_report(self, gap_report: Dict[str, Any]) -> str:
        """Generate human-readable gap analysis report."""
        lines = [
            f"\n{'='*70}",
            f"GAP ANALYSIS REPORT: {gap_report['country']} ({gap_report['country_code']})",
            f"{'='*70}",
            f"Generated: {gap_report['generated_at']}",
            f"Schema Version: {gap_report['schema_version']}",
            ""
        ]

        # Summary
        summary = gap_report["summary"]
        lines.append("SUMMARY")
        lines.append(f"  Total Items Present: {summary['total_items']}/{summary['target_items_type1']}")
        lines.append(f"  Completeness: {summary['completeness_pct']:.1f}%")
        lines.append("")

        # By Category
        lines.append("ITEMS BY CATEGORY:")
        for category, items in gap_report["by_category"].items():
            lines.append(f"  {category}: {len(items)} items")
            for item in items[:3]:  # Show first 3
                lines.append(f"    - {item['item']} (role: {item['role']}, tier: {item.get('source_tier')})")
            if len(items) > 3:
                lines.append(f"    ... and {len(items)-3} more")
        lines.append("")

        # Data Quality
        lines.append("DATA QUALITY METRICS:")
        quality = gap_report["data_quality"]
        lines.append(f"  Timeseries Coverage: {quality.get('timeseries_coverage', 0):.1f}%")
        lines.append(f"  Source Tiers: {quality.get('source_tiers', {})}")
        lines.append("")

        # Critical Gaps
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

        # Type 1 Readiness
        lines.append("TYPE 1 REPORT (SINGLE-COUNTRY TCO) READINESS:")
        type1 = gap_report["type1_readiness"]
        lines.append(f"  Can Generate: {'YES ✓' if type1['can_generate'] else 'NO ✗'}")
        for tab_id, status in type1["tabs"].items():
            ready_icon = "✓" if status["ready"] else "✗"
            lines.append(f"  Tab 1-{tab_id}: {ready_icon} {status['name']}")
            if not status["ready"]:
                lines.append(f"           Missing: {', '.join(status['missing_fields'][:2])}")
        lines.append("")

        # Type 2 Readiness
        lines.append("TYPE 2 REPORT (REGION RANKING) READINESS:")
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
    """CLI entry point for report generation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python report_engine.py <country_data_json> [--type TYPE1|TYPE2] [output_base_path]")
        print("Example (Type 1): python report_engine.py data/country/ES_latest.json --type TYPE1")
        print("Example (Type 2): python report_engine.py data/region/EU_region.json --type TYPE2")
        print("\nIf --type not specified, auto-detects based on data structure:")
        print("  - Single country JSON -> TYPE1 (single-country TCO)")
        print("  - Region JSON -> TYPE2 (region ranking)")
        sys.exit(1)

    country_data_path = sys.argv[1]

    # Parse optional arguments
    report_type = "TYPE1"
    output_base = "storage/report"

    # Check for --type flag
    if "--type" in sys.argv:
        type_idx = sys.argv.index("--type")
        if type_idx + 1 < len(sys.argv):
            report_type = sys.argv[type_idx + 1].upper()
            if report_type not in ["TYPE1", "TYPE2"]:
                print(f"Error: Invalid report type '{report_type}'. Must be TYPE1 or TYPE2")
                sys.exit(1)

    # Last positional argument is output_base if provided
    positional_args = [arg for arg in sys.argv[2:] if not arg.startswith("--") and arg != report_type]
    if positional_args:
        output_base = positional_args[-1]

    # Initialize engine
    engine = ReportEngine(country_data_path, output_base, report_type)

    # Load data
    if not engine.load_country_data():
        sys.exit(1)

    # Auto-detect report type if not explicitly set
    detected_type = engine.detect_report_type()
    if engine.report_type == "TYPE1" and detected_type == "TYPE2":
        engine.report_type = "TYPE2"
    elif engine.report_type == "TYPE2" and detected_type == "TYPE1":
        engine.report_type = "TYPE1"

    # Generate gap report
    gap_report = engine.generate_gap_report()

    # Display readable report
    readable = engine.generate_readable_gap_report(gap_report)
    print(readable)

    # Save JSON report
    json_path = engine.save_gap_report(gap_report)
    print(f"📁 Gap analysis JSON saved: {json_path}")
    print(f"📊 Report Type: {engine.report_type}")

    return 0 if gap_report.get("type1_readiness", {}).get("can_generate") else 1


if __name__ == "__main__":
    main()
