#!/usr/bin/env python3
"""
Data contract validator (U1).

검증 대상 — 두 종류의 입력 데이터:
  1. country research JSON (schema v1.1)  — storage/data/research/country/<CODE>/<CODE>_latest.json
  2. internal ruleset JSON (v1.3)          — storage/data/internal/internal_latest.json

이 모듈은 "계약"만 검사한다(값의 사실성·산식은 검사하지 않음). U2 이후 엔진이
이 계약을 신뢰하고 계산하므로, 여기서 구조·범위·일관성을 못 박는다.

사용:
  python3 app/backend/validation/validate_data.py            # 전체(존재하는 country 전부 + internal)
  python3 app/backend/validation/validate_data.py PL         # 특정 국가만
  pytest app/backend/validation/validate_data.py             # 정상 PASS + 오염 FAIL 회귀

각 엔진과 동일하게 자기 위치 기준으로 storage를 해석한다(STORAGE 변수).
"""

import json
import re
import sys
from pathlib import Path

# 엔진 컨벤션: 자기 위치 기준 storage 해석. validation/ → backend/ → storage/
STORAGE = Path(__file__).resolve().parent.parent / "storage"
COUNTRY_DIR = STORAGE / "data" / "research" / "country"
INTERNAL_LATEST = STORAGE / "data" / "internal" / "internal_latest.json"

# ── 계약 상수 (스키마 v1.1 / internal v1.3) ───────────────────────────────
SCHEMA_VERSION = "1.1"
REGIONS = {"EU", "NORTH_AMERICA", "SOUTH_AMERICA", "APAC"}
CATEGORIES = {"business", "it", "shared"}
ROLES = {"gate", "score", "context"}
DIRECTIONS = {"up", "down"}
AXES = {"attractiveness", "difficulty", "similarity"}
GATE_RESULTS = {"PASS", "FAIL", "FLAG"}
GATE_SCOPES = {"country", "segment", "operating_model"}
CONTEXT_TYPES = {"descriptive", "segmenting", "news"}
NEWS_CATEGORIES = {"geopolitical", "finance", "auto_market", "auto_finance", "credit_abs"}

COUNTRY_TOP_KEYS = {
    "country", "country_ko", "code", "region", "is_baseline", "currency",
    "schema_version", "data_year", "fetched_at", "fetched_by", "overall_insight", "items",
}
ITEM_COMMON_KEYS = {"item", "category", "role", "tier", "source"}

# internal v1.3 — 4카테고리(영문 키). PS1 한글 라벨은 프론트가 매핑.
RULESET_CATEGORIES = {"market", "finance", "regulation", "system"}
FX_BASE = "KRW"

# NEWS 출처 화이트리스트 (country_research_schema.md §3 / prompt [NEWS 규칙])
NEWS_WHITELIST = {
    "geopolitical": {"Reuters", "Bloomberg", "AP"},
    "finance": {"Financial Times", "Wall Street Journal"},
    "auto_market": {"Automotive News", "Automotive News Europe", "Just Auto",
                    "WardsAuto", "Automobilwoche", "Nikkei Asia"},
    "auto_finance": {"Auto Finance News", "American Banker",
                     "Cox Automotive/Manheim", "Cox Automotive", "Manheim",
                     "MUVVI", "S&P Global Mobility", "S&P Global"},
    "credit_abs": {"Moody's", "S&P", "Fitch", "S&P Global", "S&P Global Ratings"},
}

ISO_A2 = re.compile(r"^[A-Z]{2}$")
EPS = 1e-6  # 가중치 합 비교 허용 오차


class ValidationError(Exception):
    """검증 실패. 누적된 오류 목록을 담는다."""

    def __init__(self, label, errors):
        self.label = label
        self.errors = errors
        super().__init__(f"{label}: {len(errors)} error(s)")


# ── country JSON 검증 ─────────────────────────────────────────────────────
def validate_country(data, label="country"):
    """country research JSON(v1.1) 구조·범위·일관성 검사. 오류 목록 반환(빈 = PASS)."""
    errors = []

    missing = COUNTRY_TOP_KEYS - data.keys()
    if missing:
        errors.append(f"최상위 키 누락: {sorted(missing)}")

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version={data.get('schema_version')!r} (기대 {SCHEMA_VERSION!r})")

    code = data.get("code")
    if not isinstance(code, str) or not ISO_A2.match(code):
        errors.append(f"code={code!r} — ISO alpha-2 2자리 대문자여야 함")

    if data.get("region") not in REGIONS:
        errors.append(f"region={data.get('region')!r} ∉ {sorted(REGIONS)}")

    if not isinstance(data.get("is_baseline"), bool):
        errors.append("is_baseline 은 bool 이어야 함")

    items = data.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items 는 비어있지 않은 배열이어야 함")
        return errors  # items 없으면 이후 검사 불가

    for idx, it in enumerate(items):
        errors.extend(_validate_item(it, idx))

    return errors


