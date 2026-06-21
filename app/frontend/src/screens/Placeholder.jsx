/** 화면 자리표시 (U17). 실제 콘텐츠는 U18~U21 에서 구현. */
const LABELS = {
  C1: '챗봇', P1: '국가 정보', P2: '권역 정보',
  PR1: '국가 진단 보고서', PR2: '권역 진단 보고서',
  PS1: '룰셋 설정', PS2: '프로그레스',
}

export default function Placeholder({ screen, params, mode }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-sm text-center">
      <span className="material-symbols-outlined text-[48px] text-outline-variant">construction</span>
      <p className="text-headline-md text-primary">{LABELS[screen] || screen}</p>
      <p className="text-body-sm text-text-secondary">
        {screen} · {mode}{params?.code ? ` · ${params.code}` : ''}
      </p>
      <p className="text-label-sm text-text-disabled">이 화면은 다음 단위(U18~)에서 구현됩니다.</p>
    </div>
  )
}
