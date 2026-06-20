#!/usr/bin/env python3
"""권역(region) 퀵윈 스코어링 엔진
- 화면에서 "유럽(EU)" 등 권역을 선택하면 호출.
- 해당 region의 베이스라인국(is_baseline:true)을 기준으로,
  권역 내 나머지 국가들을 일괄 스코어링(매력도·난이도·유사도) → 퀵윈 후보 산출.
- 단일국 엔진(calculation/scoring_engine)의 검증된 스코어링 로직을 그대로 재사용.
- 렌더링은 rendering/region_report_rendering_engine 에 위임.
- 출력: report/region/<REGION>/<REGION>_rpt_<TS>.json (+ _latest 포인터)

퀵윈(quick_win) 정의:
  "적은 노력으로 빠르게 성과" = 게이트 통과 + 베이스라인 재사용률(유사도) 높아
  구축비·기간 절감 + 매력도 양호 + 진입난이도 과하지 않음.
  quick_win_score = w_sim*유사도 + w_attr*매력도 + w_ease*(100-난이도)
"""
import json, os, sys, glob, shutil

# 형제 엔진 폴더(calculation, rendering)를 모듈 경로에 추가
_ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("calculation", "rendering"):
    sys.path.insert(0, os.path.join(_ENGINE_ROOT, _sub))

import scoring_engine as se
import region_report_rendering_engine as rre

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
DATA = os.path.join(REPO, "data")
REPORT = os.path.join(REPO, "report")
# 단일국 엔진의 데이터 경로를 현재 레포 레이아웃(레포루트/data)으로 정렬
se.DATA = DATA

TS = "2026-06-19T12:00:00+09:00"
TS_FILE = "2026-06-19T1200"


def list_region_countries(region):
    """region 일치 + 베이스라인 아님 인 국가 latest 목록 (code 정렬)."""
    out = []
    for p in sorted(glob.glob(f"{DATA}/country/*/*_latest.json")):
        c = se.load(p)
        if c.get("region") == region and not c.get("is_baseline"):
            out.append(c)
    return out


def quick_win_eval(qrules, A, D, S, gate_passed, has_flag):
    w = qrules["weights"]; th = qrules["thresholds"]
    ease = round(100 - D, 1)
    qscore = round(w["similarity"] * S + w["attractiveness"] * A + w["ease"] * ease, 1)
    is_qw = (gate_passed
             and S >= th["min_similarity"]
             and A >= th["min_attractiveness"]
             and D <= th["max_difficulty"]
             and qscore >= th["quick_win_score"])
    reasons, blockers = [], []
    if gate_passed: reasons.append("필수 게이트 전부 통과 — 구조적 진입 장벽 없음")
    else: blockers.append("필수 게이트 FAIL — 진입 불가 항목 존재")
    if S >= 70: reasons.append(f"유사도 {S} → 베이스라인 재사용률 높아 구축비·기간 절감폭 큼")
    elif S >= th["min_similarity"]: reasons.append(f"유사도 {S} → 부분 재사용 가능")
    else: blockers.append(f"유사도 {S} 낮음 → IT 재구축 부담")
    if A >= 50: reasons.append(f"매력도 {A} 양호")
    elif A < th["min_attractiveness"]: blockers.append(f"매력도 {A} 낮음 → 시장 매력 제한")
    if D < 50: reasons.append(f"진입난이도 {D} 낮음")
    elif D > th["max_difficulty"]: blockers.append(f"진입난이도 {D} 높음(캡티브/집중도)")
    if has_flag: blockers.append("저신뢰(FLAG) 게이트 존재 → 실사로 확정 필요")
    return is_qw, qscore, ease, reasons, blockers


