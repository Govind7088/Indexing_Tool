import { useId, useState } from 'react'
import { ApiError, submitUrl } from '../api/client'
import { MAX_URL_LENGTH, validateUrl } from '../lib/validateUrl'

function successText(record, created) {
  const start = created ? 'Saved.' : 'Already saved, so it moved to the top.'
  if (record.inspection_status === 'not_inspected') {
    return `${start} Google is not configured, so no status was checked.`
  }
    if (record.inspection_status === 'quota_exceeded') {
    return `${start} Google's quota is used up right now, so no status was checked. Use "Check again" later.`
  }
  if (record.inspection_status === 'auth_error') {
    return `${start} The backend could not log in to Google. Check the Google setup.`
  }
  if (record.inspection_status === 'permission_denied') {
    return `${start} Your Google account has no Search Console access to this URL.`
  }
  if (record.inspection_status === 'error') {
    return `${start} Google could not check this URL right now. Use "Check again" later.`
  }
  return created
    ? `${start} Checked with Google. The current status is in the list below; indexing can take days.`
    : `${start} Status was checked again with Google. See the list below.`
}

export default function UrlSubmitForm({ onSaved }) {
  const inputId = useId()
  const messageId = useId()
  const [value, setValue] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState(null) // { type: 'error'|'success', text }

  function handleChange(event) {
    setValue(event.target.value)
    if (feedback) setFeedback(null)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return

    const check = validateUrl(value)
    if (!check.ok) {
      setFeedback({ type: 'error', text: check.error })
      return
    }

    setSubmitting(true)
    setFeedback(null)
    try {
      const { record, created } = await submitUrl(check.value)
      setValue('')
      setFeedback({
        type: 'success',
        text: successText(record, created),
      })
      if (onSaved) onSaved()
    } catch (error) {
      setFeedback({
        type: 'error',
        text: error instanceof ApiError ? error.message : 'Something went wrong. Please try again.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  const hasError = feedback?.type === 'error'

  return (
    <form className="card" onSubmit={handleSubmit} noValidate>
      <label htmlFor={inputId}>URL to save</label>
      <div className="form-row">
        <input
          id={inputId}
          type="text"
          inputMode="url"
          autoComplete="off"
          spellCheck="false"
          maxLength={MAX_URL_LENGTH}
          placeholder="https://example.com/page"
          value={value}
          onChange={handleChange}
          disabled={submitting}
          aria-invalid={hasError ? 'true' : 'false'}
          aria-describedby={feedback ? messageId : undefined}
        />
        <button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save URL'}
        </button>
      </div>
      {feedback && (
        <p
          id={messageId}
          className={hasError ? 'message error' : 'message success'}
          role={hasError ? 'alert' : 'status'}
        >
          {feedback.text}
        </p>
      )}
    </form>
  )
}