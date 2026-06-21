import { useApi } from '../lib/useApi'
import { api } from '../lib/api'

/**
 * PR1/PR2 진단 보고서 (U19 → 원격 통합판).
 * 원격이 생성한 완성형 HTML 보고서를 iframe 으로 표시(원격 정본 원칙).
 * 보고서 목록에서 HTML 이 있는 최신본을 선택.
 * kind: 'country'|'region'.
 */
export default function Report({ kind, code, onSettings }) {
  const list = useApi(() => api.reports(kind, code), [kind, code])

  if (list.loading) return <Centered>보고서 목록 불러오는 중…</Centered>
  if (list.error) return <Centered>목록 오류: {list.error}</Centered>

  // HTML 있는 보고서만, report_id 기준 최신 우선. (중복 report_id 는 dedup)
  const seen = new Set()
  const withHtml = (list.data || [])
    .filter((r) => r.has_html && !seen.has(r.report_id) && seen.add(r.report_id))
    .sort((a, b) => b.report_id.localeCompare(a.report_id))

  if (!withHtml.length) {
    return <Centered>
      생성된 보고서가 없습니다. P{kind === 'country' ? '1' : '2'} 에서 [보고서 생성]을 눌러주세요.
    </Centered>
  }

  const rid = withHtml[0].report_id
  const htmlUrl = api.reportHtmlUrl(kind, code, rid)

  return (
    <div className="flex h-full flex-col">
      {/* 액션 바 */}
      <div className="flex shrink-0 items-center justify-between border-b border-surface-border bg-surface-container-lowest px-lg py-sm">
        <div className="flex items-center gap-sm">
          <span className="text-label-md text-text-secondary">{rid}</span>
          {withHtml.length > 1 && (
            <span className="text-label-sm text-text-disabled">외 {withHtml.length - 1}건</span>
          )}
        </div>
        <div className="flex items-center gap-sm">
          <a href={api.reportPdfUrl(kind, code, rid)} target="_blank" rel="noreferrer"
            className="flex items-center gap-xs rounded border border-primary px-md py-xs text-label-md text-primary no-underline transition-colors hover:bg-surface-light">
            <span className="material-symbols-outlined text-[18px]">picture_as_pdf</span>PDF
          </a>
          <a href={mailtoUrl(rid, kind, code)}
            className="flex items-center gap-xs rounded bg-secondary px-md py-xs text-label-md text-on-primary no-underline">
            <span className="material-symbols-outlined text-[18px]">forward_to_inbox</span>메일
          </a>
          {onSettings && (
            <button onClick={onSettings} className="flex items-center gap-xs text-label-md text-secondary">
              <span className="material-symbols-outlined text-[18px]">tune</span>룰셋
            </button>
          )}
        </div>
      </div>
      {/* 원격 HTML 보고서 */}
      <iframe
        title={`report-${rid}`}
        src={htmlUrl}
        className="min-h-0 flex-1 border-0"
      />
    </div>
  )
}

function mailtoUrl(rid, kind, code) {
  const subject = `[Silk Road] ${code} 진단 보고서 — ${rid}`
  const link = `${location.origin}${api.reportHtmlUrl(kind, code, rid)}`
  const body = [`${code} 진단 보고서입니다.`, `보고서 링크: ${link}`,
    'PDF가 필요하면 다운로드 후 첨부해 주세요.'].join('\n')
  return `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
}

function Centered({ children }) {
  return <div className="flex h-full items-center justify-center px-lg text-center text-body-md text-text-secondary">{children}</div>
}
