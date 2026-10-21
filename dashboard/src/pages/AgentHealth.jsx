import React from 'react'
import { Icon } from '../components/Layout'
import { Panel, StatCard } from '../components/ui'
import { CHECKS, ENGINE_INFO, RUNS, SCENARIOS } from '../data'
import {
  buildMatrix,
  computeBreakdown,
  computeScenarioStats,
  findingsCatalog,
} from '../analytics'

function cellLabel(key, passed) {
  if (passed === null) return 'NO DATA'
  if (key === 'T') return passed ? 'CLEAN' : 'FLAGGED'
  return passed ? 'PASSED' : 'FLAGGED'
}

export default function AgentHealth() {
  const matrix = React.useMemo(
    () => buildMatrix(RUNS, Object.keys(SCENARIOS), CHECKS),
    []
  )
  const stats = React.useMemo(() => computeScenarioStats(matrix), [matrix])
  const scenarioCount = stats.total

  // Failure-mode breakdown: counted from the matrix cells above.
  const breakdown = React.useMemo(
    () => computeBreakdown(matrix, CHECKS),
    [matrix]
  )

  const catalog = React.useMemo(() => findingsCatalog(RUNS), [])

  // System health, all derived from the recorded runs.
  const hasLocal = RUNS.some((r) => r.backend === 'local')
  const sandboxRuns = RUNS.filter((r) => r.backend === 'sandbox')
  const sandboxConnected = sandboxRuns.some((r) => r.verdict === 'VERIFIED')
  const liveRuns = RUNS.filter((r) => r.nemotron_mode === 'live')
  const modelDispatch = liveRuns.length ? 'LIVE NEMOTRON' : 'RECORDED REPLAY'
  const executionMode = sandboxRuns.length ? 'LOCAL + SANDBOX' : 'LOCAL ONLY'

  return (
    <div className="p-6 space-y-5">
      <header>
        <div className="micro-label text-ink-faint">Continuous aggregate audit analytics</div>
        <h1 className="text-2xl font-semibold tracking-tight mt-1">
          Agent Performance &amp; Verification Health
        </h1>
        <p className="text-sm text-ink-dim mt-0.5 max-w-3xl">
          Every value on this page is computed from the recorded runs in{' '}
          <span className="metric text-ink">run_history.json</span> — no sample data, no
          mockup literals.
        </p>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          icon="dataset"
          label="Demo Scenarios"
          value={scenarioCount}
          sub="Evaluated"
          tone="verified"
        />
        <StatCard
          icon="rule"
          label="Pass Rate"
          value={`${stats.passRate}%`}
          sub={`${stats.clean} of ${stats.total} clean`}
          tone="verified"
        />
        <StatCard
          icon="warning"
          label="Quarantined Scenarios"
          value={stats.flagged}
          sub="Identified tampering/regressions"
          tone="flagged"
          valueClass="text-flagged-soft"
        />
        <StatCard
          icon="sync"
          label="Execution Mode"
          value={executionMode}
          sub={modelDispatch === 'LIVE NEMOTRON' ? 'Live inference' : 'Deterministic replay'}
        />
      </div>

      <Panel
        title="Scenario Detection Matrix"
        subtitle={`${scenarioCount} demo scenarios — cell = that check's real result for the latest run of that scenario.`}
        icon="grid_view"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-edge text-left">
                <th className="px-3 py-2 micro-label text-ink-faint font-semibold">Scenario</th>
                {CHECKS.map((c) => (
                  <th key={c.key} className="px-3 py-2 micro-label text-ink-faint font-semibold">
                    {c.name.replace(' Coverage', '').replace(' Match', '')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.map((row) => (
                <tr key={row.scenario} className="border-b border-edge/60 last:border-0">
                  <td className="px-3 py-2.5">
                    <div className="metric text-ink">{row.scenario}</div>
                    <div className="text-xs text-ink-faint max-w-md truncate">
                      {SCENARIOS[row.scenario]?.description}
                    </div>
                  </td>
                  {row.cells.map((cell) => {
                    const passed = cell.passed
                    const cls =
                      passed === null
                        ? 'bg-surface-2 border-edge text-ink-faint'
                        : passed
                          ? 'bg-verified/10 border-verified/35 text-verified-soft'
                          : 'bg-flagged/12 border-flagged/40 text-flagged-soft'
                    return (
                      <td key={cell.key} className="px-3 py-2.5">
                        <span
                          className={`metric text-[10px] px-2 py-0.5 rounded border whitespace-nowrap ${cls}`}
                        >
                          {cellLabel(cell.key, passed)}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-ink-faint mt-3">
          Matrix benchmark:{' '}
          <span className="metric text-ink-dim">
            {breakdown.reduce((acc, b) => acc + b.caught, 0)} failure cells across{' '}
            {scenarioCount} scenarios
          </span>
        </p>
      </Panel>

      <Panel
        title="Failure Mode Breakdown"
        subtitle="Derived from the matrix above — the two panels are the same data."
        icon="troubleshoot"
      >
        <div className="space-y-3">
          {breakdown.map((b, i) => (
            <div
              key={b.key}
              className="flex items-center gap-4 border border-edge bg-panel/40 rounded px-4 py-3"
            >
              <span className="metric text-sm text-ink-faint w-6">
                {String(i + 1).padStart(2, '0')}.
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-sm text-ink">{b.name}</div>
                <div className="text-xs text-ink-faint">
                  {b.uses_model
                    ? 'Nemotron-generated adversarial coverage'
                    : 'Static diff analysis of the patched test suite'}
                </div>
              </div>
              <div className="metric text-sm text-ink-dim whitespace-nowrap">
                caught in {b.caught} of {b.total} scenarios
              </div>
              <div className="flex gap-1 w-40">
                {matrix.map((row) => {
                  const cell = row.cells.find((c) => c.key === b.key)
                  const failed = cell && cell.passed === false
                  return (
                    <span
                      key={row.scenario}
                      title={`${row.scenario}: ${cellLabel(b.key, cell?.passed ?? null)}`}
                      className={`h-6 flex-1 rounded-sm border ${
                        failed
                          ? 'bg-flagged/25 border-flagged/45'
                          : 'bg-verified/10 border-verified/30'
                      }`}
                    />
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel
        title="System Health & Engine Infrastructure"
        subtitle="Derived from the recorded runs."
        icon="developer_board"
      >
        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
          <HealthCell
            title="Local Backend"
            value={hasLocal ? 'ONLINE' : 'NOT RUN'}
            tone={hasLocal ? 'verified' : 'default'}
            lines={[
              `${RUNS.filter((r) => r.backend === 'local').length} local run(s) recorded`,
              'Filesystem snapshot backend, no isolation',
            ]}
          />
          <HealthCell
            title="Nebius Sandboxes"
            value={sandboxConnected ? 'CONNECTED' : 'NOT RUN'}
            tone={sandboxConnected ? 'verified' : 'default'}
            lines={[
              `${sandboxRuns.length} sandbox run(s) recorded`,
              sandboxConnected
                ? 'A sandbox-backed run completed successfully'
                : 'No successful sandbox-backed run in history',
            ]}
          />
          <HealthCell
            title="Model Dispatch"
            value={modelDispatch}
            tone="default"
            lines={[
              `Nemotron ${ENGINE_INFO.models.super}`,
              liveRuns.length
                ? `${liveRuns.length} live inference run(s)`
                : 'No live inference run recorded (fixtures replayed)',
            ]}
          />
          <HealthCell
            title="Execution Mode"
            value={executionMode}
            tone="default"
            lines={[
              `${RUNS.length} total run(s) in history`,
              'LocalBackend: offline, deterministic',
            ]}
          />
        </div>
      </Panel>

      <Panel
        title="Findings Library & Agent Tampering Catalog"
        subtitle="Tamper kinds actually detected in the recorded runs."
        icon="bug"
      >
        {catalog.length === 0 ? (
          <p className="text-sm text-ink-faint">No tampering findings recorded.</p>
        ) : (
          <div className="grid md:grid-cols-2 gap-3">
            {catalog.map((f) => (
              <div key={f.kind} className="border border-edge bg-panel/40 rounded px-4 py-3">
                <div className="flex items-center gap-2">
                  <Icon name="bug" className="text-flagged-soft" />
                  <span className="text-sm text-ink metric">{f.kind}</span>
                  <span className="metric text-[10px] ml-auto px-2 py-0.5 rounded border border-flagged/40 bg-flagged/10 text-flagged-soft">
                    caught {f.count} time{f.count === 1 ? '' : 's'}
                  </span>
                </div>
                <div className="text-xs text-ink-faint mt-1">
                  seen in {f.runCount} run{f.runCount === 1 ? '' : 's'} across{' '}
                  {f.scenarioList.length} scenario{f.scenarioList.length === 1 ? '' : 's'}:{' '}
                  {f.scenarioList.join(', ')}
                </div>
                <div className="metric text-[11px] text-ink-dim mt-2 break-words">{f.example}</div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  )
}

function HealthCell({ title, value, tone, lines }) {
  const color =
    tone === 'verified' ? 'text-verified-soft' : 'text-ink-dim'
  return (
    <div className="border border-edge bg-panel/40 rounded px-4 py-3">
      <div className="micro-label text-ink-faint">{title}</div>
      <div className={`metric text-sm mt-1 ${color}`}>{value}</div>
      <div className="text-xs text-ink-faint mt-1.5 space-y-0.5">
        {lines.map((l, i) => (
          <div key={i}>{l}</div>
        ))}
      </div>
    </div>
  )
}
