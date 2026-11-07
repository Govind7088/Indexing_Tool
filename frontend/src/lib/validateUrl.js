export const MAX_URL_LENGTH = 2048

const fail = (error) => ({ ok: false, error })

/**
 * Client-side check (sirf user ko jaldi feedback dene ke liye).
 * Asli aur final validation hamesha Django backend karta hai.
 */
export function validateUrl(input) {
  const value = typeof input === 'string' ? input.trim() : ''

  if (!value) return fail('Enter a URL.')
  if (value.length > MAX_URL_LENGTH) {
    return fail(`That URL is too long (maximum ${MAX_URL_LENGTH} characters).`)
  }
  if (/\s/.test(value)) return fail('A URL cannot contain spaces.')
  if (!/^https?:\/\//i.test(value)) {
    return fail('Enter a full URL starting with http:// or https://, for example https://example.com/page')
  }

  // username:password@ sirf authority (host wale hisse) mein dekhna hai;
  // path mein '@' (jaise medium.com/@user) bilkul theek hai.
  const authority = value.slice(value.indexOf('//') + 2).split(/[/?#]/)[0]
  if (authority.includes('@')) {
    return fail('URLs with a username or password are not allowed.')
  }

  let parsed
  try {
    parsed = new URL(value)
  } catch {
    return fail('That does not look like a valid URL.')
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return fail('Only http:// and https:// URLs are allowed.')
  }
  if (!parsed.hostname) return fail('That URL has no website address (host).')

  return { ok: true, value }
}