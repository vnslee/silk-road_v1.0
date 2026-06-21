import { useEffect, useState } from 'react'
import { useApi } from '../lib/useApi'
import { api } from '../lib/api'

/**
 * PS1 룰셋 설정 (원격 internal 구조판).
 * 비즈니스·IT 항목 가중치 표시 + report_blend(비즈니스↔IT) 슬라이더(합=1.0) + 임계값.
 */
export default function Settings() {
  const { data, loading, error } = useApi(() => api.ruleset(), [])
  const [wBiz, setWBiz] = useState(60)   // % 단위 슬라이더
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data?.report_blend) setWBiz(Math.round((data.report_blend.w_biz ?? 0.6) * 100))
  }, [data])

  if (loading) return <Centered>불러오는 중…</Centered>
  if (error) return <Centered>오류: {error}</Centered>

  const wIt = 100 - wBiz
  const th = data.quick_win_rules?.thresholds || {}

  async function save() {
    setSaving(true); setSaved(false)
    try {
      await api.saveBlend(wBiz / 100, wIt / 100)
      setSaved(true)
    } catch (e) { alert('저장 실패: ' + e.message) }
    finally { setSaving(false) }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-surface-border px-lg py-lg">
        <h2 className="text-headline-lg text-primary">룰셋 설정</h2>
        <span className="text-label-md text-text-secondary">버전 v{data.version}</span>
      </div>

      <div className="flex-1 overflow-y-auto p-lg">
        {/* 패널 1: 퀵윈 배합 (report_blend) */}
        <Panel title="퀵윈 점수 배합" right={<span className="text-body-sm text-text-secondary">합계 100%</span>}>
          <div className="mb-md flex items-center justify-between text-body-sm">
            <span className="text-on-surface">비즈니스 매력도 <b className="text-primary tabular-nums">{wBiz}%</b></span>
            <span className="text-on-surface">IT 준비도 <b className="text-primary tabular-nums">{wIt}%</b></span>
          </div>
          <input type="range" min="0" max="100" value={wBiz}
            onChange={(e) => { setWBiz(Number(e.target.value)); setSaved(false) }}
            className="w-full accent-primary" />
        </Panel>

        {/* 패널 2: 항목 가중치 (읽기) */}
        <div className="grid grid-cols-1 gap-lg md:grid-cols-2">
          <Panel title="비즈니스 매력도 가중치">
            <WeightList weights={data.biz_attractiveness} />
          </Panel>
          <Panel title="IT 준비도 가중치">
            <WeightList weights={data.it_readiness} />
          </Panel>
        </div>

        {/* 패널 3: 임계값 */}
        <Panel title="퀵윈 임계값">
          <div className="grid grid-cols-2 gap-md text-body-sm">
            {Object.entries(th).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between rounded border border-surface-border px-md py-sm">
                <span className="text-on-surface-variant">{k}</span>
                <span className="tabular-nums font-semibold text-primary">{v}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="flex shrink-0 items-center justify-end gap-md border-t border-surface-border px-lg py-md">
        {saved && <span className="text-body-sm text-[#137333]">저장되었습니다</span>}
        <button onClick={save} disabled={saving}
          className="rounded bg-primary px-lg py-sm text-label-md text-on-primary shadow-sm transition-transform hover:scale-[0.98] disabled:opacity-50">
          {saving ? '저장 중…' : '저장'}
        </button>
      </div>
    </div>
  )
}

function WeightList({ weights }) {
  const entries = Object.entries(weights || {})
  if (!entries.length) return <p className="text-body-sm text-text-disabled">—</p>
  return (
    <div className="space-y-sm">
      {entries.map(([k, v]) => (
        <div key={k}>
          <div className="mb-1 flex items-center justify-between text-body-sm">
            <span className="text-on-surface">{k}</span>
            <span className="tabular-nums text-primary">{Math.round(v * 100)}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-border">
            <div className="h-full rounded-full bg-secondary" style={{ width: `${v * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function Panel({ title, right, children }) {
  return (
    <div className="mb-lg rounded-md border border-surface-border bg-surface-container-lowest p-lg shadow-[0_4px_8px_rgba(0,32,78,0.04)]">
      <div className="mb-md flex items-center justify-between border-b border-surface-border pb-sm">
        <h3 className="text-headline-md text-primary">{title}</h3>
        {right}
      </div>
      {children}
    </div>
  )
}

function Centered({ children }) {
  return <div className="flex h-full items-center justify-center text-body-md text-text-secondary">{children}</div>
}
