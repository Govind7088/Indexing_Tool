import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from './App'
import { fakeResponse, makeRecord, routeFetch } from './test/helpers'

const many = (count) => Array.from({ length: count }, (_, i) => makeRecord(i + 1))

describe('App', () => {
  it('has the form, the recent list, and a clear note that Google is not connected', async () => {
    routeFetch({ 'GET /api/urls/recent/': async () => fakeResponse([]) })
    render(<App />)
    expect(screen.getByLabelText(/url/i)).toBeInTheDocument()
    expect(screen.getByRole('note')).toHaveTextContent(/google search console/i)
    expect(screen.getByRole('note')).not.toHaveTextContent(/not connected/i)
    await screen.findByText(/no urls saved yet/i)
  })

  it('has no login or signup UI', async () => {
    routeFetch({ 'GET /api/urls/recent/': async () => fakeResponse([]) })
    render(<App />)
    await screen.findByText(/no urls saved yet/i)
    expect(screen.queryByText(/log ?in|sign ?up|password/i)).toBeNull()
  })

  it('View all loads the all endpoint, and Show recent only goes back', async () => {
    routeFetch({
      'GET /api/urls/recent/': async () => fakeResponse(many(8)),
      'GET /api/urls/all/': async () => fakeResponse(many(8)),
    })
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findAllByRole('listitem')).toHaveLength(5)

    await user.click(screen.getByRole('button', { name: /view all/i }))
    await waitFor(() => expect(screen.getAllByRole('listitem')).toHaveLength(8))
    expect(screen.getByRole('heading', { name: /all urls/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /show recent only/i }))
    await waitFor(() => expect(screen.getAllByRole('listitem')).toHaveLength(5))
  })

  it('refreshes the list after a successful submit', async () => {
    let saved = false
    routeFetch({
      'GET /api/urls/recent/': async () =>
        fakeResponse(saved ? [makeRecord(9, { url: 'https://new.example.com' })] : []),
      'POST /api/urls/': async () => {
        saved = true
        return fakeResponse(makeRecord(9, { url: 'https://new.example.com' }), 201)
      },
    })
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText(/no urls saved yet/i)

    await user.type(screen.getByLabelText(/url/i), 'https://new.example.com')
    await user.click(screen.getByRole('button', { name: /save url/i }))

    const list = await screen.findByRole('list')
    expect(within(list).getByText('https://new.example.com')).toBeInTheDocument()
  })
})