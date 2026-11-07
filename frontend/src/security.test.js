
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC_DIR = resolve(process.cwd(), 'frontend', 'src')

function sourceFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name)

    if (statSync(full).isDirectory()) {
      return sourceFiles(full)
    }

    const isCode = /\.(js|jsx|ts|tsx)$/.test(name)
    const isTest =
      /\.test\.(js|jsx|ts|tsx)$/.test(name) ||
      full.includes(join('src', 'test'))

    return isCode && !isTest ? [full] : []
  })
}

const FORBIDDEN = [
  'dangerouslySetInnerHTML',
  'innerHTML',
  'outerHTML',
  'insertAdjacentHTML',
  'document.write',
  'eval(',
  'new Function',
  'localStorage',
  'sessionStorage',
]

describe('source code safety scan', () => {
  const files = sourceFiles(SRC_DIR)

  it('finds the app source files', () => {
    expect(files.length).toBeGreaterThan(3)
  })

  it.each(FORBIDDEN)('no app source uses %s', (pattern) => {
    for (const file of files) {
      expect(readFileSync(file, 'utf8'), file).not.toContain(pattern)
    }
  })

  it('never renders submitted URLs as links', () => {
    for (const file of files) {
      expect(readFileSync(file, 'utf8'), file).not.toMatch(/<a[\s>]/)
    }
  })
})
