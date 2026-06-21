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
            "required_fields": ["금융사 순위(Top 5)", "금융사 점유율(Top 5)", "경쟁사 금리 범위",
                              "OEM 순위(Top 5)", "EV 보급률", "EV·ICE 잔존가치 리스크"],
            "data_characteristics": ["ranking", "timeseries", "qualitative"]
        }
    }

    def __init__(self, country_data_path: str, internal_data_path: str = "storage/data/internal/internal_latest.json", output_base_path: str = "storage/report"):
        """Initialize country report engine with country data.

        Args:
            country_data_path: Path to single country JSON file
            internal_data_path: Path to internal config/parameters JSON
            output_base_path: Base output directory for reports
        """
        self.country_data_path = country_data_path
        self.internal_data_path = internal_data_path
        self.output_base = output_base_path
        self.country_data: Optional[Dict] = None
        self.internal_data: Optional[Dict] = None
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

    def load_internal_data(self) -> bool:
        """Load internal config/parameters JSON file."""
        try:
            with open(self.internal_data_path, 'r', encoding='utf-8') as f:
                self.internal_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading internal data: {e}")
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

    # Legacy/alternate country code aliases used in research data → ISO 3166-1 alpha-2
    # GB(영국), US(미국) 등이 ISO 표준. 과거 데이터의 UK/USA는 등록 시 보정.
    COUNTRY_CODE_ALIASES = {
        "USA": "US",
    }

    def normalize_country_code(self, code: str) -> str:
        """Map legacy code aliases (UK→GB, USA→US) to ISO codes used by internal.json."""
        if not code:
            return code
        return self.COUNTRY_CODE_ALIASES.get(code.upper(), code.upper())

    def resolve_base_country(self, target_country: str) -> str:
        """Resolve baseline country for the target country's region.

        Args:
            target_country: Target country code (ISO 3166-1 alpha-2)

        Returns:
            Baseline country code for the region (e.g., 'GB' for EU)
        """
        if not self.internal_data:
            self.load_internal_data()

        target_country = self.normalize_country_code(target_country)
        country_to_region = self.internal_data.get("country_to_region", {})
        region_baselines = self.internal_data.get("region_baselines", {})

        region = country_to_region.get(target_country)
        if not region:
            return "GB"  # fallback default

        return region_baselines.get(region, "GB")

    def _score_item_from_dimensions(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Compute an item-level similarity score from per-dimension target/base scores.

        Each dimension carries target_score and base_score on a 1~5 scale. The gap
        (|target - base|) determines closeness: 0 gap → 100, 4 gap → 0.
        Returns None when the item has no score_dimensions block.
        """
        dims = item.get("score_dimensions")
        if not dims:
            return None

        dim_results = []
        for dim_name, dim in dims.items():
            t = dim.get("target_score")
            b = dim.get("base_score")
            if t is None or b is None:
                continue
            gap = abs(float(t) - float(b))
            similarity = max(0.0, (1.0 - gap / 4.0) * 100.0)  # 1~5 → max gap 4 → 0
            dim_results.append({
                "dimension": dim_name,
                "target_score": t,
                "base_score": b,
                "gap": gap,
                "similarity": similarity,
                "note": dim.get("note", ""),
            })

        if not dim_results:
            return None

        item_similarity = sum(d["similarity"] for d in dim_results) / len(dim_results)
        item_name = item.get("item")
        # 가중치/축은 internal.similarity_item_weights에서 우선 조회, 없으면 항목 내 fallback
        weights_cfg = (self.internal_data or {}).get("similarity_item_weights", {}) or {}
        w_entry = weights_cfg.get(item_name) or {}
        axis = w_entry.get("axis") or item.get("similarity_axis")
        weight = w_entry.get("weight")
        if weight is None:
            weight = item.get("similarity_weight", 0.0)

        return {
            "item": item_name,
            "axis": axis,
            "weight": weight or 0.0,
            "dimensions": dim_results,
            "item_similarity": item_similarity,
        }

    def calculate_similarity_score(self, target_country: str, base_country: str) -> Dict[str, Any]:
        """Calculate similarity score between target country and base country.

        Returns:
            Dict with overall score and axis breakdown
        """
        # 자기 자신이 베이스라인인 경우 (is_baseline 국가): 유사도 100점 자동
        if self.normalize_country_code(target_country) == self.normalize_country_code(base_country):
            return {
                "overall_score": 100.0,
                "axes": {"system": 100.0, "product": 100.0, "regulatory": 100.0, "risk": 100.0},
                "items": [],
                "method": "self_baseline",
                "note": "베이스라인 국가 자기 자신 — 유사도 100점 적용",
            }

        items = (self.country_data or {}).get("items", []) or []
        scored_items = []
        for it in items:
            scored = self._score_item_from_dimensions(it)
            if scored:
                scored_items.append(scored)

        # Aggregate per axis (system / product / regulatory / risk)
        axis_buckets: Dict[str, List[Dict[str, Any]]] = {}
        for s in scored_items:
            axis = s.get("axis") or "system"
            axis_buckets.setdefault(axis, []).append(s)

        axes: Dict[str, float] = {}
        for axis, group in axis_buckets.items():
            weight_sum = sum(s.get("weight", 0.0) for s in group) or len(group)
            weighted = sum(s["item_similarity"] * (s.get("weight") or 1.0) for s in group)
            axes[axis] = weighted / weight_sum

        # Fallback to placeholder when nothing was scored
        if not scored_items:
            return {
                "overall_score": 0.0,
                "axes": {},
                "items": [],
                "method": "dimension_based",
                "note": "score_dimensions가 country_data에 정의되지 않음",
            }

        overall_weight = sum(s.get("weight", 0.0) for s in scored_items) or len(scored_items)
        overall = sum(s["item_similarity"] * (s.get("weight") or 1.0) for s in scored_items) / overall_weight

        return {
            "overall_score": overall,
            "axes": axes,
            "items": scored_items,
            "method": "dimension_based",
            "scale": "1~5 per dimension → gap 0=100, gap 4=0",
        }

    def determine_system_decision(self, similarity_score: float, base_country: str) -> Dict[str, Any]:
        """Determine system decision based on similarity score.

        Args:
            similarity_score: Overall similarity score (0-100)
            base_country: Base country code

        Returns:
            Decision result with path and details
        """
        if not self.internal_data:
            self.load_internal_data()

        country_assets = self.internal_data.get("country_assets", {}) or {}
        base_info = country_assets.get(base_country, {})
        hq_baseline = self.internal_data.get("hq_build_baseline", {})
        base_solution = base_info.get("solution", "N/A")
        region_system_exists = base_country in country_assets

        # 임계값 — internal_data.decision_thresholds 우선, 누락 시 명세 기본값(70/50)
        thresholds = (self.internal_data or {}).get("decision_thresholds") or {}
        expansion_min = float(thresholds.get("expansion_min_score", 70))
        hq_build_min = float(thresholds.get("hq_build_min_score", 50))

        # Stage 1 — does the region already have a deployed system?
        if not region_system_exists:
            # No region system → straight into external-solution review (then HQ fallback)
            decision = "external_solution"
            recommendation = "권역 내 확산 가능 시스템 없음 → 외부솔루션 검토 (미달 시 본사 자체구축)"
        elif similarity_score >= expansion_min:
            decision = "baseline_system_expansion"
            recommendation = f"권역 내 확산: {base_country} 시스템({base_solution}) 현지화"
        elif similarity_score >= hq_build_min:
            decision = "hq_build"
            recommendation = "본사 자체구축 추천 (유사도 중간 구간)"
        else:
            decision = "external_solution"
            recommendation = "현지 외부솔루션 2~3종 추천"

        return {
            "decision": decision,
            "similarity_score": similarity_score,
            "recommendation": recommendation,
            "base_country": base_country,
            "base_system": base_solution,
            "region_system_exists": region_system_exists,
            "hq_baseline_cost": hq_baseline.get("cost", 0),
            "hq_baseline_months": hq_baseline.get("months", 0),
            "hq_baseline_currency": hq_baseline.get("currency", "EUR")
        }

    def calculate_similarity_multiplier(self, similarity_score: float) -> Dict[str, Any]:
        """명세서 산식 1 — 종합 유사도 → TCO 적용 승수%.

        승수 테이블은 internal_data.similarity_multiplier_table에서 로드.
        승수는 'B 구축비용/기간'에 곱해 신규국 구축 비용·기간을 산출하는 값.
        """
        if not self.internal_data:
            self.load_internal_data()
        table = (self.internal_data or {}).get("similarity_multiplier_table") or []
        for row in table:
            if not isinstance(row, dict):
                continue
            lo = row.get("min")
            hi = row.get("max")
            if lo is None or hi is None:
                continue
            if lo <= similarity_score <= hi:
                return {
                    "multiplier": float(row.get("multiplier", 1.0)),
                    "band": row.get("band", f"{lo}~{hi}"),
                }
        # 표가 비어 있거나 매칭 실패 → 안전 폴백 (재사용 없음 = 100%)
        return {"multiplier": 1.0, "band": "—"}

    def calculate_similarity_discount(self, similarity_score: float) -> float:
        """Map similarity score to discount percentage.

        Args:
            similarity_score: Overall similarity score (0-100)

        Returns:
            Discount multiplier (e.g., 0.70 for 70%)
        """
        if not self.internal_data:
            self.load_internal_data()

        brackets = self.internal_data.get("similarity_brackets", [])

        for bracket in brackets:
            if bracket["min"] <= similarity_score <= bracket["max"]:
                return bracket["discount"]

        return 0.0

    def calculate_expected_contracts(self, target_country_data: Dict) -> Dict[str, Any]:
        """Calculate expected contract volume for target country.

        명세서 산식 2:
            A 예상건수 = A 판매대수 × A 금융이용률 × (할부+리스 비중) × 우리사 예상 점유율

        Returns:
            Dict with computed value + 입력 추적 (산식 재현용).
        """
        if not self.internal_data:
            self.load_internal_data()

        items_by_name = {it.get("item"): it for it in target_country_data.get("items", []) or []}

        def _to_float(v, default=None):
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        def _read_value(name, default=None):
            it = items_by_name.get(name)
            if not it:
                return default
            return _to_float(it.get("value"), default)

        # 신차 판매대수 (단위는 country_data에서 unit으로 표시, 보통 units_K 또는 절대수)
        sales_item = items_by_name.get("신차 판매대수")
        sales_value = _to_float((sales_item or {}).get("value"), 0) or 0
        sales_unit = (sales_item or {}).get("unit", "")
        # 단위 정규화: units_K → ×1000, units_M → ×1,000,000, 그 외(units/대 등)는 그대로
        unit_multiplier = 1
        if sales_unit in ("units_K", "K", "thousand"):
            unit_multiplier = 1_000
        elif sales_unit in ("units_M", "M", "million"):
            unit_multiplier = 1_000_000
        # 절대수가 큰 경우(>= 10만)에는 이미 절대수로 들어왔다고 간주
        if sales_value >= 100_000 and unit_multiplier > 1:
            unit_multiplier = 1
        total_sales = sales_value * unit_multiplier

        # 금융 이용률(신차) — % 값
        penetration_pct = _read_value("금융 이용률(신차)", 0) or 0
        penetration = penetration_pct / 100.0

        # 구매 패턴(할부·리스 비중) — % 값
        installment_lease_pct = _read_value("구매 패턴(할부·리스 비중)", 0) or 0
        installment_lease = installment_lease_pct / 100.0

        # 우리사 예상 점유율 — internal.json
        expected_share = self.internal_data.get("expected_market_share", 0.02) or 0
        try:
            expected_share = float(expected_share)
        except (TypeError, ValueError):
            expected_share = 0.02

        expected_contracts = total_sales * penetration * installment_lease * expected_share
        expected_contracts_int = int(round(expected_contracts))

        return {
            "value": expected_contracts_int,
            "formula": "신차 판매대수 × 금융이용률(신차) × (할부+리스 비중) × 우리사 예상 점유율",
            "inputs": {
                "신차 판매대수": int(total_sales) if total_sales else 0,
                "신차 판매대수(원본값)": sales_value,
                "신차 판매대수(단위)": sales_unit,
                "금융 이용률(신차)_%": penetration_pct,
                "구매 패턴(할부·리스 비중)_%": installment_lease_pct,
                "우리사 예상 점유율": expected_share,
            },
        }

    def calculate_subscription_fee(self, new_volume: int) -> Dict[str, Any]:
        """Calculate subscription fee with volume-based tiering.

        All existing volume is repriced at the new tier rate.

        Args:
            new_volume: New contracts to add

        Returns:
            Subscription fee details
        """
        if not self.internal_data:
            self.load_internal_data()

        existing_volume = self.internal_data.get("existing_total_volume", 0)
        total_volume = existing_volume + new_volume
        tiers = self.internal_data.get("subscription_tiers", [])

        # Find applicable tier
        applicable_tier = None
        for tier in tiers:
            if tier["min_volume"] <= total_volume <= tier["max_volume"]:
                applicable_tier = tier
                break

        if not applicable_tier:
            # Use highest tier if volume exceeds all ranges
            applicable_tier = tiers[-1] if tiers else {"price_per_unit": 1.0, "currency": "EUR"}

        unit_price = applicable_tier["price_per_unit"]
        annual_fee = total_volume * unit_price

        return {
            "existing_volume": existing_volume,
            "new_volume": new_volume,
            "total_volume": total_volume,
            "unit_price": unit_price,
            "currency": applicable_tier.get("currency", "EUR"),
            "annual_fee": annual_fee,
            "note": "All volume repriced at new tier rate"
        }

    def calculate_tco_10y(self, target_country: str, base_country: str) -> Dict[str, Any]:
        """Calculate 10-year TCO for target country.

        Args:
            target_country: Target country code
            base_country: Base country code for reuse

        Returns:
            TCO breakdown
        """
        if not self.internal_data:
            self.load_internal_data()

        # Get similarity and multiplier (명세서 산식 1)
        similarity = self.calculate_similarity_score(target_country, base_country)
        mult_info = self.calculate_similarity_multiplier(similarity["overall_score"])
        multiplier = mult_info["multiplier"]
        # 'discount'는 internal.similarity_brackets(레거시) 정보 — JSON 트레이스용으로만 유지
        discount = self.calculate_similarity_discount(similarity["overall_score"])

        # Get base country build info
        base_info = self.internal_data.get("country_assets", {}).get(base_country, {})
        base_cost = base_info.get("build_cost", 5000)
        base_months = base_info.get("build_months", 18)

        # 명세서 산식 4:
        #   구축비   = B 구축비용 × 유사도승수
        #   구축기간 = B 구축기간 × 유사도승수
        build_cost = base_cost * multiplier
        build_months = base_months * multiplier

        build_breakdown = {
            "formula": "구축비용/기간 = 베이스라인(B) 값 × 유사도 승수",
            "inputs": {
                "베이스라인 국가": base_country,
                "베이스라인 솔루션": base_info.get("solution"),
                "B 구축비용": base_cost,
                "B 구축기간(개월)": base_months,
                "종합 유사도": round(similarity["overall_score"], 1),
                "승수 구간": mult_info["band"],
                "적용 승수": multiplier,
            },
            "outputs": {
                "신규국 구축비용": build_cost,
                "신규국 구축기간(개월)": build_months,
            },
        }

        # Calculate subscription
        expected = self.calculate_expected_contracts(self.country_data or {})
        expected_volume = expected.get("value", 0) if isinstance(expected, dict) else int(expected or 0)
        subscription = self.calculate_subscription_fee(expected_volume)
        annual_subscription = subscription["annual_fee"]

        # Maintenance
        maintenance_annual = self.internal_data.get("maintenance_cost_annual", {}).get("amount", 500)

        # Operations
        operations_10y = self.internal_data.get("operational_cost_10y", {}).get("amount", 50000)

        # Total TCO (명세 산식 4)
        annual_recurring = annual_subscription + maintenance_annual
        system_cost = build_cost + (annual_recurring * 10)
        total_tco = system_cost + operations_10y

        return {
            "build_cost": build_cost,
            "build_months": build_months,
            "annual_subscription": annual_subscription,
            "annual_maintenance": maintenance_annual,
            "annual_recurring": annual_recurring,
            "operations_10y": operations_10y,
            "system_cost_10y": system_cost,
            "total_tco_10y": total_tco,
            "currency": "EUR",
            "similarity_score": similarity["overall_score"],
            "similarity_multiplier": multiplier,
            "similarity_band": mult_info["band"],
            "discount_applied": discount,
            "build_breakdown": build_breakdown,
            "expected_contracts": expected_volume,
            "expected_contracts_breakdown": expected if isinstance(expected, dict) else None,
            "subscription_details": subscription,
            "subscription_tiers": self.internal_data.get("subscription_tiers", []),
            "existing_total_volume": self.internal_data.get("existing_total_volume", 0),
        }

    def _extract_item_detail(self, item_name: str) -> Optional[Dict[str, Any]]:
        """Extract full detail of a single item from country_data.items by name.

        Returns the item dict (value, unit, source, insight, tier, timeseries, ...)
        or None if the item is not present.
        """
        if not self.country_data:
            return None

        for item in self.country_data.get("items", []):
            if item.get("item") == item_name:
                return {
                    "item": item.get("item"),
                    "category": item.get("category"),
                    "role": item.get("role"),
                    "value": item.get("value"),
                    "unit": item.get("unit"),
                    "direction": item.get("direction"),
                    "axis": item.get("axis"),
                    "gate_result": item.get("gate_result"),
                    "gate_scope": item.get("gate_scope"),
                    "segment": item.get("segment"),
                    "context_type": item.get("context_type"),
                    "timeseries": item.get("timeseries"),
                    "tier": item.get("tier"),
                    "source": item.get("source"),
                    "insight": item.get("insight"),
                    "insight_ai_generated": item.get("insight_ai_generated"),
                }
        return None

    def _collect_tab_items(self, tab_id: str) -> List[Dict[str, Any]]:
        """Collect full item details for every required_field of a tab.

        Missing items are returned as stubs with status='missing' so the
        renderer can surface the gap rather than silently dropping the row.
        """
        tab_spec = self.TYPE1_TABS.get(tab_id, {})
        results: List[Dict[str, Any]] = []
        for field in tab_spec.get("required_fields", []):
            detail = self._extract_item_detail(field)
            if detail is None:
                results.append({"item": field, "status": "missing"})
            else:
                detail["status"] = "present"
                results.append(detail)
        return results

    def generate_type1_report(self) -> Dict[str, Any]:
        """Generate complete Type 1 (single country TCO) report.

        Returns:
            Complete report with all tabs and data quality assessment
        """
        if not self.country_data:
            self.load_country_data()
        if not self.internal_data:
            self.load_internal_data()

        # 데이터에 기록된 원본 코드(예: UK)는 저장/표시용으로 유지하고,
        # 내부 룩업(베이스라인·진출상태)에만 정규화된 코드(예: GB)를 쓴다.
        target_country = self.country_data.get("code", "N/A")
        base_country = self.resolve_base_country(target_country)

        # Data quality and gap analysis
        analysis = self.analyze_data_structure()
        quality = self._assess_data_quality()
        readiness = self._assess_type1_readiness(analysis)

        # 기준국 자가 분석 감지 — TCO/결정 산식이 무의미해지므로 명시적 안내로 대체.
        is_baseline_self = (
            self.normalize_country_code(target_country)
            == self.normalize_country_code(base_country)
        )
        base_solution = (
            (self.internal_data or {}).get("country_assets", {}).get(base_country, {}).get("solution")
            or "N/A"
        )

        # Tab 1-1: Similarity Scoring
        # calculate_similarity_score()가 디멘전 채점 결과를 'items'에 채움.
        # 보조적인 raw evidence는 별도 'evidence_items' 키로 분리해서 보관.
        similarity = self.calculate_similarity_score(target_country, base_country)
        similarity["evidence_items"] = self._collect_tab_items("1-1")

        # Tab 1-2: System Decision Tree
        if is_baseline_self:
            decision = {
                "is_baseline": True,
                "decision": "baseline_already_deployed",
                "recommendation": (
                    f"{target_country}는 권역 기준국 — 시스템({base_solution})이 이미 운영 중입니다. "
                    f"신규 진출 결정 트리는 적용되지 않습니다."
                ),
                "similarity_score": similarity.get("overall_score"),
                "base_country": base_country,
                "base_system": base_solution,
                "region_system_exists": True,
                "items": self._collect_tab_items("1-2"),
            }
        else:
            decision = self.determine_system_decision(similarity["overall_score"], base_country)
            decision["items"] = self._collect_tab_items("1-2")

        # Tab 1-3: Contract Volume & 10Y TCO
        if is_baseline_self:
            tco = {
                "is_baseline": True,
                "message": (
                    f"{target_country}는 권역 기준국 — 신규 구축 비용·기간이 적용되지 않습니다. "
                    f"운영 현황(기존 누적 계약·운영비)은 별도 관리 보고서를 참조하세요."
                ),
                "currency": (self.country_data.get("currency") or "EUR"),
                "items": self._collect_tab_items("1-3"),
            }
        else:
            tco = self.calculate_tco_10y(target_country, base_country)
            tco["items"] = self._collect_tab_items("1-3")

        # Tab 1-4: Market & Competition — fully sourced from country_data.items
        tab_1_4_items = self._collect_tab_items("1-4")
        market = {
            "items": tab_1_4_items,
            "competitors": self._extract_item_detail("경쟁사 리스트"),
            "competitor_entry_form": self._extract_item_detail("경쟁사 진출 형태"),
            "brand_top10": self._extract_item_detail("브랜드 Top10"),
            "news": self._extract_item_detail("외부 이슈 스캔"),
            "regulators": self._extract_item_detail("규제기관 식별"),
            "country_summary": self._extract_item_detail("해당국 정성 요약"),
        }

        report = {
            # 일련번호는 save_type1_report()에서 출력 디렉터리를 스캔해 자동 갱신.
            "report_id": f"RPT_CTR_{target_country}_001",  # placeholder — save 시점에 덮어씀
            "report_type": "type1_country",
            "title": f"{self.country_data.get('country_ko') or self.country_data.get('country', target_country)} 진출 진단 보고서",
            "target": {
                "country": target_country,
                "base_country": base_country
            },
            "generated_at": datetime.now().isoformat(),
            "schema_version": self.country_data.get("schema_version", "N/A"),

            "overall_insight": self.country_data.get("overall_insight"),
            "country_meta": {
                "country": self.country_data.get("country"),
                "country_ko": self.country_data.get("country_ko"),
                "region": self.country_data.get("region"),
                "currency": self.country_data.get("currency"),
                "data_year": self.country_data.get("data_year"),
                "fetched_at": self.country_data.get("fetched_at"),
                "fetched_by": self.country_data.get("fetched_by"),
                "entry_status": (
                    (self.internal_data or {}).get("country_status", {}).get(target_country)
                    or (self.internal_data or {}).get("country_status", {}).get(self.normalize_country_code(target_country))
                    or "미진출"
                ),
            },

            "data_quality": {
                "completeness_pct": (analysis["total_items"] / 48 * 100) if analysis["total_items"] <= 48 else (48 / analysis["total_items"] * 100),
                "total_items": analysis["total_items"],
                "target_items": 48,
                "timeseries_coverage": quality.get("timeseries_coverage", 0),
                "source_tiers": quality.get("source_tiers", {}),
                "items_by_category": analysis.get("items_by_category", {}),
                "critical_gaps": self._identify_critical_gaps(analysis),
                "readiness": readiness
            },

            "tabs": {
                "tab_1_1_similarity": similarity,
                "tab_1_2_decision": decision,
                "tab_1_3_tco": tco,
                "tab_1_4_market": market,
            }
        }

        return report

    def save_type1_report(self, report: Dict[str, Any]) -> str:
        """Save Type 1 report to file with RPT_CTR_{code}_nnn.json naming.

        Args:
            report: Complete Type 1 report

        Returns:
            Path to saved report file
        """
        country_code = report["target"]["country"]
        output_dir = Path(self.output_base) / "country" / country_code / "data"
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

        new_report_id = f"RPT_CTR_{country_code}_{next_num:03d}"
        report["report_id"] = new_report_id  # 일련번호에 맞춰 ID 동기화

        output_file = output_dir / f"{new_report_id}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return str(output_file)


def main():
    """CLI entry point for country report generation."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python country_report_engine.py <country_data_json> [internal_data_json] [output_base_path]")
        print("Example: python country_report_engine.py data/country/ES_latest.json")
        print("         python country_report_engine.py data/country/ES_latest.json storage/data/internal/internal_latest.json")
        sys.exit(1)

    country_data_path = sys.argv[1]
    internal_data_path = sys.argv[2] if len(sys.argv) > 2 else "storage/data/internal/internal_latest.json"
    output_base = sys.argv[3] if len(sys.argv) > 3 else "storage/report"

    engine = CountryReportEngine(country_data_path, internal_data_path, output_base)

    if not engine.load_country_data():
        sys.exit(1)

    if not engine.load_internal_data():
        print("Warning: Could not load internal data, some features may be limited")

    # Generate Type 1 report with integrated data quality check
    print("="*70)
    print("Generating Type 1 Report (TCO Analysis with Data Quality Check)...")
    print("="*70)

    type1_report = engine.generate_type1_report()

    # Display data quality summary
    quality = type1_report["data_quality"]
    print(f"\nData Quality:")
    print(f"  Completeness: {quality['completeness_pct']:.1f}% ({quality['total_items']}/{quality['target_items']} items)")
    print(f"  Timeseries Coverage: {quality['timeseries_coverage']:.1f}%")
    print(f"  Critical Gaps: {len(quality['critical_gaps'])}")

    can_generate = quality["readiness"].get("can_generate", False)

    if can_generate:
        type1_path = engine.save_type1_report(type1_report)
        print(f"\n📊 Type 1 TCO Report saved: {type1_path}")
        tco_tab = type1_report['tabs']['tab_1_3_tco']
        if tco_tab.get("is_baseline"):
            print(f"\n[기준국 자가 분석] TCO/결정 트리는 적용되지 않음 (운영 중인 시스템 기준).")
        else:
            print(f"\n10Y TCO: {tco_tab.get('total_tco_10y', 0):,.0f} EUR")
        print(f"Similarity Score: {type1_report['tabs']['tab_1_1_similarity']['overall_score']:.1f}")
        print(f"Decision: {type1_report['tabs']['tab_1_2_decision']['recommendation']}")

        # 자동으로 렌더러까지 호출해서 HTML 생성
        try:
            import sys as _sys
            from pathlib import Path as _Path
            renderer_dir = _Path(__file__).resolve().parent.parent / "rendering"
            if str(renderer_dir) not in _sys.path:
                _sys.path.insert(0, str(renderer_dir))
            from country_report_renderer import CountryReportRenderer  # type: ignore

            renderer = CountryReportRenderer(type1_path)
            if renderer.load_report():
                html_path = renderer.save_html()
                print(f"🖼  HTML rendered: {html_path}")
            else:
                print("⚠️  렌더링용 보고서 JSON 로드 실패 — HTML 생성 건너뜀.")
        except Exception as render_err:
            print(f"⚠️  HTML 자동 렌더 실패: {render_err}")
        return 0
    else:
        print("\n⚠️  Data gaps exist but report generated for review")
        type1_path = engine.save_type1_report(type1_report)
        print(f"📊 Report saved: {type1_path}")
        return 1


if __name__ == "__main__":
    main()
