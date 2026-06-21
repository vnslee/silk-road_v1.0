import { useEffect, useState } from 'react'

/** 데이터 페치 훅. fn 은 api.* 호출을 반환. deps 변경 시 재요청. */
export function useApi(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null })
  useEffect(() => {
    let alive = true
    setState({ data: null, loading: true, error: null })
    Promise.resolve(fn())
      .then((data) => { if (alive) setState({ data, loading: false, error: null }) })
      .catch((e) => { if (alive) setState({ data: null, loading: false, error: e.message }) })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

/** ISO alpha-2 → 국기 이모지 (regional indicator). UK→GB 보정. */
export function flagEmoji(code) {
  if (!code) return '🏳️'
  const cc = code.toUpperCase() === 'UK' ? 'GB' : code.toUpperCase()
  if (cc.length !== 2) return '🏳️'
  return String.fromCodePoint(...[...cc].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65))
}
