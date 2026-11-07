// Backend ke inspection_status / indexing_request_status ke exact labels.
// Jo value yahan nahi hai wo "Unknown" dikhegi; kuch bhi apni taraf se
// "Indexed" ya "Submitted" nahi banaya jata.
const INSPECTION = {
  not_inspected: 'Not inspected',
  pending: 'Pending',
  indexed: 'Indexed',
  not_indexed: 'Not indexed',
  quota_exceeded: 'Quota exceeded',
  auth_error: 'Google login problem',
  permission_denied: 'No access to this URL',
  error: 'Error',
}

const REQUEST = {
  not_requested: 'Not requested',
  pending: 'Pending',
  submitted: 'Submitted',
  failed: 'Failed',
}

function lookup(table, value) {
  return typeof value === 'string' && Object.hasOwn(table, value) ? table[value] : 'Unknown'
}

export const inspectionLabel = (value) => lookup(INSPECTION, value)
export const requestLabel = (value) => lookup(REQUEST, value)

// CSS class sirf is fixed list se aati hai, server ki raw value se kabhi nahi.
const TONES = {
  indexed: 'good',
  submitted: 'good',
  error: 'bad',
  auth_error: 'bad',
  permission_denied: 'bad',
  quota_exceeded: 'bad',
  failed: 'bad',
  not_indexed: 'warn',
  pending: 'warn',
}

export function toneFor(value) {
  return typeof value === 'string' && Object.hasOwn(TONES, value) ? TONES[value] : 'neutral'
}