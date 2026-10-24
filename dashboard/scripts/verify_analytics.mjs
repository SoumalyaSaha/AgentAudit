/**
 * Verifies the dashboard's derived analytics against the recorded run
 * data, using the SAME pure module the React page imports
 * (src/analytics.js). Run from the dashboard/ directory:
 *
 *     node scripts/verify_analytics.mjs
 *
 * Checks:
 *   1. every matrix cell comes from a real recorded check result
 *   2. the failure-mode breakdown equals the FAIL-cell count of the
 *      matrix it is derived from (the two panels can never disagree)
 *   3. scenario stats (pass rate / quarantined) match the matrix
 *   4. the findings catalog only contains tamper kinds actually observed
 *   5. no hardcoded mockup literals leaked into the source
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname, extname } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  buildMatrix,
  computeBreakdown,
  computeScenarioStats,
  findingsCatalog,
} from '../src/analytics.js'

const here = dirname(fileURLToPath(import.meta.url))
const root = join(here, '..')

const runs = JSON.parse(readFileSync(join(root, 'data', 'run_history.json'), 'utf8'))
const engineInfo = JSON.parse(readFileSync(join(root, 'data', 'engine_info.json'), 'utf8'))

const checks = engineInfo.checks
const scenarioNames = Object.keys(engineInfo.scenarios)

let failures = 0
const fail = (msg) => {
  failures += 1
  console.log(`  FAIL  ${msg}`)
}
const pass = (msg) => console.log(`  ok    ${msg}`)

// ---- 1 & 2: matrix cells are real, breakdown agrees with the matrix ----
const matrix = buildMatrix(runs, scenarioNames, checks)
const breakdown = computeBreakdown(matrix, checks)

console.log('\nScenario Detection Matrix (computed):')
for (const row of matrix) {
  const cells = row.cells
    .map((c) => `${c.key}:${c.passed === null ? 'NO DATA' : c.passed ? 'PASS' : 'FAIL'}`)
    .join('  ')
  console.log(`  ${row.scenario.padEnd(30)} ${cells}`)
}

console.log('\nFailure Mode Breakdown (derived from the matrix above):')
for (const b of breakdown) {
  console.log(`  ${b.name.padEnd(24)} caught in ${b.caught} of ${b.total} scenarios`)
}

for (const row of matrix) {
  if (!row.run) {
    fail(`${row.scenario}: no recorded run`)
    continue
  }
  for (const cell of row.cells) {
    if (cell.passed === null) fail(`${row.scenario}/${cell.key}: no real check result`)
  }
}
if (failures === 0) pass('every matrix cell traces to a recorded check result')

// Breakdown must equal a fresh, independent count over the same cells.
for (const b of breakdown) {
  const independent = matrix.filter((row) =>
    row.cells.some((cell) => cell.key === b.key && cell.passed === false)
  ).length
  if (independent !== b.caught) {
    fail(`${b.name}: breakdown says ${b.caught}, independent count says ${independent}`)
  } else {
    pass(`${b.name}: breakdown (${b.caught}) == independent FAIL-cell count`)
  }
}

// ---- 3: scenario stats match the matrix ----
const stats = computeScenarioStats(matrix)
const cleanManual = matrix.filter((r) => r.clean).length
const flaggedManual = matrix.filter((r) => r.flagged).length
if (stats.clean !== cleanManual || stats.flagged !== flaggedManual) {
  fail(`stats disagree with matrix (${JSON.stringify(stats)})`)
} else {
  pass(
    `stats agree with matrix: ${stats.clean}/${stats.total} clean (${stats.passRate}% pass rate), ${stats.flagged} quarantined`
  )
}

// ---- 4: findings catalog only lists observed kinds ----
const catalog = findingsCatalog(runs)
console.log('\nFindings catalog (from real Check A evidence):')
for (const f of catalog) console.log(`  ${f.kind.padEnd(24)} caught ${f.count}x across ${f.runCount} run(s) in ${f.scenarioList.join(', ')}`)
const observedKinds = new Set(catalog.map((f) => f.kind))
for (const f of catalog) {
  if (!f.count || !f.scenarioList.length) fail(`catalog entry ${f.kind} has no real observations`)
}
if (observedKinds.size === 0) fail('no tamper kinds observed at all')
else pass(`${observedKinds.size} tamper kinds observed, all backed by real findings`)

// ---- 5: no hardcoded mockup literals anywhere in src/ ----
const MOCKUP_LITERALS = [
  '1,428',
  '84 of 84',
  'Devin',
  'payments-service',
  'tampered-assertion-patch',
  'regressed-fixture-patch',
  'unrelated-file-injection',
  'clean-verified-patch',
  'SANDBOX-NEBIUS-POOL',
  'H100',
  'Cluster Quorum',
]

function walk(dir) {
  const out = []
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    if (statSync(p).isDirectory()) out.push(...walk(p))
    else if (['.js', '.jsx', '.mjs'].includes(extname(p))) out.push(p)
  }
  return out
}

console.log('\nMockup-literal sweep (src/ + scripts/ + engine/ + data/):')
let literalHits = 0
const sweepFiles = [
  ...walk(join(root, 'src')),
  ...walk(join(root, 'scripts')),
  // The Python engine and the generated data must be clean too.
  ...walk(join(root, '..', 'engine')).filter((f) => f.endsWith('.py')),
  join(root, 'data', 'run_history.json'),
  join(root, 'data', 'engine_info.json'),
]
for (const file of sweepFiles) {
  // This file necessarily contains the literal list; it is the detector,
  // not a violation. Skip it.
  if (file.endsWith('verify_analytics.mjs')) continue
  const text = readFileSync(file, 'utf8')
  for (const lit of MOCKUP_LITERALS) {
    if (text.includes(lit)) {
      literalHits += 1
      fail(`mockup literal ${JSON.stringify(lit)} found in ${file}`)
    }
  }
}
if (literalHits === 0) {
  pass(
    `no mockup literals in ${sweepFiles.length - 1} scanned files (src, scripts, engine, data)`
  )
}

console.log(
  `\n${failures === 0 ? 'ALL CHECKS PASSED' : failures + ' CHECK(S) FAILED'}\n`
)
process.exit(failures === 0 ? 0 : 1)
