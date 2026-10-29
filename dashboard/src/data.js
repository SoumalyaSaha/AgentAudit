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

/** Most recent run overall — the default target for the Run Detail view,
 *  so the nav item never lands on an empty page. */
export function mostRecentRun(runs = RUNS) {
  if (!runs.length) return null
  return runs.reduce((a, b) => (a.timestamp >= b.timestamp ? a : b))
}

export function checkOf(run, key) {
  return (run.checks || []).find((c) => c.key === key) || null
}

// The findings catalog lives in ./analytics.js so the exact same code
// runs in the browser AND in scripts/verify_analytics.mjs. Re-exported
// here for convenience; there is deliberately only ONE implementation.
export { findingsCatalog } from './analytics'
