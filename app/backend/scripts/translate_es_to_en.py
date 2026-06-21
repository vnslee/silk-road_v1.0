#!/usr/bin/env python3
"""
ES_latest.json에 영문 번역(*_en) 필드를 일괄 추가.

대상 필드 (원본 한글이 있는 경우에만 _en 추가):
- 최상위: overall_insight
- 각 item: value(str), insight, source
- "외부 이슈 스캔" 항목의 value 리스트 안 각 뉴스: headline, so_what

번역 사전은 본 스크립트 안에 직접 박혀 있으며, 매칭 안 되는 항목은
간단한 fallback(원본 유지) 처리. 사전 갱신은 이 스크립트만 고치면 됨.

실행:
    cd app/backend
    python3 scripts/translate_es_to_en.py
"""

import json
import sys
from pathlib import Path

ES_PATH = Path("storage/data/research/country/ES/ES_latest.json")

OVERALL_EN = (
    "Spain ranks among the EU's top-5 auto markets. New-car (turismos) registrations "
    "reached 1,148,650 units in 2025 (+12.9%, ANFAC), with renting (operating lease) "
    "accounting for 25.6% of registrations (281,593 units, AER) as corporate and fleet "
    "demand drove growth. Cost/difficulty drivers are clear — consumer auto finance "
    "faces a dual regulatory burden: EFC (specialized credit institution) licensing "
    "(minimum capital €5M, fully cash-paid, RD 309/2020, supervised by Banco de España) "
    "and the upcoming 2026 Consumer Credit Act (temporary 22% APR cap plus a permanent "
    "mechanism based on BdE quarterly average rates with amount-tiered margins). "
    "B2B leasing/renting faces lighter licensing. Business attractiveness "
    "(EU #5 market size, fast-growing renting) is strong, while the bank-led (not captive) "
    "structure — Santander Consumer, CA Auto Bank, Cetelem account for ~60% of passenger-car "
    "finance — leaves room for independent entrants. IT similarity is high — EU GDPR, SEPA, "
    "Bizum, and mature credit bureau infrastructure (CIRBE/ASNEF/Experian) deliver strong "
    "NetSol baseline reuse. The attractiveness↔IT mismatch is in repossession — leasing/renting "
    "is easy thanks to ownership, but consumer-loan collateral recovery takes 6-12 months due to "
    "court backlogs, so product mix drives recovery risk. The dark horse is EV share in the "
    "renting market (51.3% of new registrations), making residual-value risk the key lever "
    "for lease P&L. A staged strategy — renting/fleet first, then consumer finance under EFC "
    "licensing — is effective."
)

