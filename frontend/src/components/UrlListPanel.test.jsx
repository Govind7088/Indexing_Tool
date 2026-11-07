import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import UrlListPanel from './UrlListPanel'
import { fakeResponse, makeRecord, routeFetch } from '../test/helpers'

const many = (count) => Array.from({ length: count }, (_, i) => makeRecord(i + 1))

describe('UrlListPanel (recent mode)', () => {
  it('shows a loading state first', async () => {
    routeFetch({ 'GET /api/urls/recent/': () => new Promise(() => {}) })
    render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    expect(screen.getByRole('status')).toHaveTextContent(/loading/i)
  })

  it('shows at most 5 URLs', async () => {
    routeFetch({ 'GET /api/urls/recent/': async () => fakeResponse(many(7)) })
    render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    const items = await screen.findAllByRole('listitem')
    expect(items).toHaveLength(5)
  })

  it('shows an empty state', async () => {
    routeFetch({ 'GET /api/urls/recent/': async () => fakeResponse([]) })
    render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    expect(await screen.findByText(/no urls saved yet/i)).toBeInTheDocument()
  })

  it('shows the real status values, not fake success', async () => {
    routeFetch({ 'GET /api/urls/recent/': async () => fakeResponse([makeRecord(1)]) })
    render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    const item = await screen.findByRole('listitem')
    expect(within(item).getByText(/inspection: not inspected/i)).toBeInTheDocument()
    expect(within(item).getByText(/indexing request: not requested/i)).toBeInTheDocument()
    expect(item.textContent).not.toMatch(/indexed(?! )|submitted/i)
  })

  it('shows Indexed only when the backend says so', async () => {
    routeFetch({
      'GET /api/urls/recent/': async () =>
        fakeResponse([
          makeRecord(1, { inspection_status: 'indexed', indexing_request_status: 'submitted' }),
        ]),
    })
    render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    const item = await screen.findByRole('listitem')
    expect(within(item).getByText(/inspection: indexed/i)).toBeInTheDocument()
    expect(within(item).getByText(/indexing request: submitted/i)).toBeInTheDocument()
  })

  it('shows an error with a working Retry button', async () => {
    let calls = 0
    routeFetch({
      'GET /api/urls/recent/': async () => {
        calls += 1
        if (calls === 1) throw new TypeError('Failed to fetch')
        return fakeResponse([makeRecord(1)])
      },
    })
    const user = userEvent.setup()
    render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
    await user.click(screen.getByRole('button', { name: /retry/i }))
    expect(await screen.findByText('https://site1.example.com')).toBeInTheDocument()
  })

  it('offers a View all button that calls onToggle', async () => {
    routeFetch({ 'GET /api/urls/recent/': async () => fakeResponse([]) })
    const onToggle = vi.fn()
    const user = userEvent.setup()
    render(<UrlListPanel mode="recent" onToggle={onToggle} />)
    await user.click(await screen.findByRole('button', { name: /view all/i }))
    expect(onToggle).toHaveBeenCalledTimes(1)
  })
})

describe('UrlListPanel (all mode)', () => {
  it('shows every URL and a way back to recent', async () => {
    routeFetch({ 'GET /api/urls/all/': async () => fakeResponse(many(8)) })
    render(<UrlListPanel mode="all" onToggle={() => {}} />)
    expect(await screen.findAllByRole('listitem')).toHaveLength(8)
    expect(screen.getByRole('button', { name: /show recent only/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /all urls/i })).toBeInTheDocument()
  })
})

describe('UrlListPanel XSS safety', () => {
  it('renders hostile URLs as plain text, never as HTML', async () => {
    const hostile = 'https://x.com/<img src=x onerror=alert(1)><script>alert(2)</script>'
    routeFetch({
      'GET /api/urls/recent/': async () => fakeResponse([makeRecord(1, { url: hostile })]),
    })
    const { container } = render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    const item = await screen.findByRole('listitem')
    expect(item).toHaveTextContent(hostile)
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('a')).toBeNull()
  })
})

describe('UrlListPanel Check again', () => {
  it('asks the backend to recheck and shows the new status', async () => {
    routeFetch({
      'GET /api/urls/recent/': async () =>
        fakeResponse([makeRecord(1, { inspection_status: 'not_indexed' })]),
      'POST /api/urls/1/recheck/': async () =>
        fakeResponse(makeRecord(1, { inspection_status: 'indexed' })),
    })
    const user = userEvent.setup()
    render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    const item = await screen.findByRole('listitem')
    expect(within(item).getByText(/inspection: not indexed/i)).toBeInTheDocument()
    await user.click(within(item).getByRole('button', { name: /check again/i }))
    expect(await within(item).findByText(/inspection: indexed/i)).toBeInTheDocument()
  })

  it('shows an error for that URL if the recheck fails, and keeps the old status', async () => {
    routeFetch({
      'GET /api/urls/recent/': async () =>
        fakeResponse([makeRecord(1, { inspection_status: 'not_indexed' })]),
      'POST /api/urls/1/recheck/': async () => fakeResponse({ detail: 'nope' }, 503),
    })
    const user = userEvent.setup()
    render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    const item = await screen.findByRole('listitem')
    await user.click(within(item).getByRole('button', { name: /check again/i }))
    expect(await within(item).findByRole('alert')).toBeInTheDocument()
    expect(within(item).getByText(/inspection: not indexed/i)).toBeInTheDocument()
  })
})

describe('UrlListPanel Google details', () => {
  it("shows Google's own coverage text as plain text (never as HTML)", async () => {
    routeFetch({
      'GET /api/urls/recent/': async () => fakeResponse([
        makeRecord(1, {
          inspection_status: 'not_indexed',
          coverage_state: 'URL is unknown to Google <img src=x onerror=alert(1)>',
          last_inspected_at: '2026-11-05T10:00:00Z',
        }),
      ]),
    })
    const { container } = render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    const item = await screen.findByRole('listitem')
    expect(item).toHaveTextContent(/url is unknown to google/i)
    expect(item).toHaveTextContent(/last inspected/i)
    expect(container.querySelector('img')).toBeNull()
  })

  it('shows no "last inspected" and no coverage line when Google never answered', async () => {
    routeFetch({
      'GET /api/urls/recent/': async () =>
        fakeResponse([makeRecord(1, { inspection_status: 'quota_exceeded' })]),
    })
    render(<UrlListPanel mode="recent" onToggle={() => {}} />)
    const item = await screen.findByRole('listitem')
    expect(item).toHaveTextContent(/inspection: quota exceeded/i)
    expect(item.textContent).not.toMatch(/last inspected/i)
  })
})