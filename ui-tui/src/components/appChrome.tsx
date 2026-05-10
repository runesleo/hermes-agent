import { Box, type ScrollBoxHandle, Text } from '@hermes/ink'
import { type ReactNode, type RefObject, useCallback, useEffect, useState, useSyncExternalStore } from 'react'

import { FACES } from '../content/faces.js'
import { VERBS } from '../content/verbs.js'
import { fmtDuration } from '../domain/messages.js'
import { stickyPromptFromViewport } from '../domain/viewport.js'
import { fmtK } from '../lib/text.js'
import type { Theme } from '../theme.js'
import type { Msg, QuotaInfo, Usage } from '../types.js'

const FACE_TICK_MS = 2500
const HEART_COLORS = ['#ff5fa2', '#ff4d6d']

function FaceTicker({ color }: { color: string }) {
  const [tick, setTick] = useState(() => Math.floor(Math.random() * 1000))

  useEffect(() => {
    const id = setInterval(() => setTick(n => n + 1), FACE_TICK_MS)

    return () => clearInterval(id)
  }, [])

  return (
    <Text color={color}>
      {FACES[tick % FACES.length]} {VERBS[tick % VERBS.length]}…
    </Text>
  )
}

function ctxBarColor(pct: number | undefined, t: Theme) {
  if (pct == null) {
    return t.color.dim
  }

  if (pct >= 95) {
    return t.color.statusCritical
  }

  if (pct > 80) {
    return t.color.statusBad
  }

  if (pct >= 50) {
    return t.color.statusWarn
  }

  return t.color.statusGood
}

function quotaColor(quota: QuotaInfo | null | undefined, t: Theme) {
  if (!quota) {
    return t.color.dim
  }
  if (quota.severity === 'bad') {
    return t.color.statusBad
  }
  if (quota.severity === 'warn') {
    return t.color.statusWarn
  }
  return t.color.statusGood
}

function ctxBar(pct: number | undefined, w = 10) {
  const p = Math.max(0, Math.min(100, pct ?? 0))
  const filled = Math.round((p / 100) * w)

  return '█'.repeat(filled) + '░'.repeat(w - filled)
}

function SessionDuration({ startedAt }: { startedAt: number }) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    setNow(Date.now())
    const id = setInterval(() => setNow(Date.now()), 1000)

    return () => clearInterval(id)
  }, [startedAt])

  return fmtDuration(now - startedAt)
}

interface StatusRuleLineOptions {
  bgCount: number
  busy: boolean
  compactWidth: number
  model: string
  quota?: QuotaInfo | null
  sessionStartedAt?: number | null
  status: string
  usage: Usage
  voiceLabel?: string
}

export function buildStatusRuleLines({
  bgCount,
  busy,
  compactWidth,
  model,
  quota,
  sessionStartedAt,
  status,
  usage,
  voiceLabel
}: StatusRuleLineOptions): { primary: string; secondary: string } {
  const pct = usage.context_percent
  const ctxLabel = usage.context_max
    ? `${fmtK(usage.context_used ?? 0)}/${fmtK(usage.context_max)}`
    : usage.total > 0
      ? `${fmtK(usage.total)} tok`
      : ''
  const quotaLabel = quota?.summary ?? ''
  const durationLabel = sessionStartedAt ? fmtDuration(Date.now() - sessionStartedAt) : ''
  const barLabel = usage.context_max ? `${pct != null ? `${pct}%` : ''}` : ''

  const primaryParts = [
    status,
    model,
    ctxLabel,
    barLabel,
    durationLabel,
    voiceLabel || '',
    bgCount > 0 ? `${bgCount} bg` : ''
  ].filter(Boolean)
  const primary = primaryParts.join(' │ ')

  if (!quotaLabel) {
    return { primary, secondary: '' }
  }

  const combined = [status, model, quotaLabel, ctxLabel, barLabel, durationLabel, voiceLabel || '', bgCount > 0 ? `${bgCount} bg` : '']
    .filter(Boolean)
    .join(' │ ')

  if (combined.length <= compactWidth) {
    return { primary: [status, model, quotaLabel, ctxLabel, barLabel, durationLabel, voiceLabel || '', bgCount > 0 ? `${bgCount} bg` : ''].filter(Boolean).join(' │ '), secondary: '' }
  }

  return { primary, secondary: quotaLabel }
}

