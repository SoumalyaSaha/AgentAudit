/**
 * Pure analytics for the Agent Health page.
 *
 * Deliberately dependency-free (no React, no JSON imports) so the exact
 * same code can run in the browser AND in the Node verification script
 * (dashboard/scripts/verify_analytics.mjs). That is what guarantees the
 * detection matrix and the failure-mode breakdown can never disagree:
 * the breakdown is counted from the matrix cells themselves.
 */

/** Latest run per scenario (runs are append-ordered, so the last wins). */
export function latestRunFor(scenario, runs) {
  const matches = runs.filter((r) => r.scenario === scenario)
  if (!matches.length) return null
  return matches.reduce((a, b) => (a.timestamp >= b.timestamp ? a : b))
}

/**
 * Build the scenario x check detection matrix from the recorded runs.
 * Each cell is that check's real pass/fail for the latest run of the
 * scenario -- never a hardcoded pattern.
 */
export function buildMatrix(runs, scenarioNames, checks) {
  return scenarioNames.map((scenario) => {
    const run = latestRunFor(scenario, runs)
    const cells = checks.map((c) => {
      const check = (run?.checks || []).find((x) => x.key === c.key) || null
      return {
        key: c.key,
        name: c.name,
        passed: check ? check.passed : null,
        missing: !check,
      }
    })
    return {
      scenario,
      run,
      cells,
      clean: run ? cells.every((c) => c.passed) : false,
      flagged: run ? cells.some((c) => !c.passed) : false,
    }
  })
}

/**
 * Failure-mode breakdown: for each check, how many scenarios it CAUGHT.
 * Counted directly from the matrix cells above -- the single source of
 * truth -- so the two panels always agree.
 */
export function computeBreakdown(matrix, checks) {
  return checks.map((c) => {
    const caught = matrix.filter((row) =>
      row.cells.some((cell) => cell.key === c.key && cell.passed === false)
    ).length
    const total = matrix.length
    return {
      ...c,
      caught,
      total,
      rate: total ? Math.round((caught / total) * 100) : 0,
    }
  })
}

/** Aggregate scenario-level stats (pass rate, quarantined count). */
export function computeScenarioStats(matrix) {
  const total = matrix.length
  const clean = matrix.filter((r) => r.clean).length
  const flagged = matrix.filter((r) => r.flagged).length
  return {
    total,
    clean,
    flagged,
    passRate: total ? Math.round((clean / total) * 100) : 0,
  }
}

/** Tamper kinds actually detected, counted from real Check A evidence. */
export function findingsCatalog(runs) {
  const catalog = new Map()
  for (const run of runs) {
    const tamper = (run.checks || []).find((c) => c.key === 'T')
    if (!tamper) continue
    for (const line of tamper.evidence?.findings || []) {
      // findings look like: "  line 10: modified_assertion -- was: `...`  now: `...`"
      const m = line.match(/:\s*([a-z_]+)\s+--\s+was:/)
      if (!m) continue
      const kind = m[1]
      const entry =
        catalog.get(kind) ||
        { kind, count: 0, runs: new Set(), scenarios: new Set(), example: line.trim() }
      entry.count += 1
      entry.runs.add(run.id || `${run.scenario}-${run.timestamp}`)
      entry.scenarios.add(run.scenario)
      catalog.set(kind, entry)
    }
  }
  return [...catalog.values()]
    .map((e) => ({
      ...e,
      runCount: e.runs.size,
      scenarioList: [...e.scenarios],
    }))
    .sort((a, b) => b.count - a.count)
}
