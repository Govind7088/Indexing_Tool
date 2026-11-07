import { describe, expect, it } from 'vitest'
import { MAX_URL_LENGTH, validateUrl } from './validateUrl'

describe('validateUrl', () => {
  it.each([
    'https://example.com',
    'http://example.com/path?x=1#frag',
    'https://sub.example.co.uk:8443/a/b',
    'http://localhost:3000',
    'https://medium.com/@someone/post',
  ])('accepts %s', (input) => {
    expect(validateUrl(input)).toEqual({ ok: true, value: input })
  })

  it('trims surrounding spaces', () => {
    expect(validateUrl('  https://example.com  ')).toEqual({
      ok: true,
      value: 'https://example.com',
    })
  })

  it.each(['', '   ', null, undefined, 42])('rejects empty or non-string: %s', (input) => {
    const result = validateUrl(input)
    expect(result.ok).toBe(false)
    expect(result.error).toMatch(/enter a url/i)
  })

  it.each([
    'example.com',
    'www.example.com',
    'javascript:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    'ftp://example.com',
    'file:///etc/passwd',
    'https:example.com',
    '//example.com',
  ])('rejects non-http(s) or incomplete URL: %s', (input) => {
    const result = validateUrl(input)
    expect(result.ok).toBe(false)
    expect(result.error).toMatch(/http/i)
  })

  it.each([
    'https://admin:password@example.com/',
    'https://token@example.com/',
    'https://@example.com/',
  ])('rejects credentials in URL: %s', (input) => {
    const result = validateUrl(input)
    expect(result.ok).toBe(false)
    expect(result.error).toMatch(/username or password/i)
  })

  it('rejects spaces inside the URL', () => {
    const result = validateUrl('https://exam ple.com')
    expect(result.ok).toBe(false)
    expect(result.error).toMatch(/space/i)
  })

  it('rejects URLs longer than the limit', () => {
    const long = 'https://example.com/' + 'a'.repeat(MAX_URL_LENGTH)
    const result = validateUrl(long)
    expect(result.ok).toBe(false)
    expect(result.error).toMatch(/too long/i)
  })

  it('rejects a URL with no host', () => {
    expect(validateUrl('https://').ok).toBe(false)
  })
})