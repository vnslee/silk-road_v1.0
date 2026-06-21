#!/usr/bin/env python3
"""
Storage 접근 서비스 (U8).

API 라우터가 파일시스템 storage/ (A1) 를 읽을 때 쓰는 공용 로더.
경로 해석·목록 스캔·로드를 한 곳에 모은다. 계산·생성은 하지 않음(읽기 전용).

진출 상태(web_design_spec M1 지도): internal.country_assets 보유 여부로 판정
  (자산 있으면 진출국, 없으면 진출예정국 — 스키마 §4 자산 식별 원칙).
"""

import json
from pathlib import Path

# services/ → backend/ → storage/
STORAGE = Path(__file__).resolve().parent.parent / "storage"
COUNTRY_DIR = STORAGE / "data" / "research" / "country"
INTERNAL_LATEST = STORAGE / "data" / "internal" / "internal_latest.json"
REPORT_BASE = STORAGE / "report"


class NotFound(Exception):
    """리소스 없음 — 라우터가 404 로 변환."""


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── internal ──────────────────────────────────────────────────────────────
def load_internal():
    if not INTERNAL_LATEST.exists():
        raise NotFound("internal ruleset 없음")
    return _read_json(INTERNAL_LATEST)


def save_internal(data):
    """internal_latest.json 갱신(PS1 저장). latest 만 갱신(스냅샷은 사람이 관리)."""
    INTERNAL_LATEST.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return INTERNAL_LATEST


# ── country ─────────────────────────────────────────────────────────────--
def country_codes_with_data():
    """research 데이터(<CODE>_latest.json)가 존재하는 국가 코드 집합."""
    if not COUNTRY_DIR.exists():
        return set()
    return {d.name for d in COUNTRY_DIR.iterdir()
            if d.is_dir() and (d / f"{d.name}_latest.json").exists()}


def load_country(code):
    path = COUNTRY_DIR / code / f"{code}_latest.json"
    if not path.exists():
        raise NotFound(f"country '{code}' 데이터 없음")
    return _read_json(path)


def list_countries():
    """국가 목록 — research 보유국 + 권역 멤버(데이터 없어도 '예정')를 합친다.

    각 항목: code, country_ko/en(있으면), region, has_data, is_entered, is_baseline.
    is_entered = internal.country_assets 보유 여부(진출 상태, M1 지도용).
    """
    internal = load_internal()
    assets = internal.get("country_assets", {})
    regions = internal.get("regions", {})

    # 멤버 → 권역 역인덱스
    member_region = {}
    for rid, meta in regions.items():
        for m in meta.get("members", []):
            member_region.setdefault(m, rid)

    have = country_codes_with_data()
    codes = set(have) | set(member_region) | set(assets)

    out = []
    for code in sorted(codes):
        entry = {
            "code": code,
            "region": member_region.get(code),
            "has_data": code in have,
            "is_entered": code in assets,   # 진출국 여부 (채운 점)
            "is_baseline": False,
            "country_ko": None, "country_en": None,
        }
        if code in have:
            d = load_country(code)
            entry["country_ko"] = d.get("country_ko")
            entry["country_en"] = d.get("country")
            entry["is_baseline"] = bool(d.get("is_baseline"))
            entry["region"] = d.get("region", entry["region"])
        out.append(entry)
    return out


# ── region ──────────────────────────────────────────────────────────────--
def list_regions():
    """권역 목록 — internal.regions 카탈로그 + 멤버 보유 현황."""
    internal = load_internal()
    have = country_codes_with_data()
    out = []
    for rid, meta in internal.get("regions", {}).items():
        members = meta.get("members", [])
        out.append({
            "region": rid,
            "name_ko": meta.get("name_ko"),
            "name_en": meta.get("name_en"),
            "baseline": meta.get("baseline"),
            "members": members,
            "members_with_data": [m for m in members if m in have],
        })
    return out


def get_region(region):
    for r in list_regions():
        if r["region"] == region:
            return r
    raise NotFound(f"region '{region}' 없음")


# ── reports ─────────────────────────────────────────────────────────────--
def _report_dir(kind, code):
    return REPORT_BASE / kind / code


def list_reports(kind, code):
    """보고서 목록. 신구조(<code>/<RPT_ID>/data/) + 구버전(<code>/data/) 모두 스캔.

    각 항목: report_id, created_at(있으면), has_html, path(상대).
    """
    base = _report_dir(kind, code)
    if not base.exists():
        return []
    out = []
    # 신구조: <code>/<report_id>/data/<report_id>.json
    for sub in base.iterdir():
        if not sub.is_dir():
            continue
        if sub.name == "data" or sub.name == "html":
            continue  # 구버전 폴더는 아래에서 별도 처리
        data_dir = sub / "data"
        if data_dir.exists():
            for jf in data_dir.glob("*.json"):
                out.append(_report_entry(jf, sub / "html"))
    # 구버전: <code>/data/*.json
    legacy_data = base / "data"
    if legacy_data.exists():
        for jf in legacy_data.glob("*.json"):
            if jf.name.endswith("_latest.json"):
                continue
            out.append(_report_entry(jf, base / "html", legacy=True))
    # report_id 기준 정렬(최신 우선은 호출부에서)
    out.sort(key=lambda r: r["report_id"])
    return out


def _report_entry(json_path, html_dir, legacy=False):
    try:
        d = _read_json(json_path)
        rid = d.get("report_id", json_path.stem)
        created = d.get("created_at") or d.get("generated_at")
    except (json.JSONDecodeError, OSError):
        rid, created = json_path.stem, None
    html_path = html_dir / (json_path.stem + ".html")
    return {
        "report_id": rid,
        "created_at": created,
        "has_html": html_path.exists(),
        "legacy": legacy,
        "json_name": json_path.name,
    }


def _find_report_json(kind, code, report_id):
    """report_id 로 JSON 파일 경로 찾기(신구조 우선, 구버전 폴백)."""
    base = _report_dir(kind, code)
    # 신구조
    cand = base / report_id / "data" / f"{report_id}.json"
    if cand.exists():
        return cand
    # 신구조이나 파일명이 다른 경우
    new_data = base / report_id / "data"
    if new_data.exists():
        js = list(new_data.glob("*.json"))
        if js:
            return js[0]
    # 구버전: data/ 에서 report_id 매칭
    legacy = base / "data"
    if legacy.exists():
        for jf in legacy.glob("*.json"):
            try:
                if _read_json(jf).get("report_id") == report_id:
                    return jf
            except (json.JSONDecodeError, OSError):
                continue
            if jf.stem == report_id:
                return jf
    raise NotFound(f"report '{report_id}' ({kind}/{code}) 없음")


def load_report(kind, code, report_id):
    return _read_json(_find_report_json(kind, code, report_id))


def report_html_path(kind, code, report_id):
    """보고서 HTML 파일 경로(U5 산출물). 없으면 NotFound."""
    json_path = _find_report_json(kind, code, report_id)
    html_path = json_path.parent.parent / "html" / (json_path.stem + ".html")
    if not html_path.exists():
        raise NotFound(f"report '{report_id}' HTML 없음 (렌더링 필요)")
    return html_path
