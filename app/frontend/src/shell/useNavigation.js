import { useCallback, useEffect, useState } from 'react'

/**
 * 경량 화면 라우팅 (U17). web_design_spec §5.1 진입모드 + 경로 A/B/C.
 * 화면 8종 × 진입모드(popup|fullsize). react-router 없이 자체 상태머신.
 *
 * 딥링크: location.hash 와 동기화 (#P1/ES, #PR2/EU 등). intro_spec 의 hash 진입과 호환.
 */
export const SCREENS = ['M1', 'C1', 'P1', 'P2', 'PR1', 'PR2', 'PS1', 'PS2']

function parseHash() {
  // "#P1/ES" → { screen:'P1', params:{code:'ES'} }
  const h = window.location.hash.replace(/^#/, '')
  if (!h) return null
  const [screen, ...rest] = h.split('/')
  if (!SCREENS.includes(screen)) return null
  const params = {}
  if (rest[0]) params.code = rest[0]
  if (rest[1] != null) params.tab = Number(rest[1])  // #PR1/ES/4 → 탭 인덱스
  return { screen, params }
}

export function useNavigation() {
  // nav: { screen, mode, params } | null(=M1 지도만)
  const [nav, setNav] = useState(() => {
    const fromHash = parseHash()
    // 딥링크는 풀사이즈로 진입(메뉴 경로와 동일 취급)
    return fromHash ? { ...fromHash, mode: 'fullsize' } : null
  })

  // hash ↔ 상태 동기화
  useEffect(() => {
    if (nav && nav.screen !== 'M1') {
      const code = nav.params?.code
      window.location.hash = code ? `${nav.screen}/${code}` : nav.screen
    } else if (window.location.hash) {
      history.replaceState(null, '', window.location.pathname + window.location.search)
    }
  }, [nav])

  // 브라우저 뒤로가기 대응
  useEffect(() => {
    const onPop = () => setNav(parseHash() ? { ...parseHash(), mode: 'fullsize' } : null)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const open = useCallback((screen, { mode = 'popup', params = {} } = {}) => {
    if (screen === 'M1') { setNav(null); return }
    setNav({ screen, mode, params })
  }, [])

  const close = useCallback(() => setNav(null), [])

  return { nav, open, close }
}
