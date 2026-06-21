import { useEffect, useRef, useState } from 'react'
import { api } from './api'

/** job 진행률 폴링 훅 (U20). jobId 가 있으면 done/error 까지 1.2초 간격 폴링. */
export function useJob(jobId) {
  const [job, setJob] = useState(null)
  const timer = useRef(null)

  useEffect(() => {
    if (!jobId) { setJob(null); return }
    let alive = true
    const poll = async () => {
      try {
        const j = await api.job(jobId)
        if (!alive) return
        setJob(j)
        if (j.status !== 'done' && j.status !== 'error') {
          timer.current = setTimeout(poll, 1200)
        }
      } catch {
        if (alive) timer.current = setTimeout(poll, 2000)
      }
    }
    poll()
    return () => { alive = false; clearTimeout(timer.current) }
  }, [jobId])

  return job
}
