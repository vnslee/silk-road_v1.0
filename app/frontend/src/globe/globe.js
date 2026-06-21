/**
 * M1 지구본 + 시네마틱 인트로 (U16).
 *
 * intro_spec.md 권장 패턴: vanilla 모듈로 캡슐화, React 가 마운트만.
 * stitch mockup(M1_intro.html)의 three.js 프로시저럴 지구 + D3 평면지도 전환을 이식.
 * CDN 전역 대신 npm import 사용. 공개 API: createGlobe(opts) → { runIntro, skipIntro, destroy }.
 */
import * as THREE from 'three'
import * as d3 from 'd3'
import { feature } from 'topojson-client'

const TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'
const ISO_NUM = { UK: 826, GB: 826, DE: 276, ES: 724, PL: 616, BR: 76, IN: 356, KR: 410 }
const HQ = { name: 'SEOUL HQ', lonlat: [126.978, 37.5665] }

const DEFAULT_CATALOG = [
  { code: 'UK', country_ko: '영국', capital: [-0.1276, 51.5074], is_baseline: true, region: 'EU' },
  { code: 'DE', country_ko: '독일', capital: [13.405, 52.52], is_baseline: false, region: 'EU' },
  { code: 'ES', country_ko: '스페인', capital: [-3.7038, 40.4168], is_baseline: false, region: 'EU' },
  { code: 'PL', country_ko: '폴란드', capital: [21.0122, 52.2297], is_baseline: false, region: 'EU' },
  { code: 'BR', country_ko: '브라질', capital: [-47.8825, -15.794], is_baseline: false, region: 'LATAM' },
  { code: 'IN', country_ko: '인도', capital: [77.209, 28.614], is_baseline: false, region: 'APAC' },
]

const easeOut = (t) => 1 - (1 - t) * (1 - t) * (1 - t)

/**
 * WebGL 불가 환경 폴백: 3D 지구본 없이 D3 평면지도만 렌더.
 * createGlobe 와 동일한 공개 API({runIntro, skipIntro, destroy})를 반환.
 */
function _flatOnlyFallback(opts) {
  const { canvas, svg, stage, onIntroDone } = opts
  const CATALOG = opts.countries || DEFAULT_CATALOG
  let disposed = false
  if (canvas) canvas.style.display = 'none'

  let W = innerWidth, H = innerHeight, proj, pathFn, LAND = [], ready = false
  const p = d3.json(TOPO_URL).then((topo) => {
    if (disposed) return
    W = stage.clientWidth || innerWidth
    H = stage.clientHeight || (innerHeight - 56)
    proj = d3.geoNaturalEarth1().scale(W / 5.4).translate([W / 2, H * 0.46]).precision(0.4)
    pathFn = d3.geoPath(proj)
    LAND = feature(topo, topo.objects.countries).features
    ready = true
    _renderFlat({ svg, CATALOG, W, H, proj, pathFn, LAND })
    svg.style.opacity = '1'
    svg.style.pointerEvents = 'auto'
    if (onIntroDone) onIntroDone()
  })
  return {
    runIntro: () => p,
    skipIntro: () => p,
    destroy: () => { disposed = true },
  }
}