# 항목명 → {value_en?, insight_en, source_en}
ITEM_TRANSLATIONS = {
    "오토금융/리스 시장규모": {
        "insight": "Passenger-car finance market exceeds €15B/yr + renting revenue €9.5B (passing 1M vehicles). ASNEF discontinued auto-only statistics, so a single official figure is unavailable — estimation needed. 2025 ECB easing creates a favorable rate environment.",
        "source": "El Economista 2024 (passenger-car finance >€15,000M/yr) + AER Informe Anual 2026 (renting revenue €9,512M, +8.44%); ASNEF stopped disclosing auto-only figures since 2018.",
    },
    "오토금융 성장률(CAGR)": {
        "insight": "Corporate/renting segments grow ~15% (high single-digit overall including retail). Above EU average.",
        "source": "6Wresearch / Mordor Intelligence (corporate/renting CAGR ~15%; high single-digit incl. retail).",
    },
    "금융 이용률(신차)": {
        "insight": "~60% of new-car purchases are financed (Cetelem: 48% each finance/cash; dealer-finance channel 57%) + 25.7% renting. High penetration → share competition; captive and renting shares rising.",
        "source": "OCU/El Economista (~60% of new cars financed; promo segment 70%+), Observatorio Cetelem 2025 (finance vs cash each 48%), AER (renting 25.7%).",
    },
    "금융 이용률(중고차)": {
        "insight": "Used-car formal-finance penetration of 42% — lower than new cars, leaving room for growth. Used and certified-used finance is a niche opportunity.",
        "source": "Mordor Intelligence (used-car formal-finance penetration ~42%).",
    },
    "평균 금리/APR": {
        "insight": "ECB deposit rate at 2.00% (end-2025, 4 cuts during the year); BdE consumer credit ~7% TEDR. Auto-loan APR is above this. The temporary 22% APR cap under the 2026 Consumer Credit Act leaves room, but quarterly cap monitoring is required.",
        "source": "Banco de España consumer credit statistics 2025 (TEDR ~7%, APR higher); ECB deposit rate 2.00% (end-2025).",
    },
    "신차 판매대수": {
        "insight": "+12.9% in 2025 to 1.149M units, comfortably above the 1M mark. Renting drives 25.6% of registrations (281,593 units), making fleet a key driver — EU top-5 scale anchors finance demand. Base unit for volume calculations.",
        "source": "ANFAC 2025 (turismos 1,148,650 units, +12.9%; private channel 539,642 +18.1%; renting 25.6%).",
    },
    "구매 패턴(할부·리스 비중)": {
        "insight": "Renting (operating lease) revenue €9.5B with 1M+ vehicles, 25.7% of new registrations (slightly down from 27.67% in 2024). Driven by corporate/fleet; EVs make up 51.3% of new renting — renting-first entry is effective.",
        "source": "AER Informe Anual 2026 (renting revenue €9,512M +8.44%; vehicles 1,013,507 first crossed 1M; new registrations 351,287 +4.5%; share 25.7%).",
    },
    "캡티브 강도(점유율)": {
        "insight": "Spain is bank-led, not captive-led — Santander Consumer, CA Auto Bank, Cetelem account for ~60% of passenger-car finance. OEM captives (VW FS, Toyota) are concentrated on their own brands, leaving relatively more room for independent entrants.",
        "source": "El Economista 2024 (Santander Consumer + CA Auto Bank + Cetelem ~60% of passenger-car finance); Mordor (banks ~46% in Europe).",
    },
    "금융사 점유율(Top 5)": {
        "insight": "Santander Consumer Finance is #1 with ~20% share (handling 18 OEMs; Stellantis will also route through SCF by 2026). Top-3 banks ~60% — for new entrants, focus on niches (EV, used, fleet).",
        "source": "El Economista 2024 / Santander (SCF #1, finances 18 OEMs; Oct 2025 merger announcement with Openbank).",
    },
    "법인세율": {
        "insight": "Standard corporate tax 25%. SMEs (INCN<€10M) drop from 24% in 2025 to 20% by 2029 (21% in 2028); micro-firms (INCN<€1M) 21/22% in 2025; new firms 15% for 2 years — eases early-stage tax burden.",
        "source": "Ley 7/2024 (2025 tax year onward): standard 25%, SME 24% (2025) → 20% (2029), micro 21/22% (2025), new firms 15%.",
    },
    "이자소득 원천징수": {
        "insight": "Non-resident interest WHT 19%; EU Interest & Royalties Directive allows exemption — favorable for HQ-funded structures.",
        "source": "PwC Spain WHT (EU Interest & Royalties Directive exemption available).",
    },
    "배당 원천징수": {
        "insight": "Dividend WHT 19%; EU Parent-Subsidiary Directive (5% stake, 1-yr holding) allows 0% exemption — efficient profit repatriation.",
        "source": "PwC Spain WHT (EU Parent-Subsidiary Directive 0% available).",
    },
    "외국인 지분 한도": {
        "value": "100% allowed (EU member; financial sector requires prior licensing).",
        "insight": "Foreigners may own 100% — no JV required. However, financial business requires sector-specific prior authorization (EFC etc.) as a separate gate.",
        "source": "Spanish Foreign Investment Law (RD 664/1999), EU free movement of capital.",
    },
    "외환·배당 송금 자유도": {
        "value": "No FX controls (19% non-resident WHT on dividends/interest; EU directive exemptions available).",
        "insight": "Free remittance. 19% WHT on dividends/interest can be reduced to 0% via EU directives/tax treaties — no obstacle to repatriation.",
        "source": "PwC Spain Withholding Taxes; EU Parent-Subsidiary & Interest-Royalty Directives.",
    },
    "데이터 현지화 의무": {
        "value": "EU GDPR directly applies; free intra-EU transfer; no forced localization.",
        "insight": "EU GDPR directly applicable, free intra-EU transfer. No forced localization — low constraint for HQ (EU) connected architecture.",
        "source": "EU GDPR; Spain LOPDGDD (Data Protection Act).",
    },
    "국가신용등급": {
        "value": "A (S&P, upgraded Sep 2025) / A3 (Moody's) / A- (Fitch), stable.",
        "insight": "Investment-grade, stable (S&P upgraded to A in Sep 2025). Low remittance/capital-recovery risk — killswitch passes.",
        "source": "S&P/Moody's/Fitch sovereign ratings (2025); S&P upgraded from A- to A in Sep 2025.",
    },
    "라이선스 취득 가능 여부(외국사)": {
        "value": "Consumer auto-finance requires EFC (specialized credit institution) license (obtainable); B2B leasing/renting relatively flexible.",
        "insight": "Consumer credit requires EFC licensing (Ministry of Economy authorization + Banco de España prior notice + min capital €5M). Renting (operating lease) entry is flexible — recommend renting first, then staged consumer-finance licensing.",
        "source": "Law 5/2015, Banco de España, Baker McKenzie.",
    },
    "라이선스 체제(세그먼트별)": {
        "value": "Consumer credit = EFC license (S.A. + min capital €5M + BdE supervision); B2B operating lease (renting) = lighter licensing.",
        "insight": "Regulatory intensity varies by segment. Consumer credit has heavy governance overhead (EFC licensing, capital, supervision); renting has relatively light compliance burden.",
        "source": "Law 5/2015, Banco de España, Baker McKenzie Spain.",
    },
    "금리 상한 규제": {
        "value": "Jan 7 2026: new Consumer Credit Act draft approved (public consultation until Jan 30 2026): temporary 22% APR cap; permanent mechanism is BdE quarterly average + amount-tiered margins (≤€1,500 +15pp; €1,500–6,000 +10pp; >€6,000 +8pp). High-cost loans capped at 4%/month.",
        "insight": "2026 introduces consumer-credit rate caps (temporary 22% APR; permanent BdE quarterly average + amount-tiered margins). Product APR logic must support dynamic caps and quarterly updates. Still pending — re-confirm effective date and margin details during due diligence. B2B remains relatively free.",
        "source": "La Moncloa/MINECO 2026.1.7 (implementing EU Directive 2023/2225), Ley de Usura (1908).",
    },
    "최저자본금": {
        "value": "EFC (specialized credit institution): €5,000,000; ordinary S.A./S.L. = corporate-law minimums.",
        "insight": "Consumer credit (EFC) min capital €5M (per RD 309/2020) — meaningful entry burden. Renting operating companies use ordinary corporate-law minimums — segment-specific capital strategies needed.",
        "source": "Art. 10.b RD 309/2020 (developing Ley 5/2015), BOE-A-2020-2613 (EFC min capital €5,000,000 fully cash-paid).",
    },
    "솔루션 벤더": {
        "value": "Global vendors (NETSOL / Sopra Banking / Sofico) + local SI mix.",
        "insight": "Shares EU vendor ecosystem (NETSOL, Sopra, Sofico) — high baseline reuse. Key driver of similarity score.",
        "source": "Market research (EU shared lease/auto-finance package ecosystem).",
    },
    "솔루션 유형": {
        "value": "Global packages + bank-built core, mixed.",
        "insight": "Large banks use proprietary core; captives and specialized lessors use global packages. Aligned with EU standard architecture.",
        "source": "Industry.",
    },
    "디지털 채널 성숙도": {
        "insight": "Bizum payments, e-signature, online dealer financing are widespread — digital contracting is mature. Full digital onboarding transition is in progress.",
        "source": "Industry (Bizum, online dealer financing, e-signature widespread).",
    },
    "신용정보(CB) 인프라": {
        "insight": "Banco de España CIRBE (mandatory reporting for €1,000+) + ASNEF + Experian — very mature infrastructure. UK CB integration patterns are reusable — top similarity.",
        "source": "CIRBE (Banco de España), ASNEF (Equifax), Experian/BADEXCUG.",
    },
    "결제·정산 인프라": {
        "insight": "SEPA Direct Debit + Bizum instant transfer are common. Payment/settlement infrastructure ranks among the EU's best — easy collection automation.",
        "source": "SEPA, Bizum, Iberpay.",
    },
    "디지털 딜러 성숙도": {
        "insight": "coches.net, online dealer finance, OEM direct-sales channels are well-developed. Digital retail is mature — embedded-finance integration opportunity.",
        "source": "Industry (coches.net, Wallapop, OEM online sales).",
    },
    "국외이전 제한": {
        "insight": "Free within EU; third countries require adequacy/SCC. No forced localization — high architectural freedom.",
        "source": "EU GDPR, LOPDGDD.",
    },
    "차량회수 절차 용이성": {
        "insight": "Leasing and renting are easy (financier holds ownership). Consumer-loan collateral recovery takes months via courts — segment-specific recovery modules needed.",
        "source": "Spanish Civil Procedure Law, Baker McKenzie Spain.",
    },
    "법적 회수 소요기간": {
        "insight": "Consumer-loan collateral recovery takes 6-12 months due to court backlogs; renting/leasing recovery is much faster — product mix drives recovery risk.",
        "source": "Spanish Civil Procedure Law, Banco de España (court enforcement statistics).",
    },
    "추심 규제": {
        "insight": "Strict consumer-protection rules. Outsourced collection allowed but requires consent and transparency.",
        "source": "LGDCU, Spanish DPA (AEPD), Bank of Spain.",
    },
    "충당금 규정": {
        "insight": "IFRS 9 expected-loss model applies; BdE Anejo 9 (Circular 4/2017) for prudential treatment.",
        "source": "IFRS 9, Banco de España Circular 4/2017 Annex 9.",
    },
    "연체 분류 기준": {
        "insight": "EBA NPE/forbearance definitions apply: 90+ days past due, refined by unlikely-to-pay criteria.",
        "source": "EBA NPE Guidelines, Banco de España Circular 4/2017.",
    },
    "의무보험 규제": {
        "value": "Compulsory third-party auto liability insurance, RDL 8/2004 / Ley 5/2024.",
        "insight": "Mandatory third-party motor liability insurance under RDL 8/2004 / Ley 5/2024.",
        "source": "RDL 8/2004 (LRCSCVM), Ley 5/2024.",
    },
    "신용생명보험 규제": {
        "value": "Tying prohibited; separate consent and alternative-offer obligations (Ley 5/2019 Consumer Credit Act).",
        "insight": "Tying credit life insurance is prohibited; lender must obtain separate consent and present alternatives (Ley 5/2019).",
        "source": "Ley 5/2019 (mortgage credit), Ley 16/2011 (consumer credit).",
    },
    "보험 끼워팔기 규제": {
        "value": "Forced bundling (tying) prohibited; bundling conditionally allowed (Insurance Distribution Law Ley 17/2023 / IDD).",
        "insight": "Mandatory bundling (tying) is prohibited; voluntary bundling allowed under conditions (Ley 17/2023 / EU IDD).",
        "source": "Ley 17/2023, EU IDD.",
    },
    "AI 신용평가 규제": {
        "value": "EU AI Act classifies credit scoring as high-risk; GDPR Art. 22 governs automated decision-making.",
        "insight": "Credit scoring qualifies as high-risk under EU AI Act; subject to GDPR Art. 22 automated-decision rules. Documentation and bias testing required.",
        "source": "EU AI Act, EU GDPR Art. 22.",
    },
    "EV 보급률": {
        "insight": "New BEV+PHEV registrations are at 12% of total (EU-laggard); renting EV share at 51.3% — gap between retail and fleet.",
        "source": "ANFAC EV registration data 2025.",
    },
    "EV·ICE 잔존가치 리스크": {
        "insight": "EV 3-yr residual values are ~10pp lower than comparable ICE vehicles, creating lease P&L risk. Conservative buyback structures needed.",
        "source": "Autovista 2025, ALD Automotive market reports.",
    },
    "해당국 정성 요약": {
        "value": "EU top-5 auto market (2025 new-car 1.149M units, +12.9%). Bank-led consumer finance (Santander Consumer, CA Auto Bank, Cetelem ~60%) coexists with OEM captives; renting (operating lease) grows fast (25.6% share; EVs 51%). Consumer credit faces EFC licensing (€5M capital) and the 2026 rate-cap law; B2B leasing/renting is more flexible. EU GDPR / SEPA / Bizum / mature CB make IT similarity high. Repossession is the key mismatch — easy for leases (ownership), 6-12 months for consumer-loan collateral. Renting/fleet first, then staged consumer finance via EFC licensing is the recommended strategy.",
        "insight": "Spain's appeal centers on EU-5 scale and fast-growing renting; key risks are EFC licensing burden and 2026 rate caps. Recommend entering renting/fleet first; expand into consumer credit after EFC licensing.",
        "source": "Synthesized from ANFAC, AER, BdE, Baker McKenzie.",
    },
    "브랜드 Top10": {
        "insight": "Toyota leads, with Renault/VW/Hyundai/SEAT close behind. Dacia and Peugeot also strong — diversified European/Asian brand mix.",
        "source": "ANFAC 2025 brand registrations.",
    },
    "OEM 순위(Top 5)": {
        "insight": "Toyota #1 (8.39%); top-5 share concentrated near 30-35%.",
        "source": "ANFAC 2025.",
    },
    "금융사 순위(Top 5)": {
        "insight": "Top-3 banks (Santander Consumer, CA Auto Bank, Cetelem) hold ~60% of passenger-car finance; OEM captives (VW FS, Toyota Kreditbank) follow.",
        "source": "El Economista 2024.",
    },
    "경쟁사 리스트": {
        "insight": "Bank subsidiaries dominate consumer finance; OEM captives serve their brand groups; multinational lessors (Arval, ALD/Ayvens, Alphabet, LeasePlan) cover fleet.",
        "source": "AER 2026, El Economista.",
    },
    "경쟁사 진출 형태": {
        "value": "Bank subsidiaries (Santander Consumer, Cetelem, CA Auto Bank) + OEM captives (VW FS, Toyota, BMW, MB) + EFC-licensed specialized lenders. Renting handled by ALD/Arval/Alphabet/LeasePlan.",
        "insight": "Bank-subsidiary led with OEM captive overlay; renting market dominated by 4 multinational lessors. Independent entrant should target the renting/EV-residual niche first.",
        "source": "AER 2026, El Economista, industry research.",
    },
    "경쟁사 금리 범위": {
        "value": "New auto-loan APR ~6-10% (promo 0-3% captive only); consumer credit avg TEDR ~7%.",
        "insight": "Mainstream auto-loan APR 6-10%; below-market promo rates are captive-only. Below 2026 22% cap, but quarterly cap monitoring required.",
        "source": "Banco de España, El Economista 2025.",
    },
    "평균 신차가격": {
        "value": "Approx. €30,000-32,000 (avg. turismos transaction price; trending up with electrification).",
        "insight": "Avg. new-car transaction price ~€30-32k; EV/SUV mix pushes it upward.",
        "source": "ANFAC, Faconauto 2025.",
    },
    "규제기관 식별": {
        "value": "Banco de España (EFC authorization & prudential supervision) / MINECO (authorization) / CNMV (securities) / DGSFP (insurance/renting) / AEPD (data protection) / CNMC (competition).",
        "insight": "BdE is the principal regulator for consumer credit (EFC). DGSFP supervises renting in its insurance-related aspects. Cross-agency coordination needed.",
        "source": "Banco de España, MINECO, CNMV, DGSFP, AEPD, CNMC.",
    },
    "외부 이슈 스캔": {
        "insight": "Six issues across market, regulation, electrification, and competition.",
        "source": "Reuters, WardsAuto, Automotive News Europe (whitelist).",
    },
}