export function GoodVibesHeart({ tick, t }: { tick: number; t: Theme }) {
  const [active, setActive] = useState(false)
  const [color, setColor] = useState(t.color.amber)

  useEffect(() => {
    if (tick <= 0) {
      return
    }

    const palette = [...HEART_COLORS, t.color.amber]
    setColor(palette[Math.floor(Math.random() * palette.length)]!)
    setActive(true)

    const id = setTimeout(() => setActive(false), 650)

    return () => clearTimeout(id)
  }, [t.color.amber, tick])

  return <Text color={color}>{active ? '♥' : ' '}</Text>
}

export function StatusRule({
  cwdLabel,
  cols,
  busy,
  status,
  statusColor,
  model,
  usage,
  quota,
  bgCount,
  sessionStartedAt,
  voiceLabel,
  t
}: StatusRuleProps) {
  const quotaTone = quotaColor(quota, t)
  const leftWidth = Math.max(12, cols - cwdLabel.length - 3)
  const lines = buildStatusRuleLines({
    bgCount,
    busy,
    compactWidth: Math.max(24, leftWidth - 6),
    model,
    quota,
    sessionStartedAt,
    status,
    usage,
    voiceLabel
  })

  return (
    <Box>
      <Box flexDirection="column" flexShrink={1} width={leftWidth}>
        <Text color={t.color.bronze} wrap="truncate-end">
          {'─ '}
          {busy ? <FaceTicker color={statusColor} /> : <Text color={statusColor}>{lines.primary}</Text>}
        </Text>
        {lines.secondary ? (
          <Text color={quotaTone} wrap="truncate-end">
            {'  '}
            {lines.secondary}
          </Text>
        ) : null}
      </Box>

      <Text color={t.color.bronze}> ─ </Text>
      <Text color={t.color.label}>{cwdLabel}</Text>
    </Box>
  )
}

export function FloatBox({ children, color }: { children: ReactNode; color: string }) {
  return (
    <Box
      alignSelf="flex-start"
      borderColor={color}
      borderStyle="double"
      flexDirection="column"
      marginTop={1}
      opaque
      paddingX={1}
    >
      {children}
    </Box>
  )
}

export function StickyPromptTracker({ messages, offsets, scrollRef, onChange }: StickyPromptTrackerProps) {
  useSyncExternalStore(
    useCallback((cb: () => void) => scrollRef.current?.subscribe(cb) ?? (() => {}), [scrollRef]),
    () => {
      const s = scrollRef.current

      if (!s) {
        return NaN
      }

      const top = Math.max(0, s.getScrollTop() + s.getPendingDelta())

      return s.isSticky() ? -1 - top : top
    },
    () => NaN
  )

  const s = scrollRef.current
  const top = Math.max(0, (s?.getScrollTop() ?? 0) + (s?.getPendingDelta() ?? 0))
  const text = stickyPromptFromViewport(messages, offsets, top, s?.isSticky() ?? true)

  useEffect(() => onChange(text), [onChange, text])

  return null
}