/** 평면 SVG 렌더(폴백·정상 경로 공용 코어). */
function _renderFlat({ svg, CATALOG, W, H, proj, pathFn, LAND }) {
  const sel = d3.select(svg).attr('viewBox', `0 0 ${W} ${H}`)
  sel.selectAll('*').remove()
  const defs = sel.append('defs')
  const og = defs.append('radialGradient').attr('id', 'fm-ocean')
    .attr('cx', '38%').attr('cy', '32%').attr('r', '78%')
  ;[['0%', '#fff'], ['32%', '#eef3ff'], ['62%', '#c2d8fb'], ['86%', '#7aa6ec'], ['100%', '#2F79D9']]
    .forEach((s) => og.append('stop').attr('offset', s[0]).attr('stop-color', s[1]))
  sel.append('rect').attr('width', W).attr('height', H).attr('fill', 'url(#fm-ocean)')
  sel.append('path').attr('class', 'graticule').attr('d', pathFn(d3.geoGraticule10()))
  const activeIds = new Set(CATALOG.filter((d) => d.is_baseline).map((d) => ISO_NUM[d.code]))
  sel.append('g').selectAll('path').data(LAND).enter().append('path')
    .attr('class', 'country-land')
    .classed('region-active', (d) => activeIds.has(d.id))
    .attr('d', pathFn)
  const mkG = sel.append('g')
  CATALOG.map((d) => ({ ...d, xy: proj(d.capital) })).forEach((d) => {
    if (!d.xy) return
    const g = mkG.append('g').attr('transform', `translate(${d.xy[0]},${d.xy[1]})`)
    g.append('circle').attr('r', d.is_baseline ? 6 : 6)
      .attr('fill', d.is_baseline ? '#2F79D9' : '#fff')
      .attr('stroke', '#2F79D9').attr('stroke-width', d.is_baseline ? 0 : 1.5)
    g.append('text').attr('class', 'mk-label').attr('y', -15)
      .attr('text-anchor', 'middle').style('opacity', 1).text(d.country_ko)
  })
}

/**
 * @param {object} opts
 *   canvas: WebGL 캔버스, svg: 평면지도 SVG, stage: 컨테이너 div
 *   countries: 마커 카탈로그(없으면 DEFAULT_CATALOG)
 *   reducedMotion: true 면 인트로 생략하고 바로 평면
 *   onIntroDone: 인트로 완료 콜백(UI 페이드인용)
 */
