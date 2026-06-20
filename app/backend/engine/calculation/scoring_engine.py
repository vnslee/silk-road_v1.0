#!/usr/bin/env python3
"""오토파이낸스 진출 추천 스코어링 엔진 v2 (활성 항목 기반)
- 활성 항목 목록(active_items)을 받아 그것만으로 계산
- 기본 mvp, 화면에서 ext 항목 추가 시 재계산
- 가중치는 활성 항목들 합=1로 재정규화
- 인사이트 2층: insight_detail(country 단독) + insight_compare(스코어링)
"""
import json, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
# engine/calculation → app/backend  (storage가 위치한 backend 루트)
BACKEND = os.path.dirname(os.path.dirname(BASE))
STORAGE = os.path.join(BACKEND, "storage")
DATA = os.path.join(STORAGE, "data")
REPORT = os.path.join(STORAGE, "report")

def load(p):
    with open(p, encoding="utf-8") as f: return json.load(f)
def items_map(c): return {it["item"]: it for it in c["items"]}

import glob
def load_country(code):
    """국가 코드로 latest country 로드"""
    return load(f"{DATA}/research/country/{code}/{code}_latest.json")
def find_baseline(region):
    """해당 region에서 is_baseline:true 인 국가의 latest 로드. 없으면 None"""
    for latest in glob.glob(f"{DATA}/research/country/*/*_latest.json"):
        c=load(latest)
        if c.get("region")==region and c.get("is_baseline"):
            return c
    return None

# 정규화 범위. 금액 항목(시장규모)은 base 통화(EUR_M) 기준 — 항목별 단위 통일 후 적용.
NORM_RANGE = {
    "오토금융/리스 시장규모": (0, 70000), "오토금융 성장률(CAGR)": (0, 12),
    "금융 이용률(신차)": (0, 100), "평균 금리/APR": (0, 15),
    "캡티브 강도(점유율)": (0, 100), "1위사 점유율": (0, 50),
    "신차 판매대수": (0, 3000000), "금융 이용률(중고차)": (0, 100),
    "구매 패턴(할부·리스 비중)": (0, 100), "법인세율": (0, 30),
    "이자소득 원천징수(비거주자)": (0, 30), "배당 원천징수(비거주자)": (0, 30),
    "법적 회수 소요기간": (0, 365),
}

# 통화 정규화 — internal.fx에서 주입. 비어 있으면 환산 생략(하위호환).
FX_BASE = "EUR"
FX_RATES = {}
def set_fx(internal):
    """internal.fx로 FX 테이블 주입 (CCY→base 환산율)."""
    global FX_BASE, FX_RATES
    fx = (internal or {}).get("fx") or {}
    FX_BASE = fx.get("base", "EUR")
    FX_RATES = fx.get("rates", {}) or {}
def to_base_money(value, unit):
    """'<CCY>_M' 단위 금액을 base 통화(예: EUR_M)로 환산. 환산 불가면 원값 반환."""
    if isinstance(value, (int, float)) and isinstance(unit, str) and unit.endswith("_M"):
        ccy = unit[:-2]
        if ccy in FX_RATES:
            return value * FX_RATES[ccy]
    return value
def minmax(v, lo, hi, invert=False):
    if hi==lo: return 50.0
    n=max(0,min(100,(v-lo)/(hi-lo)*100))
    return round(100-n if invert else n,1)
def grade_norm(v, invert=False):
    n=max(0,min(100,(v-1)/4*100))
    return round(100-n if invert else n,1)
def normalize(item):
    v=item["value"]; name=item["item"]; inv=(item.get("direction")=="down")
    v=to_base_money(v, item.get("unit",""))   # <CCY>_M 금액은 base 통화로 통일 후 정규화
    if name in NORM_RANGE:
        lo,hi=NORM_RANGE[name]; return minmax(v,lo,hi,inv)
    if isinstance(v,(int,float)): return grade_norm(v,inv)
    return 50.0

