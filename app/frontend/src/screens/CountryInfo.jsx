import { useApi, flagEmoji } from '../lib/useApi'
import { api } from '../lib/api'

/**
 * P1 국가 정보 (U18). web_design_spec §P1.
 * 상단: 국기·국가명·진출여부 / 중간: 시장·규제·시스템 섹션 / 하단: 보고서 버튼.
 */
const GATE_BADGE = {
  PASS: 'bg-[#e6f4ea] text-[#137333]',
  FAIL: 'bg-[#fce8e6] text-[#c5221f]',
  FLAG: 'bg-[#fef7e0] text-[#b06000]',
}

function Section({ title, children }) {
  return (
    <div className="rounded-md border border-surface-border bg-surface-container-lowest p-lg shadow-[0_4px_8px_rgba(0,32,78,0.04)]">
      <h3 className="mb-md border-b border-surface-border pb-sm text-headline-md text-primary">{title}</h3>
      {children}
    </div>
  )
}

function ItemRow({ it }) {
  return (
    <div className="flex items-start justify-between gap-md border-b border-surface-light py-sm last:border-0">
      <div className="min-w-0">
        <div className="text-body-sm font-medium text-on-surface">{it.item}</div>
        {it.insight && <div className="mt-0.5 text-label-sm text-text-secondary">{it.insight}</div>}
      </div>
      <div className="shrink-0 text-right">
        {it.role === 'gate' ? (
          <span className={`rounded px-2 py-1 text-label-sm ${GATE_BADGE[it.gate_result] || ''}`}>{it.gate_result}</span>
        ) : (
          <span className="text-body-sm font-semibold tabular-nums text-primary">
            {fmtValue(it)}
          </span>
        )}
        {it.tier >= 3 && <span className="ml-xs text-label-sm text-text-disabled">추정</span>}
      </div>
    </div>
  )
}

function fmtValue(it) {
  const v = it.value
  if (Array.isArray(v)) return `${v.length}건`
  if (typeof v === 'number') return v.toLocaleString() + (it.unit ? ` ${it.unit.replace(/_/g, ' ')}` : '')
  if (typeof v === 'string') return v.length > 24 ? v.slice(0, 24) + '…' : v
  return '—'
}

export default function CountryInfo({ code, onReport, onGenerate, onResearch }) {
  const { data, loading, error } = useApi(() => api.country(code), [code])

  if (loading) return <Centered>불러오는 중…</Centered>
  // 데이터 없음(404) → 외부 리서치 제안 (§6.5.1)
  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-md p-xl text-center">
        <span className="material-symbols-outlined text-[48px] text-outline-variant">travel_explore</span>
        <p className="text-headline-md text-primary">{code} 정보가 아직 없습니다</p>
        <p className="text-body-sm text-text-secondary">외부 리서치를 통해 이 국가의 진단 데이터를 생성할까요?</p>
        <div className="mt-sm flex gap-sm">
          <button onClick={() => onResearch && onResearch(code)}
            className="rounded bg-primary px-lg py-sm text-label-md text-on-primary shadow-sm transition-transform hover:scale-[0.98]">
            예, 리서치 진행
          </button>
        </div>
        <p className="text-label-sm text-text-disabled">완료까지 수 분 소요됩니다. 진행률은 프로그레스 화면에서 확인하세요.</p>
      </div>
    )
  }

  const items = data.items || []
  const byCat = (cats, roles) =>
    items.filter((i) => cats.includes(i.category) && (!roles || roles.includes(i.role)))
  const market = byCat(['business'], ['score', 'context'])
  const regulation = byCat(['shared'], ['gate', 'score'])
  const system = byCat(['it'], null)

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-start justify-between border-b border-surface-border px-lg py-lg">
        <div className="flex items-center gap-md">
          <span className="text-[40px] leading-none">{flagEmoji(code)}</span>
          <div>
            <h2 className="text-headline-lg text-primary">{data.country_ko}</h2>
            <p className="text-body-sm text-text-secondary">{data.country} · {data.region} · {data.currency}</p>
          </div>
        </div>
        <button className="rounded border border-primary px-md py-sm text-label-md text-primary transition-colors hover:bg-surface-light">
          시뮬레이션
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-lg">
        {data.overall_insight && (
          <div className="mb-lg rounded-md bg-primary-fixed/40 p-md text-body-sm text-on-surface">
            {data.overall_insight}
          </div>
        )}
        <div className="grid grid-cols-1 gap-lg lg:grid-cols-3">
          <Section title="시장">{market.map((it, i) => <ItemRow key={i} it={it} />)}</Section>
          <Section title="규제·게이트">{regulation.map((it, i) => <ItemRow key={i} it={it} />)}</Section>
          <Section title="시스템">{system.map((it, i) => <ItemRow key={i} it={it} />)}</Section>
        </div>
      </div>

      <div className="flex shrink-0 justify-end gap-sm border-t border-surface-border px-lg py-md">
        <button onClick={() => onReport && onReport(code)}
          className="rounded border border-primary px-lg py-sm text-label-md text-primary transition-colors hover:bg-surface-light">보고서</button>
        <button onClick={() => onGenerate && onGenerate(code)}
          className="rounded bg-primary px-lg py-sm text-label-md text-on-primary shadow-sm transition-transform hover:scale-[0.98]">보고서 생성</button>
      </div>
    </div>
  )
}

function Centered({ children }) {
  return <div className="flex h-full items-center justify-center text-body-md text-text-secondary">{children}</div>
}
