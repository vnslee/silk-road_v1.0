/**
 * nature → 차트 매핑 (U19). render_req §1 규칙을 Recharts 로 인터랙티브하게.
 * 백엔드 HTML 렌더(U5)와 동일 매핑이되 hover/툴팁 지원. Kinetic 색.
 */
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'

const NAVY = '#00204e'
const BLUE = '#005db7'
const PALETTE = ['#00204e', '#005db7', '#599bfe', '#7d9fe9', '#aec6ff', '#d8e2ff']

// ── source_flag 배지 (render_req §2) ──
const FLAG = {
  EXT: { label: '외부조사', cls: 'text-[#747782] bg-[#7477821f]' },
  INT: { label: '내부자료', cls: 'text-[#005db7] bg-[#005db71f]' },
  CALC: { label: '계산값', cls: 'text-[#137333] bg-[#1373331f]' },
  AI: { label: 'AI', cls: 'text-[#6b3fa0] bg-[#6b3fa024]' },
  NEWS: { label: '외부이슈', cls: 'text-[#b45309] bg-[#b4530924]' },
}
export function FlagBadge({ flag }) {
  const f = FLAG[flag] || FLAG.EXT
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-label-sm ${f.cls}`}>
    <span className="h-1.5 w-1.5 rounded-full bg-current" />{f.label}
  </span>
}

// ── nature별 렌더 ──
function Timeseries({ value }) {
  const hist = (value?.history || []).map((p) => ({ year: p.year, hist: p.value }))
  const fore = (value?.forecast || []).map((p) => ({ year: p.year, fore: p.value }))
  // 연결을 위해 history 마지막 점을 forecast 시작에도
  const merged = [...hist]
  fore.forEach((p) => merged.push({ year: p.year, fore: p.fore }))
  if (!merged.length) return <Empty>추세 데이터 없음</Empty>
  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={merged} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#555' }} />
        <YAxis tick={{ fontSize: 11, fill: '#555' }} width={44} />
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Line type="monotone" dataKey="hist" stroke={NAVY} strokeWidth={2} dot={{ r: 2 }} name="실측" connectNulls />
        <Line type="monotone" dataKey="fore" stroke={BLUE} strokeWidth={2} strokeDasharray="4 3" dot={{ r: 2 }} name="전망" connectNulls />
      </LineChart>
    </ResponsiveContainer>
  )
}

function Ranking({ value }) {
  if (!Array.isArray(value) || !value.length) return <Empty>데이터 없음</Empty>
  const rows = value.map((r, i) => {
    if (typeof r === 'string') return { name: r, v: null }
    const name = r.country_ko || r.name || r.code || `#${i + 1}`
    const v = num(r.attractiveness) ?? num(r.quick_win_score) ?? num(r.value) ?? num(r.market_share)
    return { name, v, band: r.quick_win_band }
  })
  const hasNum = rows.some((r) => r.v != null)
  if (!hasNum) {
    return <ul className="flex flex-col gap-1">{rows.map((r, i) =>
      <li key={i} className="flex items-center gap-sm text-body-sm"><span className="text-text-disabled tabular-nums">{i + 1}</span>{r.name}</li>)}</ul>
  }
  return (
    <ResponsiveContainer width="100%" height={Math.max(120, rows.length * 34)}>
      <BarChart layout="vertical" data={rows} margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 12, fill: '#1b1c1c' }} />
        <Tooltip contentStyle={{ fontSize: 12 }} />
        <Bar dataKey="v" radius={[0, 4, 4, 0]}>
          {rows.map((_, i) => <Cell key={i} fill={i === 0 ? NAVY : BLUE} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function Composition({ value }) {
  if (!Array.isArray(value) || !value.length) return <Empty>데이터 없음</Empty>
  const rows = value.map((r) => ({ name: r.name || r.code, v: num(r.value) ?? num(r.market_share) ?? 0 }))
  return (
    <ResponsiveContainer width="100%" height={180}>
      <PieChart>
        <Pie data={rows} dataKey="v" nameKey="name" innerRadius={40} outerRadius={70} paddingAngle={2}>
          {rows.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
        </Pie>
        <Tooltip contentStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}

function MultiAxis({ value }) {
  // {축:점수} → 레이더 / [{code,similarity,difficulty}] → 표
  if (value && !Array.isArray(value) && typeof value === 'object') {
    const data = Object.entries(value).map(([k, v]) => ({ axis: k, v: num(v) ?? 0 }))
    if (!data.length) return <Empty>데이터 없음</Empty>
    return (
      <ResponsiveContainer width="100%" height={200}>
        <RadarChart data={data} outerRadius={70}>
          <PolarGrid />
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11, fill: '#555' }} />
          <Radar dataKey="v" stroke={NAVY} fill={BLUE} fillOpacity={0.4} />
        </RadarChart>
      </ResponsiveContainer>
    )
  }
  if (Array.isArray(value)) {
    return (
      <table className="w-full text-body-sm">
        <thead><tr className="border-b border-surface-border text-left text-label-md text-text-secondary">
          <th className="py-1">국가</th><th>유사도</th><th>난이도</th></tr></thead>
        <tbody>{value.map((r, i) => (
          <tr key={i} className="border-b border-surface-light">
            <td className="py-1">{r.code}</td><td>{fmtNum(r.similarity)}</td><td>{fmtNum(r.difficulty)}</td>
          </tr>))}</tbody>
      </table>
    )
  }
  return <Empty>데이터 없음</Empty>
}

function StatusMatrix({ value }) {
  if (!Array.isArray(value) || !value.length) return <Empty>데이터 없음</Empty>
  return (
    <table className="w-full text-body-sm">
      <thead><tr className="border-b border-surface-border text-left text-label-md text-text-secondary">
        <th className="py-1">국가</th><th>판정</th><th>탈락</th><th>보류</th></tr></thead>
      <tbody>{value.map((r, i) => (
        <tr key={i} className={`border-b border-surface-light ${r.passed ? '' : 'bg-surface-container text-text-disabled'}`}>
          <td className="py-1">{r.country_ko || r.code}</td>
          <td>{r.passed ? <span className="text-[#137333]">● 통과</span> : <span className="text-error">✕ 탈락</span>}</td>
          <td>{(r.fail_items || []).join(', ') || '—'}</td>
          <td>{(r.flag_items || []).join(', ') || '—'}</td>
        </tr>))}</tbody>
    </table>
  )
}

function SingleValue({ value, source }) {
  if (value == null) return <div className="text-body-sm text-text-disabled">— {source?.note || '조사 필요'}</div>
  return <div className="text-headline-lg tabular-nums text-primary">{fmtNum(value)}</div>
}

function Qualitative({ block }) {
  const v = block.value
  if (block.key?.includes('news') && Array.isArray(v)) {
    return <div className="flex flex-col gap-sm">{v.flatMap((o, i) => {
      const issues = o.issues || [o]
      const prefix = o.code ? `[${o.code}] ` : ''
      return issues.map((it, j) => (
        <div key={`${i}-${j}`} className="border-b border-surface-light pb-sm last:border-0">
          <div className="text-body-sm font-medium">{prefix}{it.headline}</div>
          <div className="text-label-sm text-on-surface-variant">{it.so_what}</div>
          <div className="text-label-sm text-text-secondary">{it.publisher} {it.pub_date}</div>
        </div>))
    })}</div>
  }
  if (v == null) return <div className="text-body-sm text-text-disabled">— {block.source?.note || '조사 필요'}</div>
  if (typeof v === 'object') {
    return <div className="flex flex-col gap-1">{Object.entries(v).map(([k, val]) =>
      <div key={k} className="text-body-sm"><span className="font-medium">{k}</span>: {String(val)}</div>)}</div>
  }
  return <p className="text-body-sm text-on-surface-variant">{String(v)}</p>
}

export function Chart({ block }) {
  switch (block.nature) {
    case 'timeseries': return <Timeseries value={block.value} />
    case 'ranking': return <Ranking value={block.value} />
    case 'composition': return <Composition value={block.value} />
    case 'score_multiaxis': return <MultiAxis value={block.value} />
    case 'status_matrix': return <StatusMatrix value={block.value} />
    case 'single_value': return <SingleValue value={block.value} source={block.source} />
    default: return <Qualitative block={block} />
  }
}

const num = (x) => (typeof x === 'number' ? x : null)
const fmtNum = (x) => (typeof x === 'number' ? x.toLocaleString() : '—')
function Empty({ children }) { return <div className="text-body-sm text-text-disabled">— {children}</div> }
