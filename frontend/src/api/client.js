const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')
const TIMEOUT_MS = 10000
const RECENT_LIMIT = 5

export class ApiError extends Error {
  constructor(kind, message) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind // 'validation' | 'throttled' | 'network' | 'server'
  }
}

const serverError = () =>
  new ApiError('server', 'The server sent an unexpected response. Please try again later.')

// Server ka text kabhi screen par nahi dikhate; sirf apne fixed messages.
function errorForStatus(status) {
  if (status === 400) {
    return new ApiError(
      'validation',
      'This URL was not accepted. Use a full http:// or https:// address that belongs to your verified Google Search Console site.',
    )
  }
  if (status === 429) {
    return new ApiError('throttled', 'Too many submissions. Please wait a minute and try again.')
  }
    if (status === 503) {
    return new ApiError(
      'server',
      'Google is not available right now (not set up, not authorized, or quota used up). Check the backend setup.',
    )
  }
  return new ApiError('server', `Something went wrong on the server (error ${status}). Please try again later.`)
}

async function request(path, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      credentials: 'omit',
      signal: controller.signal,
      headers: { Accept: 'application/json', ...options.headers },
    })
  } catch (error) {
    if (error && error.name === 'AbortError') {
      throw new ApiError('network', 'The server took too long to respond. Please try again.')
    }
    throw new ApiError('network', 'Could not reach the server. Check that the backend is running.')
  } finally {
    clearTimeout(timer)
  }

  if (!response.ok) throw errorForStatus(response.status)

  try {
    return { status: response.status, data: await response.json() }
  } catch {
    throw serverError()
  }
}

// Sirf jaane-pehchane fields rakho; baaki sab phenk do.
function cleanRecord(raw) {
  if (
    raw === null ||
    typeof raw !== 'object' ||
    typeof raw.url !== 'string' ||
    (typeof raw.id !== 'number' && typeof raw.id !== 'string')
  ) {
    throw serverError()
  }
  return {
    id: raw.id,
    url: raw.url,
    inspection_status: raw.inspection_status,
    indexing_request_status: raw.indexing_request_status,
    coverage_state: typeof raw.coverage_state === 'string' ? raw.coverage_state : '',
    last_inspected_at: typeof raw.last_inspected_at === 'string' ? raw.last_inspected_at : null,
    created_at: raw.created_at,
    updated_at: raw.updated_at,
  }
}

function cleanList(data) {
  if (!Array.isArray(data)) throw serverError()
  return data.map(cleanRecord)
}

export async function fetchRecent() {
  const { data } = await request('/api/urls/recent/')
  return cleanList(data).slice(0, RECENT_LIMIT)
}

export async function fetchAll() {
  const { data } = await request('/api/urls/all/')
  return cleanList(data)
}

export async function submitUrl(url) {
  const { status, data } = await request('/api/urls/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  return { record: cleanRecord(data), created: status === 201 }
}

export async function recheckUrl(id) {
  if (!/^\d+$/.test(String(id))) {
    throw new ApiError('validation', 'Invalid URL id.')
  }
  const { data } = await request(`/api/urls/${id}/recheck/`, { method: 'POST' })
  return cleanRecord(data)
}