def run(region="EU", extra_items=None):
    internal = se.load(f"{DATA}/internal/internal_latest.json")
    se.set_fx(internal)
    baseline = se.find_baseline(region)
    if baseline is None:
        raise SystemExit(f"[오류] region '{region}'의 베이스라인 국가(is_baseline:true) 없음")
    bcode = baseline["code"]
    asset = internal["country_assets"].get(bcode)
    if asset is None:
        raise SystemExit(f"[오류] internal.country_assets에 베이스라인 {bcode} 자산 없음")

    candidates = list_region_countries(region)
    if not candidates:
        raise SystemExit(f"[안내] region '{region}'에 비교 대상 국가 없음 — 먼저 조사 필요")

    qrules = internal["quick_win_rules"]
    rows, gate_failed, dd_summary, cversions = [], [], [], {}

    for c in candidates:
        code = c["code"]
        active = se.resolve_active(c, internal, extra_items)
        A, D, bc, bt = se.score_business(c, internal, active)
        S, ic, itt = se.score_it(c, baseline, internal, active)
        disc = se.discount_for(S, internal["similarity_brackets"])
        build = round(asset["build_cost"] * (1 - disc), 1)
        months = round(asset["build_months"] * (1 - disc * 0.7), 1)
        maint = round(build * internal["maintenance_rate"], 1)
        passed, checks = se.eval_gates(c, active)
        has_flag = any(ck["result"] == "FLAG" for ck in checks)
        if not passed:
            gate_failed.append({"code": code, "checks": [ck for ck in checks if ck["result"] == "FAIL"]})
        dd = se.due_diligence(c, active)
        dd_summary.append({"code": code, "count": len(dd)})
        cversions[code] = f"{code}_latest"

        is_qw, qscore, ease, reasons, blockers = quick_win_eval(qrules, A, D, S, passed, has_flag)
        quad = se.quadrant(A, D)
        rows.append({
            "code": code, "country_ko": c.get("country_ko"),
            "quick_win": is_qw, "quick_win_score": qscore,
            "attractiveness": A, "difficulty": D, "ease": ease, "similarity": S,
            "quadrant": quad,
            "gate_passed": passed, "gate_flag": has_flag,
            "confidence": se.tier_conf(bt + itt),
            "cost": {"baseline": bcode, "baseline_build": asset["build_cost"],
                     "discount": disc, "build": build, "months": months,
                     "maintenance_yr": maint, "unit": "GBP_M(데모)"},
            "quick_win_reasons": reasons, "blockers": blockers,
            "verdict": (f"퀵윈 후보 — 사분면 '{quad}', {baseline['country_ko']} 대비 유사도 {S}로 "
                        f"{int(disc*100)}% 절감(구축 {build}, {months}개월)."
                        if is_qw else
                        f"퀵윈 제외 — {(blockers[0] if blockers else '점수 임계 미달')}. "
                        f"사분면 '{quad}', 유사도 {S}."),
            "business_contributions": bc, "it_contributions": ic,
            "gate_checks": checks, "due_diligence": dd,
            # 국가 원본 전체 임베드 — 화면이 권역 보고서 하나로 국가 상세까지 렌더
            "country_meta": {k: c.get(k) for k in (
                "country", "country_ko", "code", "region", "is_baseline", "currency",
                "schema_version", "data_year", "fetched_at", "fetched_by", "overall_insight")},
            "items": c["items"],
        })

    # 퀵윈 우선, 그다음 퀵윈점수 내림차순 정렬 → rank 부여
    rows.sort(key=lambda r: (r["quick_win"], r["quick_win_score"]), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    region_insight = _region_insight(region, baseline, rows)
    rpt = {
        "report_id": f"{region}_rpt_{TS_FILE}",
        "report_type": "region_quickwin",
        "created_at": TS,
        "region": region,
        "baseline": bcode,
        "candidate_count": len(rows),
        "active_groups": sorted({tg for c in candidates for tg in
                                 {it.get("tier_group") for it in se.resolve_active(c, internal, extra_items)}}),
        "based_on": {
            "country_versions": cversions,
            "baseline_versions": {region: f"{bcode}_latest"},
            "internal_version": internal.get("version"),
            "schema_version": "1.0",
        },
        "quick_win_rules": qrules,
        "region_insight": region_insight,
        "quick_wins": [r["code"] for r in rows if r["quick_win"]],
        "ranking": [{k: r[k] for k in (
            "code", "country_ko", "rank", "quick_win", "quick_win_score",
            "attractiveness", "difficulty", "ease", "similarity", "quadrant",
            "gate_passed", "gate_flag", "confidence", "cost",
            "quick_win_reasons", "blockers", "verdict",
            "country_meta", "items",
            "business_contributions", "it_contributions", "gate_checks", "due_diligence")}
            for r in rows],
        "gate_failed": gate_failed,
        "due_diligence_summary": dd_summary,
    }

    outdir = os.path.join(REPORT, "region", region)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{region}_rpt_{TS_FILE}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rpt, f, ensure_ascii=False, indent=2)
    shutil.copy(out, os.path.join(outdir, f"{region}_rpt_latest.json"))
    update_index(outdir, region, rpt, f"{region}_rpt_{TS_FILE}.json")

    qw = rpt["quick_wins"]
    print(f"[{region}] 베이스라인 {bcode} | 후보 {len(rows)}개 | 퀵윈 {len(qw)}개: {qw}")
    for r in rows:
        mark = "★퀵윈" if r["quick_win"] else "  "
        print(f"  {r['rank']}. {r['code']} {mark} QW={r['quick_win_score']} "
              f"매력 {r['attractiveness']} 난이 {r['difficulty']} 유사 {r['similarity']} "
              f"({r['quadrant']}) 구축 {r['cost']['build']}")
    print(f"→ {out}")
    rre.render(region)
    return rpt


