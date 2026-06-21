#!/usr/bin/env python3
"""
Region Report Engine: Region-Based Ranking and Comparative Analysis (Type 2)

Converts region research data (aggregating multiple countries) into region-level
reports per architecture/research/report_generate_req.md (Type 2 spec):

- Tab 2-0: Killswitch filter (status_matrix)
- Tab 2-1: Business attractiveness (normalize + weighted average, ranking)
- Tab 2-2: IT/Speed-to-market similarity vs baseline (band → 10-point bucket)
- Tab 2-3: Market background (rankings/composition/qualitative)
- Quickwin: attractiveness*w_biz + IT*w_it (10-point bucket)
- Top-3 country profile cards
- Executive summary (CALC + AI + NEWS)

Generates RPT_RGN_{code}_{NNN}.json under storage/report/region/{RGN}/data/.
Gap analysis output (legacy) is still produced under storage/report/analysis/{RGN}/.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class RegionReportEngine:
    """Generate region-level (ranking & comparative) reports from regional research data."""

    TYPE2_TABS = {
        "2-0": {
            "name": "Kill Switch Filter",
            "required_fields": ["외국인 지분 한도", "외환·배당 송금 자유도", "데이터 현지화 의무",
                                "국가신용등급"],
            "data_characteristics": ["status_matrix"]
        },
        "2-1": {
            "name": "Business Attractiveness",
            "required_fields": ["오토금융/리스 시장규모", "오토금융 성장률(CAGR)", "금융 이용률(신차)",
                                "캡티브 강도(점유율)", "디지털 채널 성숙도"],
            "data_characteristics": ["ranking", "composition", "timeseries"]
        },
        "2-2": {
            "name": "IT/Speed-to-Market Similarity",
            "required_fields": ["솔루션 유형", "디지털 채널 성숙도",
                                "라이선스 체제(세그먼트별)", "데이터 현지화 의무", "신용정보(CB) 인프라"],
            "data_characteristics": ["score_multiaxis", "ranking"]
        },
        "2-3": {
            "name": "Market Background",
            "required_fields": ["OEM 순위(Top 5)", "브랜드 Top10", "구매 패턴(할부·리스 비중)",
                                "경쟁사 리스트"],
            "data_characteristics": ["ranking", "composition", "qualitative"]
        }
    }

    # config.values.biz_attractiveness 키 → 실제 조사항목 매핑
    ATTRACTIVENESS_ITEM_MAP = {
        "GDP 성장률": {"item": "오토금융 성장률(CAGR)", "reverse": False},  # GDP 미수집 → CAGR 대체
        "자동차 판매대수": {"item": "신차 판매대수", "reverse": False},
        "시장규모(CAGR)": {"item": "오토금융/리스 시장규모", "reverse": False},
        "금융 이용률": {"item": "금융 이용률(신차)", "reverse": False},
        "금융이용유형": {"item": "구매 패턴(할부·리스 비중)", "reverse": False},
        "경쟁강도": {"item": "캡티브 강도(점유율)", "reverse": True},  # 高=惡(역점수)
    }

    # config.values.it_readiness 키 → 실제 조사항목 매핑
    # 주의: "라이선스 종류"는 EU 내에서도 FCA/EFC/KNF/TUB/Wft 등 체계가 다르므로
    #       gate_result(PASS/FAIL)가 아닌 실제 텍스트 내용을 categorical로 비교해야 변별력 확보
    IT_SIMILARITY_ITEM_MAP = {
        "솔루션 유형": {"item": "솔루션 유형", "type": "categorical"},
        "디지털 채널 성숙도": {"item": "디지털 채널 성숙도", "type": "numeric_1to5"},
        "라이선스 종류": {"item": "라이선스 체제(세그먼트별)", "type": "categorical"},
        "데이터현지화": {"item": "데이터 현지화 의무", "type": "gate"},
        "차량회수 절차": {"item": "차량회수 절차 용이성", "type": "numeric_1to5"},
    }

    KILLSWITCH_ITEMS = ["외국인 지분 한도", "외환·배당 송금 자유도",
                        "데이터 현지화 의무", "국가신용등급"]

    def __init__(self, region_data_path: str,
                 internal_data_path: str = "storage/data/internal/internal_latest.json",
                 output_base_path: str = "storage/report"):
        """Initialize region report engine.

        Args:
            region_data_path: Path to region JSON file (containing multiple countries)
            internal_data_path: Path to internal config/parameters JSON
            output_base_path: Base output directory for reports
        """
        self.region_data_path = region_data_path
        self.internal_data_path = internal_data_path
        self.output_base = output_base_path
        self.region_data: Optional[Dict] = None
        self.internal_data: Optional[Dict] = None
        self.report_type = "TYPE2"

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def load_region_data(self) -> bool:
        try:
            with open(self.region_data_path, 'r', encoding='utf-8') as f:
                self.region_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading region data: {e}")
            return False

    def load_internal_data(self) -> bool:
        try:
            with open(self.internal_data_path, 'r', encoding='utf-8') as f:
                self.internal_data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading internal data: {e}")
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _country_items_index(self, country: Dict) -> Dict[str, Dict[str, Any]]:
        """{item_name: item_dict} for a single country."""
        return {it.get("item", ""): it for it in country.get("items", [])}

    def _coerce_numeric(self, value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                cleaned = value.replace(",", "").replace("%", "").strip()
                return float(cleaned)
            except ValueError:
                return None
        return None

    def _krw_convert(self, amount: float, currency: str) -> Optional[float]:
        """Convert currency amount → KRW using internal_data.fx (snapshotted)."""
        if not self.internal_data:
            return None
        rates = (self.internal_data.get("fx") or {}).get("rates") or {}
        rate = rates.get(currency)
        if rate is None:
            return None
        return amount * rate

    def _load_region_news(self, max_items: int = 3) -> List[Dict[str, Any]]:
        """권역 단위 뉴스 파일에서 '조사 필요' 가 아닌 항목을 최대 N건 반환.

        파일 위치: region_data_path와 같은 디렉토리의 {CODE}_news_latest.json.
        스키마: items[].value = [{headline, so_what, publisher, pub_date, url, news_category, scope}, ...]
        """
        from pathlib import Path
        region_path = Path(self.region_data_path)
        region_code = (self.region_data or {}).get("code") or region_path.parent.name
        news_path = region_path.parent / f"{region_code}_news_latest.json"
        if not news_path.exists():
            return []
        try:
            with open(news_path, "r", encoding="utf-8") as f:
                news_doc = json.load(f)
        except Exception as e:
            print(f"Error loading region news: {e}")
            return []
        items = news_doc.get("items") or []
        collected: List[Dict[str, Any]] = []
        for it in items:
            val = it.get("value")
            if not isinstance(val, list):
                continue
            for entry in val:
                if not isinstance(entry, dict):
                    continue
                headline = (entry.get("headline") or "").strip()
                if not headline or headline == "조사 필요":
                    continue
                collected.append({
                    "scope": "region",
                    "headline": headline,
                    "so_what": entry.get("so_what"),
                    "publisher": entry.get("publisher"),
                    "date": entry.get("pub_date") or entry.get("date"),
                    "url": entry.get("url"),
                    "news_category": entry.get("news_category"),
                })
                if len(collected) >= max_items:
                    return collected
        return collected

    def _tier_multiplier(self, tier: Any) -> float:
        """Return weight multiplier for a source tier (1.0 for missing/invalid).

        Config: internal_data.tier_weights = {tier1: 1.0, tier2: 0.85, tier3: 0.7, tier4: 0.5}
        Tier1=1.0 is fixed convention; Tier2~4 are admin-editable.
        """
        if not self.internal_data:
            return 1.0
        tier_weights = self.internal_data.get("tier_weights") or {}
        try:
            t = int(tier)
        except (TypeError, ValueError):
            return 1.0
        return float(tier_weights.get(f"tier{t}", 1.0))

    # ------------------------------------------------------------------
    # Gap analysis (legacy — preserved)
    # ------------------------------------------------------------------

    def analyze_region_structure(self) -> Dict[str, Any]:
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
        countries = self.region_data.get("countries", [])
        analysis["total_countries"] = len(countries)
        analysis["countries"] = [c.get("code") for c in countries]

        for country in countries:
            for item in country.get("items", []):
                category = item.get("category", "unknown")
                analysis["items_by_category"].setdefault(category, []).append({
                    "item": item.get("item", ""),
                    "country": country.get("code"),
                    "role": item.get("role", ""),
                    "has_timeseries": "timeseries" in item,
                    "source_tier": item.get("tier", "N/A")
                })

        analysis["data_quality"] = self._assess_region_data_quality(countries)
        return analysis

    def _assess_region_data_quality(self, countries: List[Dict]) -> Dict[str, Any]:
        quality = {
            "countries_coverage": len(countries),
            "timeseries_coverage_avg": 0,
            "source_tiers": {"tier1": 0, "tier2": 0, "tier3": 0, "tier4": 0},
            "data_sources": set(),
            "gaps_by_tab": {},
            "country_completeness": {}
        }
        all_items: List[Dict] = []
        for country in countries:
            items = country.get("items", [])
            all_items.extend(items)
            quality["country_completeness"][country.get("code", "N/A")] = {
                "total_items": len(items),
                "target_items": 48,
                "completeness": (len(items) / 48 * 100) if len(items) <= 48 else (48 / len(items) * 100)
            }

        if all_items:
            total = len(all_items)
            ts_count = sum(1 for it in all_items if "timeseries" in it)
            quality["timeseries_coverage_avg"] = (ts_count / total) * 100
            for it in all_items:
                tier = it.get("tier", 0)
                key = f"tier{tier}"
                if key in quality["source_tiers"]:
                    quality["source_tiers"][key] += 1
                quality["data_sources"].add(it.get("source", "unknown"))
            quality["gaps_by_tab"] = self._identify_region_gaps(countries)

        quality["data_sources"] = list(quality["data_sources"])
        return quality

    def _identify_region_gaps(self, countries: List[Dict]) -> Dict[str, List[str]]:
        gaps: Dict[str, List[str]] = {}
        for tab_id, tab_spec in self.TYPE2_TABS.items():
            all_items: Dict[str, Dict] = {}
            for country in countries:
                for it in country.get("items", []):
                    all_items[it.get("item", "")] = it
            missing = [f for f in tab_spec.get("required_fields", []) if f not in all_items]
            if missing:
                gaps[f"Type2-Tab-{tab_id}"] = missing
        return gaps

    def generate_gap_report(self) -> Dict[str, Any]:
        if not self.region_data:
            self.load_region_data()
        analysis = self.analyze_region_structure()
        completeness = analysis["data_quality"]["country_completeness"]
        avg = (sum(c["completeness"] for c in completeness.values()) / len(completeness)) if completeness else 0
        return {
            "report_type": "gap_analysis",
            "analysis_type": "TYPE2",
            "region": analysis["region"],
            "region_code": analysis["code"],
            "generated_at": datetime.now().isoformat(),
            "schema_version": analysis["schema_version"],
            "summary": {
                "total_countries": analysis["total_countries"],
                "countries": analysis["countries"],
                "avg_completeness_pct": avg,
            },
            "by_category": analysis["items_by_category"],
            "data_quality": analysis["data_quality"],
            "critical_gaps": self._identify_critical_gaps(analysis),
            "type2_readiness": self._assess_type2_readiness(analysis),
        }

    def _identify_critical_gaps(self, analysis: Dict) -> List[Dict[str, Any]]:
        critical = []
        for tab, missing in analysis["data_quality"].get("gaps_by_tab", {}).items():
            if missing:
                critical.append({
                    "tab": tab,
                    "missing_fields": missing,
                    "count": len(missing),
                    "severity": "HIGH" if len(missing) > 3 else "MEDIUM"
                })
        return critical

    def _assess_type2_readiness(self, analysis: Dict) -> Dict[str, Any]:
        readiness = {"can_generate": True, "tabs": {}}
        gaps_by_tab = analysis["data_quality"].get("gaps_by_tab", {})
        for tab_id in self.TYPE2_TABS:
            missing = gaps_by_tab.get(f"Type2-Tab-{tab_id}", [])
            readiness["tabs"][tab_id] = {
                "name": self.TYPE2_TABS[tab_id]["name"],
                "ready": len(missing) == 0,
                "missing_count": len(missing),
                "missing_fields": missing,
            }
            if missing:
                readiness["can_generate"] = False
        return readiness

    # ------------------------------------------------------------------
    # Tab 2-0: Killswitch
    # ------------------------------------------------------------------

    def compute_killswitch(self) -> Dict[str, Any]:
        """Per-country pass/fail across killswitch gates → status_matrix."""
        countries = self.region_data.get("countries", [])
        matrix: List[Dict[str, Any]] = []
        passed_codes: List[str] = []
        failed_codes: List[str] = []

        for country in countries:
            idx = self._country_items_index(country)
            code = country.get("code")
            gates = {}
            country_pass = True
            for gate in self.KILLSWITCH_ITEMS:
                item = idx.get(gate)
                if item is None:
                    gates[gate] = {"status": "UNKNOWN", "value": None,
                                   "source": None, "tier": None}
                    country_pass = False
                    continue
                result = (item.get("gate_result") or "").upper()
                gates[gate] = {
                    "status": result or "UNKNOWN",
                    "value": item.get("value"),
                    "source": item.get("source"),
                    "tier": item.get("tier"),
                    "gate_scope": item.get("gate_scope"),
                }
                if result != "PASS":
                    country_pass = False
            matrix.append({
                "country": code,
                "country_name": country.get("country"),
                "pass": country_pass,
                "gates": gates,
            })
            (passed_codes if country_pass else failed_codes).append(code)

        return {
            "nature": "status_matrix",
            "source_flag": "CALC",
            "gates": self.KILLSWITCH_ITEMS,
            "countries": matrix,
            "passed": passed_codes,
            "failed": failed_codes,
            "passed_count": len(passed_codes),
            "failed_count": len(failed_codes),
        }

    # ------------------------------------------------------------------
    # Tab 2-1: Business Attractiveness
    # ------------------------------------------------------------------

    def _collect_attractiveness_values(self) -> Dict[str, Dict[str, Optional[float]]]:
        """{country_code: {weight_key: numeric_value_or_None}}"""
        out: Dict[str, Dict[str, Optional[float]]] = {}
        for country in self.region_data.get("countries", []):
            idx = self._country_items_index(country)
            row: Dict[str, Optional[float]] = {}
            for w_key, spec in self.ATTRACTIVENESS_ITEM_MAP.items():
                item = idx.get(spec["item"])
                row[w_key] = self._coerce_numeric(item.get("value")) if item else None
            out[country.get("code")] = row
        return out

    def _collect_attractiveness_tiers(self) -> Dict[str, Dict[str, Optional[int]]]:
        """{country_code: {weight_key: tier_or_None}} — 산식 가중에 사용."""
        out: Dict[str, Dict[str, Optional[int]]] = {}
        for country in self.region_data.get("countries", []):
            idx = self._country_items_index(country)
            row: Dict[str, Optional[int]] = {}
            for w_key, spec in self.ATTRACTIVENESS_ITEM_MAP.items():
                item = idx.get(spec["item"])
                row[w_key] = item.get("tier") if item else None
            out[country.get("code")] = row
        return out

    def _normalize_axis(self, values: Dict[str, Optional[float]], reverse: bool) -> Dict[str, Optional[float]]:
        """Normalize per-country values to 0–100 across region; reverse=True flips."""
        nums = [v for v in values.values() if v is not None]
        if not nums:
            return {c: None for c in values}
        lo, hi = min(nums), max(nums)
        spread = hi - lo
        out: Dict[str, Optional[float]] = {}
        for code, v in values.items():
            if v is None:
                out[code] = None
                continue
            if spread == 0:
                norm = 50.0  # 모두 동일 → 중립
            else:
                norm = (v - lo) / spread * 100.0
            if reverse:
                norm = 100.0 - norm
            out[code] = round(norm, 1)
        return out

    def compute_attractiveness(self) -> Dict[str, Any]:
        """Tab 2-1: normalize each item, weighted average → 0–100 score per country.

        Effective weight = item_weight × tier_multiplier(item.tier).
        Tier 멀티플라이어는 internal_data.tier_weights에서 읽음 (Tier1=1.0 고정).
        """
        weights = (self.internal_data.get("values", {}) or {}).get("biz_attractiveness", {})
        raw = self._collect_attractiveness_values()
        tiers = self._collect_attractiveness_tiers()

        # Per-axis normalization
        axes: Dict[str, Dict[str, Optional[float]]] = {}
        for w_key, spec in self.ATTRACTIVENESS_ITEM_MAP.items():
            values = {code: row[w_key] for code, row in raw.items()}
            axes[w_key] = self._normalize_axis(values, reverse=spec["reverse"])

        countries_out: List[Dict[str, Any]] = []
        for country in self.region_data.get("countries", []):
            code = country.get("code")
            contributions: Dict[str, Dict[str, Any]] = {}
            weighted_sum = 0.0
            weight_total = 0.0
            for w_key, weight in weights.items():
                if w_key not in self.ATTRACTIVENESS_ITEM_MAP:
                    continue
                spec = self.ATTRACTIVENESS_ITEM_MAP[w_key]
                norm = axes[w_key].get(code)
                tier = tiers[code].get(w_key)
                tier_mult = self._tier_multiplier(tier)
                eff_weight = weight * tier_mult
                contributions[w_key] = {
                    "raw_value": raw[code].get(w_key),
                    "normalized": norm,
                    "weight": weight,
                    "tier": tier,
                    "tier_multiplier": tier_mult,
                    "effective_weight": round(eff_weight, 4),
                    "reverse": spec["reverse"],
                    "source_item": spec["item"],
                    "contribution": round(norm * eff_weight, 2) if norm is not None else None,
                }
                if norm is not None:
                    weighted_sum += norm * eff_weight
                    weight_total += eff_weight
            score = round(weighted_sum / weight_total, 1) if weight_total > 0 else None
            countries_out.append({
                "country": code,
                "country_name": country.get("country"),
                "attractiveness_score": score,
                "contributions": contributions,
            })

        ranked = sorted(
            [c for c in countries_out if c["attractiveness_score"] is not None],
            key=lambda c: c["attractiveness_score"], reverse=True
        )
        for rank, c in enumerate(ranked, start=1):
            c["rank"] = rank

        return {
            "nature": "ranking",
            "source_flag": "CALC",
            "weights": weights,
            "tier_weights": self.internal_data.get("tier_weights") or {},
            "axes": axes,
            "countries": countries_out,
            "ranking": [{"rank": c["rank"], "country": c["country"], "score": c["attractiveness_score"]}
                        for c in ranked],
            "method": "min-max normalize per axis → effective weight = item_weight × tier_multiplier → weighted average. config: values.biz_attractiveness × tier_weights.",
        }

    # ------------------------------------------------------------------
    # Tab 2-2: IT/Speed-to-Market Similarity (band, vs baseline)
    # ------------------------------------------------------------------

    def _baseline_country_code(self) -> str:
        """Baseline B국 code. Prefer is_baseline flag in region data, then explicit
        baseline_country field, then internal config region_baselines.

        Falls back to first country whose code matches the configured baseline
        case-insensitively (handles UK vs GB)."""
        countries = (self.region_data or {}).get("countries", []) or []
        # 1) is_baseline flag (most authoritative — comes from research data)
        for c in countries:
            if c.get("is_baseline"):
                return c.get("code")
        # 2) explicit region-level baseline_country
        explicit = (self.region_data or {}).get("baseline_country")
        if explicit:
            return explicit
        # 3) internal config region_baselines
        if not self.internal_data:
            self.load_internal_data()
        region_code = (self.region_data or {}).get("code", "EU")
        cfg = (self.internal_data.get("region_baselines", {}) or {}).get(region_code, "GB")
        # 4) Fuzzy match against actual country codes (GB ↔ UK)
        codes = {c.get("code") for c in countries}
        if cfg in codes:
            return cfg
        aliases = {"GB": "UK", "UK": "GB"}
        alt = aliases.get(cfg)
        if alt and alt in codes:
            return alt
        return cfg

    def _it_axis_similarity(self, axis_key: str, base_item: Optional[Dict],
                            target_item: Optional[Dict]) -> Optional[float]:
        """Band similarity (0–100) for one axis comparing target vs baseline."""
        spec = self.IT_SIMILARITY_ITEM_MAP[axis_key]
        kind = spec["type"]
        if base_item is None or target_item is None:
            return None

        if kind == "numeric_1to5":
            bv = self._coerce_numeric(base_item.get("value"))
            tv = self._coerce_numeric(target_item.get("value"))
            if bv is None or tv is None:
                return None
            diff = abs(bv - tv)  # 0..4
            # band: diff 0 → 100, 1 → 80, 2 → 60, 3 → 40, 4 → 20
            return max(0.0, 100.0 - diff * 20.0)

        if kind == "gate":
            br = (base_item.get("gate_result") or "").upper()
            tr = (target_item.get("gate_result") or "").upper()
            if not br or not tr:
                return None
            # 동일 PASS/FAIL → 高 / 한쪽만 PASS → 中 / 둘 다 모름 처리 위
            if br == tr:
                return 90.0  # 동일 규제 결과 → 高 밴드
            if "PASS" in (br, tr):
                return 50.0  # 한쪽 통과 → 中 밴드
            return 30.0

        if kind == "categorical":
            bv = str(base_item.get("value") or "").strip().lower()
            tv = str(target_item.get("value") or "").strip().lower()
            if not bv or not tv:
                return None
            if bv == tv:
                return 100.0
            # Jaccard 유사도 (CJK 안전: 단어/한자 단위 + 영문 구두점 정규화)
            import re
            def tokens(s: str) -> set:
                # 구두점·괄호·세그먼트 구분자 정규화 후 토큰화
                s = re.sub(r"[,()·/+\-]+", " ", s)
                raw = [t for t in s.split() if len(t) > 1]
                return set(raw)
            b_t, t_t = tokens(bv), tokens(tv)
            if not b_t or not t_t:
                return 50.0
            jaccard = len(b_t & t_t) / len(b_t | t_t)
            # 0~1 → 30~95 매핑 (완전 동일=100은 위에서 처리)
            return round(30.0 + jaccard * 65.0, 1)

        return None

    def _bucket_10(self, score: Optional[float]) -> Optional[int]:
        """Round to nearest 10-point bucket per spec (착시 방지)."""
        if score is None:
            return None
        return int(round(score / 10.0) * 10)

    def compute_it_similarity(self) -> Dict[str, Any]:
        weights = (self.internal_data.get("values", {}) or {}).get("it_readiness", {})
        base_code = self._baseline_country_code()
        countries = self.region_data.get("countries", [])
        base_country = next((c for c in countries if c.get("code") == base_code), None)
        base_idx = self._country_items_index(base_country) if base_country else {}

        per_country: List[Dict[str, Any]] = []
        for country in countries:
            code = country.get("code")
            idx = self._country_items_index(country)
            axes: Dict[str, Dict[str, Any]] = {}
            weighted_sum = 0.0
            weight_total = 0.0
            for axis_key, weight in weights.items():
                if axis_key not in self.IT_SIMILARITY_ITEM_MAP:
                    continue
                source_item = self.IT_SIMILARITY_ITEM_MAP[axis_key]["item"]
                target_item = idx.get(source_item)
                raw_score = self._it_axis_similarity(
                    axis_key, base_idx.get(source_item), target_item
                )
                bucket = self._bucket_10(raw_score)
                # Tier 가중: 대상국 데이터의 신뢰도 — 기준국은 비교 잣대라 대상국 tier 사용
                tier = (target_item or {}).get("tier")
                tier_mult = self._tier_multiplier(tier)
                eff_weight = weight * tier_mult
                axes[axis_key] = {
                    "source_item": source_item,
                    "weight": weight,
                    "tier": tier,
                    "tier_multiplier": tier_mult,
                    "effective_weight": round(eff_weight, 4),
                    "target_value": (target_item or {}).get("value"),
                    "baseline_value": (base_idx.get(source_item) or {}).get("value"),
                    "score_raw": raw_score,
                    "score_band": bucket,
                }
                if raw_score is not None:
                    weighted_sum += raw_score * eff_weight
                    weight_total += eff_weight
            it_score_raw = (weighted_sum / weight_total) if weight_total > 0 else None
            per_country.append({
                "country": code,
                "country_name": country.get("country"),
                "it_similarity_raw": round(it_score_raw, 1) if it_score_raw is not None else None,
                "it_similarity_band": self._bucket_10(it_score_raw),
                "is_baseline": code == base_code,
                "axes": axes,
            })

        ranked = sorted(
            [c for c in per_country if c["it_similarity_band"] is not None],
            key=lambda c: (c["it_similarity_band"] or 0, c["it_similarity_raw"] or 0),
            reverse=True,
        )
        for rank, c in enumerate(ranked, start=1):
            c["rank"] = rank

        return {
            "nature": "score_multiaxis",
            "source_flag": "CALC",
            "baseline_country": base_code,
            "weights": weights,
            "tier_weights": self.internal_data.get("tier_weights") or {},
            "countries": per_country,
            "ranking": [{"rank": c["rank"], "country": c["country"],
                         "score_band": c["it_similarity_band"]}
                        for c in ranked],
            "method": ("축별 raw = 수치(100−|Δ|×20) / 범주(텍스트 Jaccard 30+J×65) / gate(동일=90·한쪽 PASS=50) "
                       "→ effective weight = item_weight × tier_multiplier → 가중평균 raw → 10점 구간 반올림."),
            "note": "10점 구간 표기. 소수점·1점 단위 비교 금지(spec). 동률 시 raw로 타이브레이크. Tier 가중은 대상국 데이터 신뢰도 기준.",
        }

    # ------------------------------------------------------------------
    # Tab 2-3: Market Background
    # ------------------------------------------------------------------

    def compute_market_background(self) -> Dict[str, Any]:
        countries_out: List[Dict[str, Any]] = []
        for country in self.region_data.get("countries", []):
            idx = self._country_items_index(country)
            countries_out.append({
                "country": country.get("code"),
                "country_name": country.get("country"),
                "oem_top5": (idx.get("OEM 순위(Top 5)") or {}).get("value"),
                "brand_top10": (idx.get("브랜드 Top10") or {}).get("value"),
                "purchase_pattern": (idx.get("구매 패턴(할부·리스 비중)") or {}).get("value"),
                "purchase_pattern_unit": (idx.get("구매 패턴(할부·리스 비중)") or {}).get("unit"),
                "competitors": (idx.get("경쟁사 리스트") or {}).get("value"),
                "competitor_entry_form": (idx.get("경쟁사 진출 형태") or {}).get("value"),
                "competitor_rates": (idx.get("경쟁사 금리 범위") or {}).get("value"),
                "avg_new_car_price": (idx.get("평균 신차가격") or {}).get("value"),
                "qualitative_summary": (idx.get("해당국 정성 요약") or {}).get("value"),
            })
        return {
            "nature": "ranking",
            "source_flag": "EXT",
            "countries": countries_out,
        }

    # ------------------------------------------------------------------
    # Quickwin (overall) + Top-3 cards
    # ------------------------------------------------------------------

    def compute_quickwin(self, killswitch: Dict, attractiveness: Dict,
                         it_similarity: Dict) -> Dict[str, Any]:
        blend = ((self.internal_data.get("values", {}) or {}).get("report_blend", {}) or {})
        w_biz = blend.get("w_biz", 0.6)
        w_it = blend.get("w_it", 0.4)

        attr_map = {c["country"]: c["attractiveness_score"] for c in attractiveness["countries"]}
        it_map = {c["country"]: c["it_similarity_raw"] for c in it_similarity["countries"]}
        it_band_map = {c["country"]: c["it_similarity_band"] for c in it_similarity["countries"]}
        passed = set(killswitch["passed"])
        baseline = it_similarity.get("baseline_country")

        rows: List[Dict[str, Any]] = []
        for country in self.region_data.get("countries", []):
            code = country.get("code")
            attr = attr_map.get(code)
            it = it_map.get(code)
            is_baseline = code == baseline
            ks_excluded = code not in passed
            excluded = is_baseline or ks_excluded
            raw_score = None
            if attr is not None and it is not None:
                raw_score = attr * w_biz + it * w_it
            rows.append({
                "country": code,
                "country_name": country.get("country"),
                "attractiveness": attr,
                "it_similarity": it,
                "it_similarity_band": it_band_map.get(code),
                "quickwin_raw": round(raw_score, 1) if raw_score is not None else None,
                "quickwin_band": self._bucket_10(raw_score),
                "is_baseline": is_baseline,
                "killswitch_excluded": ks_excluded,
                "excluded": excluded,
                "exclusion_reason": (
                    "baseline (기준국, 후보 아님)" if is_baseline else
                    "killswitch fail" if ks_excluded else None
                ),
            })

        eligible = [r for r in rows if not r["excluded"] and r["quickwin_band"] is not None]
        # band 동률 시 raw 값으로 타이브레이크 (실제 점수 정밀도 보존)
        ranked = sorted(
            eligible,
            key=lambda r: (r["quickwin_band"] or 0, r["quickwin_raw"] or 0),
            reverse=True,
        )
        for rank, r in enumerate(ranked, start=1):
            r["rank"] = rank

        return {
            "nature": "ranking",
            "source_flag": "CALC",
            "weights": {"w_biz": w_biz, "w_it": w_it},
            "baseline_country": baseline,
            "rows": rows,
            "ranking": [{"rank": r["rank"], "country": r["country"],
                         "score_band": r["quickwin_band"],
                         "attractiveness": r["attractiveness"],
                         "it_similarity_band": r["it_similarity_band"]}
                        for r in ranked],
            "note": "퀵윈 = 매력도×w_biz + IT유사도×w_it. 기준국(B국) 및 킬스위치 탈락국 제외. 10점 구간 표기.",
        }

    def build_top3_cards(self, quickwin: Dict, killswitch: Dict,
                          attractiveness: Dict, it_similarity: Dict) -> List[Dict[str, Any]]:
        ranking = quickwin.get("ranking", [])[:3]
        attr_map = {c["country"]: c for c in attractiveness["countries"]}
        it_map = {c["country"]: c for c in it_similarity["countries"]}
        ks_map = {c["country"]: c for c in killswitch["countries"]}

        cards: List[Dict[str, Any]] = []
        for entry in ranking:
            code = entry["country"]
            country = next((c for c in self.region_data.get("countries", []) if c.get("code") == code), {})
            idx = self._country_items_index(country)
            news = (idx.get("외부 이슈 스캔") or {}).get("value")
            top_news = None
            if isinstance(news, list) and news:
                top_news = news[0]
            cards.append({
                "rank": entry["rank"],
                "country": code,
                "country_name": country.get("country"),
                "quickwin_score_band": entry["score_band"],
                "attractiveness": attr_map.get(code, {}).get("attractiveness_score"),
                "it_similarity_band": it_map.get(code, {}).get("it_similarity_band"),
                "killswitch_pass": ks_map.get(code, {}).get("pass"),
                "market_brief": {
                    "신차_판매대수": (idx.get("신차 판매대수") or {}).get("value"),
                    "금융_이용률_신차": (idx.get("금융 이용률(신차)") or {}).get("value"),
                    "EV_보급률": (idx.get("EV 보급률") or {}).get("value"),
                },
                "competition_brief": {
                    "금융사_Top5": (idx.get("금융사 순위(Top 5)") or {}).get("value"),
                    "경쟁사_진출_형태": (idx.get("경쟁사 진출 형태") or {}).get("value"),
                },
                "top_news": top_news,  # NEWS flag
                "ai_comment": (idx.get("해당국 정성 요약") or {}).get("insight")
                              or (idx.get("해당국 정성 요약") or {}).get("value"),
                "source_flags": {
                    "rank": "CALC", "score": "CALC", "market": "EXT",
                    "competition": "EXT", "news": "NEWS", "ai_comment": "AI",
                },
            })
        return cards

    # ------------------------------------------------------------------
    # Executive Summary
    # ------------------------------------------------------------------

    def build_executive_summary(self, quickwin: Dict, killswitch: Dict,
                                 attractiveness: Dict, it_similarity: Dict,
                                 top3: List[Dict]) -> Dict[str, Any]:
        # A. 핵심 결론 (CALC 인용만)
        top_ranking = quickwin.get("ranking", [])[:3]
        why_top1 = None
        if top3:
            top1 = top3[0]
            why_top1 = (
                f"{top1['country_name']}({top1['country']}) — "
                f"매력도 {top1['attractiveness']}, IT유사도 {top1['it_similarity_band']} 구간, "
                f"퀵윈 {top1['quickwin_score_band']} 구간"
            )

        # B. AI 교차 인사이트 (탭 간 해석) — 기준국 제외하고 후보국 중에서 비교
        ai_insights: List[str] = []
        baseline = quickwin.get("baseline_country")
        attr_rank = {r["country"]: r["rank"] for r in attractiveness["ranking"] if r["country"] != baseline}
        it_rank = {r["country"]: r["rank"] for r in it_similarity["ranking"] if r["country"] != baseline}
        if attr_rank and it_rank:
            top_attr = min(attr_rank, key=lambda k: attr_rank[k])
            top_it = min(it_rank, key=lambda k: it_rank[k])
            if top_attr != top_it:
                ai_insights.append(
                    f"후보국 중 매력도 1위({top_attr})와 IT유사도 1위({top_it})가 일치하지 않음 — "
                    f"단기 확산(IT 유사)과 시장 잠재력(매력도) 사이 트레이드오프 존재."
                )
            else:
                ai_insights.append(
                    f"{top_attr}이 후보국 매력도·IT유사도 모두 1위 — 권역 진출의 명백한 1순위."
                )
        if baseline:
            ai_insights.append(
                f"기준국 {baseline}은 이미 시스템 보유국 → 순위에서 제외(B국 시스템 확산의 비교 기준)."
            )
        if killswitch.get("failed"):
            ai_insights.append(
                f"킬스위치 탈락국: {', '.join(killswitch['failed'])} — "
                f"규제·신용등급 게이트로 사전 차단(스코어링 제외)."
            )

        # C. 외부 이슈 스캔 (NEWS) — 권역 공통 이슈를 가장 위에, 그 다음 상위 3개국 헤드라인
        news: List[Dict[str, Any]] = []
        # C-1. 권역 단위 뉴스 (별도 파일 {CODE}_news_latest.json)
        region_news = self._load_region_news(max_items=3)
        for item in region_news:
            news.append({
                "country": None,                  # 권역 공통 — 특정 국가 없음
                "scope": "region",
                "headline": item.get("headline"),
                "so_what": item.get("so_what"),
                "publisher": item.get("publisher"),
                "date": item.get("date"),
                "url": item.get("url"),
                "news_category": item.get("news_category"),
            })
        # C-2. 상위 3개국 헤드라인
        for country in self.region_data.get("countries", []):
            code = country.get("code")
            if code not in [t["country"] for t in top3]:
                continue
            idx = self._country_items_index(country)
            country_news = (idx.get("외부 이슈 스캔") or {}).get("value")
            if isinstance(country_news, list) and country_news:
                first = country_news[0]
                news.append({
                    "country": code,
                    "scope": "country",
                    "headline": first.get("headline") if isinstance(first, dict) else str(first),
                    "so_what": first.get("so_what") if isinstance(first, dict) else None,
                    "publisher": first.get("publisher") if isinstance(first, dict) else None,
                    "date": first.get("date") if isinstance(first, dict) else None,
                })

        return {
            "core_conclusion": {
                "source_flag": "CALC",
                "top3": top_ranking,
                "killswitch_failed_count": killswitch.get("failed_count", 0),
                "why_top1": why_top1,
            },
            "ai_cross_insight": {
                "source_flag": "AI",
                "insights": ai_insights,
            },
            "external_news_scan": {
                "source_flag": "NEWS",
                "items": news,
                "region_news_count": len(region_news),
                "note": f"권역 공통 이슈 {len(region_news)}건 + 상위 3개국 헤드라인. '조사 필요' 항목은 제외.",
            },
        }

    # ------------------------------------------------------------------
    # Type 2 Report Assembly
    # ------------------------------------------------------------------

    def generate_type2_report(self) -> Dict[str, Any]:
        if not self.region_data:
            self.load_region_data()
        if not self.internal_data:
            self.load_internal_data()

        region_code = self.region_data.get("code", "N/A")
        base_country = self._baseline_country_code()

        analysis = self.analyze_region_structure()
        quality = analysis["data_quality"]
        readiness = self._assess_type2_readiness(analysis)

        killswitch = self.compute_killswitch()
        attractiveness = self.compute_attractiveness()
        it_similarity = self.compute_it_similarity()
        market_bg = self.compute_market_background()
        quickwin = self.compute_quickwin(killswitch, attractiveness, it_similarity)
        top3 = self.build_top3_cards(quickwin, killswitch, attractiveness, it_similarity)
        exec_summary = self.build_executive_summary(
            quickwin, killswitch, attractiveness, it_similarity, top3
        )

        evaluated = [c.get("code") for c in self.region_data.get("countries", [])]

        report = {
            "report_id": f"RPT_RGN_{region_code}_001",  # finalized at save time
            "report_type": "type2_region",
            "title": f"{self.region_data.get('region', region_code)} 권역 퀵윈 순위 보고서",
            "target": {
                "region": region_code,
                "evaluated_countries": evaluated,
                "baseline_country": base_country,
            },
            "generated_at": datetime.now().isoformat(),
            "generated_by": "engine",
            "data_snapshot_id": self.region_data.get("fetched_at"),
            "config_version": (self.internal_data or {}).get("version"),
            "engine_version": "v1.0",
            "schema_version": self.region_data.get("schema_version", "N/A"),
            "fx": (self.internal_data or {}).get("fx"),

            "region_meta": {
                "region": self.region_data.get("region"),
                "region_ko": self.region_data.get("region_ko"),
                "code": region_code,
                "fetched_at": self.region_data.get("fetched_at"),
                "fetched_by": self.region_data.get("fetched_by"),
            },

            "data_quality": {
                "total_countries": len(evaluated),
                "countries": evaluated,
                "timeseries_coverage_avg": quality.get("timeseries_coverage_avg", 0),
                "source_tiers": quality.get("source_tiers", {}),
                "country_completeness": quality.get("country_completeness", {}),
                "critical_gaps": self._identify_critical_gaps(analysis),
                "readiness": readiness,
            },

            "tabs": {
                "tab_2_0_killswitch": killswitch,
                "tab_2_1_attractiveness": attractiveness,
                "tab_2_2_it_similarity": it_similarity,
                "tab_2_3_market_background": market_bg,
                "quickwin": quickwin,
                "top3_country_cards": top3,
                "executive_summary": exec_summary,
            },
        }
        return report

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_gap_report(self, gap_report: Dict[str, Any]) -> str:
        region_code = gap_report["region_code"]
        output_dir = Path(self.output_base) / "analysis" / region_code
        output_dir.mkdir(parents=True, exist_ok=True)
        existing = list(output_dir.glob(f"RPT_RGN_{region_code}_*.json"))
        next_num = (max((int(f.stem.split("_")[-1]) for f in existing
                         if f.stem.split("_")[-1].isdigit()), default=0) + 1)
        out = output_dir / f"RPT_RGN_{region_code}_{next_num:03d}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(gap_report, f, ensure_ascii=False, indent=2)
        return str(out)

    def save_type2_report(self, report: Dict[str, Any]) -> str:
        region_code = report["target"]["region"]
        output_dir = Path(self.output_base) / "region" / region_code / "data"
        output_dir.mkdir(parents=True, exist_ok=True)
        existing = list(output_dir.glob(f"RPT_RGN_{region_code}_*.json"))
        next_num = (max((int(f.stem.split("_")[-1]) for f in existing
                         if f.stem.split("_")[-1].isdigit()), default=0) + 1)
        report["report_id"] = f"RPT_RGN_{region_code}_{next_num:03d}"
        out = output_dir / f"RPT_RGN_{region_code}_{next_num:03d}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return str(out)

    # ------------------------------------------------------------------
    # Readable gap report (legacy)
    # ------------------------------------------------------------------

    def generate_readable_gap_report(self, gap_report: Dict[str, Any]) -> str:
        lines = [
            f"\n{'='*70}",
            f"REGION GAP ANALYSIS: {gap_report['region']} ({gap_report['region_code']})",
            f"{'='*70}",
            f"Generated: {gap_report['generated_at']}",
            f"Schema Version: {gap_report['schema_version']}",
            "",
        ]
        summary = gap_report["summary"]
        lines += [
            "SUMMARY",
            f"  Countries Analyzed: {summary['total_countries']}",
            f"  Countries: {', '.join(summary['countries'])}",
            f"  Average Completeness: {summary['avg_completeness_pct']:.1f}%",
            "",
        ]
        critical = gap_report["critical_gaps"]
        lines.append("CRITICAL GAPS:")
        if critical:
            for gap in critical:
                lines.append(f"  [{gap['severity']}] {gap['tab']}: missing {gap['count']} fields")
        else:
            lines.append("  None — all required fields present across region!")
        lines.append("")
        type2 = gap_report["type2_readiness"]
        lines.append(f"TYPE2 READINESS: {'YES' if type2['can_generate'] else 'NO'}")
        for tab_id, st in type2["tabs"].items():
            lines.append(f"  Tab {tab_id} {'OK' if st['ready'] else 'FAIL'}: {st['name']}")
        lines.append(f"\n{'='*70}\n")
        return "\n".join(lines)


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python region_report_engine.py <region_data_json> [internal_data_json] [output_base_path]")
        print("Example: python region_report_engine.py storage/data/research/region/EU/EU_latest.json")
        sys.exit(1)

    region_data_path = sys.argv[1]
    internal_path = sys.argv[2] if len(sys.argv) > 2 else "storage/data/internal/internal_latest.json"
    output_base = sys.argv[3] if len(sys.argv) > 3 else "storage/report"

    engine = RegionReportEngine(region_data_path, internal_path, output_base)
    if not engine.load_region_data():
        sys.exit(1)
    if not engine.load_internal_data():
        print("Warning: Could not load internal data, some features may be limited")

    # 1) Gap analysis (legacy)
    gap_report = engine.generate_gap_report()
    print(engine.generate_readable_gap_report(gap_report))
    gap_path = engine.save_gap_report(gap_report)
    print(f"Gap analysis saved: {gap_path}")

    # 2) Full Type 2 report
    print("=" * 70)
    print("Generating Type 2 Region Report (Quickwin Ranking)...")
    print("=" * 70)
    report = engine.generate_type2_report()
    out = engine.save_type2_report(report)
    print(f"Type 2 report saved: {out}")

    ks = report["tabs"]["tab_2_0_killswitch"]
    qw = report["tabs"]["quickwin"]
    print(f"\nKillswitch: {ks['passed_count']} pass / {ks['failed_count']} fail")
    print("Quickwin Top 3:")
    for entry in qw.get("ranking", [])[:3]:
        print(f"  #{entry['rank']} {entry['country']} — band {entry['score_band']} "
              f"(attractiveness {entry['attractiveness']}, IT band {entry['it_similarity_band']})")
    return 0


if __name__ == "__main__":
    main()
