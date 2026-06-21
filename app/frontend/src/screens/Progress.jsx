import { useJob } from '../lib/useJob'

/**
 * PS2 프로그레스 (U20). web_design_spec §PS2/§5.3.
 * job 폴링 → 5단계 병렬 프로그레스바(시장/규제/상품/시스템/결과 생성).
 * '결과 생성'은 상위 4단계와 분리. 완료 시 [보고서 보기].
 */
const STATE_COLOR = {
  done: 'bg-secondary',
  running: 'bg-primary-container',
  pending: 'bg-surface-border',
  error: 'bg-error',
}

export default function Progress({ jobId, purpose, onViewReport }) {
  const job = useJob(jobId)

  if (!jobId) return <Centered>진행 중인 작업이 없습니다.</Centered>
  if (!job) return <Centered>작업 상태 불러오는 중…</Centered>

  const steps = job.steps || []
  const main = steps.filter((s) => s.key !== 'result')
  const result = steps.find((s) => s.key === 'result')
  const done = job.status === 'done'

  return (
    <div className="flex h-full flex-col items-center justify-center gap-lg p-xl">
      <div className="w-full max-w-md">
        <div className="mb-md flex items-center justify-between">
          <h2 className="text-headline-md text-primary">{purpose === 'research' ? '외부 리서치' : '보고서 생성'}</h2>
          <span className="text-body-sm tabular-nums text-text-secondary">{job.progress}%</span>
        </div>

        {/* 상위 4단계 */}
        <div className="space-y-md">
          {main.map((s) => <Bar key={s.key} step={s} />)}
        </div>

        {/* 결과 생성 — 분리 */}
        {result && (
          <div className="mt-lg border-t border-surface-border pt-lg">
            <Bar step={result} emphasize />
          </div>
        )}

        {job.status === 'error' && (
          <p className="mt-md text-body-sm text-error">오류: {job.error}</p>
        )}

        {done && (
          <button onClick={() => onViewReport && onViewReport(job)}
            className="mt-lg w-full rounded bg-primary py-md text-label-md text-on-primary shadow-sm transition-transform hover:scale-[0.99]">
            {purpose === 'research' ? '국가 정보 보기' : '보고서 보기'}
          </button>
        )}
      </div>
    </div>
  )
}

function Bar({ step, emphasize }) {
  const pct = step.state === 'done' ? 100 : step.state === 'running' ? 55 : step.state === 'error' ? 100 : 0
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-body-sm">
        <span className={emphasize ? 'font-semibold text-primary' : 'text-on-surface'}>{step.label}</span>
        <span className="text-label-sm text-text-secondary">
          {step.state === 'done' ? '완료' : step.state === 'running' ? '진행 중' : step.state === 'error' ? '오류' : '대기'}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-border">
        <div className={`h-full rounded-full transition-all duration-500 ${STATE_COLOR[step.state] || ''}`}
          style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Centered({ children }) {
  return <div className="flex h-full items-center justify-center text-body-md text-text-secondary">{children}</div>
}