export function TranscriptScrollbar({ scrollRef, t }: TranscriptScrollbarProps) {
  useSyncExternalStore(
    useCallback((cb: () => void) => scrollRef.current?.subscribe(cb) ?? (() => {}), [scrollRef]),
    () => {
      const s = scrollRef.current

      if (!s) {
        return NaN
      }

      const vp = Math.max(0, s.getViewportHeight())
      const total = Math.max(vp, s.getScrollHeight())
      const top = Math.max(0, s.getScrollTop() + s.getPendingDelta())
      const thumb = total > vp ? Math.max(1, Math.round((vp * vp) / total)) : vp
      const travel = Math.max(1, vp - thumb)
      const thumbTop = total > vp ? Math.round((top / Math.max(1, total - vp)) * travel) : 0

      return `${thumbTop}:${thumb}:${vp}`
    },
    () => ''
  )

  const [hover, setHover] = useState(false)
  const [grab, setGrab] = useState<number | null>(null)

  const s = scrollRef.current
  const vp = Math.max(0, s?.getViewportHeight() ?? 0)

  if (!vp) {
    return <Box width={1} />
  }

  const total = Math.max(vp, s?.getScrollHeight() ?? vp)
  const scrollable = total > vp
  const thumb = scrollable ? Math.max(1, Math.round((vp * vp) / total)) : vp
  const travel = Math.max(1, vp - thumb)
  const pos = Math.max(0, (s?.getScrollTop() ?? 0) + (s?.getPendingDelta() ?? 0))
  const thumbTop = scrollable ? Math.round((pos / Math.max(1, total - vp)) * travel) : 0
  const thumbColor = grab !== null ? t.color.gold : hover ? t.color.amber : t.color.bronze
  const trackColor = hover ? t.color.bronze : t.color.dim

  const jump = (row: number, offset: number) => {
    if (!s || !scrollable) {
      return
    }

    s.scrollTo(Math.round((Math.max(0, Math.min(travel, row - offset)) / travel) * Math.max(0, total - vp)))
  }

  return (
    <Box
      flexDirection="column"
      onMouseDown={(e: { localRow?: number }) => {
        const row = Math.max(0, Math.min(vp - 1, e.localRow ?? 0))
        const off = row >= thumbTop && row < thumbTop + thumb ? row - thumbTop : Math.floor(thumb / 2)
        setGrab(off)
        jump(row, off)
      }}
      onMouseDrag={(e: { localRow?: number }) =>
        jump(Math.max(0, Math.min(vp - 1, e.localRow ?? 0)), grab ?? Math.floor(thumb / 2))
      }
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onMouseUp={() => setGrab(null)}
      width={1}
    >
      {!scrollable ? (
        <Text color={trackColor} dim>
          {' \n'.repeat(Math.max(0, vp - 1))}{' '}
        </Text>
      ) : (
        <>
          {thumbTop > 0 ? (
            <Text color={trackColor} dim={!hover}>
              {`${'│\n'.repeat(Math.max(0, thumbTop - 1))}${thumbTop > 0 ? '│' : ''}`}
            </Text>
          ) : null}
          {thumb > 0 ? (
            <Text color={thumbColor}>{`${'┃\n'.repeat(Math.max(0, thumb - 1))}${thumb > 0 ? '┃' : ''}`}</Text>
          ) : null}
          {vp - thumbTop - thumb > 0 ? (
            <Text color={trackColor} dim={!hover}>
              {`${'│\n'.repeat(Math.max(0, vp - thumbTop - thumb - 1))}${vp - thumbTop - thumb > 0 ? '│' : ''}`}
            </Text>
          ) : null}
        </>
      )}
    </Box>
  )
}

interface StatusRuleProps {
  bgCount: number
  busy: boolean
  cols: number
  cwdLabel: string
  model: string
  quota?: QuotaInfo | null
  sessionStartedAt?: number | null
  status: string
  statusColor: string
  t: Theme
  usage: Usage
  voiceLabel?: string
}

interface StickyPromptTrackerProps {
  messages: readonly Msg[]
  offsets: ArrayLike<number>
  onChange: (text: string) => void
  scrollRef: RefObject<ScrollBoxHandle | null>
}

interface TranscriptScrollbarProps {
  scrollRef: RefObject<ScrollBoxHandle | null>
  t: Theme
}
