import { describe, expect, it } from 'vitest'

import type { QuotaInfo, Usage } from '../types.js'
import { buildStatusRuleLines } from './appChrome.js'

const baseUsage: Usage = {
  calls: 0,
  input: 0,
  output: 0,
  total: 0
}

const quota: QuotaInfo = {
  provider: 'codex',
  summary: 'pro · 5h 90% · 7d 98%'
}

describe('buildStatusRuleLines', () => {
  it('moves quota to a second line when width is narrow', () => {
    const lines = buildStatusRuleLines({
      busy: false,
      model: 'gpt-5.4',
      quota,
      sessionStartedAt: null,
      status: 'running…',
      usage: {
        ...baseUsage,
        context_max: 1_100_000,
        context_percent: 1,
        context_used: 13_300
      },
      voiceLabel: '',
      bgCount: 0,
      compactWidth: 48
    })

    expect(lines.primary).toContain('running…')
    expect(lines.primary).toContain('gpt-5.4')
    expect(lines.primary).toContain('13.3K/1.1M')
    expect(lines.secondary).toContain('pro · 5h 90% · 7d 98%')
  })

  it('keeps quota on the primary line when width is sufficient', () => {
    const lines = buildStatusRuleLines({
      busy: false,
      model: 'gpt-5.4',
      quota,
      sessionStartedAt: null,
      status: 'ready',
      usage: baseUsage,
      voiceLabel: '',
      bgCount: 0,
      compactWidth: 160
    })

    expect(lines.primary).toContain('pro · 5h 90% · 7d 98%')
    expect(lines.secondary).toBe('')
  })
})
