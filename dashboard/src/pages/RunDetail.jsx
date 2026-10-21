import React from 'react'
import { Icon } from '../components/Layout'
import { CheckStrip, CodeBlock, Collapsible, KeyValue, ModeBadges, Panel, VerdictBadge } from '../components/ui'
import {
  CHECK_NAMES,
  CHECK_USES_MODEL,
  ENGINE_INFO,
  SCENARIOS,
  checkOf,
  fmtDuration,
  fmtTimestamp,
  modeLabel,
} from '../data'

function CheckCard({ run, check }) {
  const [open, setOpen] = React.useState(false)
  const passed = check.passed
  const usesModel = CHECK_USES_MODEL[check.key]

  return (
    <div
      className={`border rounded-md overflow-hidden ${
        passed ? 'border-verified/30 bg-surface' : 'border-flagged/35 bg-surface'
      }`}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full text-left px-4 py-3 hover:bg-surface-2/40 transition-colors"
      >
        <div className="flex items-center gap-3 flex-wrap">
          <Icon name={passed ? 'check_circle' : 'bug'} className={passed ? 'text-verified-soft' : 'text-flagged-soft'} />
          <span className="font-medium">
            {check.key}. {check.name}
          </span>
          <span
            className={`metric text-[10px] px-2 py-0.5 rounded border ${
              passed
                ? 'bg-verified/15 border-verified/40 text-verified-soft'
                : 'bg-flagged/15 border-flagged/40 text-flagged-soft'
            }`}
          >
            {passed ? 'PASSED' : 'FAILED CHECK'}
          </span>
          <span className="ml-auto flex items-center gap-3">
            <ModeBadges run={run} usesModel={usesModel} modelName={ENGINE_INFO.models.super} />
            <Icon name={open ? 'collapse' : 'expand'} className="text-ink-faint" />
          </span>
        </div>
        <p className="text-sm text-ink-dim mt-1.5">{check.summary}</p>
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-edge pt-3 space-y-3">
          <div className="flex flex-wrap gap-2">
            <KeyValue k="Check" v={check.name} />
            <KeyValue k="Duration" v={fmtDuration(check.duration_ms)} mono />
            {check.counts?.total != null && (
              <KeyValue
                k="Pytest"
                v={`${check.counts.passed}/${check.counts.total} passed`}
                mono
              />
            )}
            {check.counts?.generated_total != null && (
              <KeyValue
                k="Generated tests"
                v={`${check.counts.generated_passed}/${check.counts.generated_total} passed`}
                mono
              />
            )}
          </div>

          {check.key === 'T' && <TamperEvidence check={check} />}

          {check.key === 'R' && (
            <div className="space-y-2">
              <div className="micro-label text-ink-faint">Pytest output (original suite vs patched code)</div>
              <CodeBlock text={check.evidence?.pytest_output} />
            </div>
          )}

          {check.key === 'B' && (
            <div className="space-y-2">
              <div className="micro-label text-ink-faint">Nemotron-generated test code</div>
              <CodeBlock text={(check.evidence?.generated_tests || []).join('\n\n')} />
              <div className="micro-label text-ink-faint pt-1">Pytest output</div>
              <CodeBlock text={check.evidence?.pytest_output} />
            </div>
          )}

          {check.key === 'D' && (
            <div className="space-y-2">
              <div className="micro-label text-ink-faint">Nemotron explanation</div>
              <CodeBlock text={check.summary} />
              <div className="micro-label text-ink-faint pt-1">Unrelated changes</div>
              <CodeBlock
                text={(check.evidence?.unrelated_changes || []).join('\n') || '(none reported)'}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TamperEvidence({ check }) {
  const findings = check.evidence?.findings || []
  if (!findings.length) {
    return (
      <div className="text-sm text-ink-faint">
        No tampering findings — no existing test was modified, removed, or bypassed.
      </div>
    )
  }
  return (
    <div className="space-y-2">
      <div className="micro-label text-ink-faint">
        Finding description (AST + diff heuristic verification)
      </div>
      {findings.map((f, i) => (
        <div key={i} className="border border-flagged/30 bg-flagged/5 rounded px-3 py-2">
          <div className="metric text-[11px] text-flagged-soft break-words">{f.trim()}</div>
        </div>
      ))}
    </div>
  )
}

function DiffPanel({ run }) {
  const diff = run.diff || ''
  const files = [...diff.matchAll(/^\+\+\+ b\/(.+)$/gm)].map((m) => m[1])
  const added = diff.split('\n').filter((l) => l.startsWith('+') && !l.startsWith('+++')).length
  const removed = diff.split('\n').filter((l) => l.startsWith('-') && !l.startsWith('---')).length
  return (
    <Collapsible
      label="Unified patch diff"
      right={`${files.length} file(s) modified • +${added} −${removed}`}
    >
      <div className="space-y-2">
        <div className="micro-label text-ink-faint">Files touched</div>
        <div className="flex flex-wrap gap-2">
          {files.map((f) => (
            <span key={f} className="metric text-[11px] px-2 py-0.5 rounded border border-edge bg-panel text-ink-dim">
              {f}
            </span>
          ))}
          {files.length === 0 && <span className="text-xs text-ink-faint">none</span>}
        </div>
        <CodeBlock text={diff} />
      </div>
    </Collapsible>
  )
}

export default function RunDetail({ run, setPage }) {
  if (!run) {
    return (
      <div className="p-10 text-center text-ink-faint">
        No run selected. Pick a run from{' '}
        <button className="text-verified-soft underline" onClick={() => setPage('history')}>
          Run History
        </button>
        .
      </div>
    )
  }

  const failed = (run.checks || []).filter((c) => !c.passed)
  const passedCount = (run.checks || []).length - failed.length
  const tamper = checkOf(run, 'T')
  const regression = checkOf(run, 'R')
  const blind = checkOf(run, 'B')
  const description = checkOf(run, 'D')
  const headline = failed.length
    ? `FLAGGED: ${failed.length} check${failed.length > 1 ? 's' : ''} failed (${failed
        .map((c) => c.name)
        .join(', ')}), ${passedCount} check${passedCount !== 1 ? 's' : ''} passed`
    : `VERIFIED: all ${passedCount} checks passed`

  const bannerTone = failed.length
    ? 'border-flagged/40 bg-flagged/10'
    : 'border-verified/40 bg-verified/10'
  const bannerText = failed.length ? 'text-flagged-soft' : 'text-verified-soft'

  return (
    <div className="p-6 space-y-5">
      <nav className="flex items-center gap-2 text-sm text-ink-dim">
        <button onClick={() => setPage('history')} className="inline-flex items-center gap-1.5 hover:text-ink">
          <Icon name="arrow_back" className="w-4 h-4" />
          Run History
        </button>
        <span className="text-ink-faint">/</span>
        <span className="metric text-ink">{run.scenario}</span>
      </nav>

      <div className={`border ${bannerTone} rounded-md px-5 py-4`}>
        <div className="flex items-center gap-3 flex-wrap">
          <VerdictBadge verdict={run.verdict} size="lg" />
          <span className={`text-lg font-medium ${bannerText}`}>{headline}</span>
          <div className="ml-auto flex items-center gap-3">
            <CheckStrip checks={run.checks} />
          </div>
        </div>
        <div className="mt-2 text-sm text-ink-dim">
          Target patch: <span className="metric">{run.scenario}</span>
          {SCENARIOS[run.scenario] ? ` — ${SCENARIOS[run.scenario].description}` : ''}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Statish
          icon="gavel"
          label="Tampering"
          value={tamper?.passed ? 'Clean' : 'Detected'}
          tone={tamper?.passed ? 'verified' : 'flagged'}
        />
        <Statish
          icon="check_circle"
          label="Pytest"
          value={
            regression?.counts?.total
              ? `${regression.counts.passed}/${regression.counts.total} passed`
              : '—'
          }
          tone={regression?.passed ? 'verified' : 'flagged'}
        />
        <Statish
          icon="task"
          label="Generated tests"
          value={
            blind?.counts?.generated_total != null
              ? `${blind.counts.generated_passed}/${blind.counts.generated_total} passed`
              : '—'
          }
          tone={blind?.passed ? 'verified' : 'flagged'}
        />
        <Statish
          icon="rule"
          label="Description"
          value={description?.passed ? 'Match' : 'Mismatch'}
          tone={description?.passed ? 'verified' : 'flagged'}
        />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KeyValue k="Scenario name" v={run.scenario} mono />
        <KeyValue k="Execution" v={run.backend === 'sandbox' ? 'Nebius Sandboxes' : 'Local Backend'} />
        <KeyValue
          k="Model"
          v={run.nemotron_mode === 'live' ? 'Nemotron (live)' : 'Recorded replay'}
        />
        <KeyValue k="Duration" v={fmtDuration(run.duration_ms)} mono />
      </div>

      <Panel
        title="Structured lab-report verification matrix"
        subtitle="Expand a check to see the evidence that produced its verdict."
        icon="fact_check"
      >
        <div className="space-y-3">
          {(run.checks || []).map((c) => (
            <CheckCard key={c.key} run={run} check={c} />
          ))}
        </div>
      </Panel>

      <div className="grid lg:grid-cols-2 gap-4">
        <Collapsible label="Ticket description" defaultOpen>
          <CodeBlock text={run.ticket} />
        </Collapsible>
        <DiffPanel run={run} />
      </div>
    </div>
  )
}

function Statish({ icon, label, value, tone }) {
  const color = tone === 'verified' ? 'text-verified-soft' : 'text-flagged-soft'
  const iconColor = tone === 'verified' ? 'text-verified' : 'text-flagged'
  return (
    <div className="border border-edge bg-surface rounded-md px-4 py-3">
      <div className="flex items-center gap-2 micro-label text-ink-faint">
        <Icon name={icon} className={iconColor} />
        <span>{label}</span>
      </div>
      <div className={`metric text-xl mt-1.5 ${color}`}>{value}</div>
    </div>
  )
}
