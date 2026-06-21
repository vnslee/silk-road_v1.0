import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Globe from './globe/GlobeView'
import MenuDropdown from './shell/MenuDropdown'
import Modal from './shell/Modal'
import Placeholder from './screens/Placeholder'
import CountryInfo from './screens/CountryInfo'
import RegionInfo from './screens/RegionInfo'
import Report from './screens/Report'
import Chatbot from './screens/Chatbot'
import Progress from './screens/Progress'
import Settings from './screens/Settings'
import { useNavigation } from './shell/useNavigation'
import { api } from './lib/api'

// 공통 셸 + 전 화면 연결(U17~U20).
export default function App() {
  const { t, i18n } = useTranslation()
  // 딥링크로 바로 화면 진입 시엔 인트로 없이 UI 즉시 노출.
  const [uiVisible, setUiVisible] = useState(!!window.location.hash)
  const [notifyOpen, setNotifyOpen] = useState(true)  // 시작 안내 패널(지도 클릭 시 치움)
  const [job, setJob] = useState(null)   // {jobId, kind, code} — PS2 진행 중인 작업
  const { nav, open, close } = useNavigation()
  const toggleLang = () => i18n.changeLanguage(i18n.language === 'ko' ? 'en' : 'ko')

  // 안전장치: 인트로 onReady 가 (WebGL 실패 등으로) 안 불려도 4초 후엔 UI 노출.
  useEffect(() => {
    const t = setTimeout(() => setUiVisible(true), 4000)
    return () => clearTimeout(t)
  }, [])

  const popupOpen = nav && nav.mode === 'popup'

  // 보고서 생성 트리거 → PS2
  async function generateReport(kind, code, mode = 'popup') {
    try {
      const { job_id } = await api.generateReport(kind, code)
      setJob({ jobId: job_id, kind, code })
      open('PS2', { mode, params: { code } })
    } catch (e) { alert('생성 실패: ' + e.message) }
  }
  // 챗봇 리서치 트리거 → PS2(리서치 job)
  // 국가 리서치 트리거 → PS2 진행률 (§6.5.1). code 문자열 또는 {code,region}.
  async function triggerResearch(arg) {
    const code = (typeof arg === 'string' ? arg : arg?.code || '').toUpperCase()
    const region = (typeof arg === 'object' && arg?.region) || 'EU'
    if (!code) return
    try {
      const { job_id } = await api.research(code, code, region)
      setJob({ jobId: job_id, kind: 'country', code, purpose: 'research' })
      open('PS2', { mode: 'popup', params: { code } })
    } catch (e) { alert('리서치 실패: ' + e.message) }
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-surface text-on-surface">
      <header className="z-30 flex shrink-0 items-center justify-between border-b border-surface-border bg-surface-container-lowest/95 px-lg py-md backdrop-blur">
        {/* 경로 C: 메뉴 → 풀사이즈 진입 */}
        <MenuDropdown onSelect={(screen) => open(screen, { mode: 'fullsize' })} />
        <div className="flex flex-col items-center">
          <img src="/brand/logo_hc.png" alt="Hyundai Capital" className="h-7 w-auto" />
          <p className="mt-0.5 text-label-sm text-text-secondary">{t('app.subtitle')}</p>
        </div>
        <div className="flex items-center gap-sm">
          <button onClick={toggleLang}
            className="rounded border border-primary px-md py-xs text-label-md text-primary transition-colors hover:bg-surface-light">
            {t('lang.toggle')}
          </button>
          <button onClick={() => open('PS1', { mode: 'fullsize' })} className="text-on-surface-variant transition-colors hover:text-primary" aria-label="settings">
            <span className="material-symbols-outlined">settings</span>
          </button>
        </div>
      </header>

      <div className="relative flex flex-1 flex-col">
        {/* 지도: 팝업 떠 있으면 반투명(§M1) */}
        <div className={`flex flex-1 flex-col transition-opacity ${popupOpen ? 'opacity-40' : 'opacity-100'}`}>
          <Globe onReady={() => setUiVisible(true)}
            onSelectCountry={(c) => { setNotifyOpen(false); open('P1', { mode: 'popup', params: { code: c } }) }}
            onSelectRegion={(r) => { setNotifyOpen(false); open('P2', { mode: 'popup', params: { code: r } }) }} />
        </div>

        {/* 인트로 완료 후 오버레이(범례·노티·챗봇 위젯) */}
        <div className={`pointer-events-none absolute inset-0 z-10 transition-opacity duration-700 ${uiVisible && !nav ? 'opacity-100' : 'opacity-0'}`}>
          <div className="pointer-events-auto absolute right-lg top-lg w-[220px] rounded-md border border-surface-border bg-surface-light p-md shadow-[0_4px_12px_rgba(0,32,78,0.08)]">
            <h3 className="mb-sm text-label-md uppercase text-text-secondary">Market Overview</h3>
            <div className="my-xs flex items-center gap-sm text-body-sm">
              <span className="inline-block h-3 w-3 rounded-full bg-secondary" /> {t('legend.entered')}
            </div>
            <div className="my-xs flex items-center gap-sm text-body-sm">
              <span className="inline-block h-3 w-3 rounded-full border-2 border-dashed border-primary-container" /> {t('legend.candidate')}
            </div>
          </div>
          {/* 시작 안내 패널 (web_design_spec Notification) — 중앙 상단, 명확한 진입 버튼.
              지도 마커를 가리므로 닫기 가능 + 지도 클릭 시 자동으로 사라짐. */}
          {notifyOpen && (
          <div className="pointer-events-auto absolute left-1/2 top-sm flex max-w-[92%] -translate-x-1/2 items-center gap-md rounded-full border border-surface-border bg-surface-container-lowest/95 py-xs pl-lg pr-sm shadow-[0_8px_20px_rgba(0,32,78,0.12)] backdrop-blur">
            <span className="material-symbols-outlined shrink-0 text-[20px] text-primary">touch_app</span>
            <p className="truncate text-body-sm text-on-surface">{t('notify.intro')}</p>
            <button onClick={() => setNotifyOpen(false)}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-surface-light"
              aria-label="닫기">
              <span className="material-symbols-outlined text-[18px]">close</span>
            </button>
          </div>
          )}

          {/* 챗봇 위젯(좌하단, 상시) */}
          <button
            onClick={() => open('C1', { mode: 'popup' })}
            className="pointer-events-auto absolute bottom-lg left-lg flex h-14 w-14 items-center justify-center rounded-full bg-primary text-on-primary shadow-[0_12px_24px_rgba(0,32,78,0.2)] transition-transform hover:scale-105"
            aria-label="chatbot"
          >
            <span className="material-symbols-outlined">smart_toy</span>
          </button>
        </div>

        {/* 화면 모달 (팝업/풀사이즈) */}
        {nav && (
          <Modal
            mode={nav.mode}
            size={nav.screen === 'C1' ? 'chat' : 'default'}
            onClose={close}
            title={nav.screen}
            chrome={!['P1', 'P2', 'PR1', 'PR2', 'C1', 'PS1'].includes(nav.screen)}
          >
            {renderScreen()}
          </Modal>
        )}
      </div>
    </div>
  )

  // 화면 디스패치 (App 내부 — job/generate 등 상태 접근).
  function renderScreen() {
    const { screen, params, mode } = nav
    const code = params?.code
    switch (screen) {
      case 'P1':
        return <CountryInfo code={code || 'ES'}
          onReport={(c) => open('PR1', { mode, params: { code: c } })}
          onGenerate={(c) => generateReport('country', c, mode)}
          onResearch={triggerResearch} />
      case 'P2':
        return <RegionInfo code={code || 'EU'}
          onReport={(c) => open('PR2', { mode, params: { code: c } })}
          onGenerate={(c) => generateReport('region', c, mode)} />
      case 'PR1':
        return <Report kind="country" code={code || 'ES'} onClose={close} />
      case 'PR2':
        return <Report kind="region" code={code || 'EU'} onClose={close} />
      case 'C1':
        return <Chatbot onResearch={triggerResearch} />
      case 'PS2':
        return <Progress jobId={job?.jobId}
          purpose={job?.purpose}
          onViewReport={() => {
            if (!job) return
            // 리서치 완료 → 국가 정보(P1)로, 보고서 생성 완료 → 보고서(PR1/PR2)로
            if (job.purpose === 'research') open('P1', { mode: 'popup', params: { code: job.code } })
            else open(job.kind === 'country' ? 'PR1' : 'PR2', { mode, params: { code: job.code } })
          }} />
      case 'PS1':
        return <Settings />
      default:
        return <Placeholder screen={screen} params={params} mode={mode} />
    }
  }
}
