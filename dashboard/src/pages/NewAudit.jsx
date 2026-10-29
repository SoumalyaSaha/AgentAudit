import React from 'react'
import { Icon } from '../components/Layout'
import { CheckStrip, VerdictBadge } from '../components/ui'
import { SCENARIOS, fmtDuration } from '../data'

const API = '/api'

export default function NewAudit({ setPage, openRun }) {
  const [mode, setMode] = React.useState('scenario')
  const [scenario, setScenario] = React.useState('bad-agent-patch')
  const [diff, setDiff] = React.useState('')
  const [ticket, setTicket] = React.useState('')
  const [events, setEvents] = React.useState([])
  const [running, setRunning] = React.useState(false)
  const [result, setResult] = React.useState(null)
  const [error, setError] = React.useState(null)

  async function start() {
    setEvents([])
    setResult(null)
    setError(null)
    setRunning(true)
    try {
      const body =
        mode === 'scenario'
          ? { scenario }
          : { scenario: 'custom-patch', diff, ticket: ticket || undefined }

      const res = await fetch(`${API}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.error || `HTTP ${res.status}`)
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.trim()) continue
          const evt = JSON.parse(line)
          setEvents((e) => [...e, evt])
          if (evt.type === 'result') setResult(evt)
          if (evt.type === 'error') setError(evt.error)
        }
      }
    } catch (e) {
      setError(String(e.message || e))
    } finally {
      setRunning(false)
    }
  }

  const checkEvents = events.filter((e) => e.type === 'check_done')
  const started = events.find((e) => e.type === 'started')
  const pipeline = [
    { key: 'T', label: 'Test Tampering' },
    { key: 'R', label: 'Baseline Regression' },
    { key: 'B', label: 'Blind-Spot Coverage' },
    { key: 'D', label: 'Description Match' },
  ]

  return (
    <div className="p-6 space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Run New Agent Verification Audit</h1>
        <p className="text-sm text-ink-dim mt-0.5 max-w-3xl">
          Executes the four checks locally against the demo repo and streams real per-check
          progress.
        </p>
      </header>

      <div className="grid lg:grid-cols-2 gap-4">
        <section className="border border-edge bg-surface rounded-2xl shadow-card">
          <header className="px-4 py-2.5 border-b border-edge bg-[rgba(255,255,255,0.5)] flex items-center gap-2">
            <button
              onClick={() => setMode('scenario')}
              className={`metric text-[11px] px-2.5 py-1 rounded border ${
                mode === 'scenario'
                  ? 'bg-surface-2 border-edge-strong text-ink'
                  : 'border-edge text-ink-dim'
              }`}
            >
              Scenario
            </button>
            <button
              onClick={() => setMode('paste')}
              className={`metric text-[11px] px-2.5 py-1 rounded border ${
                mode === 'paste'
                  ? 'bg-surface-2 border-edge-strong text-ink'
                  : 'border-edge text-ink-dim'
              }`}
            >
              Paste Diff
            </button>
          </header>

          <div className="p-4 space-y-3">
            {mode === 'scenario' ? (
              <>
                <label className="micro-label text-ink-faint block">Select a scenario</label>
                <select
                  value={scenario}
                  onChange={(e) => setScenario(e.target.value)}
                  className="w-full metric text-sm bg-canvas border border-edge rounded px-3 py-2 text-ink outline-none focus:border-edge-strong"
                >
                  {Object.entries(SCENARIOS).map(([name, meta]) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-ink-faint">
                  {SCENARIOS[scenario]?.description}
                </p>
              </>
            ) : (
              <>
                <label className="micro-label text-ink-faint block">
                  Unified diff (applied to a throwaway copy of demo_repo)
                </label>
                <textarea
                  value={diff}
                  onChange={(e) => setDiff(e.target.value)}
                  rows={10}
                  placeholder={'--- a/discount.py\n+++ b/discount.py\n@@ -17,6 +17,6 @@ ...'}
                  className="w-full metric text-[11px] bg-canvas border border-edge rounded px-3 py-2 text-ink placeholder:text-ink-faint outline-none focus:border-edge-strong"
                />
                <label className="micro-label text-ink-faint block">Ticket (optional)</label>
                <textarea
                  value={ticket}
                  onChange={(e) => setTicket(e.target.value)}
                  rows={3}
                  placeholder="Paste a ticket description..."
                  className="w-full metric text-[11px] bg-canvas border border-edge rounded px-3 py-2 text-ink placeholder:text-ink-faint outline-none focus:border-edge-strong"
                />
              </>
            )}

            <button
              onClick={start}
              disabled={running || (mode === 'paste' && !diff.trim())}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-pending text-[#120e0c] text-sm font-semibold hover:bg-[#fbbf24] active:translate-y-px disabled:opacity-40 disabled:hover:bg-pending transition-colors focus-ring"
            >
              <Icon name={running ? 'stop' : 'play'} />
              {running ? 'Running…' : 'Run Audit'}
            </button>
          </div>
        </section>

        <section className="border border-edge bg-surface rounded-2xl shadow-card">
          <header className="px-4 py-2.5 border-b border-edge bg-[rgba(255,255,255,0.5)] flex items-center gap-2">
            <Icon name="monitoring" className="text-ink-faint" />
            <h2 className="text-sm font-medium">Verification Pipeline State</h2>
            {result && (
              <span className="ml-auto">
                <VerdictBadge verdict={result.verdict} />
              </span>
            )}
          </header>

          <div className="p-4 space-y-2">
            {pipeline.map((p) => {
              const done = checkEvents.find((e) => e.key === p.key)
              const active = running && !done && checkEvents.length === pipeline.findIndex((x) => x.key === p.key)
              return (
                <div
                  key={p.key}
                  className={`flex items-center gap-3 border rounded-lg px-3 py-2 ${
                    done
                      ? done.passed
                        ? 'border-[#6ee7b7] bg-[#d1fae5]'
                        : 'border-[#fca5a5] bg-[#fee2e2]'
                      : 'border-edge bg-[rgba(255,255,255,0.5)]'
                  }`}
                >
                  <span className="metric text-[10px] text-ink-faint w-4">{p.key}</span>
                  <span className="text-sm text-ink-dim flex-1">{p.label}</span>
                  {done ? (
                    <>
                      <span
                        className={`metric text-[10px] ${
                          done.passed ? 'text-[#065f46]' : 'text-[#991b1b]'
                        }`}
                      >
                        {done.passed ? 'PASSED' : 'FAILED'}
                      </span>
                      <span className="metric text-[11px] text-ink-faint w-14 text-right">
                        {fmtDuration(done.duration_ms)}
                      </span>
                    </>
                  ) : (
                    <span className="micro-label text-ink-faint">
                      {active ? 'running…' : 'pending'}
                    </span>
                  )}
                </div>
              )
            })}

            {result && (
              <div className="mt-3 border-t border-edge pt-3 space-y-2">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="metric text-sm text-ink-dim">
                    Total {fmtDuration(result.duration_ms)}
                  </span>
                  <CheckStrip
                    checks={(result.checks || []).map((c) => ({
                      key: c.key,
                      name: c.name,
                      passed: c.passed,
                    }))}
                  />
                  <button
                    onClick={() => openRun(result.run)}
                    className="ml-auto text-xs text-ink-dim hover:text-verified-soft inline-flex items-center gap-1.5"
                  >
                    Open in Run Detail
                    <Icon name="arrow_forward" className="w-4 h-4" />
                  </button>
                </div>
                {(result.notes || []).map((n, i) => (
                  <p key={i} className="text-xs text-ink-faint">
                    {n}
                  </p>
                ))}
              </div>
            )}

            {error && (
              <div className="mt-3 border border-flagged/40 bg-flagged/10 rounded px-3 py-2 text-sm text-flagged-soft">
                {error}
              </div>
            )}

            {!result && !running && !error && (
              <p className="text-xs text-ink-faint pt-2">
                {started
                  ? 'Run finished without a result event.'
                  : 'Pick a scenario and press Run Audit. Progress streams back per check.'}
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
