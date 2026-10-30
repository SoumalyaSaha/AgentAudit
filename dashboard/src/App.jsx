import React from 'react'
import Layout from './components/Layout'
import RunHistory from './pages/RunHistory'
import RunDetail from './pages/RunDetail'
import AgentHealth from './pages/AgentHealth'
import NewAudit from './pages/NewAudit'
import { latestRunFor, mostRecentRun } from './data'
import useRuns from './useRuns'

export default function App() {
  const [page, setPage] = React.useState('history')
  const [run, setRun] = React.useState(null)

  // One shared list for every run-selection path below: the Run Detail
  // default, scenario jumps and the history table all read the SAME data
  // (live when the runner is reachable, bundled snapshot when it is not).
  const { runs, source, loading, refresh } = useRuns()

  const openRun = React.useCallback((r) => {
    setRun(r)
    setPage('detail')
  }, [])

  const openScenario = React.useCallback(
    (scenario) => {
      setRun(latestRunFor(scenario, runs))
      setPage('detail')
    },
    [runs]
  )

  let content
  if (page === 'history')
    content = (
      <RunHistory
        setPage={setPage}
        openRun={openRun}
        allRuns={runs}
        source={source}
        loading={loading}
        refresh={refresh}
      />
    )
  else if (page === 'detail')
    content = (
      <RunDetail run={run || mostRecentRun(runs)} setPage={setPage} openScenario={openScenario} />
    )
  else if (page === 'health') content = <AgentHealth />
  // The runner appends the new record BEFORE it streams the result event, so
  // refresh() makes Run History and the Run Detail default include the run
  // that just finished — no manual Refresh needed.
  else content = <NewAudit setPage={setPage} openRun={openRun} onRunRecorded={refresh} />

  return (
    <Layout page={page} setPage={setPage}>
      {content}
    </Layout>
  )
}
