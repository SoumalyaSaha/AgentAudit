import React from 'react'
import { Icon } from '../components/Layout'
import { CheckStrip, StatCard, VerdictBadge } from '../components/ui'
import { RUNS, SCENARIOS, fmtDuration, fmtTimestamp, modeLabel } from '../data'

export default function RunHistory({ setPage, openRun }) {
  const [tab, setTab] = React.useState('all')
  const [query, setQuery] = React.useState('')
  const [sort, setSort] = React.useState('newest')

  const runs = React.useMemo(() => {
    let list = [...RUNS]
    if (tab === 'verified') list = list.filter((r) => r.verdict === 'VERIFIED')
    if (tab === 'flagged') list = list.filter((r) => r.verdict === 'FLAGGED')
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      list = list.filter(
        (r) =>
          r.scenario.toLowerCase().includes(q) ||
          (SCENARIOS[r.scenario]?.description || '').toLowerCase().includes(q)
      )
    }
    list.sort((a, b) =>
      sort === 'newest'
        ? b.timestamp.localeCompare(a.timestamp)
        : a.timestamp.localeCompare(b.timestamp)
    )
    return list
  }, [tab, query, sort])

  const total = RUNS.length
  const verified = RUNS.filter((r) => r.verdict === 'VERIFIED').length
  const flagged = RUNS.filter((r) => r.verdict === 'FLAGGED').length
  const avg = total
    ? RUNS.reduce((acc, r) => acc + (r.duration_ms || 0), 0) / total
    : 0

  return (
    <div className="p-6 space-y-5">
      <header className="flex items-end gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Audit Verification Feed</h1>
          <p className="text-sm text-ink-dim mt-0.5">
            Every row is a completed AgentAudit run recorded from real executions.
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setPage('new')}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-pending text-[#120e0c] text-xs font-semibold hover:bg-[#fbbf24] active:translate-y-px transition-colors focus-ring"
          >
            <Icon name="bolt" />
            Run New Audit
          </button>
        </div>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard icon="dataset" label="Total" value={total} sub="Recorded runs" />
        <StatCard
          icon="verified"
          label="Verified"
          value={verified}
          sub="All checks passed"
          tone="verified"
          valueClass="text-verified-soft"
        />
        <StatCard
          icon="warning"
          label="Flagged"
          value={flagged}
          sub="One or more checks failed"
          tone="flagged"
          valueClass="text-flagged-soft"
        />
        <StatCard
          icon="timer"
          label="Avg Duration"
          value={fmtDuration(avg)}
          sub="Wall clock per run"
        />
      </div>

      <div className="border border-edge bg-surface rounded-2xl shadow-card overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-edge flex-wrap">
          {[
            { key: 'all', label: 'All' },
            { key: 'verified', label: 'Verified' },
            { key: 'flagged', label: 'Flagged' },
          ].map((t) => {
            const count =
              t.key === 'all'
                ? RUNS.length
                : RUNS.filter((r) => r.verdict.toLowerCase() === t.key).length
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`metric text-[11px] px-2.5 py-1 rounded border transition-colors ${
                  tab === t.key
                    ? 'bg-surface-2 border-edge-strong text-ink'
                    : 'border-edge text-ink-dim hover:text-ink'
                }`}
              >
                {t.label} {count}
              </button>
            )
          })}

          <div className="flex items-center gap-2 ml-3 border border-edge rounded px-2 py-1">
            <Icon name="search" className="text-ink-faint" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by scenario"
              className="bg-transparent outline-none text-sm w-48 placeholder:text-ink-faint"
            />
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <span className="micro-label text-ink-faint">Sort runs by</span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="metric text-[11px] bg-[rgba(255,255,255,0.55)] border border-edge rounded px-2 py-1 text-ink-dim"
            >
              <option value="newest">Timestamp (newest)</option>
              <option value="oldest">Timestamp (oldest)</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-edge text-left">
                {['Verdict', 'Scenario / Patch', 'Diagnostic Checks', 'Engine & Environment', 'Duration', 'Timestamp', ''].map(
                  (h, i) => (
                    <th
                      key={i}
                      className="px-4 py-2 micro-label text-ink-faint font-semibold whitespace-nowrap"
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {runs.map((run, i) => (
                <tr
                  key={run.id || `${run.scenario}-${run.timestamp}`}
                  className={`${i % 2 === 1 ? 'row-alt' : ''} border-b border-edge/60 last:border-0 hover:bg-[rgba(147,197,253,0.3)] transition-colors`}
                >
                  <td className="px-4 py-3">
                    <VerdictBadge verdict={run.verdict} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="metric txt">{run.scenario}</div>
                    <div className="text-xs txt-dim max-w-lg truncate">
                      {SCENARIOS[run.scenario]?.description || '—'}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <CheckStrip checks={run.checks} />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="metric text-[11px] txt">
                      {run.backend === 'sandbox' ? 'Nebius Sandboxes' : 'Local Backend'}
                    </div>
                    <div className="metric text-[11px] txt-dim">
                      {modeLabel(run)}
                    </div>
                  </td>
                  <td className="px-4 py-3 metric txt whitespace-nowrap">
                    {fmtDuration(run.duration_ms)}
                  </td>
                  <td className="px-4 py-3 metric text-[11px] txt-dim whitespace-nowrap">
                    {fmtTimestamp(run.timestamp)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => openRun(run)}
                      className="inline-flex items-center gap-1.5 text-xs txt-dim hover:text-verified transition-colors focus-ring"
                    >
                      Inspect
                      <Icon name="arrow_forward" className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-ink-faint text-sm">
                    No runs match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <footer className="px-4 py-2.5 border-t border-edge text-xs text-ink-faint flex items-center gap-2">
          <Icon name="dataset" />
          <span>
            Showing {runs.length} of {RUNS.length} recorded runs
          </span>
        </footer>
      </div>
    </div>
  )
}