# 뉴스 항목 번역 (외부 이슈 스캔 value 리스트)
NEWS_TRANSLATIONS = [
    {
        "headline": "Spain's 2025 new-car registrations reach 1,149K, +12.9% — driving EU major-market recovery",
        "so_what": "Market recovery underpins finance penetration — entry timing favorable. Note renting/fleet share rise decoupling from consumer retail.",
    },
    {
        "headline": "Spain to introduce 22% APR ceiling under new Consumer Credit Act (EU Directive 2023/2225)",
        "so_what": "Consumer-finance APR logic needs dynamic cap monitoring quarterly. High-margin subprime products constrained — strengthens B2B/renting-first strategy.",
    },
    {
        "headline": "Spain renting: 51.3% of new registrations are EVs — electrification accelerates in fleet",
        "so_what": "Renting entry brings strong EV residual-value and charging-infrastructure exposure. Conservative buyback/residual guarantees required.",
    },
    {
        "headline": "ECB cuts deposit rate to 2.00% in 2025 — favorable funding environment",
        "so_what": "Lower funding cost expands auto-loan margin room. Pair with consumer-credit cap to design APR with margin headroom.",
    },
    {
        "headline": "Santander Consumer Finance to merge with Openbank by Oct 2025 — distribution expansion",
        "so_what": "Stronger SCF position raises bar for #1 lender — new entrants should sharpen niche positioning (used / EV / fleet).",
    },
    {
        "headline": "Stellantis to route all Spanish financing through SCF by 2026",
        "so_what": "Multi-brand captive consolidation accelerates — independent entrants should secure niche brand/dealer partnerships.",
    },
]


