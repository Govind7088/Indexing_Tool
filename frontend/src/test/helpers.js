import { vi } from 'vitest'

export function makeRecord(n, overrides = {}) {
  return {
    id: n,
    url: `https://site${n}.example.com`,
    inspection_status: 'not_inspected',
    indexing_request_status: 'not_requested',
    coverage_state: '',
    last_inspected_at: null,
    created_at: '2026-11-05T09:00:00Z',
    updated_at: '2026-11-05T09:00:00Z',
    ...overrides,
  }
}

export function fakeResponse(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}

// routes: { 'GET /api/urls/recent/': (url, options) => fakeResponse(...) }
export function routeFetch(routes) {
  const fn = vi.fn(async (url, options = {}) => {
    const path = new URL(url, 'http://localhost').pathname
    const key = `${(options.method || 'GET').toUpperCase()} ${path}`
    const handler = routes[key]
    if (!handler) throw new Error(`Unexpected request: ${key}`)
    return handler(url, options)
  })
  vi.stubGlobal('fetch', fn)
  return fn
}