def tier_conf(tiers):
    if not tiers: return "하"
    coef={1:1.0,2:0.8,3:0.6,4:0.4}
    a=sum(coef.get(t,0.4) for t in tiers)/len(tiers)
    return "상" if a>=0.85 else ("중" if a>=0.65 else "하")
def renorm(weights):
    s=sum(weights.values())
    return {k:(v/s if s else 0) for k,v in weights.items()} if s else weights

def resolve_active(country, internal, extra_items=None):
    rules=internal.get("scoring_rules",{"default_active":["mvp"]})
    default_tg=set(rules.get("default_active",["mvp"]))
    excluded=set(rules.get("always_excluded",[]))
    extra=set(extra_items or [])
    active=[]
    for it in country["items"]:
        tg=it.get("tier_group","mvp")
        if tg in excluded: continue
        if tg in default_tg or it["item"] in extra:
            active.append(it)
    return active

def make_flag(match, weight):
    if weight>=0.25 and match<60: return "cost_driver"
    if match>=90: return "strength"
    if match<50: return "gap"
    return None
def it_compare_insight(item, match, weight, bname, flag, tier):
    if flag=="cost_driver": s=f"가중치 비중 큰데 {bname} 대비 정합도 {match}% — 유사도를 끌어내림. 코어 재구축이 비용 핵심."
    elif flag=="strength": s=f"{bname} 대비 정합도 {match}%로 거의 동일 — 재사용률 높음."
    elif flag=="gap": s=f"{bname} 대비 정합도 {match}%로 격차 큼 — 추가 개발/현지화 필요."
    elif match>=80: s=f"{bname} 대비 정합도 {match}% — 기존 자산 재사용 높음."
    elif match>=50: s=f"{bname} 대비 정합도 {match}% — 부분 재사용, 일부 추가개발."
    else: s=f"{bname} 대비 정합도 {match}% — 신규 구축에 가까움."
    if item=="솔루션 벤더": s+=" 베이스라인 벤더 현지 존재 시 이식 토대 확보."
    if item=="라이선스 체제(세그먼트별)": s+=" EU 규제 공통 기반이라 컴플라이언스 로직 재사용 가능."
    return s+(" (저신뢰 — 실사 권장)" if tier and tier>=3 else "")
def biz_compare_insight(axis, norm, tier):
    if axis=="attractiveness":
        s=f"정규화 {norm} — "+("매력도 강점." if norm>=80 else ("평이한 기여." if norm>=40 else "기여 낮음."))
    else:
        s=f"정규화 {norm} — "+("진입난이도 가중 요인." if norm>=60 else "난이도 부담 낮음.")
    return s+(" (tier"+str(tier)+" 추정 — 실사 필요)" if tier and tier>=3 else "")

def score_business(country, internal, active):
    wall=internal["weights"]["business"]
    attr=[it for it in active if it["category"]=="business" and it["role"]=="score" and it.get("axis")=="attractiveness"]
    diff=[it for it in active if it["category"]=="business" and it["role"]=="score" and it.get("axis")=="difficulty"]
    aw=renorm({it["item"]:wall.get(it["item"],0) for it in attr})
    dw=renorm({it["item"]:wall.get(it["item"],0) for it in diff})
    contrib=[]; A=0.0; D=0.0; tiers=[]
    for it in attr:
        nm=normalize(it); w=aw[it["item"]]; wd=round(nm*w,1); A+=wd; tiers.append(it["tier"])
        contrib.append({"axis":"attractiveness","item":it["item"],"raw":it["value"],"normalized":nm,
                        "weight":round(w,3),"weighted":wd,"tier":it["tier"],
                        "insight_detail":it.get("insight",""),
                        "insight_compare":biz_compare_insight("attractiveness",nm,it["tier"])})
    for it in diff:
        nm=normalize(it); w=dw[it["item"]]; wd=round(nm*w,1); D+=wd; tiers.append(it["tier"])
        contrib.append({"axis":"difficulty","item":it["item"],"raw":it["value"],"normalized":nm,
                        "weight":round(w,3),"weighted":wd,"tier":it["tier"],
                        "insight_detail":it.get("insight",""),
                        "insight_compare":biz_compare_insight("difficulty",nm,it["tier"])})
    return round(A,1), round(D,1), contrib, tiers