def _validate_item(it, idx):
    errors = []
    where = f"items[{idx}]({it.get('item', '?')})"

    miss = ITEM_COMMON_KEYS - it.keys()
    if miss:
        errors.append(f"{where}: 공통 필드 누락 {sorted(miss)}")

    if it.get("category") not in CATEGORIES:
        errors.append(f"{where}: category={it.get('category')!r} ∉ {sorted(CATEGORIES)}")

    role = it.get("role")
    if role not in ROLES:
        errors.append(f"{where}: role={role!r} ∉ {sorted(ROLES)}")

    tier = it.get("tier")
    if not isinstance(tier, int) or not (1 <= tier <= 4):
        errors.append(f"{where}: tier={tier!r} — 1~4 정수여야 함")

    # role별 추가 필드
    if role == "score":
        if it.get("direction") not in DIRECTIONS:
            errors.append(f"{where}: direction={it.get('direction')!r} ∉ {sorted(DIRECTIONS)}")
        if it.get("axis") not in AXES:
            errors.append(f"{where}: axis={it.get('axis')!r} ∉ {sorted(AXES)}")
        if "value" not in it:
            errors.append(f"{where}: score 는 value 필수")
        if "timeseries" not in it:
            errors.append(f"{where}: score 는 timeseries 필드 필수(없으면 null)")
    elif role == "gate":
        gr = it.get("gate_result")
        if gr not in GATE_RESULTS:
            errors.append(f"{where}: gate_result={gr!r} ∉ {sorted(GATE_RESULTS)}")
        if it.get("gate_scope") not in GATE_SCOPES:
            errors.append(f"{where}: gate_scope={it.get('gate_scope')!r} ∉ {sorted(GATE_SCOPES)}")
        # tier≤3 데이터로 FAIL 금지 → FLAG (schema §3 / prompt 규칙6)
        if gr == "FAIL" and isinstance(tier, int) and tier >= 3:
            errors.append(f"{where}: tier {tier} 인데 gate_result=FAIL — tier≤3 은 FLAG 여야 함")
    elif role == "context":
        ct = it.get("context_type")
        if ct not in CONTEXT_TYPES:
            errors.append(f"{where}: context_type={ct!r} ∉ {sorted(CONTEXT_TYPES)}")
        if ct == "news":
            errors.extend(_validate_news(it, where))

    return errors


def _validate_news(it, where):
    errors = []
    value = it.get("value")
    if not isinstance(value, list):
        errors.append(f"{where}: news 의 value 는 이슈 객체 배열이어야 함")
        return errors

    for j, obj in enumerate(value):
        w = f"{where}.value[{j}]"
        if not isinstance(obj, dict):
            errors.append(f"{w}: 객체여야 함")
            continue
        nc = obj.get("news_category")
        if nc not in NEWS_CATEGORIES:
            errors.append(f"{w}: news_category={nc!r} ∉ {sorted(NEWS_CATEGORIES)}")
        publisher = (obj.get("publisher") or "").strip()
        so_what = (obj.get("so_what") or "").strip()
        # "조사 필요" 플레이스홀더는 빈 출처 허용. 그 외엔 화이트리스트 강제.
        is_placeholder = (so_what == "조사 필요") or publisher == ""
        if not is_placeholder and nc in NEWS_WHITELIST:
            if publisher not in NEWS_WHITELIST[nc]:
                errors.append(
                    f"{w}: publisher={publisher!r} 가 '{nc}' 화이트리스트 밖 "
                    f"(허용: {sorted(NEWS_WHITELIST[nc])})"
                )
    return errors


# ── internal JSON 검증 ────────────────────────────────────────────────────
def validate_internal(data, known_country_codes=None, label="internal"):
    """internal ruleset(v1.3) 검사. 오류 목록 반환(빈 = PASS)."""
    errors = []
    known_country_codes = known_country_codes or set()

    for key in ("version", "updated_at", "weights", "regions",
                "similarity_brackets", "fx"):
        if key not in data:
            errors.append(f"최상위 키 누락: {key!r}")

    # fx.base = KRW
    fx = data.get("fx", {})
    if fx.get("base") != FX_BASE:
        errors.append(f"fx.base={fx.get('base')!r} (기대 {FX_BASE!r})")
    if not isinstance(fx.get("rates"), dict) or not fx.get("rates"):
        errors.append("fx.rates 는 비어있지 않은 객체여야 함")

    # weights: category_weights(합=100) + items(카테고리별 합=1)
    errors.extend(_validate_weights(data.get("weights", {})))

    # similarity_brackets 연속성(0~100 빈틈/겹침 없이 커버)
    errors.extend(_validate_brackets(data.get("similarity_brackets")))

    # regions 메타: name_ko/name_en/members/baseline, baseline ∈ members
    errors.extend(_validate_regions(data.get("regions", {}), known_country_codes))

    return errors


