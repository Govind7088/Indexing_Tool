import { describe, expect, it } from 'vitest'
import { inspectionLabel, requestLabel, toneFor } from './status'

describe('status labels', () => {
  it('shows the default statuses as-is (nothing is faked as indexed)', () => {
    expect(inspectionLabel('not_inspected')).toBe('Not inspected')
    expect(requestLabel('not_requested')).toBe('Not requested')
  })

  it('maps every backend value', () => {
    expect(inspectionLabel('pending')).toBe('Pending')
    expect(inspectionLabel('indexed')).toBe('Indexed')
    expect(inspectionLabel('not_indexed')).toBe('Not indexed')
    expect(inspectionLabel('error')).toBe('Error')
    expect(inspectionLabel('quota_exceeded')).toBe('Quota exceeded')
    expect(inspectionLabel('auth_error')).toBe('Google login problem')
    expect(inspectionLabel('permission_denied')).toBe('No access to this URL')
    expect(requestLabel('pending')).toBe('Pending')
    expect(requestLabel('submitted')).toBe('Submitted')
    expect(requestLabel('failed')).toBe('Failed')
  })

  it('shows Unknown for anything unexpected, including prototype keys', () => {
    for (const bad of ['hacked', '', undefined, null, 'constructor', '__proto__', 'toString']) {
      expect(inspectionLabel(bad)).toBe('Unknown')
      expect(requestLabel(bad)).toBe('Unknown')
    }
  })
})

describe('status tones', () => {
  it('never shows Google failures as a green or "not indexed" state', () => {
    for (const value of ['quota_exceeded', 'auth_error', 'permission_denied', 'error']) {
      expect(toneFor(value)).not.toBe('good')
      expect(inspectionLabel(value)).not.toBe('Not indexed')
    }
    expect(toneFor('indexed')).toBe('good')
  })
})