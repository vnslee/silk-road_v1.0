import { useApi, flagEmoji } from '../lib/useApi'
import { api } from '../lib/api'

/**
 * P2 권역 정보 (U18). web_design_spec §P2.
 * 권역명 / 기진출국(baseline)·후보국 리스트 + 보유현황 / 보고서 버튼.
 * 퀵윈 순위는 보고서(PR2)에서 — 여기선 멤버 현황까지.
 */
export default function RegionInfo({ code, onReport, onGenerate }) {
  const { data, loading, error } = useApi(() => api.region(code), [code])

  if (loading) return <Centered>불러오는 중…</Centered>
  if (error) return <Centered>데이터를 불러올 수 없습니다: {error}</Centered>

  const members = data.members || []
  const withData = new Set(data.members_with_data || [])

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-start justify-between border-b border-surface-border px-lg py-lg">
        <div className="flex items-center gap-md">
          <span className="material-symbols-outlined text-[40px] text-primary-container">public</span>
          <div>
            <h2 className="text-headline-lg text-primary">{data.name_ko}</h2>
            <p className="text-body-sm text-text-secondary">{data.name_en} · 기준국 {data.baseline}</p>
          </div>
        </div>
        <button className="rounded border border-primary px-md py-sm text-label-md text-primary transition-colors hover:bg-surface-light">
          시뮬레이션
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-lg">
        <div className="rounded-md border border-surface-border bg-surface-container-lowest p-lg shadow-[0_4px_8px_rgba(0,32,78,0.04)]">
          <h3 className="mb-md text-headline-md text-primary">소속 국가 ({members.length})</h3>
          <div className="grid grid-cols-2 gap-md sm:grid-cols-3">
            {members.map((m) => {
              const isBaseline = m === data.baseline
              const has = withData.has(m)
              return (
                <div key={m} className={`flex items-center gap-sm rounded-md border p-md ${isBaseline ? 'border-secondary bg-secondary-container/10' : 'border-surface-border'}`}>
                  <span className="text-[28px] leading-none">{flagEmoji(m)}</span>
                  <div className="min-w-0">
                    <div className="text-body-sm font-medium text-on-surface">{m}</div>
                    <div className="text-label-sm text-text-secondary">
                      {isBaseline ? '기진출(기준국)' : has ? '데이터 보유' : '진출예정'}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          <p className="mt-md text-label-sm text-text-disabled">
            진출예정국 퀵윈 순위·IT준비도·종합점수는 권역 진단 보고서(PR2)에서 확인하세요.
          </p>
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