def _validate_weights(weights):
    errors = []
    cw = weights.get("category_weights")
    if not isinstance(cw, dict):
        errors.append("weights.category_weights 객체 누락")
        return errors
    if set(cw.keys()) != RULESET_CATEGORIES:
        errors.append(f"category_weights 키={sorted(cw.keys())} (기대 {sorted(RULESET_CATEGORIES)})")
    total = sum(v for v in cw.values() if isinstance(v, (int, float)))
    if abs(total - 100) > EPS:
        errors.append(f"category_weights 합={total} (기대 100)")

    items = weights.get("items")
    if not isinstance(items, dict):
        errors.append("weights.items 객체 누락")
        return errors
    for cat in RULESET_CATEGORIES:
        sub = items.get(cat)
        if not isinstance(sub, dict) or not sub:
            errors.append(f"weights.items.{cat} 누락/비어있음")
            continue
        s = sum(v for v in sub.values() if isinstance(v, (int, float)))
        if abs(s - 1.0) > EPS:
            errors.append(f"weights.items.{cat} 내부 합={s} (기대 1.0)")
    return errors


def _validate_brackets(brackets):
    errors = []
    if not isinstance(brackets, list) or not brackets:
        errors.append("similarity_brackets 는 비어있지 않은 배열이어야 함")
        return errors
    # min 오름차순 정렬 후 0~100 연속성 확인
    try:
        ordered = sorted(brackets, key=lambda b: b["min"])
    except (KeyError, TypeError):
        errors.append("similarity_brackets 각 항목에 min/max 필요")
        return errors
    if ordered[0]["min"] != 0:
        errors.append(f"similarity_brackets 최저 min={ordered[0]['min']} (기대 0)")
    if ordered[-1]["max"] != 100:
        errors.append(f"similarity_brackets 최고 max={ordered[-1]['max']} (기대 100)")
    for a, b in zip(ordered, ordered[1:]):
        if b["min"] != a["max"] + 1:
            errors.append(f"similarity_brackets 불연속: [{a['min']},{a['max']}] → [{b['min']},{b['max']}]")
    return errors


def _validate_regions(regions, known_country_codes):
    errors = []
    if not isinstance(regions, dict) or not regions:
        errors.append("regions 는 비어있지 않은 객체여야 함")
        return errors
    for rid, meta in regions.items():
        if rid not in REGIONS:
            errors.append(f"regions.{rid}: 알 수 없는 권역 코드 (기대 {sorted(REGIONS)})")
        if not isinstance(meta, dict):
            errors.append(f"regions.{rid}: 객체여야 함")
            continue
        for k in ("name_ko", "name_en", "members", "baseline"):
            if k not in meta:
                errors.append(f"regions.{rid}: {k!r} 누락")
        members = meta.get("members")
        if not isinstance(members, list) or not members:
            errors.append(f"regions.{rid}.members 는 비어있지 않은 배열이어야 함")
            continue
        baseline = meta.get("baseline")
        if baseline not in members:
            errors.append(f"regions.{rid}.baseline={baseline!r} 가 members 에 없음")
        # members 가 실제 country 코드와 매칭되는지(데이터 있으면)
        if known_country_codes:
            unknown = [m for m in members if m not in known_country_codes]
            # 아직 리서치 안 된 후보국은 허용 — 경고가 아닌 정보. 여기선 강제하지 않음.
    return errors


# ── 러너 ──────────────────────────────────────────────────────────────────
def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def discover_country_codes():
    """research/country 아래 *_latest.json 이 존재하는 국가 코드 집합."""
    codes = set()
    if COUNTRY_DIR.exists():
        for sub in COUNTRY_DIR.iterdir():
            if sub.is_dir() and (sub / f"{sub.name}_latest.json").exists():
                codes.add(sub.name)
    return codes


def run(only_code=None):
    """전체(또는 특정 국가) + internal 검증. (passed: bool, report: str) 반환."""
    lines = []
    ok = True

    codes = sorted(discover_country_codes())
    if only_code:
        codes = [c for c in codes if c == only_code]
        if not codes:
            return False, f"country '{only_code}' 데이터 없음 ({COUNTRY_DIR})"

    for code in codes:
        path = COUNTRY_DIR / code / f"{code}_latest.json"
        errs = validate_country(_load(path), label=code)
        if errs:
            ok = False
            lines.append(f"✗ {code}: {len(errs)} error(s)")
            lines += [f"    - {e}" for e in errs]
        else:
            lines.append(f"✓ {code}")

    # internal (특정 국가만 검증 요청이어도 함께 검사)
    if INTERNAL_LATEST.exists():
        errs = validate_internal(_load(INTERNAL_LATEST), known_country_codes=set(codes))
        if errs:
            ok = False
            lines.append(f"✗ internal: {len(errs)} error(s)")
            lines += [f"    - {e}" for e in errs]
        else:
            lines.append("✓ internal")
    else:
        ok = False
        lines.append(f"✗ internal: 파일 없음 ({INTERNAL_LATEST})")

    return ok, "\n".join(lines)


def main(argv):
    only = argv[1] if len(argv) > 1 else None
    ok, report = run(only)
    print(report)
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
