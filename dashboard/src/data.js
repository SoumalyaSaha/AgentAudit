import runsRaw from '../data/run_history.json'
import engineInfoRaw from '../data/engine_info.json'

/**
 * All dashboard numbers come from these two generated files. Nothing in
 * the UI is hardcoded: run_history.json is written by the Python engine
 * (engine/history.py) as runs actually execute, and engine_info.json
 * carries the engine's own constants (model names, scenario catalog).
 */
export const RUNS = runsRaw
export const ENGINE_INFO = engineInfoRaw

export const SCENARIOS = ENGINE_INFO.scenarios || {}
export const CHECKS = ENGINE_INFO.checks || []

export const CHECK_KEYS = CHECKS.map((c) => c.key)
export const CHECK_NAMES = Object.fromEntries(CHECKS.map((c) => [c.key, c.name]))

/** Checks that call Nemotron (never shown as a model badge on Check A). */
export const CHECK_USES_MODEL = Object.fromEntries(
  CHECKS.map((c) => [c.key, c.uses_model])
)

export function fmtDuration(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export function fmtTimestamp(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

export function engineLabel(run) {
  return run.backend === 'sandbox' ? 'Nebius Sandboxes' : 'Local Backend'
}

export function modeLabel(run) {
  return run.nemotron_mode === 'live' ? 'Live Nemotron' : 'Recorded replay'
}

/** Latest run per scenario, for single-scenario views (Run Detail). */
export function latestRunFor(scenario, runs = RUNS) {
  const matches = runs.filter((r) => r.scenario === scenario)
  if (!matches.length) return null
  return matches.reduce((a, b) => (a.timestamp >= b.timestamp ? a : b))
}

export function checkOf(run, key) {
  return (run.checks || []).find((c) => c.key === key) || null
}

/** Tamper kinds actually observed across all runs, counted from evidence. */
export function findingsCatalog(runs = RUNS) {
  const catalog = new Map()
  for (const run of runs) {
    const tamper = checkOf(run, 'T')
    if (!tamper) continue
    for (const line of tamper.evidence?.findings || []) {
      // findings look like: "  line 10: modified_assertion -- was: `...`  now: `...`"
      const m = line.match(/:\s*([a-z_]+)\s+--\s+was:/)
      if (!m) continue
      const kind = m[1]
      const entry = catalog.get(kind) || { kind, count: 0, runs: new Set(), example: line.trim() }
      entry.count += 1
      entry.runs.add(run.scenario)
      catalog.set(kind, entry)
    }
  }
  return [...catalog.values()].sort((a, b) => b.count - a.count)
}
