// 백엔드 API 호출 래퍼. dev 에서는 vite 프록시(/api → :8000), prod 는 동일 출처.
const BASE = '/api/v1'

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export const api = {
  health: () => req('/../../health'),
  countries: () => req('/countries'),
  country: (code) => req(`/countries/${code}`),
  regions: () => req('/regions'),
  region: (id) => req(`/regions/${id}`),
  reports: (kind, code) => req(`/reports/${kind}/${code}`),
  report: (kind, code, id) => req(`/reports/${kind}/${code}/${id}`),
  reportHtmlUrl: (kind, code, id) => `${BASE}/reports/${kind}/${code}/${id}/html`,
  reportPdfUrl: (kind, code, id) => `${BASE}/reports/${kind}/${code}/${id}/pdf`,
  generateReport: (kind, code) => req(`/reports/${kind}/${code}`, { method: 'POST' }),
  job: (jobId) => req(`/jobs/${jobId}`),
  chat: (message, target = {}) =>
    req('/chat', { method: 'POST', body: JSON.stringify({ message, ...target }) }),
  research: (country, code, region) =>
    req('/chat/research', { method: 'POST', body: JSON.stringify({ country, code, region }) }),
  ruleset: () => req('/ruleset'),
  saveWeights: (category_weights) =>
    req('/ruleset/weights', { method: 'PUT', body: JSON.stringify({ category_weights }) }),
}
