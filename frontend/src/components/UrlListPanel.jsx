import { useEffect, useState } from 'react'
import { ApiError, fetchAll, fetchRecent, recheckUrl } from '../api/client'
import { inspectionLabel, requestLabel } from '../lib/status'
import StatusBadge from './StatusBadge'

function formatDate(iso) {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? null : { iso: date.toISOString(), text: date.toLocaleString() }
}

function UrlItem({ record: loaded }) {
  const [override, setOverride] = useState(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState(null)
  const record = override && override.base === loaded ? override.data : loaded
  const when = formatDate(record.updated_at)
  const inspected = record.last_inspected_at ? formatDate(record.last_inspected_at) : null

  async function checkAgain() {
    setChecking(true)
    setError(null)
    try {
      setOverride({ base: loaded, data: await recheckUrl(loaded.id) })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not check this URL. Please try again.')
    } finally {
      setChecking(false)
    }
  }

  return (
    <li className="url-item">
      <span className="url-text">{record.url}</span>
      <span className="badges">
        <StatusBadge
          title="Inspection"
          label={inspectionLabel(record.inspection_status)}
          value={record.inspection_status}
        />
        <StatusBadge
          title="Indexing request"
          label={requestLabel(record.indexing_request_status)}
          value={record.indexing_request_status}
        />
      </span>
      {record.coverage_state && (
        <span className="coverage">Google says: {record.coverage_state}</span>
      )}
      {inspected && (
        <time className="when" dateTime={inspected.iso}>
          Last inspected: {inspected.text}
        </time>
      )}
      {when && (
        <time className="when" dateTime={when.iso}>
          {when.text}
        </time>
      )}
      <button type="button" className="secondary" onClick={checkAgain} disabled={checking}>
        {checking ? 'Checking…' : 'Check again'}
      </button>
      {error && (
        <p className="message error" role="alert">
          {error}
        </p>
      )}
    </li>
  )
}

// key={mode} ke saath mount hota hai, isliye Recent <-> All badalne par state fresh hoti hai.
function UrlListBody({ mode, refreshKey }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    const load = mode === 'all' ? fetchAll : fetchRecent
    load()
      .then((data) => {
        if (cancelled) return
        setError(null)
        setItems(data)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Could not load the list. Please try again.')
      })
    return () => {
      cancelled = true
    }
  }, [mode, refreshKey, attempt])

  function retry() {
    setError(null)
    setAttempt((n) => n + 1)
  }

  if (error) {
    return (
      <div>
        <p className="message error" role="alert">
          {error}
        </p>
        <button type="button" className="secondary" onClick={retry}>
          Retry
        </button>
      </div>
    )
  }
  if (items === null) {
    return (
      <p className="muted" role="status">
        Loading…
      </p>
    )
  }
  if (items.length === 0) return <p className="muted">No URLs saved yet.</p>

  return (
    <>
      {mode === 'all' && <p className="muted">{items.length} saved</p>}
      <ul className="url-list">
        {items.map((record) => (
          <UrlItem key={record.id} record={record} />
        ))}
      </ul>
    </>
  )
}

export default function UrlListPanel({ mode, onToggle, refreshKey = 0 }) {
  const showingAll = mode === 'all'
  return (
    <section className="card">
      <div className="panel-head">
        <h2>{showingAll ? 'All URLs' : 'Recent URLs'}</h2>
        <button type="button" className="secondary" onClick={onToggle}>
          {showingAll ? 'Show recent only' : 'View all'}
        </button>
      </div>
      <UrlListBody key={mode} mode={mode} refreshKey={refreshKey} />
    </section>
  )
}