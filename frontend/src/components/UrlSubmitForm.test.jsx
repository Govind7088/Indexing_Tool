import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import UrlSubmitForm from './UrlSubmitForm'
import { fakeResponse, makeRecord, routeFetch } from '../test/helpers'

function setup(routes = {}) {
  const fetchMock = routeFetch(routes)
  const onSaved = vi.fn()
  const user = userEvent.setup()
  render(<UrlSubmitForm onSaved={onSaved} />)
  return { fetchMock, onSaved, user }
}

const input = () => screen.getByLabelText(/url/i)
const button = () => screen.getByRole('button', { name: /save url|saving/i })

describe('UrlSubmitForm', () => {
  it('renders an input and a submit button', () => {
    setup()
    expect(input()).toBeInTheDocument()
    expect(button()).toBeEnabled()
  })

  it('shows a validation error and does not call the API for bad input', async () => {
    const { fetchMock, user } = setup()
    await user.type(input(), 'javascript:alert(1)')
    await user.click(button())
    expect(await screen.findByRole('alert')).toHaveTextContent(/http/i)
    expect(fetchMock).not.toHaveBeenCalled()
    expect(input()).toHaveAttribute('aria-invalid', 'true')
  })

  it('shows an error for an empty submit', async () => {
    const { fetchMock, user } = setup()
    await user.click(button())
    expect(await screen.findByRole('alert')).toHaveTextContent(/enter a url/i)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows a loading state and blocks double submit', async () => {
    let release
    const gate = new Promise((resolve) => {
      release = resolve
    })
    const { fetchMock, user } = setup({
      'POST /api/urls/': async () => {
        await gate
        return fakeResponse(makeRecord(1), 201)
      },
    })
    await user.type(input(), 'https://example.com')
    await user.click(button())

    expect(button()).toBeDisabled()
    expect(button()).toHaveTextContent(/saving/i)
    await user.click(button())
    expect(fetchMock).toHaveBeenCalledTimes(1)

    release()
    await screen.findByRole('status')
    expect(button()).toBeEnabled()
  })

  it('shows an honest success message and clears the input', async () => {
    const { onSaved, user } = setup({
      'POST /api/urls/': async () => fakeResponse(makeRecord(1, { inspection_status: 'not_indexed' }), 201),
    })
    await user.type(input(), 'https://example.com')
    await user.click(button())

    const message = await screen.findByRole('status')
    expect(message).toHaveTextContent(/saved/i)
    expect(message).toHaveTextContent(/checked with google/i)
    expect(message.textContent).not.toMatch(/indexed successfully|will be indexed/i)
    expect(input()).toHaveValue('')
    expect(onSaved).toHaveBeenCalledTimes(1)
  })

  it('sends the trimmed URL', async () => {
    const { fetchMock, user } = setup({
      'POST /api/urls/': async () => fakeResponse(makeRecord(1), 201),
    })
    await user.type(input(), '  https://example.com/a  ')
    await user.click(button())
    await screen.findByRole('status')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ url: 'https://example.com/a' })
  })

  it('explains a duplicate (HTTP 200) differently from a new URL', async () => {
    const { user } = setup({
      'POST /api/urls/': async () => fakeResponse(makeRecord(1, { inspection_status: 'not_indexed' }), 200),
    })
    await user.type(input(), 'https://example.com')
    await user.click(button())
    const message = await screen.findByRole('status')
    expect(message).toHaveTextContent(/checked again/i)
  })

  it('shows a message when Google is not configured', async () => {
    const { user } = setup({
    'POST /api/urls/': async () =>
      fakeResponse(makeRecord(1, { inspection_status: 'not_inspected' }), 201),
    })
    await user.type(input(), 'https://example.com')
    await user.click(button())
    expect(await screen.findByRole('status')).toHaveTextContent(/google is not configured/i)
  })

  it('shows an error when Google inspection fails and allows retry', async () => {
  const { user } = setup({
    'POST /api/urls/': async () =>
      fakeResponse(makeRecord(1, { inspection_status: 'error' }), 201),
    })
    await user.type(input(), 'https://example.com')
    await user.click(button())

    const message = await screen.findByRole('status')
    expect(message).toHaveTextContent(/could not check/i)
    expect(message).toHaveTextContent(/check again/i)
  })

  it('shows a clear error when the backend rejects the URL (400)', async () => {
    const { onSaved, user } = setup({
      'POST /api/urls/': async () => fakeResponse({ url: ['nope'] }, 400),
    })
    await user.type(input(), 'https://example.com')
    await user.click(button())
    expect(await screen.findByRole('alert')).toHaveTextContent(/not accepted/i)
    expect(onSaved).not.toHaveBeenCalled()
    expect(input()).toHaveValue('https://example.com')
  })

  it('shows a rate-limit message on 429', async () => {
    const { user } = setup({
      'POST /api/urls/': async () => fakeResponse({ detail: 'throttled' }, 429),
    })
    await user.type(input(), 'https://example.com')
    await user.click(button())
    expect(await screen.findByRole('alert')).toHaveTextContent(/too many/i)
  })

  it('shows a network error and lets the user retry', async () => {
    const { fetchMock, user } = setup({
      'POST /api/urls/': async () => {
        throw new TypeError('Failed to fetch')
      },
    })
    await user.type(input(), 'https://example.com')
    await user.click(button())
    expect(await screen.findByRole('alert')).toHaveTextContent(/reach the server/i)
    await waitFor(() => expect(button()).toBeEnabled())
    await user.click(button())
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  })

  it('clears the old message when the user starts typing again', async () => {
    const { user } = setup()
    await user.click(button())
    await screen.findByRole('alert')
    await user.type(input(), 'h')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('UrlSubmitForm Google failure messages', () => {
  it.each([
    ['quota_exceeded', /quota/i],
    ['auth_error', /could not log in to google/i],
    ['permission_denied', /no search console access/i],
  ])('explains %s honestly and never claims success', async (status, pattern) => {
    const { user } = setup({
      'POST /api/urls/': async () =>
        fakeResponse(makeRecord(1, { inspection_status: status }), 201),
    })
    await user.type(input(), 'https://example.com')
    await user.click(button())
    const message = await screen.findByRole('status')
    expect(message).toHaveTextContent(pattern)
    expect(message).toHaveTextContent(/saved/i)
    expect(message.textContent).not.toMatch(/checked with google|indexed/i)
  })
})