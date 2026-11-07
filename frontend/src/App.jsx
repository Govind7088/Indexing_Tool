import { useState } from 'react'
import UrlListPanel from './components/UrlListPanel'
import UrlSubmitForm from './components/UrlSubmitForm'

export default function App() {
  const [showAll, setShowAll] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  return (
    <main className="app">
      <header>
        <h1>URL Indexing Tool</h1>
        <p className="muted">Save URLs you want to track.</p>
      </header>

      <p className="notice" role="note">
        Status comes from Google Search Console. Indexing can take days, so use "Check again" later to refresh a status.
      </p>

      <UrlSubmitForm onSaved={() => setRefreshKey((n) => n + 1)} />
      <UrlListPanel
        mode={showAll ? 'all' : 'recent'}
        refreshKey={refreshKey}
        onToggle={() => setShowAll((value) => !value)}
      />
    </main>
  )
}