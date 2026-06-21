import { useApi } from '../lib/useApi'
import { api } from '../lib/api'

/**
 * PR1/PR2 진단 보고서 — 원격 생성 HTML 을 그대로 전체화면 iframe 으로.
 * 우리 액자(중복 헤더/버튼) 제거: 원격 HTML 자체에 헤더·PDF·메일 버튼이 있음.
 * 닫기 버튼만 우상단에 띄움. kind: 'country'|'region'.
 */
export default function Report({ kind, code, onClose }) {
  const list = useApi(() => api.reports(kind, code), [kind, code])

  if (list.loading) return <Centered>보고서 불러오는 중…</Centered>
  if (list.error) return <Centered>오류: {list.error}</Centered>

  // HTML 있는 보고서만, 최신 우선, report_id dedup
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

  return (
    <div className="relative h-full w-full">
      {/* 원격 HTML 보고서 전체화면 */}
      <iframe title={`report-${rid}`} src={api.reportHtmlUrl(kind, code, rid)}
        className="h-full w-full border-0" />
      {/* 닫기(우상단 떠있는 버튼) */}
      {onClose && (
        <button onClick={onClose}
          className="absolute right-md top-md flex h-9 w-9 items-center justify-center rounded-full bg-primary text-on-primary shadow-md transition-transform hover:scale-95"
          aria-label="close">
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>
      )}
    </div>
  )
}

function Centered({ children }) {
  return <div className="flex h-full items-center justify-center px-lg text-center text-body-md text-text-secondary">{children}</div>
}