def match_numeric(a,b): return round(100-abs(a-b)/4*100,1)
def match_solution(cand, base):
    v=str(cand.get("value","")); bv=str(base.get("value",""))
    bvendors=re.findall(r"[A-Z][A-Za-z]{3,}",bv)
    present=any(x in v for x in bvendors)
    if present and "혼재" not in v: return 100.0
    if present: return 78.0
    if "패키지" in v: return 50.0
    if "자체" in v: return 30.0
    return 50.0
def score_it(country, baseline, internal, active):
    wall=internal["weights"]["it"]; bm=items_map(baseline); bname=baseline["country_ko"]
    its=[it for it in active if it["role"]=="score" and it.get("axis")=="similarity"]
    w=renorm({it["item"]:wall.get(it["item"],0) for it in its})
    contrib=[]; S=0.0; tiers=[]
    for it in its:
        name=it["item"]; b=bm.get(name); wi=w[name]
        if name=="솔루션 벤더":
            m=match_solution(it,bm["솔루션 벤더"]); detail={"cand":str(it.get("value"))[:24],"baseline":str(bm["솔루션 벤더"].get("value"))[:24]}
        elif name=="라이선스 체제(세그먼트별)":
            m=70.0; detail={"note":"EU 규제 공통, 세그먼트 체제 상이"}
        elif b and isinstance(it["value"],(int,float)) and isinstance(b["value"],(int,float)):
            m=match_numeric(it["value"],b["value"]); detail={"cand":it["value"],"baseline":b["value"]}
        else:
            m=60.0; detail={"note":"베이스라인 비교 불가, 기본값"}
        wd=round(m*wi,1); S+=wd; tiers.append(it["tier"]); flag=make_flag(m,wi)
        contrib.append({"item":name,"match":m,"weight":round(wi,3),"weighted":wd,"tier":it["tier"],"flag":flag,
                        "insight_detail":it.get("insight",""),
                        "insight_compare":it_compare_insight(name,m,wi,bname,flag,it["tier"]),**detail})
    return round(S,1), contrib, tiers

def discount_for(sim, brackets):
    for b in brackets:
        if b["min"]<=sim<=b["max"]: return b["discount"]
    return 0.0
def quadrant(a,d):
    return ("즉시 진출" if a>=50 and d<50 else "선별 진출" if a>=50 else "기회 탐색" if d<50 else "JV/제휴 필요")
def eval_gates(country, active):
    checks=[]; passed=True
    for g in [it for it in active if it["role"]=="gate"]:
        r=g.get("gate_result","PASS")
        if r=="FAIL" and g.get("tier",4)>=3: r="FLAG"
        if r=="FAIL": passed=False
        checks.append({"item":g["item"],"scope":g.get("gate_scope"),"result":r,"tier":g.get("tier")})
    return passed, checks
def due_diligence(country, active, th=3):
    return [{"code":country["code"],"item":it["item"],"tier":it["tier"],"action":"1차 출처·실사 확인 필요"}
            for it in active if it.get("tier",1)>=th]

