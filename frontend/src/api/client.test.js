import { describe, expect, it, vi } from 'vitest'
import { ApiError, fetchAll, fetchRecent, submitUrl, recheckUrl } from './client'
import { fakeResponse, makeRecord } from '../test/helpers'

function stubFetch(impl) {
  const fn = vi.fn(impl)
  vi.stubGlobal('fetch', fn)
  return fn
}

describe('fetchRecent / fetchAll', () => {
  it('GETs the recent endpoint without credentials', async () => {
    const fn = stubFetch(async () => fakeResponse([makeRecord(1)]))
    const result = await fetchRecent()
    const [url, options] = fn.mock.calls[0]
    expect(url).toMatch(/\/api\/urls\/recent\/$/)
    expect(options.method ?? 'GET').toBe('GET')
    expect(options.credentials).toBe('omit')
    expect(result).toHaveLength(1)
  })

  it('never returns more than 5 recent records, even if the server sends more', async () => {
    stubFetch(async () => fakeResponse([1, 2, 3, 4, 5, 6, 7].map((n) => makeRecord(n))))
    expect(await fetchRecent()).toHaveLength(5)
  })

  it('GETs the all endpoint and returns every record', async () => {
    const fn = stubFetch(async () =>
      fakeResponse([1, 2, 3, 4, 5, 6, 7, 8].map((n) => makeRecord(n))),
    )
    const result = await fetchAll()
    expect(fn.mock.calls[0][0]).toMatch(/\/api\/urls\/all\/$/)
    expect(result).toHaveLength(8)
  })

  it('keeps only known fields (drops anything unexpected)', async () => {
    stubFetch(async () => fakeResponse([{ ...makeRecord(1), url_hash: 'abc', evil: '<x>' }]))
    const [record] = await fetchRecent()
    expect(Object.keys(record).sort()).toEqual([
      'coverage_state',
      'created_at',
      'id',
      'indexing_request_status',
      'inspection_status',
      'last_inspected_at',
      'updated_at',
      'url',
    ])
  })

  it.each([
    ['not an array', { detail: 'hi' }],
    ['item without url', [{ id: 1 }]],
    ['item with non-string url', [{ id: 1, url: 123 }]],
    ['null item', [null]],
  ])('rejects malformed payload: %s', async (_name, payload) => {
    stubFetch(async () => fakeResponse(payload))
    await expect(fetchRecent()).rejects.toMatchObject({ kind: 'server' })
  })
})

describe('submitUrl', () => {
  it('POSTs JSON {url} without credentials', async () => {
    const fn = stubFetch(async () => fakeResponse(makeRecord(1), 201))
    await submitUrl('https://example.com')
    const [url, options] = fn.mock.calls[0]
    expect(url).toMatch(/\/api\/urls\/$/)
    expect(options.method).toBe('POST')
    expect(options.credentials).toBe('omit')
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(options.body)).toEqual({ url: 'https://example.com' })
  })

  it('reports created=true for 201', async () => {
    stubFetch(async () => fakeResponse(makeRecord(1), 201))
    expect(await submitUrl('https://example.com')).toMatchObject({ created: true })
  })

  it('reports created=false for 200 (duplicate)', async () => {
    stubFetch(async () => fakeResponse(makeRecord(1), 200))
    expect(await submitUrl('https://example.com')).toMatchObject({ created: false })
  })

  it('maps 400 to a validation error without echoing server text', async () => {
    stubFetch(async () => fakeResponse({ url: ['<b>server text</b>'] }, 400))
    const error = await submitUrl('https://example.com').catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.kind).toBe('validation')
    expect(error.message).not.toContain('server text')
  })

  it('maps 429 to a throttled error', async () => {
    stubFetch(async () => fakeResponse({ detail: 'Request was throttled.' }, 429))
    await expect(submitUrl('https://example.com')).rejects.toMatchObject({ kind: 'throttled' })
  })

  it('maps 500 to a server error', async () => {
    stubFetch(async () => fakeResponse('<html>boom</html>', 500))
    const error = await submitUrl('https://example.com').catch((e) => e)
    expect(error.kind).toBe('server')
    expect(error.message).not.toContain('boom')
  })

  it('maps a network failure to a network error', async () => {
    stubFetch(async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(submitUrl('https://example.com')).rejects.toMatchObject({ kind: 'network' })
  })

  it('maps an aborted (timed out) request to a network error', async () => {
    stubFetch(async () => {
      const error = new Error('aborted')
      error.name = 'AbortError'
      throw error
    })
    await expect(submitUrl('https://example.com')).rejects.toMatchObject({ kind: 'network' })
  })

  it('treats a non-JSON success body as a server error', async () => {
    stubFetch(async () => ({
      ok: true,
      status: 201,
      json: async () => {
        throw new SyntaxError('bad json')
      },
    }))
    await expect(submitUrl('https://example.com')).rejects.toMatchObject({ kind: 'server' })
  })
})

describe('recheckUrl', () => {
  it('POSTs to the recheck endpoint of that id and returns the clean record', async () => {
    const fn = stubFetch(async () =>
      fakeResponse({ ...makeRecord(7, { inspection_status: 'indexed' }), secret: 'x' }),
    )
    const record = await recheckUrl(7)
    const [url, options] = fn.mock.calls[0]
    expect(url).toMatch(/\/api\/urls\/7\/recheck\/$/)
    expect(options.method).toBe('POST')
    expect(options.credentials).toBe('omit')
    expect(record.inspection_status).toBe('indexed')
    expect(record).not.toHaveProperty('secret')
  })

  it('rejects ids that are not whole numbers (no path tricks)', async () => {
    stubFetch(async () => fakeResponse(makeRecord(1)))
    await expect(recheckUrl('1/../../admin')).rejects.toBeInstanceOf(ApiError)
  })

  it('maps 503 (Google not configured) to a server error', async () => {
    stubFetch(async () => fakeResponse({ detail: 'Google is not configured.' }, 503))
    await expect(recheckUrl(1)).rejects.toMatchObject({ kind: 'server' })
  })
})

describe('Google unavailable (HTTP 503)', () => {
  it('submitUrl gives a fixed, safe message and never the server text', async () => {
    stubFetch(async () => fakeResponse({ detail: 'SECRET-DETAIL auth_error' }, 503))
    const error = await submitUrl('https://example.com').catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.kind).toBe('server')
    expect(error.message).toMatch(/google is not available/i)
    expect(error.message).not.toMatch(/SECRET-DETAIL|auth_error/)
  })
})