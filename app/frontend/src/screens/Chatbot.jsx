import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../lib/api'

/**
 * C1 챗봇 (U20). web_design_spec §6.5 질의응답 분기.
 * 메시지 → /chat → answered/needs_research/blocked. 리서치 제안 시 예/아니오 칩.
 * 제한 질문 칩 + 직접 입력. 대상(국가/권역)은 칩 또는 코드 입력으로.
 */
const SUGGESTIONS = [
  { label: '스페인 시장 알려줘', country: 'ES', msg: '스페인 오토파이낸스 시장을 알려줘' },
  { label: '유럽 권역 유망국은?', region: 'EU', msg: '유럽에서 어디가 유망해?' },
  { label: '프랑스 정보 있어?', country: 'FR', msg: '프랑스 시장 정보를 알려줘' },
]

export default function Chatbot({ onResearch }) {
  const { t } = useTranslation()
  const [msgs, setMsgs] = useState([
    { role: 'bot', text: '안녕하세요. 국가·권역 진단을 도와드릴게요. 무엇이 궁금하신가요?' },
  ])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const targetRef = useRef({})  // {country?|region?}
  const scrollRef = useRef(null)

  const push = (m) => setMsgs((p) => [...p, m])
  const scrollDown = () => requestAnimationFrame(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  })

  async function send(text, target) {
    if (!text.trim() || busy) return
    push({ role: 'user', text }); scrollDown()
    setInput(''); setBusy(true)
    const tgt = target || targetRef.current
    targetRef.current = tgt
    try {
      const res = await api.chat(text, tgt)
      handleResponse(res, tgt)
    } catch (e) {
      push({ role: 'bot', text: `오류가 발생했어요: ${e.message}` })
    } finally { setBusy(false); scrollDown() }
  }

  function handleResponse(res, tgt) {
    if (res.status === 'answered') {
      push({ role: 'bot', text: res.answer })
      if (res.low_tier_flags?.length) {
        push({ role: 'note', text: `추정 항목 ${res.low_tier_flags.length}건 — 실사 보류 라벨` })
      }
    } else if (res.status === 'needs_research') {
      push({
        role: 'bot', text: res.message,
        chips: [
          { label: '예, 리서치 진행', action: 'research', code: res.code, region: res.region },
          { label: '아니오', action: 'decline' },
        ],
      })
    } else if (res.status === 'blocked') {
      push({ role: 'bot', text: res.message })
    } else if (res.status === 'needs_target') {
      push({ role: 'bot', text: res.message })
    }
  }

  function onChip(chip) {
    if (chip.action === 'decline') {
      push({ role: 'bot', text: '정보가 있는 대상만 답변이 가능해요. 다른 질문을 해주세요.' }); scrollDown()
    } else if (chip.action === 'research') {
      // 리서치 트리거 → PS2 로 위임(App)
      push({ role: 'bot', text: '외부 리서치를 시작합니다. 진행률을 확인하세요.' }); scrollDown()
      onResearch && onResearch({ code: chip.code, region: chip.region })
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-md overflow-y-auto p-lg">
        {msgs.map((m, i) => <Bubble key={i} m={m} onChip={onChip} />)}
      </div>
      {/* 제한 질문 칩 */}
      <div className="flex flex-wrap gap-sm border-t border-surface-border px-lg py-sm">
        {SUGGESTIONS.map((s, i) => (
          <button key={i} disabled={busy}
            onClick={() => send(s.msg, s.country ? { country: s.country } : { region: s.region })}
            className="rounded-full border border-surface-border bg-surface-light px-md py-xs text-label-md text-on-surface-variant transition-colors hover:border-secondary hover:text-secondary disabled:opacity-50">
            {s.label}
          </button>
        ))}
      </div>
      {/* 입력 */}
      <form onSubmit={(e) => { e.preventDefault(); send(input) }}
        className="flex gap-sm border-t border-surface-border p-md">
        <input value={input} onChange={(e) => setInput(e.target.value)} disabled={busy}
          placeholder={t('chat.placeholder')}
          className="flex-1 rounded border border-surface-border px-md py-sm text-body-sm outline-none focus:border-primary" />
        <button type="submit" disabled={busy || !input.trim()}
          className="rounded bg-primary px-md py-sm text-on-primary disabled:opacity-50">
          <span className="material-symbols-outlined text-[20px]">send</span>
        </button>
      </form>
    </div>
  )
}

function Bubble({ m, onChip }) {
  if (m.role === 'note') {
    return <div className="text-center text-label-sm text-text-disabled">— {m.text} —</div>
  }
  const isUser = m.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] rounded-xl px-md py-sm text-body-sm ${isUser ? 'bg-primary text-on-primary' : 'bg-surface-container text-on-surface'}`}>
        <p className="whitespace-pre-wrap">{m.text}</p>
        {m.chips && (
          <div className="mt-sm flex flex-wrap gap-xs">
            {m.chips.map((c, i) => (
              <button key={i} onClick={() => onChip(c)}
                className="rounded-full bg-secondary px-md py-xs text-label-md text-on-primary transition-transform hover:scale-[0.97]">
                {c.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
