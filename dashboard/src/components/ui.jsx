import React from 'react'
import { Icon } from './Layout'
import { fmtDuration } from '../data'

export function Panel({ title, subtitle, right, children, className = '', icon }) {
  return (
    <section className={`border border-edge bg-surface rounded-2xl shadow-card overflow-hidden ${className}`}>
      {(title || right) && (
        <header className="flex items-center gap-3 px-4 py-2.5 border-b border-edge bg-[rgba(255,255,255,0.5)]">
          {icon && <Icon name={icon} className="text-ink-faint" />}
          <div className="min-w-0">
            {title && <h2 className="text-sm font-medium truncate">{title}</h2>}
            {subtitle && (
              <p className="text-xs text-ink-faint truncate">{subtitle}</p>
            )}
          </div>
          {right && <div className="ml-auto shrink-0">{right}</div>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  )
}

export function StatCard({ icon, label, value, sub, tone = 'default', valueClass = '' }) {
  const toneRing = {
    default: 'border-edge',
    verified: 'border-verified/40',
    flagged: 'border-flagged/40',
    pending: 'border-pending/40',
  }[tone]
  const iconTone = {
    default: 'text-ink-faint',
    verified: 'text-verified-soft',
    flagged: 'text-flagged-soft',
    pending: 'text-pending',
  }[tone]
  return (
    <div className={`border ${toneRing} bg-surface rounded-xl shadow-card-sm px-4 py-3`}>
      <div className="flex items-center gap-2 micro-label text-ink-faint">
        {icon && <Icon name={icon} className={iconTone} />}
        <span className="truncate">{label}</span>
      </div>
      <div className={`metric text-2xl mt-1.5 ${valueClass || 'text-ink'}`}>{value}</div>
      {sub && <div className="text-xs text-ink-faint mt-0.5 truncate">{sub}</div>}
    </div>
  )
}

export function VerdictBadge({ verdict, size = 'sm' }) {
  const verified = verdict === 'VERIFIED'
  const pad = size === 'lg' ? 'px-3 py-1 text-xs' : 'px-2 py-0.5 text-[10px]'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${pad} font-mono font-semibold tracking-wider ${
        verified
          ? 'bg-[#d1fae5] border-[#6ee7b7] text-[#065f46] glow-verified'
          : 'bg-[#fee2e2] border-[#fca5a5] text-[#991b1b] glow-flagged'
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${verified ? 'bg-verified' : 'bg-flagged pulse-dot'}`}
      />
      {verdict}
    </span>
  )
}

export function CheckStrip({ checks, compact = false }) {
  return (
    <div className="flex items-center gap-2">
      {(checks || []).map((c) => (
        <span
          key={c.key}
          className={`metric text-[10px] px-1.5 py-0.5 rounded border ${
            c.passed
              ? 'bg-[#d1fae5] border-[#6ee7b7] text-[#065f46]'
              : 'bg-[#fee2e2] border-[#fca5a5] text-[#991b1b]'
          }`}
          title={`${c.name}: ${c.passed ? 'PASS' : 'FAIL'}`}
        >
          {c.key}: {c.passed ? 'PASS' : 'FAIL'}
        </span>
      ))}
    </div>
  )
}

export function ModeBadges({ run, usesModel, modelName }) {
  return (
    <div className="flex items-center gap-2">
      <span className="metric text-[10px] px-1.5 py-0.5 rounded border border-edge bg-[rgba(255,255,255,0.55)] text-ink-dim">
        {run.backend === 'sandbox' ? 'Nebius Sandboxes' : 'Local Backend'}
      </span>
      {usesModel ? (
        <span className="metric text-[10px] px-1.5 py-0.5 rounded border border-edge bg-[rgba(255,255,255,0.55)] text-ink-dim">
          {run.nemotron_mode === 'live' ? 'Nemotron (live)' : 'Recorded replay'}
        </span>
      ) : (
        <span className="metric text-[10px] px-1.5 py-0.5 rounded border border-edge bg-[rgba(255,255,255,0.55)] text-ink-faint">
          Static analysis (no model)
        </span>
      )}
    </div>
  )
}

export function KeyValue({ k, v, mono = false }) {
  return (
    <div className="border border-edge bg-[rgba(255,255,255,0.55)] rounded-xl px-3 py-2">
      <div className="micro-label text-ink-faint">{k}</div>
      <div className={`text-sm mt-0.5 break-words ${mono ? 'metric' : ''}`}>{v}</div>
    </div>
  )
}

export function Collapsible({ label, children, defaultOpen = false, right }) {
  const [open, setOpen] = React.useState(defaultOpen)
  return (
    <div className="border border-edge rounded-xl bg-[rgba(255,255,255,0.45)]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-surface transition-colors focus-ring"
      >
        <Icon name={open ? 'collapse' : 'expand'} className="text-ink-faint" />
        <span className="micro-label text-ink-dim">{label}</span>
        {right && <span className="ml-auto text-xs text-ink-faint">{right}</span>}
      </button>
      {open && <div className="px-3 pb-3 pt-1 border-t border-edge">{children}</div>}
    </div>
  )
}

export function CodeBlock({ text, diff = false, className = '' }) {
  const base = `metric text-[11px] leading-[1.55] whitespace-pre-wrap break-words bg-code text-code-ink border border-[#0d2229] rounded-xl p-3 ${className}`
  if (!diff) {
    return <pre className={base}>{text || '—'}</pre>
  }
  // Diff & Code Matrix: added lines tint emerald, removed lines tint crimson.
  return (
    <pre className={base}>
      {(text || '').split('\n').map((line, i) => {
        const isAdd = line.startsWith('+') && !line.startsWith('+++')
        const isDel = line.startsWith('-') && !line.startsWith('---')
        const tone = isAdd
          ? 'bg-[rgba(6,78,59,0.45)] text-[#6ee7b7]'
          : isDel
            ? 'bg-[rgba(127,29,29,0.45)] text-[#fca5a5]'
            : ''
        return (
          <div key={i} className={tone}>
            {line || ' '}
          </div>
        )
      })}
    </pre>
  )
}

export function DurationText({ ms }) {
  return <span className="metric">{fmtDuration(ms)}</span>
}