def run(target_code, extra_items=None):
    internal=load(f"{DATA}/internal/internal_latest.json")
    set_fx(internal)
    cpath=f"{DATA}/research/country/{target_code}/{target_code}_latest.json"
    if not os.path.exists(cpath):
        raise SystemExit(f"[안내] {target_code} country 데이터 없음 — 먼저 조사(리서치)가 필요합니다.")
    target=load_country(target_code)
    region=target.get("region")
    baseline=find_baseline(region)
    if baseline is None:
        raise SystemExit(f"[오류] region '{region}'의 베이스라인 국가(is_baseline:true) 없음")
    if baseline["code"]==target_code:
        raise SystemExit(f"[안내] {target_code}는 베이스라인 자신 — 비교 대상 아님")
    bcode=baseline["code"]
    asset=internal["country_assets"].get(bcode)
    if asset is None:
        raise SystemExit(f"[오류] internal.country_assets에 베이스라인 {bcode} 자산 없음")

    active=resolve_active(target, internal, extra_items)
    A,D,bc,bt=score_business(target, internal, active)
    S,ic,it_t=score_it(target, baseline, internal, active)
    disc=discount_for(S, internal["similarity_brackets"])
    build=round(asset["build_cost"]*(1-disc),1)
    months=round(asset["build_months"]*(1-disc*0.7),1)
    maint=round(build*internal["maintenance_rate"],1)
    pass_,checks=eval_gates(target, active)
    ts=target.get("fetched_at","").replace(":","").replace("-","").replace("+0900","")[:13] or "ver"
    rpt={
      "report_id":f"rpt_{target_code}_2026-06-18T1500","created_at":"2026-06-18T15:00:00+09:00",
      "target":target_code,"region":region,"baseline":bcode,
      "active_items":[it["item"] for it in active],
      "active_groups":sorted(set(it.get("tier_group") for it in active)),
      "based_on":{"country_versions":{target_code:f"{target_code}_latest"},
                  "baseline_versions":{region:f"{bcode}_latest"},
                  "internal_version":internal.get("version"),"schema_version":"1.0"},
      "gate_result":{target_code:{"passed":pass_,"checks":checks}},"gate_failed":[],
      "views":{
        "business":{"ranking":[{"code":target_code,"rank":1,"score":A,"difficulty":D,"quadrant":quadrant(A,D),
                    "contributions":bc,"confidence":tier_conf(bt)}]},
        "it":{"baseline":bcode,"ranking":[{"code":target_code,"rank":1,"similarity":S,
                    "cost":{"baseline":bcode,"baseline_build":asset["build_cost"],"discount":disc,
                            "build":build,"months":months,"maintenance_yr":maint,"unit":"GBP_M(데모)"},
                    "contributions":ic,"confidence":tier_conf(it_t)}]},
        "integrated":{"note":"합성점수 없음 — 2축 매트릭스 + 사분면",
                    "ranking":[{"code":target_code,"rank":1,"attractiveness":A,"difficulty":D,"similarity":S,
                    "bubble_cost":build,"quadrant":quadrant(A,D),
                    "verdict":f"게이트 통과·사분면 '{quadrant(A,D)}'. {baseline['country_ko']} 대비 유사도 {S}로 {int(disc*100)}% 절감."}]}
      },
      "due_diligence":due_diligence(target, active)
    }
    outdir=f"{REPORT}/country/{target_code}/data"
    os.makedirs(outdir, exist_ok=True)
    out=f"{outdir}/{target_code}_rpt_2026-06-18T1500.json"
    json.dump(rpt,open(out,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    import shutil; shutil.copy(out,f"{outdir}/{target_code}_rpt_latest.json")
    print(f"대상 {target_code}({region}) ↔ 베이스라인 {bcode} | 활성 {rpt['active_groups']} {len(active)}개")
    print(f"매력도 {A} 난이도 {D} ({quadrant(A,D)}) | 유사도 {S} 감축 {int(disc*100)}% 구축비 {build}")
    return rpt

if __name__=="__main__":
    args=sys.argv[1:]
    if not args:
        raise SystemExit("사용법: python3 scoring_engine.py <국가코드> [추가항목...]\n예: python3 scoring_engine.py PL \"국외이전 제한\"")
    code=args[0]; extra=args[1:] or None
    if extra: print(f"[추가 항목: {extra}]")
    run(code, extra)
