import { useState } from 'react'
import { useApi } from '../lib/useApi'
import { api } from '../lib/api'
import { Chart, FlagBadge } from '../lib/charts'

/**
 * PR1/PR2 진단 보고서 (U19). render_req 탭 구조 + nature별 차트 + source_flag 배지.
 * kind: 'country'|'region'. 보고서 목록에서 최신을 선택해 상세 렌더.
 * PDF 다운로드(U10) + 메일(mailto §6.6) 버튼.
 */
export default function Report({ kind, code, initialTab = 0, onSettings }) {
  // 1) 보고서 목록 → 최신 선택
  const list = useApi(() => api.reports(kind, code), [kind, code])
  const latestId = list.data?.length
    ? [...list.data].sort((a, b) => a.report_id.localeCompare(b.report_id)).at(-1).report_id
    : null
  // 2) 상세
  const detail = useApi(() => (latestId ? api.report(kind, code, latestId) : Promise.resolve(null)), [kind, code, latestId])
  const [tabIdx, setTabIdx] = useState(initialTab)

  if (list.loading) return <Centered>보고서 목록 불러오는 중…</Centered>
  if (list.error) return <Centered>목록 오류: {list.error}</Centered>
  if (!latestId) return <Centered>생성된 보고서가 없습니다. P{kind === 'country' ? '1' : '2'}에서 [보고서 생성]을 눌러주세요.</Centered>
  if (detail.loading) return <Centered>보고서 불러오는 중…</Centered>
  if (detail.error || !detail.data) return <Centered>보고서 오류: {detail.error}</Centered>

  const rpt = detail.data
  const tabs = rpt.tabs || []
  const tab = tabs[tabIdx] || tabs[0]

  return (
    <div className="flex h-full flex-col">
      {/* 마스트헤드 */}
      <header className="flex shrink-0 items-start justify-between bg-primary px-lg py-lg text-on-primary">
        <div>
          <div className="mb-1 flex items-center gap-sm text-label-sm uppercase tracking-wider text-primary-fixed-dim">
            <span>{rpt.report_id}</span>
            {rpt.based_on?.internal_version && <><span>·</span><span>룰셋 v{rpt.based_on.internal_version}</span></>}
          </div>
          <h2 className="text-headline-lg text-on-primary">{rpt.title}</h2>
        </div>
        <div className="flex shrink-0 gap-sm">
          <a href={api.reportPdfUrl(kind, code, latestId)} target="_blank" rel="noreferrer"
            className="flex items-center gap-xs rounded border border-primary-fixed-dim px-md py-sm text-label-md text-primary-fixed">
            <span className="material-symbols-outlined text-[18px]">picture_as_pdf</span>PDF
          </a>
          <a href={mailtoUrl(rpt, kind, code, latestId)}
            className="flex items-center gap-xs rounded bg-secondary px-md py-sm text-label-md text-on-primary no-underline">
            <span className="material-symbols-outlined text-[18px]">forward_to_inbox</span>메일
          </a>
        </div>
      </header>

      {/* 탭 네비 */}
      <nav className="flex shrink-0 gap-xl overflow-x-auto border-b border-surface-border bg-surface-container-lowest px-lg">
        {tabs.map((tb, i) => (
          <button key={tb.tab} onClick={() => setTabIdx(i)}
            className={`whitespace-nowrap border-b-2 py-md text-label-md transition-colors ${i === tabIdx ? 'border-primary text-primary' : 'border-transparent text-on-surface-variant hover:text-primary'}`}>
            {tb.name}
          </button>
        ))}
      </nav>

      {/* 탭 콘텐츠 */}
      <div className="flex-1 overflow-y-auto bg-surface p-lg">
        {tab.notes?.map((n, i) => <p key={i} className="mb-sm text-label-sm text-text-secondary">⚠ {n}</p>)}
        <div className="grid grid-cols-1 gap-md md:grid-cols-2">
          {tab.blocks.map((b, i) => (
            <div key={i} className={`rounded-md border border-surface-border bg-surface-container-lowest p-lg shadow-[0_4px_8px_rgba(0,32,78,0.04)] ${spanFor(b)}`}>
              <div className="mb-sm flex items-center justify-between gap-sm">
                <h3 className="text-body-md font-semibold text-primary">{b.label}</h3>
                <FlagBadge flag={b.source_flag} />
              </div>
              <Chart block={b} />
              {b.source?.org && <p className="mt-sm text-label-sm text-text-secondary">출처: {b.source.org}{b.source.tier ? ` · Tier ${b.source.tier}` : ''}</p>}
            </div>
          ))}
        </div>
      </div>

      <footer className="flex shrink-0 justify-between border-t border-surface-border bg-surface-container-lowest px-lg py-sm">
        <span className="text-label-sm text-text-secondary">출처 신뢰도: 각 수치 옆 뱃지 참조</span>
        <button onClick={() => onSettings && onSettings()} className="flex items-center gap-xs text-label-md text-secondary">
          <span className="material-symbols-outlined text-[18px]">tune</span>룰셋 설정
        </button>
      </footer>
    </div>
  )
}

// mailto (§6.6): 제목·본문 채우고 to 는 비움. 첨부 불가 → 링크+안내.
function mailtoUrl(rpt, kind, code, id) {
  const name = rpt.title || code
  const subject = `[Silk Road] ${name} — ${id}`
  const link = `${location.origin}${api.reportHtmlUrl(kind, code, id)}`
  const body = [
    `${name} 진단 보고서입니다.`,
    `보고서 링크: ${link}`,
    'PDF가 필요하면 다운로드 후 첨부해 주세요.',
  ].join('\n')
  return `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

// 와이드 차트(시계열·신호등·다축)는 2칸 차지
function spanFor(b) {
  return ['status_matrix', 'score_multiaxis'].includes(b.nature) ? 'md:col-span-2' : ''
}

function Centered({ children }) {
  return <div className="flex h-full items-center justify-center px-lg text-center text-body-md text-text-secondary">{children}</div>
}