export function createGlobe(opts) {
  const { canvas, svg, stage, onIntroDone } = opts
  const CATALOG = opts.countries || DEFAULT_CATALOG
  const reducedMotion = opts.reducedMotion ||
    (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)

  let disposed = false
  const timers = []
  const setT = (fn, ms) => { const id = setTimeout(fn, ms); timers.push(id); return id }

  // ── THREE.js (WebGL 미지원 환경 graceful 폴백) ──
  let renderer
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true })
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    renderer.setSize(innerWidth, innerHeight)
    renderer.setClearColor(0x04080f, 1)
  } catch (e) {
    // WebGL 불가(헤드리스·비활성 브라우저) → 3D 인트로 생략, 평면지도만.
    return _flatOnlyFallback(opts)
  }

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 200)

  // 별
  ;(function () {
    const n = 5500, arr = new Float32Array(n * 3)
    for (let i = 0; i < n * 3; i++) arr[i] = (Math.random() - 0.5) * 160
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(arr, 3))
    scene.add(new THREE.Points(geo, new THREE.PointsMaterial({
      color: 0xffffff, size: 0.14, sizeAttenuation: true, transparent: true, opacity: 0.8,
    })))
  })()

  const earthVert = `
    varying vec3 vNormal; varying vec2 vUv; varying vec3 vViewPos;
    void main(){ vNormal=normalize(normalMatrix*normal); vUv=uv;
      vViewPos=-(modelViewMatrix*vec4(position,1.0)).xyz;
      gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`
  const earthFrag = `
    varying vec3 vNormal; varying vec2 vUv; varying vec3 vViewPos;
    uniform float uTime; uniform vec3 uSunDir;
    float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    float noise(vec2 p){vec2 i=floor(p),f=fract(p);vec2 u=f*f*(3.0-2.0*f);
      return mix(mix(hash(i),hash(i+vec2(1,0)),u.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),u.x),u.y);}
    float fbm(vec2 p){float v=0.0,a=0.5;for(int i=0;i<5;i++){v+=a*noise(p);p*=2.1;a*=0.5;}return v;}
    void main(){
      vec3 n=normalize(vNormal); vec3 sun=normalize(uSunDir); float NdotL=dot(n,sun);
      vec2 uvScaled=vec2(vUv.x*4.5,vUv.y*2.8);
      float landMask=clamp(fbm(uvScaled+vec2(0.3,0.7))*1.4-0.45,0.0,1.0);
      float polar=smoothstep(0.7,0.95,abs(vUv.y-0.5)*2.0);
      landMask=mix(landMask,0.0,polar*0.7);
      vec3 deepOcean=vec3(0.02,0.09,0.28),shallowOcean=vec3(0.04,0.18,0.48);
      vec3 land1=vec3(0.10,0.28,0.10),land2=vec3(0.17,0.40,0.12);
      vec3 sand=vec3(0.60,0.52,0.30),snow=vec3(0.88,0.92,0.96),nightGlow=vec3(0.55,0.40,0.08);
      float oceanDepth=fbm(uvScaled*0.7+vec2(1.2,0.4));
      vec3 oceanCol=mix(deepOcean,shallowOcean,oceanDepth*0.8);
      float elevation=fbm(uvScaled*1.4+vec2(2.1,1.3));
      vec3 landCol=mix(land1,land2,elevation);
      landCol=mix(landCol,sand,smoothstep(0.5,0.75,elevation)*(1.0-polar));
      landCol=mix(landCol,snow,polar+smoothstep(0.85,1.0,elevation)*0.5);
      vec3 dayCol=mix(oceanCol,landCol,landMask);
      float cityNoise=fbm(uvScaled*2.2+vec2(3.3,1.1))*(1.0-polar*0.8);
      float cityGlow=pow(clamp(cityNoise-0.35,0.0,1.0)*landMask,1.5)*2.2;
      vec3 nightCol=deepOcean*0.25+nightGlow*cityGlow;
      float dayFactor=smoothstep(-0.3,0.35,NdotL);
      vec3 col=mix(nightCol,dayCol,dayFactor);
      col*=0.35+0.75*max(NdotL,0.0);
      float seaMask=1.0-landMask; vec3 viewDir=normalize(vViewPos);
      vec3 halfVec=normalize(sun+viewDir);
      col+=pow(max(dot(n,halfVec),0.0),80.0)*seaMask*0.6*vec3(0.7,0.85,1.0);
      float rim=1.0-max(dot(normalize(vViewPos),n),0.0);
      col*=1.0-rim*rim*0.4;
      gl_FragColor=vec4(col,1.0);
    }`
  const atmVert = `varying vec3 vNormal; void main(){vNormal=normalize(normalMatrix*normal);
    gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`
  const atmFrag = `varying vec3 vNormal; void main(){
    float i=pow(0.68-dot(vNormal,vec3(0,0,1)),4.2);
    gl_FragColor=vec4(0.12,0.50,1.0,1.0)*i*2.5;}`

  const earthGroup = new THREE.Group()
  scene.add(earthGroup)
  earthGroup.position.y = -0.6

  const earthUniforms = { uTime: { value: 0 }, uSunDir: { value: new THREE.Vector3(4, 2, 5).normalize() } }
  const earthMesh = new THREE.Mesh(
    new THREE.SphereGeometry(1, 80, 80),
    new THREE.ShaderMaterial({ uniforms: earthUniforms, vertexShader: earthVert, fragmentShader: earthFrag }),
  )
  earthGroup.add(earthMesh)
  const atmMesh = new THREE.Mesh(
    new THREE.SphereGeometry(1.09, 64, 64),
    new THREE.ShaderMaterial({
      vertexShader: atmVert, fragmentShader: atmFrag,
      blending: THREE.AdditiveBlending, side: THREE.BackSide, transparent: true, depthWrite: false,
    }),
  )
  earthGroup.add(atmMesh)

  const CAM_FROM = new THREE.Vector3(0, 2.0, 5.8), CAM_TO = new THREE.Vector3(0, 1.4, 4.2)
  const LOOK_FROM = new THREE.Vector3(0, -0.8, 0), LOOK_TO = new THREE.Vector3(0, -0.4, 0)
  camera.position.copy(CAM_FROM)

  let camT = 0, camDone = false, autoRotate = true, lastT = 0
  renderer.setAnimationLoop((t) => {
    if (disposed) return
    const dt = Math.min((t - lastT) / 1000, 0.05); lastT = t
    earthUniforms.uTime.value = t * 0.001
    if (!camDone) {
      camT = Math.min(camT + dt * 0.32, 1)
      const e = easeOut(camT)
      camera.position.lerpVectors(CAM_FROM, CAM_TO, e)
      camera.lookAt(new THREE.Vector3().lerpVectors(LOOK_FROM, LOOK_TO, e))
      if (camT >= 1) { camDone = true; camera.lookAt(0, -0.4, 0) }
    }
    if (autoRotate) earthGroup.rotation.y += dt * 0.085
    renderer.render(scene, camera)
  })

  // ── D3 평면지도 ──
  let LAND = [], flatReady = false, proj, pathFn
  let W = innerWidth, H = innerHeight
  d3.json(TOPO_URL).then((topo) => {
    if (disposed) return
    W = stage.clientWidth || innerWidth
    H = stage.clientHeight || (innerHeight - 56)
    proj = d3.geoNaturalEarth1().scale(W / 5.4).translate([W / 2, H * 0.46]).precision(0.4)
    pathFn = d3.geoPath(proj)
    LAND = feature(topo, topo.objects.countries).features
    flatReady = true
  })

  function buildFlatSVG() {
    const sel = d3.select(svg).attr('viewBox', `0 0 ${W} ${H}`)
    sel.selectAll('*').remove()
    const defs = sel.append('defs')
    const og = defs.append('radialGradient').attr('id', 'fm-ocean')
      .attr('cx', '38%').attr('cy', '32%').attr('r', '78%')
    ;[['0%', '#fff'], ['32%', '#eef3ff'], ['62%', '#c2d8fb'], ['86%', '#7aa6ec'], ['100%', '#2F79D9']]
      .forEach((s) => og.append('stop').attr('offset', s[0]).attr('stop-color', s[1]))
    const mf = defs.append('filter').attr('id', 'mkGlow')
      .attr('x', '-60%').attr('y', '-60%').attr('width', '220%').attr('height', '220%')
    mf.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'b')
    const fm2 = mf.append('feMerge'); fm2.append('feMergeNode').attr('in', 'b'); fm2.append('feMergeNode').attr('in', 'SourceGraphic')

    sel.append('rect').attr('width', W).attr('height', H).attr('fill', 'url(#fm-ocean)')
    sel.append('path').attr('class', 'graticule').attr('d', pathFn(d3.geoGraticule10()))

    const activeIds = new Set(CATALOG.filter((d) => d.is_baseline).map((d) => ISO_NUM[d.code]))
    sel.append('g').selectAll('path').data(LAND).enter().append('path')
      .attr('class', 'country-land')
      .classed('region-active', (d) => activeIds.has(d.id))
      .attr('d', pathFn)

    const arcG = sel.append('g').attr('id', 'arc-layer')
    CATALOG.forEach((d) => {
      const line = { type: 'LineString', coordinates: [HQ.lonlat, d.capital] }
      const arcPath = arcG.append('path')
        .attr('class', 'arc ' + (d.is_baseline ? 'base' : 'cand'))
        .attr('d', pathFn(line)).attr('id', 'arc-' + d.code).style('opacity', 0)
      const node = arcPath.node(); const len = node ? node.getTotalLength() : 300
      arcPath.style('stroke-dasharray', len).style('stroke-dashoffset', len)
    })

    const mkG = sel.append('g').attr('id', 'marker-layer')
    const all = CATALOG.map((d) => ({ ...d, xy: proj(d.capital) }))
    all.push({ code: 'HQ', country_ko: HQ.name, capital: HQ.lonlat, is_hq: true, xy: proj(HQ.lonlat) })
    all.forEach((d) => {
      if (!d.xy) return
      const g = mkG.append('g').attr('class', 'mk').attr('id', 'mk-' + d.code)
        .attr('transform', `translate(${d.xy[0]},${d.xy[1]})`)
      if (d.is_hq || d.is_baseline) g.append('circle').attr('class', 'pulse')
      g.append('circle').attr('r', 12).attr('fill', 'none').attr('stroke', '#2F79D9')
        .attr('stroke-opacity', 0.3).attr('filter', 'url(#mkGlow)')
      g.append('circle').attr('r', d.is_hq ? 7 : 6)
        .attr('fill', (d.is_hq || d.is_baseline) ? '#2F79D9' : '#fff')
        .attr('stroke', '#2F79D9').attr('stroke-width', (d.is_hq || d.is_baseline) ? 0 : 1.5)
      g.append('text').attr('class', 'mk-label').attr('x', 0).attr('y', -15)
        .attr('text-anchor', 'middle').text(d.is_hq ? 'SEOUL HQ' : d.country_ko)
    })
  }

  function animateMarkers() {
    const order = ['HQ'].concat(CATALOG.map((d) => d.code))
    order.forEach((code, i) => {
      const delay = 150 + i * 240
      setT(() => {
        const mk = document.getElementById('mk-' + code)
        if (!mk) return
        mk.style.animation = 'markerDrop 0.55s cubic-bezier(.34,1.56,.64,1) forwards'
        setT(() => { const lbl = mk.querySelector('.mk-label'); if (lbl) lbl.style.animation = 'labelFade 0.4s ease forwards' }, 320)
      }, delay)
      if (code !== 'HQ') {
        setT(() => {
          const arc = document.getElementById('arc-' + code)
          if (!arc) return
          arc.style.opacity = '1'
          arc.style.transition = 'stroke-dashoffset 1s cubic-bezier(.4,0,.2,1)'
          arc.style.strokeDashoffset = '0'
        }, delay + 80)
      }
    })
  }

  function transitionToFlat() {
    if (disposed) return
    if (!flatReady) { setT(transitionToFlat, 200); return }
    buildFlatSVG()
    const dur = 1800, t0 = performance.now()
    ;(function fade() {
      if (disposed) return
      const p = easeOut(Math.min((performance.now() - t0) / dur, 1))
      earthGroup.children.forEach((m) => {
        if (!m.material) return
        m.material.transparent = true
        m.material.opacity = Math.max(0, 1 - p)
      })
      if (p < 1) requestAnimationFrame(fade)
      else { autoRotate = false; canvas.style.transition = 'opacity .8s'; canvas.style.opacity = '0' }
    })()
    setT(() => {
      svg.style.transition = 'opacity 1.1s ease'
      svg.style.opacity = '1'; svg.style.pointerEvents = 'auto'
      animateMarkers()
    }, 700)
  }

  // ── 공개 API ──
  function runIntro() {
    if (reducedMotion) { skipIntro(); return }
    setT(transitionToFlat, 3000)
    setT(() => { if (onIntroDone) onIntroDone() }, 4800)
  }

  function skipIntro() {
    // 딥링크/reduced-motion: 카메라·자전 건너뛰고 바로 평면지도
    camDone = true; autoRotate = false
    const tryFlat = () => {
      if (disposed) return
      if (!flatReady) { setT(tryFlat, 150); return }
      buildFlatSVG()
      canvas.style.opacity = '0'
      svg.style.opacity = '1'; svg.style.pointerEvents = 'auto'
      animateMarkers()
      if (onIntroDone) onIntroDone()
    }
    tryFlat()
  }

  function onResize() {
    camera.aspect = innerWidth / innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(innerWidth, innerHeight)
  }
  window.addEventListener('resize', onResize)

  function destroy() {
    disposed = true
    timers.forEach(clearTimeout)
    window.removeEventListener('resize', onResize)
    renderer.setAnimationLoop(null)
    renderer.dispose()
    scene.traverse((o) => {
      if (o.geometry) o.geometry.dispose()
      if (o.material) { (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose()) }
    })
  }

  return { runIntro, skipIntro, destroy }
}
