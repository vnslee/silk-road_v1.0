import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * 상단 좌측 메뉴 드롭다운 (U17). web_design_spec §M1 메뉴.
 * 기본 히든, 클릭 시 확장, 외부 클릭/재클릭 시 닫힘. 반투명·절제된 오버레이.
 * 메뉴 → 풀사이즈 진입(경로 C).
 */
const ITEMS = [
  { key: 'nav.status', screen: 'M1', icon: 'public' },
  { key: 'nav.country', screen: 'P1', icon: 'flag' },
  { key: 'nav.region', screen: 'P2', icon: 'globe' },
  { key: 'nav.report', screen: 'PR1', icon: 'description' },
  { key: 'nav.settings', screen: 'PS1', icon: 'tune' },
]

export default function MenuDropdown({ onSelect }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center text-on-surface-variant transition-colors hover:text-primary"
        aria-label="menu" aria-expanded={open}
      >
        <span className="material-symbols-outlined">{open ? 'close' : 'menu'}</span>
      </button>
      {open && (
        <nav className="absolute left-0 top-[calc(100%+8px)] z-30 w-[200px] overflow-hidden rounded-md border border-surface-border bg-surface-container-lowest/95 shadow-[0_12px_24px_rgba(0,32,78,0.16)] backdrop-blur">
          {ITEMS.map((it) => (
            <button
              key={it.key}
              onClick={() => { setOpen(false); onSelect(it.screen) }}
              className="flex w-full items-center gap-sm px-md py-sm text-left text-body-sm text-on-surface transition-colors hover:bg-surface-light"
            >
              <span className="material-symbols-outlined text-[20px] text-secondary">{it.icon}</span>
              {t(it.key)}
            </button>
          ))}
        </nav>
      )}
    </div>
  )
}
