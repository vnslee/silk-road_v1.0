import { useEffect, useState } from 'react'
import { useApi } from '../lib/useApi'
import { api } from '../lib/api'

/**
 * PS1 룰셋 설정 (U21). web_design_spec §PS1.
 * 카테고리 가중치 슬라이더(합=100 강제) + 임계값 표시 + 저장.
 * 한 슬라이더 조정 시 나머지를 비례 재분배해 합=100 유지.
 */
const ORDER = ['market', 'finance', 'regulation', 'system']

export default function Settings() {
  const { data, loading, error } = useApi(() => api.ruleset(), [])
  const [weights, setWeights] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => { if (data) setWeights({ ...data.category_weights }) }, [data])

  if (loading) return <Centered>불러오는 중…</Centered>
  if (error) return <Centered>오류: {error}</Centered>
  if (!weights) return <Centered>—</Centered>

  const labels = data.category_labels
  const total = Math.round(ORDER.reduce((s, k) => s + (weights[k] || 0), 0))

  // 한 카테고리 변경 → 나머지 3개를 기존 비율대로 재분배(합=100)
  function setOne(key, val) {
    val = Math.max(0, Math.min(100, Math.round(val)))
    const others = ORDER.filter((k) => k !== key)
    const restTotal = others.reduce((s, k) => s + weights[k], 0)
    const remain = 100 - val
    const next = { [key]: val }
    if (restTotal === 0) {
      others.forEach((k, i) => { next[k] = i === 0 ? remain : 0 })
    } else {
      let acc = 0
      others.forEach((k, i) => {
        if (i === others.length - 1) next[k] = remain - acc
        else { const v = Math.round((weights[k] / restTotal) * remain); next[k] = v; acc += v }
      })
    }
    setWeights(next); setSaved(false)
  }

  async function save() {
    setSaving(true); setSaved(false)
    try {
      await api.saveWeights(weights)
      setSaved(true)
    } catch (e) { alert('저장 실패: ' + e.message) }
    finally { setSaving(false) }
  }

  const th = data.quick_win_rules?.thresholds || {}

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-surface-border px-lg py-lg">
        <h2 className="text-headline-lg text-primary">룰셋 설정</h2>
        <span className="text-label-md text-text-secondary">버전 v{data.version}</span>
      </div>

      <div className="flex-1 overflow-y-auto p-lg">
        {/* 패널 1: 카테고리 가중치 */}
        <Panel title="카테고리 가중치"
          right={<span className={`text-body-sm font-semibold tabular-nums ${total === 100 ? 'text-[#137333]' : 'text-error'}`}>합계 {total}%</span>}>
          <div className="space-y-md">
            {ORDER.map((k) => (
              <div key={k}>
                <div className="mb-1 flex items-center justify-between text-body-sm">
                  <span className="text-on-surface">{labels[k]}</span>
                  <span className="tabular-nums text-primary">{weights[k]}%</span>
                </div>
                <input type="range" min="0" max="100" value={weights[k]}
                  onChange={(e) => setOne(k, Number(e.target.value))}
                  className="w-full accent-primary" />
              </div>
            ))}
          </div>
        </Panel>

        {/* 패널 2: 임계값(읽기 표시) */}
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
        <button onClick={save} disabled={saving || total !== 100}
          className="rounded bg-primary px-lg py-sm text-label-md text-on-primary shadow-sm transition-transform hover:scale-[0.98] disabled:opacity-50">
          {saving ? '저장 중…' : '저장'}
        </button>
      </div>
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
