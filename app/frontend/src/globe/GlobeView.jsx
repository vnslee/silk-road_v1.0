import { useEffect, useRef, useState } from 'react'
import { createGlobe } from './globe'
import './globe.css'

/**
 * M1 지구본 + 인트로 (U16). globe.js(vanilla)를 마운트/언마운트만.
 * 딥링크(location.hash) 또는 prefers-reduced-motion 이면 인트로 생략(intro_spec §부트).
 * @param {(api)=>void} onReady  인트로 완료 시 호출(UI 페이드인)
 * @param {Array} countries  마커 카탈로그(API에서 주입). 없으면 모듈 기본값.
 */
export default function Globe({ onReady, countries }) {
  const canvasRef = useRef(null)
  const svgRef = useRef(null)
  const stageRef = useRef(null)
  const apiRef = useRef(null)
  const [introDone, setIntroDone] = useState(false)

  useEffect(() => {
    const deepLink = !!window.location.hash
    let done = false
    const finish = (api) => { if (done) return; done = true; setIntroDone(true); onReady && onReady(api) }
    const api = createGlobe({
      canvas: canvasRef.current,
      svg: svgRef.current,
      stage: stageRef.current,
      countries,
      onIntroDone: () => finish(api),
    })
    apiRef.current = api
    if (deepLink) api.skipIntro()
    else api.runIntro()
    // 안전장치: 인트로 콜백이 안 와도 5.5초 후 강제 완료(오버레이 제거·UI 노출)
    const guard = setTimeout(() => finish(api), 5500)
    return () => { clearTimeout(guard); api.destroy() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div ref={stageRef} className="map-stage">
      <canvas ref={canvasRef} id="globe-canvas" />
      <svg ref={svgRef} id="flat-map" />
      {!introDone && (
        <div className="intro-overlay" aria-hidden="true">
          <div className="intro-logo visible">
            <div className="logo-eyebrow">Hyundai Capital · Internal Analytics</div>
            <div className="logo-title">Where Should We<br />Expand <em>Next?</em></div>
            <div className="logo-tagline">Global Auto Finance Market Diagnostics</div>
          </div>
        </div>
      )}
    </div>
  )
}
