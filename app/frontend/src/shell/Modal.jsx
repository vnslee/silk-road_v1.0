/**
 * 화면 진입 컨테이너 (U17). web_design_spec §5.1 두 모드.
 *  popup    : 좌우·상하 여백을 둔 오버레이(지도 반투명 위), 우상단 닫기.
 *  fullsize : 전체 화면 점유(상단바 아래), 닫기=메뉴/뒤로.
 * 콘텐츠 구성은 동일, 셸만 다름.
 *
 * C1(챗봇)·PS2(프로그레스)는 별도 위치 규칙이 있어 size='chat' 등으로 조정.
 */
export default function Modal({ mode = 'popup', size = 'default', onClose, title, chrome = true, children }) {
  if (mode === 'fullsize') {
    return (
      <section className="absolute inset-0 z-20 flex flex-col overflow-hidden bg-surface">
        {children}
      </section>
    )
  }

  // chrome=false: 화면이 자체 헤더를 가짐 → 모달 타이틀바 없이 카드만.
  if (!chrome) {
    const inset = size === 'chat' ? 'inset-x-[25%] inset-y-[25%]' : 'inset-x-[20%] inset-y-[20%]'
    return (
      <div className="absolute inset-0 z-20">
        <div className="absolute inset-0 bg-primary/20 backdrop-blur-[2px]" onClick={onClose} />
        <div className={`absolute ${inset} overflow-hidden rounded-xl border border-surface-border bg-surface-container-lowest shadow-[0_24px_48px_rgba(0,32,78,0.24)]`}>
          <button onClick={onClose} className="absolute right-md top-md z-10 text-on-surface-variant transition-colors hover:text-primary" aria-label="close">
            <span className="material-symbols-outlined">close</span>
          </button>
          {children}
        </div>
      </div>
    )
  }

  // popup: 배경 딤(지도 반투명) + 중앙 카드
  const inset = size === 'chat'
    ? 'inset-x-[25%] inset-y-[25%]'      // C1: 좌우·상하 50% 제외 → 25% inset
    : 'inset-x-[20%] inset-y-[20%]'      // P/PR/PS: 20% 제외

  return (
    <div className="absolute inset-0 z-20">
      <div className="absolute inset-0 bg-primary/20 backdrop-blur-[2px]" onClick={onClose} />
      <div className={`absolute ${inset} flex flex-col overflow-hidden rounded-xl border border-surface-border bg-surface-container-lowest shadow-[0_24px_48px_rgba(0,32,78,0.24)]`}>
        <header className="flex shrink-0 items-center justify-between border-b border-surface-border px-lg py-md">
          <h2 className="text-headline-md text-primary">{title}</h2>
          <button onClick={onClose} className="text-on-surface-variant transition-colors hover:text-primary" aria-label="close">
            <span className="material-symbols-outlined">close</span>
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-lg">{children}</div>
      </div>
    </div>
  )
}
