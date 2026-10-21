/**
 * Server-render smoke test: renders every page to static HTML in Node
 * and fails loudly if any component throws. This catches broken
 * imports, bad hooks and undefined data access without a browser.
 *
 *     npm run verify:render
 */
import { renderToString } from 'react-dom/server'
import { createElement } from 'react'

import Layout from '../src/components/Layout.jsx'
import RunHistory from '../src/pages/RunHistory.jsx'
import RunDetail from '../src/pages/RunDetail.jsx'
import AgentHealth from '../src/pages/AgentHealth.jsx'
import NewAudit from '../src/pages/NewAudit.jsx'
import { RUNS, latestRunFor } from '../src/data.js'

const noop = () => {}
const errors = []

function check(name, element) {
  try {
    const html = renderToString(element)
    if (!html || html.length < 50) {
      errors.push(`${name}: rendered empty output`)
      console.log(`  FAIL  ${name}: empty output`)
      return
    }
    console.log(`  ok    ${name} rendered (${html.length} bytes)`)
  } catch (e) {
    errors.push(`${name}: ${e.message}`)
    console.log(`  FAIL  ${name}: ${e.message}`)
  }
}

console.log('\nPage render smoke test:\n')

check(
  'Run History',
  createElement(Layout, { page: 'history', setPage: noop }, createElement(RunHistory, { setPage: noop, openRun: noop }))
)

const sample = latestRunFor('bad-agent-patch', RUNS) || RUNS[0]
check(
  'Run Detail',
  createElement(Layout, { page: 'detail', setPage: noop }, createElement(RunDetail, { run: sample, setPage: noop, openScenario: noop }))
)

check(
  'Agent Health',
  createElement(Layout, { page: 'health', setPage: noop }, createElement(AgentHealth))
)

check(
  'New Audit',
  createElement(Layout, { page: 'new', setPage: noop }, createElement(NewAudit, { setPage: noop, openRun: noop }))
)

// Spot-check that the rendered history contains REAL values from the data.
const html = renderToString(
  createElement(Layout, { page: 'history', setPage: noop }, createElement(RunHistory, { setPage: noop, openRun: noop }))
)
const scenarioPresent = RUNS.some((r) => html.includes(r.scenario))
if (!scenarioPresent) errors.push('Run History: no recorded scenario name rendered')
else console.log('  ok    Run History renders real scenario names from run_history.json')

console.log(
  `\n${errors.length === 0 ? 'ALL PAGES RENDERED' : errors.length + ' RENDER FAILURE(S)'}\n`
)
process.exit(errors.length === 0 ? 0 : 1)
