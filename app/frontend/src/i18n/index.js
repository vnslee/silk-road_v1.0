import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// E2: 한/영 전체 번역 대비 프레임. U15 는 UI 라벨만 — 화면별 키는 이후 단위에서 추가.
const resources = {
  ko: {
    translation: {
      'app.title': 'Hyundai Capital',
      'app.subtitle': '글로벌 오토파이낸스 진출 진단',
      'nav.status': '진출현황',
      'nav.country': '국가',
      'nav.region': '권역',
      'nav.report': '보고서',
      'nav.settings': '설정',
      'lang.toggle': 'EN',
      'notify.intro': '챗봇을 통해 질문을 하시거나 지도의 권역이나 국가를 선택하여 상세 정보를 확인할 수 있습니다.',
      'legend.entered': '진출국가',
      'legend.candidate': '진출예정국가',
      'chat.placeholder': '질문을 입력하세요',
    },
  },
  en: {
    translation: {
      'app.title': 'Hyundai Capital',
      'app.subtitle': 'Global Auto Finance Market Entry Diagnostics',
      'nav.status': 'Overview',
      'nav.country': 'Country',
      'nav.region': 'Region',
      'nav.report': 'Reports',
      'nav.settings': 'Settings',
      'lang.toggle': '한',
      'notify.intro': 'Ask the chatbot a question, or select a region or country on the map to view details.',
      'legend.entered': 'Entered',
      'legend.candidate': 'Candidate',
      'chat.placeholder': 'Type your question',
    },
  },
}

i18n.use(initReactI18next).init({
  resources,
  lng: 'ko',
  fallbackLng: 'ko',
  interpolation: { escapeValue: false },
})

export default i18n
