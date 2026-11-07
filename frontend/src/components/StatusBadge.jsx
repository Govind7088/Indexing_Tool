import { toneFor } from '../lib/status'

export default function StatusBadge({ title, label, value }) {
  return (
    <span className={`badge badge-${toneFor(value)}`}>
      {title}: {label}
    </span>
  )
}