def update_index(outdir, region, rpt, filename):
    """폴더의 index.json(버전 매니페스트) 갱신 — 화면 드롭다운 소스.
    같은 report_id면 덮어쓰고, created_at 내림차순 정렬, latest 포인터 갱신."""
    idx_path = os.path.join(outdir, "index.json")
    idx = {"region": region, "latest": None, "versions": []}
    if os.path.exists(idx_path):
        try:
            idx = se.load(idx_path)
        except Exception:
            pass
    entry = {
        "report_id": rpt["report_id"],
        "created_at": rpt["created_at"],
        "file": filename,
        "report_type": rpt["report_type"],
        "based_on": {
            "internal_version": rpt["based_on"]["internal_version"],
            "country_versions": rpt["based_on"]["country_versions"],
        },
        "summary": {
            "candidate_count": rpt["candidate_count"],
            "quick_wins": rpt["quick_wins"],
            "ranking": [{"code": r["code"], "rank": r["rank"],
                         "quick_win": r["quick_win"], "quick_win_score": r["quick_win_score"]}
                        for r in rpt["ranking"]],
        },
    }
    versions = [v for v in idx.get("versions", []) if v.get("report_id") != entry["report_id"]]
    versions.append(entry)
    versions.sort(key=lambda v: v["created_at"], reverse=True)
    idx["region"] = region
    idx["versions"] = versions
    idx["latest"] = versions[0]["report_id"] if versions else None
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)


def _region_insight(region, baseline, rows):
    qw = [r for r in rows if r["quick_win"]]
    bn = baseline["country_ko"]
    if qw:
        names = ", ".join(f"{r['country_ko']}({r['code']})" for r in qw)
        top = qw[0]
        return (f"{region} 권역 {len(rows)}개 후보 중 퀵윈 {len(qw)}개: {names}. "
                f"{bn} 베이스라인 재사용률(유사도) 기반으로 구축비·기간 절감폭이 커 우선 진입 적합. "
                f"최우선은 {top['country_ko']}({top['code']}) — 유사도 {top['similarity']}, "
                f"구축비 {top['cost']['build']}({int(top['cost']['discount']*100)}% 절감), 매력도 {top['attractiveness']}.")
    return (f"{region} 권역 {len(rows)}개 후보 중 임계 충족 퀵윈 없음. "
            f"유사도·매력도·게이트 보강 후 재평가 권장. (기준 베이스라인: {bn})")


if __name__ == "__main__":
    args = sys.argv[1:]
    region = args[0] if args else "EU"
    extra = args[1:] or None
    if extra:
        print(f"[추가 항목: {extra}]")
    run(region, extra)