def main():
    if not ES_PATH.exists():
        print(f"Not found: {ES_PATH}")
        sys.exit(1)

    data = json.loads(ES_PATH.read_text(encoding="utf-8"))

    # 1) overall_insight_en
    if data.get("overall_insight") and not data.get("overall_insight_en"):
        data["overall_insight_en"] = OVERALL_EN

    # 2) items[]
    updated = 0
    for it in data.get("items", []):
        name = it.get("item")
        tr = ITEM_TRANSLATIONS.get(name)
        if not tr:
            continue
        # value_en — if value is str
        if "value" in tr and isinstance(it.get("value"), str) and not it.get("value_en"):
            it["value_en"] = tr["value"]
            updated += 1
        # insight_en
        if "insight" in tr and it.get("insight") and not it.get("insight_en"):
            it["insight_en"] = tr["insight"]
            updated += 1
        # source_en
        if "source" in tr and it.get("source") and not it.get("source_en"):
            it["source_en"] = tr["source"]
            updated += 1

    # 3) 외부 이슈 스캔 뉴스 번역
    for it in data.get("items", []):
        if it.get("item") == "외부 이슈 스캔" and isinstance(it.get("value"), list):
            for i, news in enumerate(it["value"]):
                if not isinstance(news, dict):
                    continue
                if i < len(NEWS_TRANSLATIONS):
                    tr = NEWS_TRANSLATIONS[i]
                    if news.get("headline") and not news.get("headline_en"):
                        news["headline_en"] = tr["headline"]
                        updated += 1
                    if news.get("so_what") and not news.get("so_what_en"):
                        news["so_what_en"] = tr["so_what"]
                        updated += 1

    # 저장 (백업 후)
    backup = ES_PATH.with_suffix(".json.bak")
    if not backup.exists():
        backup.write_text(json.dumps(json.loads(ES_PATH.read_text(encoding="utf-8")),
                                      ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Backup saved: {backup}")
    ES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ES_latest.json updated. _en fields added/updated: {updated}")
    print(f"  overall_insight_en: {'set' if data.get('overall_insight_en') else 'missing'}")


if __name__ == "__main__":
    main()
